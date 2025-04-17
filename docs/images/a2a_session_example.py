#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
A2A框架会话ID处理示例

本示例展示了如何在A2A框架中正确处理会话ID，包括：
1. 首次请求（不提供session_id）
2. 从响应中提取session_id
3. 后续请求中使用session_id
4. 流式响应中的session_id处理
5. 多会话并行处理
"""

import asyncio
import logging
import json
from uuid import uuid4
from typing import Optional, Dict, Any, List

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 模拟A2A客户端
class A2AClient:
    """模拟A2A客户端实现"""
    
    def __init__(self, url: str):
        self.url = url
        logger.info(f"初始化A2A客户端，连接到服务器: {url}")
    
    async def send_task(self, **params) -> Dict[str, Any]:
        """发送任务到A2A服务器（非流式）"""
        # 在实际实现中，这里会发送HTTP请求到服务器
        logger.info(f"发送任务: {json.dumps(params, ensure_ascii=False)}")
        
        # 模拟服务器响应
        await asyncio.sleep(1)  # 模拟网络延迟
        
        # 如果客户端没有提供session_id，服务器会生成一个
        if 'sessionId' not in params:
            session_id = uuid4().hex
            logger.info(f"服务器生成新的session_id: {session_id}")
        else:
            session_id = params['sessionId']
            logger.info(f"使用客户端提供的session_id: {session_id}")
        
        # 构造响应
        response = {
            'task_status': {
                'id': params['id'],
                'sessionId': session_id,
                'state': 'completed',
                'message': f"回复: {params['message']}"
            },
            'content': "这是服务器的回复内容"
        }
        
        return response
    
    async def send_task_streaming(self, **params):
        """发送任务到A2A服务器（流式）"""
        # 在实际实现中，这里会发送HTTP请求到服务器并获取流式响应
        logger.info(f"发送流式任务: {json.dumps(params, ensure_ascii=False)}")
        
        # 如果客户端没有提供session_id，服务器会生成一个
        if 'sessionId' not in params:
            session_id = uuid4().hex
            logger.info(f"服务器生成新的流式session_id: {session_id}")
        else:
            session_id = params['sessionId']
            logger.info(f"使用客户端提供的流式session_id: {session_id}")
        
        # 模拟流式响应
        # 第一个块包含状态信息和session_id
        yield {
            'task_status': {
                'id': params['id'],
                'sessionId': session_id,
                'state': 'running',
            },
            'content': ""
        }
        
        # 模拟内容块
        chunks = ["这是", "服务器", "的", "流式", "回复", "内容"]
        for chunk in chunks:
            await asyncio.sleep(0.5)  # 模拟网络延迟
            yield {
                'task_status': {
                    'id': params['id'],
                    'sessionId': session_id,
                    'state': 'running',
                },
                'content': chunk
            }
        
        # 最后一个块标记完成
        await asyncio.sleep(0.5)
        yield {
            'task_status': {
                'id': params['id'],
                'sessionId': session_id,
                'state': 'completed',
            },
            'content': "。"
        }


def extract_session_id(response) -> Optional[str]:
    """从响应中提取session_id"""
    try:
        if response and isinstance(response, dict) and 'task_status' in response:
            return response['task_status'].get('sessionId')
    except Exception as e:
        logger.error(f"提取session_id时出错: {e}")
    return None


async def basic_conversation_example():
    """基本会话示例"""
    logger.info("开始基本会话示例")
    
    # 初始化客户端
    client = A2AClient(url="http://localhost:8000")
    
    # 初始化会话ID为None
    session_id = None
    
    # 首次请求（不提供session_id）
    logger.info("发送首次请求（不包含session_id）")
    first_response = await client.send_task(
        id=str(uuid4()),
        message="你好，请问今天的天气如何？"
        # 不包含session_id
    )
    
    # 从响应中提取session_id
    session_id = extract_session_id(first_response)
    logger.info(f"从首次响应中提取到session_id: {session_id}")
    
    # 后续请求（包含session_id）
    logger.info("发送后续请求（包含session_id）")
    second_response = await client.send_task(
        id=str(uuid4()),
        message="明天的天气预报怎么样？",
        sessionId=session_id  # 包含之前获取的session_id
    )
    
    # 验证后续响应中的session_id保持一致
    second_session_id = extract_session_id(second_response)
    logger.info(f"后续响应中的session_id: {second_session_id}")
    assert session_id == second_session_id, "会话ID不一致！"
    
    logger.info("基本会话示例完成")


async def streaming_conversation_example():
    """流式会话示例"""
    logger.info("开始流式会话示例")
    
    # 初始化客户端
    client = A2AClient(url="http://localhost:8000")
    
    # 初始化会话ID为None
    session_id = None
    
    # 首次流式请求（不提供session_id）
    logger.info("发送首次流式请求（不包含session_id）")
    
    # 收集完整响应内容
    full_content = ""
    
    # 处理流式响应
    async for chunk in client.send_task_streaming(
        id=str(uuid4()),
        message="请介绍一下北京的著名景点"
        # 不包含session_id
    ):
        # 尝试从每个块中提取session_id（如果还没有获取到）
        if not session_id:
            session_id = extract_session_id(chunk)
            if session_id:
                logger.info(f"从流式响应块中提取到session_id: {session_id}")
        
        # 处理内容
        if 'content' in chunk and chunk['content']:
            full_content += chunk['content']
    
    logger.info(f"首次流式响应的完整内容: {full_content}")
    
    # 后续流式请求（包含session_id）
    logger.info("发送后续流式请求（包含session_id）")
    
    # 重置内容收集
    full_content = ""
    
    # 处理后续流式响应
    async for chunk in client.send_task_streaming(
        id=str(uuid4()),
        message="那上海呢？",
        sessionId=session_id  # 包含之前获取的session_id
    ):
        # 处理内容
        if 'content' in chunk and chunk['content']:
            full_content += chunk['content']
    
    logger.info(f"后续流式响应的完整内容: {full_content}")
    logger.info("流式会话示例完成")


async def multi_session_example():
    """多会话并行处理示例"""
    logger.info("开始多会话并行处理示例")
    
    # 初始化客户端
    client = A2AClient(url="http://localhost:8000")
    
    # 会话1
    session1_id = None
    logger.info("开始会话1")
    
    # 会话1的首次请求
    response1 = await client.send_task(
        id=str(uuid4()),
        message="请介绍一下中国的历史"
    )
    session1_id = extract_session_id(response1)
    logger.info(f"会话1的session_id: {session1_id}")
    
    # 会话2
    session2_id = None
    logger.info("开始会话2（与会话1完全独立）")
    
    # 会话2的首次请求
    response2 = await client.send_task(
        id=str(uuid4()),
        message="请介绍一下美国的历史"
    )
    session2_id = extract_session_id(response2)
    logger.info(f"会话2的session_id: {session2_id}")
    
    # 验证两个会话ID不同
    assert session1_id != session2_id, "两个独立会话的session_id相同！"
    
    # 会话1的后续请求
    logger.info("会话1的后续请求")
    await client.send_task(
        id=str(uuid4()),
        message="具体说说明朝的历史",
        sessionId=session1_id
    )
    
    # 会话2的后续请求
    logger.info("会话2的后续请求")
    await client.send_task(
        id=str(uuid4()),
        message="具体说说美国独立战争",
        sessionId=session2_id
    )
    
    logger.info("多会话并行处理示例完成")


async def main():
    """主函数"""
    logger.info("A2A框架会话ID处理示例程序开始运行")
    
    # 运行基本会话示例
    await basic_conversation_example()
    
    # 运行流式会话示例
    await streaming_conversation_example()
    
    # 运行多会话并行处理示例
    await multi_session_example()
    
    logger.info("A2A框架会话ID处理示例程序运行完成")


if __name__ == "__main__":
    asyncio.run(main()) 