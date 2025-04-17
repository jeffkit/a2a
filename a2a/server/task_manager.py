from abc import ABC, abstractmethod
from typing import Union, AsyncIterable, List, Dict, Optional, Any
import logging

from a2a import Message, TextPart, TaskStatus, TaskState, TaskStatusUpdateEvent, Task, Artifact, TaskArtifactUpdateEvent
from a2a.server.history_provider import ConversationHistoryProvider, InMemoryHistoryProvider, extract_text_from_message
from a2a.server.notification_handler import NotificationHandler, DefaultNotificationHandler
from a2a.server.response_processor import ResponseProcessor, DefaultResponseProcessor
from a2a.server.storage import TaskStorage, InMemoryStorage
from a2a.server.types import Agent
from a2a.types import Task, SendTaskRequest, SendTaskStreamingRequest, JSONRPCResponse, InternalError, TaskSendParams, \
    InvalidParamsError, GetTaskRequest, GetTaskResponse, TaskQueryParams, TaskNotFoundError, CancelTaskRequest, \
    CancelTaskResponse, TaskIdParams, TaskNotCancelableError, SendTaskResponse, SendTaskStreamingResponse, \
    SetTaskPushNotificationRequest, SetTaskPushNotificationResponse, TaskPushNotificationConfig, \
    GetTaskPushNotificationRequest, GetTaskPushNotificationResponse, TaskResubscriptionRequest
from a2a.types import (
    JSONRPCResponse,
    TaskIdParams,
    TaskQueryParams,
    GetTaskRequest,
    TaskNotFoundError,
    SendTaskRequest,
    CancelTaskRequest,
    TaskNotCancelableError,
    SetTaskPushNotificationRequest,
    GetTaskPushNotificationRequest,
    GetTaskResponse,
    CancelTaskResponse,
    SendTaskResponse,
    SetTaskPushNotificationResponse,
    GetTaskPushNotificationResponse,
    PushNotificationNotSupportedError,
    TaskSendParams,
    TaskStatus,
    TaskState,
    TaskResubscriptionRequest,
    SendTaskStreamingRequest,
    SendTaskStreamingResponse,
    Artifact,
    PushNotificationConfig,
    TaskStatusUpdateEvent,
    JSONRPCError,
    TaskPushNotificationConfig,
    InternalError,
)
from a2a.server.utils import new_not_implemented_error, are_modalities_compatible, new_incompatible_types_error
import asyncio

# Create logger directly
logger = logging.getLogger(__name__)

class TaskManager(ABC):
    @abstractmethod
    async def on_get_task(self, request: GetTaskRequest) -> GetTaskResponse:
        pass

    @abstractmethod
    async def on_cancel_task(self, request: CancelTaskRequest) -> CancelTaskResponse:
        pass

    @abstractmethod
    async def on_send_task(self, request: SendTaskRequest) -> SendTaskResponse:
        pass

    @abstractmethod
    async def on_send_task_subscribe(
        self, request: SendTaskStreamingRequest
    ) -> Union[AsyncIterable[SendTaskStreamingResponse], JSONRPCResponse]:
        pass

    @abstractmethod
    async def on_set_task_push_notification(
        self, request: SetTaskPushNotificationRequest
    ) -> SetTaskPushNotificationResponse:
        pass

    @abstractmethod
    async def on_get_task_push_notification(
        self, request: GetTaskPushNotificationRequest
    ) -> GetTaskPushNotificationResponse:
        pass

    @abstractmethod
    async def on_resubscribe_to_task(
        self, request: TaskResubscriptionRequest
    ) -> Union[AsyncIterable[SendTaskResponse], JSONRPCResponse]:
        pass


