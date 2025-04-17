#!/bin/bash

# 启动测试脚本
# 该脚本启动 AutoGen Agent 服务器并运行客户端测试

echo "===== AutoGen Agent 测试 ====="

# 判断是否安装了必要工具
if ! command -v pip &> /dev/null; then
    echo "错误: 未找到 pip 命令"
    exit 1
fi

# 安装必要的依赖
echo "安装依赖..."
pip install -r ../requirements-examples.txt
pip install -e ../..

# 检查端口是否被占用
if lsof -i:5002 &> /dev/null; then
    echo "警告: 端口 5002 已被占用，正在尝试关闭..."
    kill $(lsof -t -i:5002) 2>/dev/null || true
    sleep 2
fi

# 确保工作目录存在
echo "确保工作目录存在..."
mkdir -p agent_workspace

# 启动服务器（后台运行）
echo "启动 AutoGen Agent 服务器..."
python autogen_agent_server.py &
SERVER_PID=$!

# 检查服务器是否成功启动
echo "等待服务器启动..."
sleep 3  # 给服务器一些启动时间

# 检查服务器进程是否存在
if ! ps -p $SERVER_PID > /dev/null; then
    echo "错误: 服务器进程已退出"
    exit 1
fi

# 检查服务器是否正在监听端口
for i in {1..10}; do
    if curl -s -o /dev/null http://localhost:5002; then
        echo "服务器已启动，可以访问"
        break
    fi
    
    if [ $i -eq 10 ]; then
        echo "错误: 服务器未能在预期时间内启动"
        kill $SERVER_PID 2>/dev/null || true
        exit 1
    fi
    
    echo "等待服务器启动... ($i/10)"
    sleep 2
done

# 运行客户端测试
echo "运行客户端测试..."
python autogen_agent_client_test.py
TEST_EXIT_CODE=$?

# 测试完成后关闭服务器
echo "测试完成，关闭服务器..."
kill $SERVER_PID 2>/dev/null || true
sleep 1

# 确保服务器已关闭
if ps -p $SERVER_PID > /dev/null 2>&1; then
    echo "服务器未能正常关闭，强制终止..."
    kill -9 $SERVER_PID 2>/dev/null || true
fi

echo "===== 测试结束 ====="

# 返回测试的退出代码
exit $TEST_EXIT_CODE 