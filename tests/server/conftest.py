"""a2a.server测试的共享fixtures和工具函数"""

import pytest
import uuid
import asyncio
from typing import List, Dict, Any, AsyncIterable
from datetime import datetime

from a2a import Message, TextPart
from a2a.server.types import Agent, GenericAgent
from a2a.server.storage import InMemoryStorage
from a2a.server.task_manager import InMemoryTaskManager
from a2a.server.history_provider import InMemoryHistoryProvider
from a2a.server.response_processor import DefaultResponseProcessor
from a2a.server.notification_handler import DefaultNotificationHandler
from a2a.types import Task, TaskStatus, TaskState, PushNotificationConfig


async def async_gen_wrapper(items):
    """辅助函数，将列表转换为异步迭代器"""
    for item in items:
        yield item


@pytest.fixture
def mock_agent():
    """创建模拟Agent用于测试"""
    # 创建同步响应
    def mock_invoke(input, session_id, history=None, **kwargs):
        return f"这是对 '{input}' 的模拟响应"
    
    # 创建异步流式响应
    async def mock_stream(input, session_id, history=None, **kwargs):
        chunks = [f"这是对 '{input}' 的", "模拟流式", "响应"]
        for chunk in chunks:
            yield chunk
    
    # 创建并返回Agent
    return GenericAgent(
        invoke_fn=mock_invoke,
        stream_fn=mock_stream,
        content_types=["text/plain"]
    )


@pytest.fixture
def storage():
    """创建存储实例"""
    return InMemoryStorage()


@pytest.fixture
def history_provider():
    """创建历史记录提供器实例"""
    return InMemoryHistoryProvider()


@pytest.fixture
def response_processor():
    """创建响应处理器实例"""
    return DefaultResponseProcessor()


@pytest.fixture
async def notification_handler(storage):
    """创建通知处理器实例"""
    handler = DefaultNotificationHandler(storage)
    yield handler
    # 清理运行中的任务
    for task in handler._notification_tasks.values():
        task.cancel()


@pytest.fixture
async def task_manager(mock_agent):
    """创建任务管理器实例"""
    manager = InMemoryTaskManager()
    # 设置模拟Agent
    manager._delegate.agent = mock_agent
    yield manager


def create_test_task(session_id="test_session", status_state=TaskState.SUBMITTED, task_id=None):
    """创建测试任务
    
    Args:
        session_id: 会话ID
        status_state: TaskState枚举值，表示任务状态
        task_id: 任务ID，如果不提供则自动生成
    
    Returns:
        Task: 测试任务实例
    """
    if task_id is None:
        task_id = str(uuid.uuid4())
    
    # 创建TaskStatus对象
    status = TaskStatus(
        state=status_state,
        timestamp=datetime.now()
    )
    
    return Task(
        id=task_id,
        sessionId=session_id,
        status=status,
        artifacts=[]
    )


def create_test_message(text="测试消息", role="user"):
    """创建测试消息"""
    return Message(
        role=role,
        content=[TextPart(text=text)]
    ) 