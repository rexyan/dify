import logging
import os
import threading
import uuid
from collections.abc import Generator
from typing import Union

from flask import Flask, current_app
from pydantic import ValidationError

from core.app.app_config.features.file_upload.manager import FileUploadConfigManager
from core.app.apps.advanced_chat.app_config_manager import AdvancedChatAppConfigManager
from core.app.apps.advanced_chat.app_runner import AdvancedChatAppRunner
from core.app.apps.advanced_chat.generate_response_converter import AdvancedChatAppGenerateResponseConverter
from core.app.apps.advanced_chat.generate_task_pipeline import AdvancedChatAppGenerateTaskPipeline
from core.app.apps.base_app_queue_manager import AppQueueManager, GenerateTaskStoppedException, PublishFrom
from core.app.apps.message_based_app_generator import MessageBasedAppGenerator
from core.app.apps.message_based_app_queue_manager import MessageBasedAppQueueManager
from core.app.entities.app_invoke_entities import AdvancedChatAppGenerateEntity, InvokeFrom
from core.app.entities.task_entities import ChatbotAppBlockingResponse, ChatbotAppStreamResponse
from core.file.message_file_parser import MessageFileParser
from core.model_runtime.errors.invoke import InvokeAuthorizationError, InvokeError
from extensions.ext_database import db
from models.account import Account
from models.model import App, Conversation, EndUser, Message
from models.workflow import Workflow

logger = logging.getLogger(__name__)


