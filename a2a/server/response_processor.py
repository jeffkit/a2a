"""Define the response processor interface for handling different types of Agent responses."""

from abc import ABC, abstractmethod
from typing import List, Optional, Tuple, Any

from a2a.types import Artifact, Message, TaskState


class ResponseProcessor(ABC):
    """Response processor interface, processing Agent responses and converting them to standard formats.
    
    Different Agents may return different formats of responses, and the response processor is responsible for converting these responses
    into the standard format that Task Manager can handle.
    """
    
    @abstractmethod
    def process_response(self, response: Any) -> Tuple[TaskState, Optional[Message], Optional[List[Artifact]]]:
        """Process the Agent's single response.
        
        Args:
            response: The response object returned by the Agent
            
        Returns:
            A tuple containing:
            - The task state
            - An optional message object
            - An optional list of artifacts
        """
        pass
    
    @abstractmethod
    async def process_stream_item(self, stream_item: Any) -> Tuple[TaskState, Optional[Message], Optional[List[Artifact]], bool]:
        """Process a single item in the Agent's stream response.
        
        Args:
            stream_item: A single item in the Agent's stream response
            
        Returns:
            A tuple containing:
            - The task state
            - An optional message object
            - An optional list of artifacts
            - A boolean value indicating whether it is the last item
        """
        pass


class DefaultResponseProcessor(ResponseProcessor):
    """Default response processor implementation, handling text-based responses."""
    
    def process_response(self, response: Any) -> Tuple[TaskState, Optional[Message], Optional[List[Artifact]]]:
        """Process text-based responses.
        
        Default assumption is that the response is a string, creating a message containing text and an artifact.
        
        Args:
            response: A string response
            
        Returns:
            A tuple containing:
            - The task state
            - An optional message object
            - An optional list of artifacts
        """
        from a2a.types import Message, Artifact, TaskState, TextPart
        
        if isinstance(response, str):
            text = response
            parts = [TextPart(type="text", text=text)]
            message = Message(role="agent", parts=parts)
            artifact = Artifact(parts=parts)
            
            state =  TaskState.COMPLETED
            
            return state, message, [artifact]
        else:
            # Try stringifying the response
            try:
                text = str(response)
                parts = [TextPart(type="text", text=text)]  
                message = Message(role="agent", parts=parts)
                artifact = Artifact(parts=parts)
                return TaskState.COMPLETED, message, [artifact]
            except:
                # Unable to process the response type
                parts = [TextPart(type="text", text="Unable to process the response type")]
                message = Message(role="agent", parts=parts)
                return TaskState.COMPLETED, message, None
    
    async def process_stream_item(self, stream_item: Any) -> Tuple[TaskState, Optional[Message], Optional[List[Artifact]], bool]:
        """Process a single item in the Agent's stream response.
        
        Default assumption is that the item is a dictionary, containing "content" and "is_task_complete" fields.
        
        Args:
            stream_item: A single item in the Agent's stream response
            
        Returns:
            A tuple containing:
            - The task state
            - An optional message object
            - An optional list of artifacts
            - A boolean value indicating whether it is the last item
        """
        from a2a.types import Message, Artifact, TaskState, TextPart
        
        if isinstance(stream_item, dict):
            # Process standard format stream response
            content = stream_item.get("content", "")
            is_complete = stream_item.get("is_task_complete", False)
            require_input = stream_item.get("require_user_input", False)
            
            parts = [TextPart(type="text", text=str(content))]
            message = Message(role="agent", parts=parts)
            
            if not is_complete and not require_input:
                return TaskState.WORKING, message, None, False
            elif require_input:
                return TaskState.INPUT_REQUIRED, message, None, True
            else:
                artifact = Artifact(parts=parts)
                return TaskState.COMPLETED, message, [artifact], True
        else:
            # Try simple string processing
            try:
                text = str(stream_item)
                parts = [TextPart(type="text", text=text)]
                message = Message(role="agent", parts=parts)
                return TaskState.WORKING, message, None, False
            except:
                parts = [TextPart(type="text", text="Unable to process the stream response item")]
                message = Message(role="agent", parts=parts)
                return TaskState.WORKING, message, None, False 