class InMemoryTaskManager(TaskManager):
    """In-memory task manager
    
    Simple wrapper of DefaultTaskManager and InMemoryStorage,
    providing a fully in-memory task management implementation.
    """
    
    def __init__(self):
        """Initialize the in-memory task manager"""
        # Import here to avoid circular imports
        from a2a.server.storage import InMemoryStorage
        from a2a.server.history_provider import InMemoryHistoryProvider
        
        # Create storage and history provider
        storage = InMemoryStorage()
        history_provider = InMemoryHistoryProvider()
        
        # Create DefaultTaskManager instance
        self._delegate = DefaultTaskManager(
            storage=storage,
            history_provider=history_provider
        )
    
    async def on_get_task(self, request: GetTaskRequest) -> GetTaskResponse:
        """Delegate to DefaultTaskManager to handle get task request"""
        return await self._delegate.on_get_task(request)

    async def on_cancel_task(self, request: CancelTaskRequest) -> CancelTaskResponse:
        """Delegate to DefaultTaskManager to handle cancel task request"""
        return await self._delegate.on_cancel_task(request)

    async def on_send_task(self, request: SendTaskRequest) -> SendTaskResponse:
        """Delegate to DefaultTaskManager to handle send task request"""
        return await self._delegate.on_send_task(request)

    async def on_send_task_subscribe(
        self, request: SendTaskStreamingRequest
    ) -> Union[AsyncIterable[SendTaskStreamingResponse], JSONRPCResponse]:
        """Delegate to DefaultTaskManager to handle streaming task request"""
        return await self._delegate.on_send_task_subscribe(request)

    async def on_set_task_push_notification(
        self, request: SetTaskPushNotificationRequest
    ) -> SetTaskPushNotificationResponse:
        """Delegate to DefaultTaskManager to handle set task push notification request"""
        return await self._delegate.on_set_task_push_notification(request)

    async def on_get_task_push_notification(
        self, request: GetTaskPushNotificationRequest
    ) -> GetTaskPushNotificationResponse:
        """Delegate to DefaultTaskManager to handle get task push notification request"""
        return await self._delegate.on_get_task_push_notification(request)

    async def on_resubscribe_to_task(
        self, request: TaskResubscriptionRequest
    ) -> Union[AsyncIterable[SendTaskStreamingResponse], JSONRPCResponse]:
        """Delegate to DefaultTaskManager to handle resubscribe to task request"""
        return await self._delegate.on_resubscribe_to_task(request)

    async def upsert_task(self, task_send_params: TaskSendParams) -> Task:
        """Delegate to DefaultTaskManager to create or update task"""
        return await self._delegate._upsert_task(task_send_params)

    async def update_store(
        self, task_id: str, status: TaskStatus, artifacts: list[Artifact]
    ) -> Task:
        """Delegate to DefaultTaskManager to update task status"""
        return await self._delegate._update_task_status(task_id, status, artifacts)

    def append_task_history(self, task: Task, historyLength: int | None):
        """Delegate to DefaultTaskManager to handle task history length"""
        return self._delegate._append_task_history(task, historyLength)

    async def setup_sse_consumer(self, task_id: str, is_resubscribe: bool = False):
        """Delegate to DefaultTaskManager to set SSE consumer"""
        return await self._delegate._setup_sse_consumer(task_id, is_resubscribe)

    async def enqueue_events_for_sse(self, task_id, task_update_event):
        """Delegate to DefaultTaskManager to enqueue events for SSE"""
        return await self._delegate._enqueue_events_for_sse(task_id, task_update_event)

    async def dequeue_events_for_sse(
        self, request_id, task_id, sse_event_queue: asyncio.Queue
    ) -> AsyncIterable[SendTaskStreamingResponse] | JSONRPCResponse:
        """Delegate to DefaultTaskManager to get events from SSE queue"""
        return self._delegate._dequeue_events_for_sse(request_id, task_id, sse_event_queue)

    async def set_push_notification_info(self, task_id: str, notification_config: PushNotificationConfig):
        """Delegate to NotificationHandler to set task push notification config"""
        return await self._delegate.notification_handler.set_notification_config(task_id, notification_config)
    
    async def get_push_notification_info(self, task_id: str) -> PushNotificationConfig:
        """Delegate to NotificationHandler to get task push notification config"""
        return await self._delegate.notification_handler.get_notification_config(task_id)
    
    async def has_push_notification_info(self, task_id: str) -> bool:
        """Delegate to NotificationHandler to check if task has push notification config"""
        return await self._delegate.notification_handler.has_notification_config(task_id)


