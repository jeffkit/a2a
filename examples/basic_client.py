#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
基本的 A2A 客户端示例
"""

import asyncio
import logging
from a2a.client import A2AClient
from a2a.types import Message, TextPart

# 设置日志级别
logging.basicConfig(level=logging.INFO)

async def main():
    # 初始化客户端
    client = A2AClient(url="http://example.com/agent")
    
    # 准备消息
    message = Message(
        role="user",
        parts=[TextPart(text="你好，这是一个简单的测试")]
    )
    
    # 发送任务
    try:
        task_response = await client.send_task({
            "id": "task-123",
            "message": message.model_dump()
        })
        
        print(f"任务创建成功: {task_response.result.id}")
        print(f"任务状态: {task_response.result.status.state}")
        
        # 获取任务状态
        task = await client.get_task({"id": "task-123"})
        print(f"任务状态: {task.result.status.state}")
        
    except Exception as e:
        print(f"发生错误: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 