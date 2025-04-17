#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
OpenAI Function Agent 客户端测试示例

此脚本测试 OpenAI Function Agent 服务器的多轮对话功能，
包括同步和流式请求，并且测试多次请求中的会话一致性。

使用方法:
1. 首先运行 openai_function_agent_server.py 启动服务器
2. 然后运行此脚本: python openai_function_agent_client_test.py

关于会话ID (session_id) 的处理:
- 首次请求时不提供会话ID，由服务器生成并返回
- 后续请求中使用服务器返回的会话ID以保持对话上下文
- 这样可以实现多个独立的会话，每个会话有自己的上下文
"""

import asyncio
import logging
import uuid
import time
from typing import List, Dict, Any

from a2a.client import A2AClient
from a2a.types import Message, TextPart, TaskState

# 设置日志级别
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 服务器URL - 匹配服务器启动的端口
SERVER_URL = "http://localhost:5003"
# 测试轮数
TEST_ROUNDS = 3

def extract_session_id(response):
    """从服务器响应中提取会话ID
    
    Args:
        response: 服务器响应对象
        
    Returns:
        str: 提取的会话ID，如果未找到则返回None
    """
    try:
        if response and hasattr(response, "result"):
            # 从直接响应中提取
            if hasattr(response.result, "sessionId") and response.result.sessionId:
                return response.result.sessionId
                
            # 从任务状态中提取
            if hasattr(response.result, "status") and hasattr(response.result.status, "task"):
                if hasattr(response.result.status.task, "sessionId"):
                    return response.result.status.task.sessionId
    except Exception as e:
        logger.error(f"提取会话ID时出错: {e}")
    
    return None

async def test_sync_conversation():
    """测试同步多轮对话"""
    logger.info("开始测试同步多轮对话...")
    
    # 初始化客户端
    client = A2AClient(url=SERVER_URL)
    
    # 准备测试问题
    test_questions = [
        "北京今天的天气怎么样？",
        "上海呢？",
        "谢谢，请问现在的时间是？"
    ]
    
    # 保存历史消息以便在UI中显示完整对话
    message_history = []
    
    # 用于存储会话ID
    session_id = None
    
    # 多轮对话测试
    for i, question in enumerate(test_questions):
        logger.info(f"第 {i+1} 轮对话: {question}")
        
        # 创建用户消息
        user_message = Message(
            role="user",
            parts=[TextPart(text=question)]
        )
        message_history.append(user_message)
        
        # 发送任务
        task_id = f"task-{int(time.time())}"
        
        try:
            # 准备请求参数
            request_params = {
                "id": task_id,
                "message": user_message.model_dump(),
                "history": [msg.model_dump() for msg in message_history[:-1]],  # 不包括当前消息
            }
            
            # 如果不是第一轮对话，添加会话ID
            if session_id is not None:
                logger.info(f"使用已有会话ID: {session_id}")
                request_params["session_id"] = session_id
            else:
                logger.info("首次请求，不提供会话ID")
            
            # 发送请求
            task_response = await client.send_task(request_params)
            
            # 从响应中获取并存储会话ID（如果是第一轮对话）
            if session_id is None:
                extracted_id = extract_session_id(task_response)
                if extracted_id:
                    session_id = extracted_id
                    logger.info(f"从服务器获取会话ID: {session_id}")
            
            logger.info(f"任务ID: {task_response.result.id}")
            logger.info(f"任务状态: {task_response.result.status.state}")
            
            # 如果任务还在进行中，轮询直到完成
            if task_response.result.status.state == "working":  # 使用字符串
                while True:
                    task = await client.get_task({"id": task_id})
                    current_state = task.result.status.state
                    logger.info(f"轮询任务状态: {current_state}")
                    
                    if current_state in ["completed", "failed", "canceled"]:  # 使用字符串
                        logger.info(f"任务状态更新为: {current_state}")
                        task_response = task
                        break
                    await asyncio.sleep(0.5)  # 等待500毫秒再次查询
            
            # 获取代理响应
            response_message = None
            if hasattr(task_response.result, "response") and task_response.result.response:
                response_message = Message.model_validate(task_response.result.response)
                
                # 提取并显示文本响应
                response_text = ""
                for part in response_message.parts:
                    if hasattr(part, "text"):
                        response_text += part.text
                
                logger.info(f"代理响应: {response_text}")
                
                # 将回复添加到历史中
                message_history.append(response_message)
            else:
                logger.warning(f"未收到有效的响应，任务状态: {task_response.result.status.state}")
            
            # 在轮次之间添加一些延时
            if i < len(test_questions) - 1:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"发生错误: {e}")
            break
    
    logger.info("同步多轮对话测试完成")

async def test_streaming_conversation():
    """测试流式多轮对话"""
    logger.info("开始测试流式多轮对话...")
    
    # 初始化客户端
    client = A2AClient(url=SERVER_URL)
    
    # 准备测试问题
    test_questions = [
        "北京现在的天气怎么样？华氏度显示",
        "谢谢，那广州的天气如何？",
        "请告诉我当前时间"
    ]
    
    # 保存历史消息以便在UI中显示完整对话
    message_history = []
    
    # 用于存储会话ID
    session_id = None
    
    # 多轮对话测试
    for i, question in enumerate(test_questions):
        logger.info(f"第 {i+1} 轮对话: {question}")
        
        # 创建用户消息
        user_message = Message(
            role="user",
            parts=[TextPart(text=question)]
        )
        message_history.append(user_message)
        
        # 发送流式任务
        task_id = f"task-stream-{int(time.time())}"
        logger.info(f"流式任务ID: {task_id}")
        
        try:
            # 准备请求参数
            request_params = {
                "id": task_id,
                "message": user_message.model_dump(),
                "history": [msg.model_dump() for msg in message_history[:-1]],  # 不包括当前消息
            }
            
            # 如果不是第一轮对话，添加会话ID
            if session_id is not None:
                logger.info(f"使用已有会话ID: {session_id}")
                request_params["session_id"] = session_id
            else:
                logger.info("首次请求，不提供会话ID")
            
            # 收集流式响应片段
            full_response_text = ""
            
            # 使用超时以避免无限等待
            timeout = 10.0  # 10秒超时
            start_time = time.time()
            
            try:
                # 获取流式响应
                stream_response = client.send_task_streaming(request_params)
                
                async for chunk in stream_response:
                    # 检查超时
                    if time.time() - start_time > timeout:
                        logger.warning(f"流式响应超时，已接收 {len(full_response_text)} 字符")
                        break
                    
                    # 从响应中获取会话ID（如果是第一轮对话）
                    if session_id is None:
                        extracted_id = extract_session_id(chunk)
                        if extracted_id:
                            session_id = extracted_id
                            logger.info(f"从流式响应获取会话ID: {session_id}")
                    
                    if chunk and hasattr(chunk, "result") and chunk.result:
                        # 处理状态更新事件
                        if hasattr(chunk.result, "status") and chunk.result.status:
                            logger.info(f"收到状态更新: {chunk.result.status.state}")
                        
                        # 处理响应内容
                        if hasattr(chunk.result, "response") and chunk.result.response:
                            response = chunk.result.response
                            
                            if hasattr(response, "parts") and response.parts:
                                for part in response.parts:
                                    if hasattr(part, "text") and part.text:
                                        text_chunk = part.text
                                        logger.info(f"流式响应片段: {text_chunk}")
                                        full_response_text += text_chunk
                    
                    # 如果是最终响应，可以提前结束
                    if hasattr(chunk.result, "final") and chunk.result.final:
                        logger.info("收到最终响应标记")
                        break
            
            except Exception as stream_error:
                logger.error(f"处理流式响应时出错: {stream_error}")
            
            logger.info(f"完整流式响应: {full_response_text}")
            
            # 将完整回复添加到历史中
            if full_response_text:
                response_message = Message(
                    role="agent",
                    parts=[TextPart(text=full_response_text)]
                )
                message_history.append(response_message)
            else:
                logger.warning(f"流式响应没有返回有效内容")
            
            # 在轮次之间添加一些延时
            if i < len(test_questions) - 1:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"发生错误: {e}")
            break
    
    logger.info("流式多轮对话测试完成")

async def test_multiple_sessions():
    """测试多个独立会话"""
    logger.info("开始测试多个独立会话...")
    
    # 初始化客户端
    client = A2AClient(url=SERVER_URL)
    
    # 会话1的对话
    session1_questions = [
        "北京今天的天气怎么样？",
        "谢谢，请问现在的时间是？"
    ]
    
    # 会话2的对话
    session2_questions = [
        "上海的天气怎么样？",
        "谢谢，请问美国纽约现在几点了？"
    ]
    
    # 测试会话1
    logger.info("测试会话1:")
    message_history1 = []
    session1_id = None
    
    for i, question in enumerate(session1_questions):
        logger.info(f"会话1 - 第 {i+1} 轮对话: {question}")
        
        user_message = Message(
            role="user",
            parts=[TextPart(text=question)]
        )
        message_history1.append(user_message)
        
        task_id = f"task-s1-{int(time.time())}"
        try:
            # 准备请求参数
            request_params = {
                "id": task_id,
                "message": user_message.model_dump(),
                "history": [msg.model_dump() for msg in message_history1[:-1]],  # 不包括当前消息
            }
            
            # 如果不是第一轮对话，添加会话ID
            if session1_id is not None:
                logger.info(f"会话1 - 使用已有会话ID: {session1_id}")
                request_params["session_id"] = session1_id
            else:
                logger.info("会话1 - 首次请求，不提供会话ID")
            
            # 发送请求
            task_response = await client.send_task(request_params)
            
            # 从响应中获取并存储会话ID（如果是第一轮对话）
            if session1_id is None:
                extracted_id = extract_session_id(task_response)
                if extracted_id:
                    session1_id = extracted_id
                    logger.info(f"会话1 - 从服务器获取会话ID: {session1_id}")
            
            # 等待任务完成
            if task_response.result.status.state == "working":
                while True:
                    task = await client.get_task({"id": task_id})
                    current_state = task.result.status.state
                    logger.info(f"会话1 - 轮询任务状态: {current_state}")
                    
                    if current_state in ["completed", "failed", "canceled"]:
                        logger.info(f"会话1 - 任务状态更新为: {current_state}")
                        task_response = task
                        break
                    await asyncio.sleep(0.5)
            
            # 获取响应
            if hasattr(task_response.result, "response") and task_response.result.response:
                response_message = Message.model_validate(task_response.result.response)
                message_history1.append(response_message)
                
                response_text = ""
                for part in response_message.parts:
                    if hasattr(part, "text"):
                        response_text += part.text
                
                logger.info(f"会话1 - 代理响应: {response_text}")
            else:
                logger.warning(f"会话1 - 未收到有效的响应，任务状态: {task_response.result.status.state}")
            
            await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"会话1错误: {e}")
    
    # 测试会话2
    logger.info("\n测试会话2:")
    message_history2 = []
    session2_id = None
    
    for i, question in enumerate(session2_questions):
        logger.info(f"会话2 - 第 {i+1} 轮对话: {question}")
        
        user_message = Message(
            role="user",
            parts=[TextPart(text=question)]
        )
        message_history2.append(user_message)
        
        task_id = f"task-s2-{int(time.time())}"
        try:
            # 准备请求参数
            request_params = {
                "id": task_id,
                "message": user_message.model_dump(),
                "history": [msg.model_dump() for msg in message_history2[:-1]],  # 不包括当前消息
            }
            
            # 如果不是第一轮对话，添加会话ID
            if session2_id is not None:
                logger.info(f"会话2 - 使用已有会话ID: {session2_id}")
                request_params["session_id"] = session2_id
            else:
                logger.info("会话2 - 首次请求，不提供会话ID")
            
            # 发送请求
            task_response = await client.send_task(request_params)
            
            # 从响应中获取并存储会话ID（如果是第一轮对话）
            if session2_id is None:
                extracted_id = extract_session_id(task_response)
                if extracted_id:
                    session2_id = extracted_id
                    logger.info(f"会话2 - 从服务器获取会话ID: {session2_id}")
            
            # 等待任务完成
            if task_response.result.status.state == "working":
                while True:
                    task = await client.get_task({"id": task_id})
                    current_state = task.result.status.state
                    logger.info(f"会话2 - 轮询任务状态: {current_state}")
                    
                    if current_state in ["completed", "failed", "canceled"]:
                        logger.info(f"会话2 - 任务状态更新为: {current_state}")
                        task_response = task
                        break
                    await asyncio.sleep(0.5)
            
            # 获取响应
            if hasattr(task_response.result, "response") and task_response.result.response:
                response_message = Message.model_validate(task_response.result.response)
                message_history2.append(response_message)
                
                response_text = ""
                for part in response_message.parts:
                    if hasattr(part, "text"):
                        response_text += part.text
                
                logger.info(f"会话2 - 代理响应: {response_text}")
            else:
                logger.warning(f"会话2 - 未收到有效的响应，任务状态: {task_response.result.status.state}")
            
            await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"会话2错误: {e}")
    
    logger.info("多会话测试完成")

async def main():
    """主函数，运行所有测试"""
    logger.info(f"开始测试 OpenAI Function Agent 客户端 (服务器: {SERVER_URL})")
    
    # 测试同步对话
    await test_sync_conversation()
    
    # 短暂暂停
    logger.info("\n等待2秒...\n")
    await asyncio.sleep(2)
    
    # 测试流式对话
    await test_streaming_conversation()
    
    # 短暂暂停
    logger.info("\n等待2秒...\n")
    await asyncio.sleep(2)
    
    # 测试多会话
    await test_multiple_sessions()
    
    logger.info("所有测试完成!")

if __name__ == "__main__":
    asyncio.run(main()) 