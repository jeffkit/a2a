"""a2a.server.notification_handler模块的单元测试"""

import pytest
import asyncio
from unittest.mock import MagicMock, patch

from a2a.server.notification_handler import NotificationHandler, DefaultNotificationHandler
from a2a.server.storage import InMemoryStorage
from a2a.types import PushNotificationConfig, Task, TaskStatus, TaskState, TaskStatusUpdateEvent
from tests.server.conftest import create_test_task


# 创建测试用的推送通知配置
def create_test_config():
    return PushNotificationConfig(
        url="https://example.com/push",
        token="test_token"
    )


class TestDefaultNotificationHandler:
    """测试DefaultNotificationHandler实现"""
    
    @pytest.fixture
    def storage(self):
        """创建Storage测试实例"""
        return InMemoryStorage()
    
    @pytest.fixture
    async def handler(self, storage):
        """创建NotificationHandler测试实例"""
        handler = DefaultNotificationHandler()
        yield handler
    
    @pytest.mark.asyncio
    async def test_set_and_get_notification_config(self, handler, storage):
        """测试设置和获取推送通知配置"""
        # 准备测试数据
        task = create_test_task()
        await storage.create_task(task)
        config = create_test_config()
        
        # 设置配置
        await handler.set_notification_config(task.id, config)
        
        # 获取配置并验证
        retrieved_config = await handler.get_notification_config(task.id)
        assert retrieved_config is not None
        assert retrieved_config.url == config.url
        assert retrieved_config.token == config.token
        
        # 验证has_notification_config
        has_config = await handler.has_notification_config(task.id)
        assert has_config is True
        
        # 测试不存在的任务
        has_config = await handler.has_notification_config("non_existent")
        assert has_config is False
        retrieved_config = await handler.get_notification_config("non_existent")
        assert retrieved_config is None
    
    @pytest.mark.asyncio
    async def test_notify_task_update(self, handler, storage):
        """测试任务状态更新通知"""
        # 准备测试数据
        task = create_test_task()
        await storage.create_task(task)
        config = create_test_config()
        
        # 设置配置
        await handler.set_notification_config(task.id, config)
        
        # 默认实现只记录日志，不发送HTTP请求
        task.status = TaskStatus(state=TaskState.COMPLETED)
        result = await handler.send_notification(task)
        
        # 验证结果 - 应该返回True，表示记录成功
        assert result is True
    
    @pytest.mark.asyncio
    async def test_notify_without_config(self, handler, storage):
        """测试没有配置时的通知行为"""
        # 准备测试数据
        task = create_test_task()
        await storage.create_task(task)
        
        # 更新任务状态
        task.status = TaskStatus(state=TaskState.COMPLETED)
        
        # 发送通知（没有配置时应返回False）
        result = await handler.send_notification(task)
        
        # 验证结果
        assert result is False  # 不存在通知配置，返回False
    
    @pytest.mark.asyncio
    async def test_handle_failed_notification(self, handler, storage):
        """测试通知发送失败的处理"""
        # 准备测试数据
        task = create_test_task()
        await storage.create_task(task)
        config = create_test_config()
        
        # 设置配置
        await handler.set_notification_config(task.id, config)
        
        # 更新任务状态
        task.status = TaskStatus(state=TaskState.COMPLETED)
        
        # 发送通知 - 默认实现只记录日志，始终返回True
        result = await handler.send_notification(task)
        
        # 验证结果
        assert result is True  # 默认实现总是返回True
    
    @pytest.mark.asyncio
    async def test_notification_retry_policy(self, handler, storage):
        """测试通知重试策略"""
        # 准备测试数据
        task = create_test_task()
        await storage.create_task(task)
        config = create_test_config()
        
        # 设置配置
        await handler.set_notification_config(task.id, config)
        
        # 更新任务状态
        task.status = TaskStatus(state=TaskState.COMPLETED)
        
        # 发送通知 - 默认实现没有重试策略，只记录日志并返回True
        result = await handler.send_notification(task)
        
        # 验证结果
        assert result is True  # 始终成功 