class AdvancedChatAppGenerator(MessageBasedAppGenerator):
    def generate(self, app_model: App,
                 workflow: Workflow,
                 user: Union[Account, EndUser],
                 args: dict,
                 invoke_from: InvokeFrom,
                 stream: bool = True) \
            -> Union[dict, Generator[dict, None, None]]:
        """
        Generate App response.

        :param app_model: App
        :param workflow: Workflow
        :param user: account or end user
        :param args: request args
        :param invoke_from: invoke from source
        :param stream: is stream
        """
        if not args.get('query'):
            raise ValueError('query is required')

        query = args['query']
        if not isinstance(query, str):
            raise ValueError('query must be a string')

        query = query.replace('\x00', '')
        inputs = args['inputs']

        extras = {
            "auto_generate_conversation_name": args['auto_generate_name'] if 'auto_generate_name' in args else False
        }

        # get conversation
        conversation = None
        if args.get('conversation_id'):
            conversation = self._get_conversation_by_user(app_model, args.get('conversation_id'), user)

        # parse files
        files = args['files'] if args.get('files') else []
        message_file_parser = MessageFileParser(tenant_id=app_model.tenant_id, app_id=app_model.id)
        file_extra_config = FileUploadConfigManager.convert(workflow.features_dict, is_vision=False)
        if file_extra_config:
            file_objs = message_file_parser.validate_and_transform_files_arg(
                files,
                file_extra_config,
                user
            )
        else:
            file_objs = []

        # convert to app config
        app_config = AdvancedChatAppConfigManager.get_app_config(
            app_model=app_model,
            workflow=workflow
        )

        # init application generate entity
        application_generate_entity = AdvancedChatAppGenerateEntity(
            task_id=str(uuid.uuid4()),
            app_config=app_config,
            conversation_id=conversation.id if conversation else None,
            inputs=conversation.inputs if conversation else self._get_cleaned_inputs(inputs, app_config),
            query=query,
            files=file_objs,
            user_id=user.id,
            stream=stream,
            invoke_from=invoke_from,
            extras=extras
        )

        return self._generate(
            app_model=app_model,
            workflow=workflow,
            user=user,
            invoke_from=invoke_from,
            application_generate_entity=application_generate_entity,
            conversation=conversation,
            stream=stream
        )
    
    def single_iteration_generate(self, app_model: App,
                                  workflow: Workflow,
                                  node_id: str,
                                  user: Account,
                                  args: dict,
                                  stream: bool = True) \
            -> Union[dict, Generator[dict, None, None]]:
        """
        Generate App response.

        :param app_model: App
        :param workflow: Workflow
        :param user: account or end user
        :param args: request args
        :param invoke_from: invoke from source
        :param stream: is stream
        """
        if not node_id:
            raise ValueError('node_id is required')
        
        if args.get('inputs') is None:
            raise ValueError('inputs is required')
        
        extras = {
            "auto_generate_conversation_name": False
        }

        # get conversation
        conversation = None
        if args.get('conversation_id'):
            conversation = self._get_conversation_by_user(app_model, args.get('conversation_id'), user)

        # convert to app config
        app_config = AdvancedChatAppConfigManager.get_app_config(
            app_model=app_model,
            workflow=workflow
        )

        # init application generate entity
        application_generate_entity = AdvancedChatAppGenerateEntity(
            task_id=str(uuid.uuid4()),
            app_config=app_config,
            conversation_id=conversation.id if conversation else None,
            inputs={},
            query='',
            files=[],
            user_id=user.id,
            stream=stream,
            invoke_from=InvokeFrom.DEBUGGER,
            extras=extras,
            single_iteration_run=AdvancedChatAppGenerateEntity.SingleIterationRunEntity(
                node_id=node_id,
                inputs=args['inputs']
            )
        )

        return self._generate(
            app_model=app_model,
            workflow=workflow,
            user=user,
            invoke_from=InvokeFrom.DEBUGGER,
            application_generate_entity=application_generate_entity,
            conversation=conversation,
            stream=stream
        )

    def _generate(self, app_model: App,
                 workflow: Workflow,
                 user: Union[Account, EndUser],
                 invoke_from: InvokeFrom,
                 application_generate_entity: AdvancedChatAppGenerateEntity,
                 conversation: Conversation = None,
                 stream: bool = True) \
            -> Union[dict, Generator[dict, None, None]]:
        is_first_conversation = False
        if not conversation:
            is_first_conversation = True

        # init generate records
        (
            conversation,
            message
        ) = self._init_generate_records(application_generate_entity, conversation)

        if is_first_conversation:
            # update conversation features
            conversation.override_model_configs = workflow.features
            db.session.commit()
            db.session.refresh(conversation)

        # init queue manager
        queue_manager = MessageBasedAppQueueManager(
            task_id=application_generate_entity.task_id,
            user_id=application_generate_entity.user_id,
            invoke_from=application_generate_entity.invoke_from,
            conversation_id=conversation.id,
            app_mode=conversation.mode,
            message_id=message.id
        )

        # new thread
        worker_thread = threading.Thread(target=self._generate_worker, kwargs={
            'flask_app': current_app._get_current_object(),
            'application_generate_entity': application_generate_entity,
            'queue_manager': queue_manager,
            'conversation_id': conversation.id,
            'message_id': message.id,
        })

        worker_thread.start()

        # return response or stream generator
        response = self._handle_advanced_chat_response(
            application_generate_entity=application_generate_entity,
            workflow=workflow,
            queue_manager=queue_manager,
            conversation=conversation,
            message=message,
            user=user,
            stream=stream
        )

        return AdvancedChatAppGenerateResponseConverter.convert(
            response=response,
            invoke_from=invoke_from
        )

    def _generate_worker(self, flask_app: Flask,
                         application_generate_entity: AdvancedChatAppGenerateEntity,
                         queue_manager: AppQueueManager,
                         conversation_id: str,
                         message_id: str) -> None:
        """
        Generate worker in a new thread.
        :param flask_app: Flask app
        :param application_generate_entity: application generate entity
        :param queue_manager: queue manager
        :param conversation_id: conversation ID
        :param message_id: message ID
        :return:
        """
        with flask_app.app_context():
            try:
                runner = AdvancedChatAppRunner()
                if application_generate_entity.single_iteration_run:
                    single_iteration_run = application_generate_entity.single_iteration_run
                    runner.single_iteration_run(
                        app_id=application_generate_entity.app_config.app_id,
                        workflow_id=application_generate_entity.app_config.workflow_id,
                        queue_manager=queue_manager,
                        inputs=single_iteration_run.inputs,
                        node_id=single_iteration_run.node_id,
                        user_id=application_generate_entity.user_id
                    )
                else:
                    # get conversation and message
                    conversation = self._get_conversation(conversation_id)
                    message = self._get_message(message_id)

                    # chatbot app
                    runner = AdvancedChatAppRunner()
                    runner.run(
                        application_generate_entity=application_generate_entity,
                        queue_manager=queue_manager,
                        conversation=conversation,
                        message=message
                    )
            except GenerateTaskStoppedException:
                pass
            except InvokeAuthorizationError:
                queue_manager.publish_error(
                    InvokeAuthorizationError('Incorrect API key provided'),
                    PublishFrom.APPLICATION_MANAGER
                )
            except ValidationError as e:
                logger.exception("Validation Error when generating")
                queue_manager.publish_error(e, PublishFrom.APPLICATION_MANAGER)
            except (ValueError, InvokeError) as e:
                if os.environ.get("DEBUG") and os.environ.get("DEBUG").lower() == 'true':
                    logger.exception("Error when generating")
                queue_manager.publish_error(e, PublishFrom.APPLICATION_MANAGER)
            except Exception as e:
                logger.exception("Unknown Error when generating")
                queue_manager.publish_error(e, PublishFrom.APPLICATION_MANAGER)
            finally:
                db.session.close()

    def _handle_advanced_chat_response(self, application_generate_entity: AdvancedChatAppGenerateEntity,
                                       workflow: Workflow,
                                       queue_manager: AppQueueManager,
                                       conversation: Conversation,
                                       message: Message,
                                       user: Union[Account, EndUser],
                                       stream: bool = False) \
            -> Union[ChatbotAppBlockingResponse, Generator[ChatbotAppStreamResponse, None, None]]:
        """
        Handle response.
        :param application_generate_entity: application generate entity
        :param workflow: workflow
        :param queue_manager: queue manager
        :param conversation: conversation
        :param message: message
        :param user: account or end user
        :param stream: is stream
        :return:
        """
        # init generate task pipeline
        generate_task_pipeline = AdvancedChatAppGenerateTaskPipeline(
            application_generate_entity=application_generate_entity,
            workflow=workflow,
            queue_manager=queue_manager,
            conversation=conversation,
            message=message,
            user=user,
            stream=stream
        )

        try:
            return generate_task_pipeline.process()
        except ValueError as e:
            if e.args[0] == "I/O operation on closed file.":  # ignore this error
                raise GenerateTaskStoppedException()
            else:
                logger.exception(e)
                raise e
