import json
import logging

from flask import abort, request
from flask_restful import Resource, marshal_with, reqparse
from werkzeug.exceptions import InternalServerError, NotFound

import services
from controllers.console import api
from controllers.console.app.error import ConversationCompletedError, DraftWorkflowNotExist, DraftWorkflowNotSync
from controllers.console.app.wraps import get_app_model
from controllers.console.setup import setup_required
from controllers.console.wraps import account_initialization_required
from core.app.apps.base_app_queue_manager import AppQueueManager
from core.app.entities.app_invoke_entities import InvokeFrom
from fields.workflow_fields import workflow_fields
from fields.workflow_run_fields import workflow_run_node_execution_fields
from libs import helper
from libs.helper import TimestampField, uuid_value
from libs.login import current_user, login_required
from models.model import App, AppMode
from services.app_generate_service import AppGenerateService
from services.errors.app import WorkflowHashNotEqualError
from services.workflow_service import WorkflowService

logger = logging.getLogger(__name__)


class DraftWorkflowApi(Resource):
    @setup_required
    @login_required
    @account_initialization_required
    @get_app_model(mode=[AppMode.ADVANCED_CHAT, AppMode.WORKFLOW])
    @marshal_with(workflow_fields)
    def get(self, app_model: App):
        """
        Get draft workflow
        """
        # fetch draft workflow by app_model
        workflow_service = WorkflowService()
        workflow = workflow_service.get_draft_workflow(app_model=app_model)

        if not workflow:
            raise DraftWorkflowNotExist()

        # return workflow, if not found, return None (initiate graph by frontend)
        return workflow

    @setup_required
    @login_required
    @account_initialization_required
    @get_app_model(mode=[AppMode.ADVANCED_CHAT, AppMode.WORKFLOW])
    def post(self, app_model: App):
        """
        Sync draft workflow
        """
        content_type = request.headers.get('Content-Type')

        if 'application/json' in content_type:
            parser = reqparse.RequestParser()
            parser.add_argument('graph', type=dict, required=True, nullable=False, location='json')
            parser.add_argument('features', type=dict, required=True, nullable=False, location='json')
            parser.add_argument('hash', type=str, required=False, location='json')
            args = parser.parse_args()
        elif 'text/plain' in content_type:
            try:
                data = json.loads(request.data.decode('utf-8'))
                if 'graph' not in data or 'features' not in data:
                    raise ValueError('graph or features not found in data')

                if not isinstance(data.get('graph'), dict) or not isinstance(data.get('features'), dict):
                    raise ValueError('graph or features is not a dict')

                args = {
                    'graph': data.get('graph'),
                    'features': data.get('features'),
                    'hash': data.get('hash')
                }
            except json.JSONDecodeError:
                return {'message': 'Invalid JSON data'}, 400
        else:
            abort(415)

        workflow_service = WorkflowService()

        try:
            workflow = workflow_service.sync_draft_workflow(
                app_model=app_model,
                graph=args.get('graph'),
                features=args.get('features'),
                unique_hash=args.get('hash'),
                account=current_user
            )
        except WorkflowHashNotEqualError:
            raise DraftWorkflowNotSync()

        return {
            "result": "success",
            "hash": workflow.unique_hash,
            "updated_at": TimestampField().format(workflow.updated_at or workflow.created_at)
        }


class AdvancedChatDraftWorkflowRunApi(Resource):
    @setup_required
    @login_required
    @account_initialization_required
    @get_app_model(mode=[AppMode.ADVANCED_CHAT])
    def post(self, app_model: App):
        """
        Run draft workflow
        """
        parser = reqparse.RequestParser()
        parser.add_argument('inputs', type=dict, location='json')
        parser.add_argument('query', type=str, required=True, location='json', default='')
        parser.add_argument('files', type=list, location='json')
        parser.add_argument('conversation_id', type=uuid_value, location='json')
        args = parser.parse_args()

        try:
            response = AppGenerateService.generate(
                app_model=app_model,
                user=current_user,
                args=args,
                invoke_from=InvokeFrom.DEBUGGER,
                streaming=True
            )

            return helper.compact_generate_response(response)
        except services.errors.conversation.ConversationNotExistsError:
            raise NotFound("Conversation Not Exists.")
        except services.errors.conversation.ConversationCompletedError:
            raise ConversationCompletedError()
        except ValueError as e:
            raise e
        except Exception as e:
            logging.exception("internal server error.")
            raise InternalServerError()

