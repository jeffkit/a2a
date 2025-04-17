"""Define a generic Agent interface as a standardized interface for different Agent frameworks."""

from abc import ABC, abstractmethod
from typing import Any, AsyncIterable, List, Callable, Awaitable, Optional, Dict, TypeVar, Generic, Union

# Define a generic type variable for representing different framework request and response types
T_Request = TypeVar('T_Request')  
T_Response = TypeVar('T_Response')
T_StreamItem = TypeVar('T_StreamItem')

class Agent(ABC):
    """The generic interface that all Agent implementations must follow.
    
    This interface defines the standard methods that an Agent must implement when interacting with Task Manager.
    """
    
    @abstractmethod
    def invoke(self, input: str, session_id: str, history: Optional[List[Dict[str, Any]]] = None, **kwargs) -> Any:
        """Invoke the Agent to process a query.
        
        Args:
            input: The current user input text
            session_id: The session ID for status tracking
            history: The conversation history, typically a list of messages, each containing a role and content
            **kwargs: Additional parameters, passed to the underlying implementation
            
        Returns:
            The result of the Agent processing, the specific type is determined by the implementation
        """
        pass
    
    @abstractmethod
    async def stream(self, input: str, session_id: str, history: Optional[List[Dict[str, Any]]] = None, **kwargs) -> AsyncIterable[Any]:
        """Invoke the Agent to process a query asynchronously.
        
        Args:
            input: The current user input text
            session_id: The session ID for status tracking
            history: The conversation history, typically a list of messages, each containing a role and content
            **kwargs: Additional parameters, passed to the underlying implementation
            
        Returns:
            An asynchronous iterator that produces intermediate results during the processing
        """
        pass
    
    @property
    @abstractmethod
    def supported_content_types(self) -> List[str]:
        """The list of supported content types for the Agent.
        
        Returns:
            A list of supported MIME type strings
        """
        pass

    @staticmethod
    def create(
        invoke_fn: Optional[Callable[..., Any]] = None, 
        stream_fn: Optional[Callable[..., Awaitable[AsyncIterable[Any]]]] = None,
        content_types: List[str] = ["text/plain"],
        agent_instance: Optional[Any] = None,
        invoke_params_mapper: Optional[Callable[[str, str, Optional[List[Dict[str, Any]]], Dict[str, Any]], Dict[str, Any]]] = None,
        stream_params_mapper: Optional[Callable[[str, str, Optional[List[Dict[str, Any]]], Dict[str, Any]], Dict[str, Any]]] = None,
        default_params: Optional[Dict[str, Any]] = None
    ) -> 'Agent':
        """Create an Agent instance, wrapping existing call functions and streaming functions.
        
        This is a convenient factory method for creating an instance that conforms to the Agent interface.
        
        Args:
            invoke_fn: The synchronous call function, can have a custom parameter structure
            stream_fn: The asynchronous streaming call function, can have a custom parameter structure
            content_types: The list of supported content types, default is plain text
            agent_instance: (optional) The actual Agent instance, invoke_fn and stream_fn will use it
            invoke_params_mapper: (optional) The function that maps standard parameters to the parameters required by invoke_fn
            stream_params_mapper: (optional) The function that maps standard parameters to the parameters required by stream_fn
            default_params: (optional) The default parameters used when calling the underlying function
            
        Returns:
            An instance that conforms to the Agent interface
        """
        return GenericAgent(
            invoke_fn=invoke_fn, 
            stream_fn=stream_fn, 
            content_types=content_types, 
            agent_instance=agent_instance,
            invoke_params_mapper=invoke_params_mapper,
            stream_params_mapper=stream_params_mapper,
            default_params=default_params
        )


