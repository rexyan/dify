from typing import Any, cast

from core.app.app_config.entities import DatasetRetrieveConfigEntity
from core.app.entities.app_invoke_entities import ModelConfigWithCredentialsEntity
from core.entities.agent_entities import PlanningStrategy
from core.entities.model_entities import ModelStatus
from core.errors.error import ModelCurrentlyNotSupportError, ProviderTokenNotInitError, QuotaExceededError
from core.model_manager import ModelInstance, ModelManager
from core.model_runtime.entities.model_entities import ModelFeature, ModelType
from core.model_runtime.model_providers.__base.large_language_model import LargeLanguageModel
from core.rag.retrieval.dataset_retrieval import DatasetRetrieval
from core.workflow.entities.base_node_data_entities import BaseNodeData
from core.workflow.entities.node_entities import NodeRunResult, NodeType
from core.workflow.entities.variable_pool import VariablePool
from core.workflow.nodes.base_node import BaseNode
from core.workflow.nodes.knowledge_retrieval.entities import KnowledgeRetrievalNodeData
from extensions.ext_database import db
from models.dataset import Dataset, Document, DocumentSegment
from models.workflow import WorkflowNodeExecutionStatus

default_retrieval_model = {
    'search_method': 'semantic_search',
    'reranking_enable': False,
    'reranking_model': {
        'reranking_provider_name': '',
        'reranking_model_name': ''
    },
    'top_k': 2,
    'score_threshold_enabled': False
}