class AdvancedChatDraftRunIterationNodeApi(Resource):
    @setup_required
    @login_required
    @account_initialization_required
    @get_app_model(mode=[AppMode.ADVANCED_CHAT])
    def post(self, app_model: App, node_id: str):
        """
        Run draft workflow iteration node
        """
        parser = reqparse.RequestParser()
        parser.add_argument('inputs', type=dict, location='json')
        args = parser.parse_args()

        try:
            response = AppGenerateService.generate_single_iteration(
                app_model=app_model,
                user=current_user,
                node_id=node_id,
                args=args,
                streaming=True
            )

            return helper.compact_generate_response(response)
        except services.errors.conversation.ConversationNotExistsError:
            raise NotFound("Conversation Not Exists.")
        except services.errors.conversation.ConversationCompletedError:
            raise ConversationCompletedError()
        except ValueError as e:
            raise e
        except Exception as e:
            logging.exception("internal server error.")
            raise InternalServerError()

class WorkflowDraftRunIterationNodeApi(Resource):
    @setup_required
    @login_required
    @account_initialization_required
    @get_app_model(mode=[AppMode.WORKFLOW])
    def post(self, app_model: App, node_id: str):
        """
        Run draft workflow iteration node
        """
        parser = reqparse.RequestParser()
        parser.add_argument('inputs', type=dict, location='json')
        args = parser.parse_args()

        try:
            response = AppGenerateService.generate_single_iteration(
                app_model=app_model,
                user=current_user,
                node_id=node_id,
                args=args,
                streaming=True
            )

            return helper.compact_generate_response(response)
        except services.errors.conversation.ConversationNotExistsError:
            raise NotFound("Conversation Not Exists.")
        except services.errors.conversation.ConversationCompletedError:
            raise ConversationCompletedError()
        except ValueError as e:
            raise e
        except Exception as e:
            logging.exception("internal server error.")
            raise InternalServerError()

class DraftWorkflowRunApi(Resource):
    @setup_required
    @login_required
    @account_initialization_required
    @get_app_model(mode=[AppMode.WORKFLOW])
    def post(self, app_model: App):
        """
        Run draft workflow
        """
        parser = reqparse.RequestParser()
        parser.add_argument('inputs', type=dict, required=True, nullable=False, location='json')
        parser.add_argument('files', type=list, required=False, location='json')
        args = parser.parse_args()

        try:
            response = AppGenerateService.generate(
                app_model=app_model,
                user=current_user,
                args=args,
                invoke_from=InvokeFrom.DEBUGGER,
                streaming=True
            )

            return helper.compact_generate_response(response)
        except ValueError as e:
            raise e
        except Exception as e:
            logging.exception("internal server error.")
            raise InternalServerError()


class WorkflowTaskStopApi(Resource):
    @setup_required
    @login_required
    @account_initialization_required
    @get_app_model(mode=[AppMode.ADVANCED_CHAT, AppMode.WORKFLOW])
    def post(self, app_model: App, task_id: str):
        """
        Stop workflow task
        """
        AppQueueManager.set_stop_flag(task_id, InvokeFrom.DEBUGGER, current_user.id)

        return {
            "result": "success"
        }


class DraftWorkflowNodeRunApi(Resource):
    @setup_required
    @login_required
    @account_initialization_required
    @get_app_model(mode=[AppMode.ADVANCED_CHAT, AppMode.WORKFLOW])
    @marshal_with(workflow_run_node_execution_fields)
    def post(self, app_model: App, node_id: str):
        """
        Run draft workflow node
        """
        parser = reqparse.RequestParser()
        parser.add_argument('inputs', type=dict, required=True, nullable=False, location='json')
        args = parser.parse_args()

        workflow_service = WorkflowService()
        workflow_node_execution = workflow_service.run_draft_workflow_node(
            app_model=app_model,
            node_id=node_id,
            user_inputs=args.get('inputs'),
            account=current_user
        )

        return workflow_node_execution