class GenericAgent(Agent):
    """A generic Agent implementation that can wrap any Agent framework.
    
    By specifying the call method and streaming method, any Agent framework can be wrapped into an implementation that conforms to the Agent interface.
    Supports custom parameter mapping, allowing it to adapt to different framework parameter structures.
    """
    
    def __init__(
        self, 
        invoke_fn: Optional[Callable[..., Any]] = None, 
        stream_fn: Optional[Callable[..., Awaitable[AsyncIterable[Any]]]] = None,
        content_types: List[str] = ["text/plain"],
        agent_instance: Optional[Any] = None,
        invoke_params_mapper: Optional[Callable[[str, str, Optional[List[Dict[str, Any]]], Dict[str, Any]], Dict[str, Any]]] = None,
        stream_params_mapper: Optional[Callable[[str, str, Optional[List[Dict[str, Any]]], Dict[str, Any]], Dict[str, Any]]] = None,
        default_params: Optional[Dict[str, Any]] = None
    ):
        """Initialize the generic Agent implementation.
        
        Args:
            invoke_fn: The synchronous call function, can have a custom parameter structure
            stream_fn: The asynchronous streaming call function, can have a custom parameter structure
            content_types: The list of supported content types, default is plain text
            agent_instance: (optional) The actual Agent instance, invoke_fn and stream_fn will use it
            invoke_params_mapper: (optional) The function that maps standard parameters to the parameters required by invoke_fn
            stream_params_mapper: (optional) The function that maps standard parameters to the parameters required by stream_fn
            default_params: (optional) The default parameters used when calling the underlying function
        """
        self._invoke_fn = invoke_fn
        self._stream_fn = stream_fn
        self._content_types = content_types
        self._agent_instance = agent_instance
        self._default_params = default_params or {}
        
        # Default parameter mapper: preserve original parameter names
        default_mapper = lambda input, session_id, history, kwargs: {
            "input": input, 
            "session_id": session_id, 
            "history": history, 
            **kwargs
        }
        
        self._invoke_params_mapper = invoke_params_mapper or default_mapper
        self._stream_params_mapper = stream_params_mapper or default_mapper
    
    def invoke(self, input: str, session_id: str, history: Optional[List[Dict[str, Any]]] = None, **kwargs) -> Any:
        """Invoke the wrapped invoke function to process the query
        
        Args:
            input: The current user input text
            session_id: The session ID for status tracking
            history: The conversation history, typically a list of messages, each containing a role and content
            **kwargs: Additional parameters, passed to the underlying implementation
            
        Returns:
            The result of the Agent processing
            
        Raises:
            ValueError: If invoke_fn is not set
        """
        if self._invoke_fn is None:
            raise ValueError("Invoke function is not set for this agent")
            
        # Prepare parameters
        all_kwargs = {**self._default_params, **kwargs}
        mapped_params = self._invoke_params_mapper(input, session_id, history, all_kwargs)
        
        # Call the underlying function
        if self._agent_instance is not None and not isinstance(self._invoke_fn, staticmethod):
            # If there is an agent instance and it is not a static method, pass it as the first parameter
            return self._invoke_fn(self._agent_instance, **mapped_params)
        else:
            # Otherwise, call the function directly
            return self._invoke_fn(**mapped_params)
    
    async def stream(self, input: str, session_id: str, history: Optional[List[Dict[str, Any]]] = None, **kwargs) -> AsyncIterable[Any]:
        """Invoke the wrapped stream function to process the query
        
        Args:
            input: The current user input text
            session_id: The session ID for status tracking
            history: The conversation history, typically a list of messages, each containing a role and content
            **kwargs: Additional parameters, passed to the underlying implementation
            
        Returns:
            An asynchronous iterator that produces intermediate results during the processing
            
        Raises:
            ValueError: If stream_fn is not set
        """
        if self._stream_fn is None:
            raise ValueError("Stream function is not set for this agent")
            
        # Prepare parameters
        all_kwargs = {**self._default_params, **kwargs}
        mapped_params = self._stream_params_mapper(input, session_id, history, all_kwargs)
        
        # Call the underlying function
        if self._agent_instance is not None and not isinstance(self._stream_fn, staticmethod):
            # If there is an agent instance and it is not a static method, pass it as the first parameter
            return await self._stream_fn(self._agent_instance, **mapped_params)
        else:
            # Otherwise, call the function directly
            return await self._stream_fn(**mapped_params)
    
    @property
    def supported_content_types(self) -> List[str]:
        """Return the list of supported content types"""
        return self._content_types 