class KnowledgeRetrievalNode(BaseNode):
    _node_data_cls = KnowledgeRetrievalNodeData
    node_type = NodeType.KNOWLEDGE_RETRIEVAL

    def _run(self, variable_pool: VariablePool) -> NodeRunResult:
        node_data: KnowledgeRetrievalNodeData = cast(self._node_data_cls, self.node_data)

        # extract variables
        query = variable_pool.get_variable_value(variable_selector=node_data.query_variable_selector)
        variables = {
            'query': query
        }
        if not query:
            return NodeRunResult(
                status=WorkflowNodeExecutionStatus.FAILED,
                inputs=variables,
                error="Query is required."
            )
        # retrieve knowledge
        try:
            results = self._fetch_dataset_retriever(
                node_data=node_data, query=query
            )
            outputs = {
                'result': results
            }
            return NodeRunResult(
                status=WorkflowNodeExecutionStatus.SUCCEEDED,
                inputs=variables,
                process_data=None,
                outputs=outputs
            )

        except Exception as e:

            return NodeRunResult(
                status=WorkflowNodeExecutionStatus.FAILED,
                inputs=variables,
                error=str(e)
            )

    def _fetch_dataset_retriever(self, node_data: KnowledgeRetrievalNodeData, query: str) -> list[
        dict[str, Any]]:
        """
        A dataset tool is a tool that can be used to retrieve information from a dataset
        :param node_data: node data
        :param query: query
        """
        tools = []
        available_datasets = []
        dataset_ids = node_data.dataset_ids
        for dataset_id in dataset_ids:
            # get dataset from dataset id
            dataset = db.session.query(Dataset).filter(
                Dataset.tenant_id == self.tenant_id,
                Dataset.id == dataset_id
            ).first()

            # pass if dataset is not available
            if not dataset:
                continue

            # pass if dataset is not available
            if (dataset and dataset.available_document_count == 0
                    and dataset.available_document_count == 0):
                continue

            available_datasets.append(dataset)
        all_documents = []
        dataset_retrieval = DatasetRetrieval()
        if node_data.retrieval_mode == DatasetRetrieveConfigEntity.RetrieveStrategy.SINGLE.value:
            # fetch model config
            model_instance, model_config = self._fetch_model_config(node_data)
            # check model is support tool calling
            model_type_instance = model_config.provider_model_bundle.model_type_instance
            model_type_instance = cast(LargeLanguageModel, model_type_instance)
            # get model schema
            model_schema = model_type_instance.get_model_schema(
                model=model_config.model,
                credentials=model_config.credentials
            )

            if model_schema:
                planning_strategy = PlanningStrategy.REACT_ROUTER
                features = model_schema.features
                if features:
                    if ModelFeature.TOOL_CALL in features \
                            or ModelFeature.MULTI_TOOL_CALL in features:
                        planning_strategy = PlanningStrategy.ROUTER
                all_documents = dataset_retrieval.single_retrieve(
                    available_datasets=available_datasets,
                    tenant_id=self.tenant_id,
                    user_id=self.user_id,
                    app_id=self.app_id,
                    user_from=self.user_from.value,
                    query=query,
                    model_config=model_config,
                    model_instance=model_instance,
                    planning_strategy=planning_strategy
                )
        elif node_data.retrieval_mode == DatasetRetrieveConfigEntity.RetrieveStrategy.MULTIPLE.value:
            all_documents = dataset_retrieval.multiple_retrieve(self.app_id, self.tenant_id, self.user_id,
                                                                self.user_from.value,
                                                                available_datasets, query,
                                                                node_data.multiple_retrieval_config.top_k,
                                                                node_data.multiple_retrieval_config.score_threshold,
                                                                node_data.multiple_retrieval_config.reranking_model.provider,
                                                                node_data.multiple_retrieval_config.reranking_model.model)

        context_list = []
        if all_documents:
            document_score_list = {}
            for item in all_documents:
                if item.metadata.get('score'):
                    document_score_list[item.metadata['doc_id']] = item.metadata['score']

            index_node_ids = [document.metadata['doc_id'] for document in all_documents]
            segments = DocumentSegment.query.filter(
                DocumentSegment.dataset_id.in_(dataset_ids),
                DocumentSegment.completed_at.isnot(None),
                DocumentSegment.status == 'completed',
                DocumentSegment.enabled == True,
                DocumentSegment.index_node_id.in_(index_node_ids)
            ).all()
            if segments:
                index_node_id_to_position = {id: position for position, id in enumerate(index_node_ids)}
                sorted_segments = sorted(segments,
                                         key=lambda segment: index_node_id_to_position.get(segment.index_node_id,
                                                                                           float('inf')))

                for segment in sorted_segments:
                    dataset = Dataset.query.filter_by(
                        id=segment.dataset_id
                    ).first()
                    document = Document.query.filter(Document.id == segment.document_id,
                                                     Document.enabled == True,
                                                     Document.archived == False,
                                                     ).first()
                    resource_number = 1
                    if dataset and document:

                        source = {
                            'metadata': {
                                '_source': 'knowledge',
                                'position': resource_number,
                                'dataset_id': dataset.id,
                                'dataset_name': dataset.name,
                                'document_id': document.id,
                                'document_name': document.name,
                                'document_data_source_type': document.data_source_type,
                                'segment_id': segment.id,
                                'retriever_from': 'workflow',
                                'score': document_score_list.get(segment.index_node_id, None),
                                'segment_hit_count': segment.hit_count,
                                'segment_word_count': segment.word_count,
                                'segment_position': segment.position,
                                'segment_index_node_hash': segment.index_node_hash,
                            },
                            'title': document.name
                        }
                        if segment.answer:
                            source['content'] = f'question:{segment.get_sign_content()} \nanswer:{segment.answer}'
                        else:
                            source['content'] = segment.get_sign_content()
                        context_list.append(source)
                        resource_number += 1
        return context_list

    @classmethod
    def _extract_variable_selector_to_variable_mapping(cls, node_data: BaseNodeData) -> dict[str, list[str]]:
        node_data = node_data
        node_data = cast(cls._node_data_cls, node_data)
        variable_mapping = {}
        variable_mapping['query'] = node_data.query_variable_selector
        return variable_mapping

    def _fetch_model_config(self, node_data: KnowledgeRetrievalNodeData) -> tuple[
        ModelInstance, ModelConfigWithCredentialsEntity]:
        """
        Fetch model config
        :param node_data: node data
        :return:
        """
        model_name = node_data.single_retrieval_config.model.name
        provider_name = node_data.single_retrieval_config.model.provider

        model_manager = ModelManager()
        model_instance = model_manager.get_model_instance(
            tenant_id=self.tenant_id,
            model_type=ModelType.LLM,
            provider=provider_name,
            model=model_name
        )

        provider_model_bundle = model_instance.provider_model_bundle
        model_type_instance = model_instance.model_type_instance
        model_type_instance = cast(LargeLanguageModel, model_type_instance)

        model_credentials = model_instance.credentials

        # check model
        provider_model = provider_model_bundle.configuration.get_provider_model(
            model=model_name,
            model_type=ModelType.LLM
        )

        if provider_model is None:
            raise ValueError(f"Model {model_name} not exist.")

        if provider_model.status == ModelStatus.NO_CONFIGURE:
            raise ProviderTokenNotInitError(f"Model {model_name} credentials is not initialized.")
        elif provider_model.status == ModelStatus.NO_PERMISSION:
            raise ModelCurrentlyNotSupportError(f"Dify Hosted OpenAI {model_name} currently not support.")
        elif provider_model.status == ModelStatus.QUOTA_EXCEEDED:
            raise QuotaExceededError(f"Model provider {provider_name} quota exceeded.")

        # model config
        completion_params = node_data.single_retrieval_config.model.completion_params
        stop = []
        if 'stop' in completion_params:
            stop = completion_params['stop']
            del completion_params['stop']

        # get model mode
        model_mode = node_data.single_retrieval_config.model.mode
        if not model_mode:
            raise ValueError("LLM mode is required.")

        model_schema = model_type_instance.get_model_schema(
            model_name,
            model_credentials
        )

        if not model_schema:
            raise ValueError(f"Model {model_name} not exist.")

        return model_instance, ModelConfigWithCredentialsEntity(
            provider=provider_name,
            model=model_name,
            model_schema=model_schema,
            mode=model_mode,
            provider_model_bundle=provider_model_bundle,
            credentials=model_credentials,
            parameters=completion_params,
            stop=stop,
        )