class PublishedWorkflowApi(Resource):

    @setup_required
    @login_required
    @account_initialization_required
    @get_app_model(mode=[AppMode.ADVANCED_CHAT, AppMode.WORKFLOW])
    @marshal_with(workflow_fields)
    def get(self, app_model: App):
        """
        Get published workflow
        """
        # fetch published workflow by app_model
        workflow_service = WorkflowService()
        workflow = workflow_service.get_published_workflow(app_model=app_model)

        # return workflow, if not found, return None
        return workflow

    @setup_required
    @login_required
    @account_initialization_required
    @get_app_model(mode=[AppMode.ADVANCED_CHAT, AppMode.WORKFLOW])
    def post(self, app_model: App):
        """
        Publish workflow
        """
        workflow_service = WorkflowService()
        workflow = workflow_service.publish_workflow(app_model=app_model, account=current_user)

        return {
            "result": "success",
            "created_at": TimestampField().format(workflow.created_at)
        }


class DefaultBlockConfigsApi(Resource):
    @setup_required
    @login_required
    @account_initialization_required
    @get_app_model(mode=[AppMode.ADVANCED_CHAT, AppMode.WORKFLOW])
    def get(self, app_model: App):
        """
        Get default block config
        """
        # Get default block configs
        workflow_service = WorkflowService()
        return workflow_service.get_default_block_configs()


class DefaultBlockConfigApi(Resource):
    @setup_required
    @login_required
    @account_initialization_required
    @get_app_model(mode=[AppMode.ADVANCED_CHAT, AppMode.WORKFLOW])
    def get(self, app_model: App, block_type: str):
        """
        Get default block config
        """
        parser = reqparse.RequestParser()
        parser.add_argument('q', type=str, location='args')
        args = parser.parse_args()

        filters = None
        if args.get('q'):
            try:
                filters = json.loads(args.get('q'))
            except json.JSONDecodeError:
                raise ValueError('Invalid filters')

        # Get default block configs
        workflow_service = WorkflowService()
        return workflow_service.get_default_block_config(
            node_type=block_type,
            filters=filters
        )


class ConvertToWorkflowApi(Resource):
    @setup_required
    @login_required
    @account_initialization_required
    @get_app_model(mode=[AppMode.CHAT, AppMode.COMPLETION])
    def post(self, app_model: App):
        """
        Convert basic mode of chatbot app to workflow mode
        Convert expert mode of chatbot app to workflow mode
        Convert Completion App to Workflow App
        """
        if request.data:
            parser = reqparse.RequestParser()
            parser.add_argument('name', type=str, required=False, nullable=True, location='json')
            parser.add_argument('icon', type=str, required=False, nullable=True, location='json')
            parser.add_argument('icon_background', type=str, required=False, nullable=True, location='json')
            args = parser.parse_args()
        else:
            args = {}

        # convert to workflow mode
        workflow_service = WorkflowService()
        new_app_model = workflow_service.convert_to_workflow(
            app_model=app_model,
            account=current_user,
            args=args
        )

        # return app id
        return {
            'new_app_id': new_app_model.id,
        }


api.add_resource(DraftWorkflowApi, '/apps/<uuid:app_id>/workflows/draft')
api.add_resource(AdvancedChatDraftWorkflowRunApi, '/apps/<uuid:app_id>/advanced-chat/workflows/draft/run')
api.add_resource(DraftWorkflowRunApi, '/apps/<uuid:app_id>/workflows/draft/run')
api.add_resource(WorkflowTaskStopApi, '/apps/<uuid:app_id>/workflow-runs/tasks/<string:task_id>/stop')
api.add_resource(DraftWorkflowNodeRunApi, '/apps/<uuid:app_id>/workflows/draft/nodes/<string:node_id>/run')
api.add_resource(AdvancedChatDraftRunIterationNodeApi, '/apps/<uuid:app_id>/advanced-chat/workflows/draft/iteration/nodes/<string:node_id>/run')
api.add_resource(WorkflowDraftRunIterationNodeApi, '/apps/<uuid:app_id>/workflows/draft/iteration/nodes/<string:node_id>/run')
api.add_resource(PublishedWorkflowApi, '/apps/<uuid:app_id>/workflows/publish')
api.add_resource(DefaultBlockConfigsApi, '/apps/<uuid:app_id>/workflows/default-workflow-block-configs')
api.add_resource(DefaultBlockConfigApi, '/apps/<uuid:app_id>/workflows/default-workflow-block-configs'
                                        '/<string:block_type>')
api.add_resource(ConvertToWorkflowApi, '/apps/<uuid:app_id>/convert-to-workflow')
