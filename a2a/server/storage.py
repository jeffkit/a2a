from abc import ABC, abstractmethod
import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, Set, Union

from a2a.types import (
    Task, TaskStatus, Artifact, PushNotificationConfig
)

logger = logging.getLogger(__name__)

class TaskStorage(ABC):
    """Task storage interface, defining methods for storing and retrieving task data"""
    
    @abstractmethod
    async def create_task(self, task: Task) -> None:
        """Create a new task
        
        Args:
            task: The task to create
        """
        pass
    
    @abstractmethod
    async def update_task(self, task: Task) -> None:
        """Update an existing task
        
        Args:
            task: The task to update
        """
        pass
    
    @abstractmethod
    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get a specific task
        
        Args:
            task_id: The task ID
            
        Returns:
            The task object, or None if it does not exist
        """
        pass
    
    @abstractmethod
    async def get_tasks_by_session(self, session_id: str) -> List[Task]:
        """Get all tasks associated with a specific session
        
        Args:
            session_id: The session ID
            
        Returns:
            A list of task objects, or an empty list if there are no tasks
        """
        pass
    
    @abstractmethod
    async def delete_task(self, task_id: str) -> bool:
        """Delete a task
        
        Args:
            task_id: The task ID
            
        Returns:
            True if the task was deleted, False if it does not exist
        """
        pass
    
    @abstractmethod
    async def set_push_notification(self, task_id: str, config: PushNotificationConfig) -> bool:
        """Set the push notification configuration for a task
        
        Args:
            task_id: The task ID
            config: The push notification configuration
        """
        pass
    
    @abstractmethod
    async def get_push_notification(self, task_id: str) -> Optional[PushNotificationConfig]:
        """Get the push notification configuration for a task
        
        Args:
            task_id: The task ID
            
        Returns:
            The push notification configuration, or None if it does not exist
        """
        pass
    
    @abstractmethod
    async def has_push_notification(self, task_id: str) -> bool:
        """Check if a task has a push notification configuration
        
        Args:
            task_id: The task ID
            
        Returns:
            True if the task has a push notification configuration, False otherwise
        """
        pass


class InMemoryStorage(TaskStorage):
    """内存任务存储实现，适用于开发和测试"""
    
    def __init__(self):
        """Initialize in-memory storage"""
        self.tasks: Dict[str, Task] = {}
        self.push_notifications: Dict[str, PushNotificationConfig] = {}
        self.lock = asyncio.Lock()
    
    async def create_task(self, task: Task) -> None:
        """Create a task in memory"""
        async with self.lock:
            self.tasks[task.id] = task
    
    async def update_task(self, task: Task) -> None:
        """Update a task in memory"""
        async with self.lock:
            self.tasks[task.id] = task
    
    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task from memory"""
        async with self.lock:
            return self.tasks.get(task_id)
    
    async def get_tasks_by_session(self, session_id: str) -> List[Task]:
        """Get tasks associated with a session ID
        
        Args:
            session_id: The session ID
            
        Returns:
            A list of task objects, or an empty list if there are no tasks
        """
        async with self.lock:
            return [task for task in self.tasks.values() if task.sessionId == session_id]
    
    async def delete_task(self, task_id: str) -> bool:
        async with self.lock:
            if task_id in self.tasks:
                del self.tasks[task_id]
                return True
            return False
    
    async def set_push_notification(self, task_id: str, config: PushNotificationConfig) -> bool:
        async with self.lock:
            if task_id not in self.tasks:
                return False
            self.push_notifications[task_id] = config
            return True
    
    async def get_push_notification(self, task_id: str) -> Optional[PushNotificationConfig]:
        async with self.lock:
            return self.push_notifications.get(task_id)
    
    async def has_push_notification(self, task_id: str) -> bool:
        async with self.lock:
            return task_id in self.push_notifications


class RedisStorage(TaskStorage):
    """Redis storage implementation
    
    Uses Redis to store task data, suitable for production and distributed deployments
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0", prefix: str = "a2a:"):
        """
        Initialize Redis storage
        
        Args:
            redis_url: Redis connection URL
            prefix: Key prefix, used to distinguish data from different applications
        """
        self.redis_url = redis_url
        self.prefix = prefix
        self.redis = None
        self._ensure_redis()
    
    def _ensure_redis(self):
        """Ensure Redis connection is available"""
        if self.redis is None:
            try:
                import redis.asyncio as aioredis
                self.redis = aioredis.from_url(self.redis_url)
            except ImportError:
                logger.error("Redis dependency not installed, please use pip install redis")
                raise ImportError("Redis dependency not installed, please use pip install redis")
    
    def _task_key(self, task_id: str) -> str:
        """Generate task key name"""
        return f"{self.prefix}task:{task_id}"
    
    def _push_notification_key(self, task_id: str) -> str:
        """Generate push notification key name"""
        return f"{self.prefix}push:{task_id}"
    
    async def get_task(self, task_id: str) -> Optional[Task]:
        self._ensure_redis()
        task_data = await self.redis.get(self._task_key(task_id))
        if not task_data:
            return None
        
        try:
            task_dict = json.loads(task_data)
            return Task.model_validate(task_dict)
        except Exception as e:
            logger.error(f"Error parsing task data: {e}")
            return None
    
    async def create_task(self, task: Task) -> Task:
        self._ensure_redis()
        task_data = task.model_dump_json()
        await self.redis.set(self._task_key(task.id), task_data)
        return task
    
    async def update_task(self, task: Task) -> Task:
        self._ensure_redis()
        task_data = task.model_dump_json()
        await self.redis.set(self._task_key(task.id), task_data)
        return task
    
    async def delete_task(self, task_id: str) -> bool:
        self._ensure_redis()
        result = await self.redis.delete(self._task_key(task_id))
        return result > 0
    
    async def set_push_notification(self, task_id: str, config: PushNotificationConfig) -> bool:
        self._ensure_redis()
        # Check if the task exists
        if not await self.redis.exists(self._task_key(task_id)):
            return False
        
        config_data = config.model_dump_json()
        await self.redis.set(self._push_notification_key(task_id), config_data)
        return True
    
    async def get_push_notification(self, task_id: str) -> Optional[PushNotificationConfig]:
        self._ensure_redis()
        config_data = await self.redis.get(self._push_notification_key(task_id))
        if not config_data:
            return None
        
        try:
            config_dict = json.loads(config_data)
            return PushNotificationConfig.model_validate(config_dict)
        except Exception as e:
            logger.error(f"Error parsing push notification config: {e}")
            return None
    
    async def has_push_notification(self, task_id: str) -> bool:
        self._ensure_redis()
        return bool(await self.redis.exists(self._push_notification_key(task_id))) 