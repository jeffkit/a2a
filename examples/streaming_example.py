#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
A2A 客户端流式响应示例
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
        parts=[TextPart(text="请生成一篇短文")]
    )
    
    # 发送流式任务请求
    try:
        print("开始接收流式响应...")
        async for response in client.send_task_streaming({
            "id": "task-stream-123",
            "message": message.model_dump()
        }):
            if response.result:
                if hasattr(response.result, "status"):
                    print(f"状态更新: {response.result.status.state}")
                elif hasattr(response.result, "artifact"):
                    # 处理文本内容
                    for part in response.result.artifact.parts:
                        if part.type == "text":
                            print(f"收到文本: {part.text}")
        
        print("流式响应结束")
        
    except Exception as e:
        print(f"发生错误: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 