"""History provider module for managing conversation history between Agent and users."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
import json
import logging

from a2a.types import Task, Message, TextPart

logger = logging.getLogger(__name__)

class ConversationHistoryProvider(ABC):
    """Conversation history provider interface, defining standard methods for storing and retrieving conversation history."""
    
    @abstractmethod
    async def get_history(self, session_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get the conversation history for a specific session.
        
        Args:
            session_id: Session ID
            limit: Maximum number of messages to return, None means no limit
            
        Returns:
            List of historical messages, formatted as [{"role": "user"|"assistant", "content": "message content"}, ...]
        """
        pass
    
    @abstractmethod
    async def add_message(self, session_id: str, message: Dict[str, Any]) -> None:
        """Add a message to the conversation history.
        
        Args:
            session_id: Session ID 
            message: Message content, containing role and content fields
        """
        pass
    
    @abstractmethod
    async def clear_history(self, session_id: str) -> None:
        """Clear the history for a specific session.
        
        Args:
            session_id: Session ID
        """
        pass


class InMemoryHistoryProvider(ConversationHistoryProvider):
    """In-memory conversation history provider implementation."""   
    
    def __init__(self):
        """Initialize in-memory storage."""
        self.history_store: Dict[str, List[Dict[str, Any]]] = {}
    
    async def get_history(self, session_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get the conversation history from in-memory storage.
        
        Args:
            session_id: Session ID
            limit: Maximum number of messages to return
            
        Returns:
            List of historical messages
        """
        if session_id not in self.history_store:
            return []
        
        history = self.history_store[session_id]
        if limit is not None and limit > 0:
            return history[-limit:]
        return history
    
    async def add_message(self, session_id: str, message: Dict[str, Any]) -> None:
        """Add a message to in-memory storage.
        
        Args:
            session_id: Session ID
            message: Message content
        """
        if session_id not in self.history_store:
            self.history_store[session_id] = []
        
        self.history_store[session_id].append(message)
    
    async def clear_history(self, session_id: str) -> None:
        """Clear the history from in-memory storage.
        
        Args:
            session_id: Session ID
        """
        if session_id in self.history_store:
            self.history_store[session_id] = []


class RedisHistoryProvider(ConversationHistoryProvider):
    """Redis-based conversation history provider implementation."""
    
    def __init__(self, redis_url: str, key_prefix: str = "chat_history:"):
        """Initialize the Redis history provider.
        
        Args:
            redis_url: Redis connection URL
            key_prefix: Key prefix, default is "chat_history:"
        """
        # Lazy import to avoid mandatory dependency
        try:
            import redis.asyncio as redis
            self.redis = redis.from_url(redis_url)
        except ImportError:
            raise ImportError("Redis library is required to use RedisHistoryProvider: pip install redis")
        
        self.key_prefix = key_prefix
    
    def _get_key(self, session_id: str) -> str:
        """Get the Redis key name.
        
        Args:
            session_id: Session ID
            
        Returns:
            Redis key name
        """
        return f"{self.key_prefix}{session_id}"
    
    async def get_history(self, session_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get the conversation history from Redis.
        
        Args:
            session_id: Session ID
            limit: Maximum number of messages to return
            
        Returns:
            List of historical messages
        """
        key = self._get_key(session_id)
        
        # Use LRANGE to get the list, start as 0, end as -1 means all elements
        # If there is a limit, only get the last limit elements
        start = -limit if limit is not None and limit > 0 else 0
        end = -1
        
        messages = await self.redis.lrange(key, start, end)
        return [json.loads(msg.decode('utf-8')) for msg in messages]
    
    async def add_message(self, session_id: str, message: Dict[str, Any]) -> None:
        """Add a message to Redis.
        
        Args:
            session_id: Session ID
            message: Message content
        """
        key = self._get_key(session_id)
        await self.redis.rpush(key, json.dumps(message))
        
        # Optional: Set expiration time
        # await self.redis.expire(key, 86400)  # 24 hours
    
    async def clear_history(self, session_id: str) -> None:
        """Clear the history from Redis.
        
        Args:
            session_id: Session ID
        """
        key = self._get_key(session_id)
        await self.redis.delete(key)


class TaskBasedHistoryProvider(ConversationHistoryProvider):
    """Compatible implementation for extracting history from Task objects.
    
    This implementation is primarily for backward compatibility, allowing the use of the old task-based history management.
    During the transition to the new history provider architecture, this class can be used to integrate with existing systems.
    
    Note: This class is not recommended for new systems, but only as a transitional measure. New systems should use InMemoryHistoryProvider
    or RedisHistoryProvider.
    """
    
    def __init__(self, storage):
        """Initialize the task history provider.
        
        Args:
            storage: Task storage backend
        """
        self.storage = storage
    
    async def get_history(self, session_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Extract the conversation history from the task object.
        
        Args:
            session_id: Session ID
            limit: Maximum number of messages to return
            
        Returns:
            List of historical messages
        """
        # Get the latest task associated with the session from the storage
        tasks = await self.storage.get_tasks_by_session(session_id)
        if not tasks:
            return []
            
        # Extract the latest task
        latest_task = max(tasks, key=lambda t: getattr(t, 'created_at', 0) or 0)
        
        # Extract the history from the task
        history = self._extract_history_from_task(latest_task)
        
        # Apply the limit
        if limit is not None and limit > 0:
            return history[-limit:]
        return history
    
    def _extract_history_from_task(self, task: Task) -> List[Dict[str, Any]]:
        """Extract the history from a single task.
        
        Args:
            task: Task object
            
        Returns:
            List of historical messages
        """
        history = []
        
        # Extract from the history field
        if task.history:
            for msg in task.history:
                if msg.role and msg.parts:
                    content = self._extract_text_from_message(msg)
                    if content:
                        history.append({
                            "role": "user" if msg.role == "user" else "assistant",
                            "content": content
                        })
        
        # Extract from the artifacts field
        if task.artifacts:
            for artifact in task.artifacts:
                if artifact.type == "message":
                    message_data = artifact.data
                    if isinstance(message_data, dict):
                        if "role" in message_data and "content" in message_data:
                            history.append({
                                "role": message_data["role"],
                                "content": message_data["content"]
                            })
                        # Handle messages containing function calls
                        elif "function_call" in message_data:
                            history.append(message_data)
        
        return history
    
    def _extract_text_from_message(self, message: Message) -> str:
        """Extract the text content from a message.
        
        Args:
            message: Message object
            
        Returns:
            Extracted text content
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
    
    async def add_message(self, session_id: str, message: Dict[str, Any]) -> None:
        """Add a message to the task (this method typically does not need to be executed in TaskBasedHistoryProvider).
        
        Args:
            session_id: Session ID
            message: Message content
        """
        # Since the message is added through the task update, there is no need for additional operations here
        pass
    
    async def clear_history(self, session_id: str) -> None:
        """Clear the task history associated with the session (use with caution).
        
        Args:
            session_id: Session ID
        """
        # This implementation may need to be cautious, as it may delete important task data
        # In a production environment, a more complex implementation or restrictions may be needed
        logger.warning(f"TaskBasedHistoryProvider does not support clearing history, session_id={session_id}")
        pass


def extract_text_from_message(message: Union[Message, Dict[str, Any]]) -> str:
    """Extract the text content from a message object or message dictionary.
    
    Args:
        message: Message object or dictionary containing a content field
        
    Returns:
        Extracted text content
    """
    if isinstance(message, dict):
        return message.get("content", "")
        
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