class DefaultTaskManager(TaskManager):
    """Base task manager

    Implement the common task management logic required for the A2A protocol,
    can be used with different storage backends and agent executors
    """

    def __init__(
        self,
        storage: TaskStorage = None,
        agent: Agent = None,
        response_processor: ResponseProcessor = None,
        notification_handler: NotificationHandler = None,
        history_provider: ConversationHistoryProvider = None
    ):
        """
        Initialize the base task manager

        Args:
            storage: Task storage backend, if None, use in-memory storage
            agent: Instance of Agent that implements the Agent interface
            response_processor: Response processor, processes Agent responses
            notification_handler: Notification handler, handles task status change notifications
            history_provider: Conversation history provider, manages conversation history
        """
        self.storage = storage or InMemoryStorage()
        self.agent = agent
        self.response_processor = response_processor or DefaultResponseProcessor()
        self.notification_handler = notification_handler or DefaultNotificationHandler()
        self.history_provider = history_provider or InMemoryHistoryProvider()
        self.lock = asyncio.Lock()
        self.task_sse_subscribers: Dict[str, List[asyncio.Queue]] = {}
        self.subscriber_lock = asyncio.Lock()

    def _validate_request(
        self, request: Union[SendTaskRequest, SendTaskStreamingRequest]
    ) -> Optional[JSONRPCResponse]:
        """Validate the request

        Check if the request parameters are valid, especially if the output mode is compatible with the Agent

        Args:
            request: Task request

        Returns:
            JSONRPCResponse, None if valid
        """
        # Check if the Agent is configured
        if self.agent is None:
            logger.error("Agent not configured")
            return JSONRPCResponse(
                id=request.id,
                error=InternalError(message="Agent not configured, service cannot process request")
            )

        task_send_params: TaskSendParams = request.params

        # 检查消息是否有效
        if not task_send_params.message or not task_send_params.message.parts:
            logger.warning("Request message is empty or invalid")
            return JSONRPCResponse(
                id=request.id,
                error=InvalidParamsError(message="Request message is empty or invalid")
            )

        # 检查输出模式兼容性
        if hasattr(task_send_params, 'acceptedOutputModes') and task_send_params.acceptedOutputModes and hasattr(self.agent, 'supported_content_types'):
            if not are_modalities_compatible(
                task_send_params.acceptedOutputModes, self.agent.supported_content_types
            ):
                logger.warning(
                    "Unsupported output mode. Received %s, supported %s",
                    task_send_params.acceptedOutputModes,
                    self.agent.supported_content_types,
                )
                return new_incompatible_types_error(request.id)

        # 检查推送通知配置
        if (
            hasattr(task_send_params, 'pushNotification') and
            task_send_params.pushNotification and
            not task_send_params.pushNotification.url
        ):
            logger.warning("Push notification URL is missing")
            return JSONRPCResponse(
                id=request.id,
                error=InvalidParamsError(message="Push notification URL is missing")
            )

        return None

    def _get_user_query(self, message: Message) -> str:
        """Extract user query from message

        Args:
            message: User message

        Returns:
            User query text
        """
        if not message or not message.parts:
            return ""

        # Extract all text parts
        text_parts = []
        for part in message.parts:
            if isinstance(part, TextPart):
                text_parts.append(part.text)
            elif hasattr(part, 'type') and part.type == 'text' and hasattr(part, 'text'):
                text_parts.append(part.text)

        return " ".join(filter(None, text_parts))

    async def on_get_task(self, request: GetTaskRequest) -> GetTaskResponse:
        """Handle get task request"""
        logger.info(f"Getting task {request.params.id}")
        task_query_params: TaskQueryParams = request.params

        # Get task from storage
        task = await self.storage.get_task(task_query_params.id)
        if task is None:
            return GetTaskResponse(id=request.id, error=TaskNotFoundError())

        # Process history
        task_result = self._append_task_history(
            task, task_query_params.historyLength
        )

        return GetTaskResponse(id=request.id, result=task_result)

    async def on_cancel_task(self, request: CancelTaskRequest) -> CancelTaskResponse:
        """Handle cancel task request

        Note: The current version does not support task cancellation,
        subclasses can override this method to implement custom cancellation logic
        """
        logger.info(f"Cancelling task {request.params.id}")
        task_id_params: TaskIdParams = request.params

        # Check if the task exists
        task = await self.storage.get_task(task_id_params.id)
        if task is None:
            return CancelTaskResponse(id=request.id, error=TaskNotFoundError())

        # Default does not support cancellation
        return CancelTaskResponse(id=request.id, error=TaskNotCancelableError())

    async def on_send_task(self, request: SendTaskRequest) -> SendTaskResponse:
        """Handle send task request

        Note: The current version does not support task cancellation,
        subclasses can override this method to implement custom cancellation logic
        """
        logger.info(f"Send task {request.params.id}")

        # Validate request
        validation_error = self._validate_request(request)
        if validation_error:
            return SendTaskResponse(id=request.id, error=validation_error.error)

        try:
            # 1. Create or update task
            task = await self._upsert_task(request.params)

            # 2. Update task status to "processing"
            task = await self._update_task_status(
                task.id,
                TaskStatus(state=TaskState.WORKING),
                []
            )

            # 3. Process push notification config
            if hasattr(request.params, 'pushNotification') and request.params.pushNotification:
                await self.notification_handler.set_notification_config(
                    request.params.id, request.params.pushNotification
                )

            # 4. Send task start notification
            await self.notification_handler.send_notification(task)

            # 5. Process user message
            user_message = self._get_user_query(request.params.message)

            # 6. Get conversation history
            session_id = request.params.sessionId
            conversation_history = await self.history_provider.get_history(session_id)

            # 7. Save user message to history
            await self.history_provider.add_message(
                session_id,
                {"role": "user", "content": user_message}
            )

            # 8. Call agent to process
            if self.agent is None:
                raise ValueError("Agent not configured, please provide an Agent instance or override this method")

            # Call agent, pass history
            response = self.agent.invoke(user_message, request.params.sessionId, history=conversation_history)

            # 9. Process agent response
            state, message, artifacts = self.response_processor.process_response(response)

            # 10. Save assistant reply to history
            assistant_message = extract_text_from_message(message)
            await self.history_provider.add_message(
                session_id,
                {"role": "assistant", "content": assistant_message}
            )

            # 11. Update task status
            task = await self._update_task_status(
                task.id,
                TaskStatus(state=state, message=message),
                artifacts or []
            )

            # 12. Send task update notification
            await self.notification_handler.send_notification(task)

            # 13. Process task history
            task_result = self._append_task_history(
                task,
                request.params.historyLength if hasattr(request.params, 'historyLength') else None
            )

            return SendTaskResponse(id=request.id, result=task_result)

        except Exception as e:
            logger.error(f"Error processing task: {e}")
            return SendTaskResponse(
                id=request.id,
                error=InternalError(message=f"Error processing task: {str(e)}")
            )

    async def on_send_task_subscribe(
        self, request: SendTaskStreamingRequest
    ) -> Union[AsyncIterable[SendTaskStreamingResponse], JSONRPCResponse]:
        """Handle streaming task request

        Note: The current version does not support task cancellation,
        subclasses can override this method to implement custom cancellation logic
        """
        logger.info(f"Send streaming task {request.params.id}")

        # Validate request
        validation_error = self._validate_request(request)
        if validation_error:
            return validation_error

        try:
            # 1. Create or update task
            task = await self._upsert_task(request.params)

            # 2. Update task status to "processing"
            task = await self._update_task_status(
                task.id,
                TaskStatus(state=TaskState.WORKING),
                []
            )

            # 3. Process push notification config
            if hasattr(request.params, 'pushNotification') and request.params.pushNotification:
                await self.notification_handler.set_notification_config(
                    request.params.id, request.params.pushNotification
                )

            # 4. Send task start notification
            await self.notification_handler.send_notification(task)

            # 5. Set SSE subscription
            sse_queue = await self._setup_sse_consumer(task.id)

            # 6. Start async task processing
            asyncio.create_task(self._process_streaming_task(request.params.id, request.params.message))

            # 7. Return SSE response
            return self._dequeue_events_for_sse(request.id, task.id, sse_queue)

        except Exception as e:
            logger.error(f"Error processing streaming task: {e}")
            return JSONRPCResponse(
                id=request.id,
                error=InternalError(message=f"Error processing streaming task: {str(e)}")
            )

    async def on_set_task_push_notification(
        self, request: SetTaskPushNotificationRequest
    ) -> SetTaskPushNotificationResponse:
        """Handle set task push notification request

        Note: The current version does not support task cancellation,
        subclasses can override this method to implement custom cancellation logic
        """
        logger.info(f"Setting task push notification {request.params.id}")
        task_notification_params: TaskPushNotificationConfig = request.params

        try:
            # Set push notification config
            success = await self.notification_handler.set_notification_config(
                task_notification_params.id,
                task_notification_params.pushNotificationConfig
            )

            if not success:
                return SetTaskPushNotificationResponse(
                    id=request.id,
                    error=TaskNotFoundError()
                )

        except Exception as e:
            logger.error(f"Error setting push notification: {e}")
            return SetTaskPushNotificationResponse(
                id=request.id,
                error=InternalError(message=f"Error setting push notification: {str(e)}")
            )

        return SetTaskPushNotificationResponse(id=request.id, result=task_notification_params)

    async def on_get_task_push_notification(
        self, request: GetTaskPushNotificationRequest
    ) -> GetTaskPushNotificationResponse:
        """Handle get task push notification request

        Note: The current version does not support task cancellation,
        subclasses can override this method to implement custom cancellation logic
        """
        logger.info(f"Getting task push notification {request.params.id}")
        task_params: TaskIdParams = request.params

        try:
            # Check if task exists
            task = await self.storage.get_task(task_params.id)
            if task is None:
                return GetTaskPushNotificationResponse(
                    id=request.id,
                    error=TaskNotFoundError()
                )

            # Get push notification config
            notification_config = await self.notification_handler.get_notification_config(task_params.id)
            if notification_config is None:
                return GetTaskPushNotificationResponse(
                    id=request.id,
                    error=TaskNotFoundError(message="Push notification not configured")
                )

        except Exception as e:
            logger.error(f"Error getting push notification: {e}")
            return GetTaskPushNotificationResponse(
                id=request.id,
                error=InternalError(message=f"Error getting push notification: {str(e)}")
            )

        return GetTaskPushNotificationResponse(
            id=request.id,
            result=TaskPushNotificationConfig(
                id=task_params.id,
                pushNotificationConfig=notification_config
            )
        )

    async def on_resubscribe_to_task(
        self, request: TaskResubscriptionRequest
    ) -> Union[AsyncIterable[SendTaskStreamingResponse], JSONRPCResponse]:
        """Handle resubscribe to task request

        Allow clients to resubscribe to previous streaming tasks to receive subsequent updates
        """
        logger.info(f"Resubscribing to task {request.params.id}")
        task_id = request.params.id

        # Check if task exists
        task = await self.storage.get_task(task_id)
        if task is None:
            return JSONRPCResponse(
                id=request.id,
                error=TaskNotFoundError()
            )

        try:
            # Set SSE subscription, marked as resubscribe
            sse_queue = await self._setup_sse_consumer(task_id, is_resubscribe=True)

            # If task is completed, send final status
            if task.status.state in [TaskState.COMPLETED, TaskState.FAILED]:
                await self._enqueue_events_for_sse(
                    task_id,
                    TaskStatusUpdateEvent(
                        id=task_id,
                        status=task.status,
                        final=True
                    )
                )

            # Return SSE response
            return self._dequeue_events_for_sse(request.id, task_id, sse_queue)

        except ValueError as e:
            # Task cannot be resubscribed
            return JSONRPCResponse(
                id=request.id,
                error=TaskNotFoundError(message=str(e))
            )
        except Exception as e:
            logger.error(f"Error resubscribing to task: {e}")
            return JSONRPCResponse(
                id=request.id,
                error=InternalError(message=f"Error resubscribing to task: {str(e)}")
            )

    async def _upsert_task(self, task_send_params: TaskSendParams) -> Task:
        """Create or update task

        Note: The current version does not support task cancellation,
        subclasses can override this method to implement custom cancellation logic
        """
        logger.info(f"Upserting task {task_send_params.id}")

        # Check if task exists
        task = await self.storage.get_task(task_send_params.id)

        if task is None:
            # Create new task
            task = Task(
                id=task_send_params.id,
                sessionId=task_send_params.sessionId,
                messages=[task_send_params.message],
                status=TaskStatus(state=TaskState.SUBMITTED),
                history=[task_send_params.message],
            )
            await self.storage.create_task(task)
        else:
            # Update existing task
            if task.history is None:
                task.history = []
            task.history.append(task_send_params.message)
            await self.storage.update_task(task)

        return task

    async def _update_task_status(
        self, task_id: str, status: TaskStatus, artifacts: List[Artifact]
    ) -> Task:
        """Update task status

        Note: The current version does not support task cancellation,
        subclasses can override this method to implement custom cancellation logic
        """
        # Get task
        task = await self.storage.get_task(task_id)
        if task is None:
            logger.error(f"Task {task_id} not found for updating")
            raise ValueError(f"Task {task_id} not found")

        # Update status
        task.status = status

        # Update message history
        if status.message is not None:
            if task.history is None:
                task.history = []
            task.history.append(status.message)

        # Update artifacts
        if artifacts:
            if task.artifacts is None:
                task.artifacts = []
            task.artifacts.extend(artifacts)

        # Save updated task
        await self.storage.update_task(task)
        return task

    def _append_task_history(self, task: Task, history_length: Optional[int]) -> Task:
        """Handle task history length

        Note: The current version does not support task cancellation,
        subclasses can override this method to implement custom cancellation logic
        """
        new_task = task.model_copy()
        if history_length is not None and history_length > 0:
            new_task.history = new_task.history[-history_length:]
        else:
            new_task.history = []
        return new_task

    async def _setup_sse_consumer(self, task_id: str, is_resubscribe: bool = False) -> asyncio.Queue:
        """Setup SSE consumer

        Note: The current version does not support task cancellation,
        subclasses can override this method to implement custom cancellation logic
        """
        async with self.subscriber_lock:
            if task_id not in self.task_sse_subscribers:
                if is_resubscribe:
                    raise ValueError("Task not found for resubscription")
                else:
                    self.task_sse_subscribers[task_id] = []

            sse_event_queue = asyncio.Queue(maxsize=0)  # Infinite queue size
            self.task_sse_subscribers[task_id].append(sse_event_queue)
            return sse_event_queue

    async def _enqueue_events_for_sse(self, task_id: str, task_update_event: Any) -> None:
        """Enqueue events for SSE

        Note: The current version does not support task cancellation,
        subclasses can override this method to implement custom cancellation logic
        """
        async with self.subscriber_lock:
            if task_id not in self.task_sse_subscribers:
                return

            current_subscribers = self.task_sse_subscribers[task_id]
            for subscriber in current_subscribers:
                await subscriber.put(task_update_event)

    async def _dequeue_events_for_sse(
        self, request_id: str, task_id: str, sse_event_queue: asyncio.Queue
    ) -> AsyncIterable[SendTaskStreamingResponse]:
        """Dequeue events for SSE

        Note: The current version does not support task cancellation,
        subclasses can override this method to implement custom cancellation logic
        """
        try:
            while True:
                event = await sse_event_queue.get()
                if isinstance(event, JSONRPCResponse):
                    yield SendTaskStreamingResponse(id=request_id, error=event.error)
                    break

                yield SendTaskStreamingResponse(id=request_id, result=event)
                if isinstance(event, TaskStatusUpdateEvent) and event.final:
                    break
        finally:
            async with self.subscriber_lock:
                if task_id in self.task_sse_subscribers:
                    self.task_sse_subscribers[task_id].remove(sse_event_queue)

    async def _process_streaming_task(self, task_id: str, message: Message) -> None:
        """Process streaming task

        Note: The current version does not support task cancellation,
        subclasses can override this method to implement custom cancellation logic
        """
        try:
            # 1. Notify subscribers of status change
            await self._enqueue_events_for_sse(
                task_id,
                TaskStatusUpdateEvent(
                    id=task_id,
                    status=TaskStatus(state=TaskState.WORKING)
                )
            )

            # 2. Extract user message
            user_message = self._get_user_query(message)

            # 3. Get task to get session ID
            task = await self.storage.get_task(task_id)
            if task is None:
                raise ValueError(f"Task {task_id} not found")
            session_id = task.sessionId

            # 4. Get conversation history
            conversation_history = await self.history_provider.get_history(session_id)

            # 5. Save user message to history
            await self.history_provider.add_message(
                session_id,
                {"role": "user", "content": user_message}
            )

            # 6. Check Agent
            if self.agent is None:
                raise ValueError("Agent not configured, please provide an Agent instance or override this method")

            # 7. Stream call Agent
            accumulated_response = ""
            async for stream_item in self.agent.stream(user_message, session_id, history=conversation_history):
                # Process stream response item
                state, message, artifacts, is_final = await self.response_processor.process_stream_item(stream_item)

                # Accumulate response content
                if message and hasattr(message, 'parts') and message.parts:
                    stream_text = extract_text_from_message(message)
                    if stream_text:
                        accumulated_response += stream_text

                # If there are artifacts, send artifact update
                if artifacts:
                    for artifact in artifacts:
                        artifact_event = TaskArtifactUpdateEvent(
                            id=task_id,
                            artifact=artifact
                        )
                        await self._enqueue_events_for_sse(task_id, artifact_event)

                # If it is the final state or needs user input, update task status
                if is_final or state != TaskState.WORKING:
                    # Save final assistant reply to history
                    if is_final and accumulated_response:
                        await self.history_provider.add_message(
                            session_id,
                            {"role": "assistant", "content": accumulated_response}
                        )

                    task = await self._update_task_status(
                        task_id,
                        TaskStatus(state=state, message=message),
                        artifacts or []
                    )

                    # Send task update notification
                    await self.notification_handler.send_notification(task)

                    # Send final status update
                    await self._enqueue_events_for_sse(
                        task_id,
                        TaskStatusUpdateEvent(
                            id=task_id,
                            status=TaskStatus(state=state, message=message),
                            final=is_final
                        )
                    )

                    if is_final:
                        break

        except Exception as e:
            logger.error(f"Error processing streaming task: {e}")

            # Update task status to "failed"
            error_message = Message(
                role="agent",
                parts=[TextPart(text=f"Error processing task: {str(e)}")]
            )

            task = await self._update_task_status(
                task_id,
                TaskStatus(state=TaskState.FAILED, message=error_message),
                []
            )

            # Send task update notification
            await self.notification_handler.send_notification(task)

            # Notify subscribers of task failure
            await self._enqueue_events_for_sse(
                task_id,
                TaskStatusUpdateEvent(
                    id=task_id,
                    status=TaskStatus(state=TaskState.FAILED, message=error_message),
                    final=True
                )
            )
