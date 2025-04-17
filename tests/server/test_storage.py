"""a2a.server.storage模块的单元测试"""

import pytest
import asyncio
import uuid
from typing import Dict, List, Optional

from a2a.server.storage import TaskStorage, InMemoryStorage
from a2a.types import Task, TaskStatus, TaskState, PushNotificationConfig
from tests.server.conftest import create_test_task


# 创建测试用的推送通知配置
def create_push_notification_config():
    return PushNotificationConfig(
        url="https://example.com/push",
        token="test_token",
    )


class TestInMemoryStorage:
    """测试InMemoryStorage实现"""
    
    @pytest.fixture
    def storage(self):
        """创建InMemoryStorage测试实例"""
        return InMemoryStorage()
    
    @pytest.mark.asyncio
    async def test_create_and_get_task(self, storage):
        """测试创建和获取任务"""
        # 创建测试任务
        task = create_test_task()
        
        # 存储任务
        await storage.create_task(task)
        
        # 获取任务并验证
        retrieved_task = await storage.get_task(task.id)
        assert retrieved_task is not None
        assert retrieved_task.id == task.id
        assert retrieved_task.sessionId == task.sessionId
        assert retrieved_task.status.state == task.status.state
    
    @pytest.mark.asyncio
    async def test_update_task(self, storage):
        """测试更新任务"""
        # 创建并存储测试任务
        task = create_test_task(status_state=TaskState.SUBMITTED)
        await storage.create_task(task)
        
        # 更新任务状态
        updated_task = task.model_copy()
        updated_task.status.state = TaskState.WORKING
        await storage.update_task(updated_task)
        
        # 获取更新后的任务并验证
        retrieved_task = await storage.get_task(task.id)
        assert retrieved_task is not None
        assert retrieved_task.status.state == TaskState.WORKING
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_task(self, storage):
        """测试获取不存在的任务"""
        non_existent_id = "non_existent_id"
        task = await storage.get_task(non_existent_id)
        assert task is None
    
    @pytest.mark.asyncio
    async def test_get_tasks_by_session(self, storage):
        """测试通过会话ID获取任务"""
        # 创建两个不同会话的任务
        session1 = "session1"
        session2 = "session2"
        
        task1 = create_test_task(session_id=session1)
        task2 = create_test_task(session_id=session1)
        task3 = create_test_task(session_id=session2)
        
        # 存储任务
        await storage.create_task(task1)
        await storage.create_task(task2)
        await storage.create_task(task3)
        
        # 获取session1的任务
        session1_tasks = await storage.get_tasks_by_session(session1)
        assert len(session1_tasks) == 2
        task_ids = [task.id for task in session1_tasks]
        assert task1.id in task_ids
        assert task2.id in task_ids
        
        # 获取session2的任务
        session2_tasks = await storage.get_tasks_by_session(session2)
        assert len(session2_tasks) == 1
        assert session2_tasks[0].id == task3.id
    
    @pytest.mark.asyncio
    async def test_delete_task(self, storage):
        """测试删除任务"""
        # 创建并存储测试任务
        task = create_test_task()
        await storage.create_task(task)
        
        # 确认任务存在
        assert await storage.get_task(task.id) is not None
        
        # 删除任务
        result = await storage.delete_task(task.id)
        assert result is True
        
        # 确认任务已被删除
        assert await storage.get_task(task.id) is None
        
        # 尝试删除不存在的任务
        result = await storage.delete_task("non_existent_id")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_push_notification_operations(self, storage):
        """测试推送通知相关操作"""
        # 创建并存储测试任务
        task = create_test_task()
        await storage.create_task(task)
        
        # 创建推送通知配置
        config = create_push_notification_config()
        
        # 设置推送通知配置
        result = await storage.set_push_notification(task.id, config)
        assert result is True
        
        # 检查是否有推送通知配置
        has_config = await storage.has_push_notification(task.id)
        assert has_config is True
        
        # 获取并验证推送通知配置
        retrieved_config = await storage.get_push_notification(task.id)
        assert retrieved_config is not None
        assert retrieved_config.url == config.url
        assert retrieved_config.token == config.token
        
        # 测试为不存在的任务设置推送通知
        result = await storage.set_push_notification("non_existent_id", config)
        assert result is False
        
        # 获取不存在的任务的推送通知配置
        config = await storage.get_push_notification("non_existent_id")
        assert config is None
        
        # 检查不存在的任务是否有推送通知配置
        has_config = await storage.has_push_notification("non_existent_id")
        assert has_config is False
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self, storage):
        """测试并发操作"""
        # 创建基础任务
        base_task = create_test_task()
        await storage.create_task(base_task)
        
        # 定义并发更新操作
        async def update_task_status(task_id, status_state):
            task = await storage.get_task(task_id)
            task.status.state = status_state
            await asyncio.sleep(0.01)  # 模拟操作延迟
            await storage.update_task(task)
            return status_state
        
        # 并发执行更新操作
        update1 = asyncio.create_task(update_task_status(base_task.id, TaskState.WORKING))
        update2 = asyncio.create_task(update_task_status(base_task.id, TaskState.COMPLETED))
        
        # 等待所有操作完成
        results = await asyncio.gather(update1, update2)
        
        # 获取最终任务状态
        final_task = await storage.get_task(base_task.id)
        
        # 验证最终状态是最后一个更新的状态
        assert final_task.status.state in results 