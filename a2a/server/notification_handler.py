"""Define the notification handler interface for handling task status change notifications."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from a2a.types import Task, PushNotificationConfig


class NotificationHandler(ABC):
    """Notification handler interface, responsible for handling task status change notifications."""
    
    @abstractmethod
    async def set_notification_config(self, task_id: str, config: PushNotificationConfig) -> bool:
        """Set the notification configuration for a task.
        
        Args:
            task_id: Task ID
            config: Notification configuration
            
        Returns:
            Whether the setting is successful
        """
        pass
    
    @abstractmethod
    async def get_notification_config(self, task_id: str) -> Optional[PushNotificationConfig]:
        """Get the notification configuration for a task.
        
        Args:
            task_id: Task ID
            
        Returns:
            Notification configuration, None if not exists
        """
        pass
    
    @abstractmethod
    async def has_notification_config(self, task_id: str) -> bool:
        """Check if a task has a notification configuration.
        
        Args:
            task_id: Task ID
            
        Returns:
            Whether the notification configuration exists
        """
        pass
    
    @abstractmethod
    async def send_notification(self, task: Task) -> bool:
        """Send a notification for a task status change.
        
        Args:
            task: Task object
            
        Returns:
            Whether the notification is sent successfully
        """
        pass
    
    @abstractmethod
    async def verify_notification_url(self, url: str) -> bool:
        """Verify the validity of the notification URL.
        
        Args:
            url: Notification URL
            
        Returns:
            Whether the URL is valid
        """
        pass


class DefaultNotificationHandler(NotificationHandler):
    """Default notification handler implementation, using memory to store notification configurations."""
    
    def __init__(self):
        """Initialize the notification handler."""
        self._configs: Dict[str, PushNotificationConfig] = {}
    
    async def set_notification_config(self, task_id: str, config: PushNotificationConfig) -> bool:
        """Set the notification configuration for a task.
        
        Args:
            task_id: Task ID
            config: Notification configuration
            
        Returns:
            Whether the setting is successful
        """
        if not config.url:
            return False
        
        # Verify the URL
        is_valid = await self.verify_notification_url(config.url)
        if not is_valid:
            return False
        
        self._configs[task_id] = config
        return True
    
    async def get_notification_config(self, task_id: str) -> Optional[PushNotificationConfig]:
        """Get the notification configuration for a task.
        
        Args:
            task_id: Task ID
            
        Returns:
            Notification configuration, None if not exists
        """
        return self._configs.get(task_id)
    
    async def has_notification_config(self, task_id: str) -> bool:
        """Check if a task has a notification configuration.
        
        Args:
            task_id: Task ID
            
        Returns:
            Whether the notification configuration exists
        """
        return task_id in self._configs
    
    async def send_notification(self, task: Task) -> bool:
        """Send a notification for a task status change.
        
        The default implementation only records the notification, does not actually send it.
        Subclasses should implement the actual notification sending logic.
        
        Args:
            task: Task object
            
        Returns:
            Whether the notification is sent successfully
        """
        import logging
        logger = logging.getLogger(__name__)
        
        if not await self.has_notification_config(task.id):
            return False
        
        config = await self.get_notification_config(task.id)
        logger.info(f"Would send notification for task {task.id} to {config.url}")
        return True
    
    async def verify_notification_url(self, url: str) -> bool:
        """Verify the validity of the notification URL.
        
        The default implementation accepts all URLs.
        Subclasses should implement the actual URL validation logic.
        
        Args:
            url: Notification URL
            
        Returns:
            Whether the URL is valid
        """
        return bool(url) 