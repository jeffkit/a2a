#!/bin/bash

# 多Python版本测试脚本
# 此脚本使用pyenv来在不同Python版本中运行测试

# 检查pyenv是否安装
if ! command -v pyenv &> /dev/null; then
    echo "错误: 未安装pyenv。请先安装pyenv: https://github.com/pyenv/pyenv#installation"
    exit 1
fi

# 需要测试的Python版本
PYTHON_VERSIONS=("3.8" "3.9" "3.10" "3.11" "3.12")
SUCCESS=0
FAILED=0

# 创建日志目录
mkdir -p logs

# 运行每个Python版本的测试
for version in "${PYTHON_VERSIONS[@]}"; do
    # 检查是否有对应版本安装
    if ! pyenv versions | grep -q "$version"; then
        echo "警告: 未找到Python $version，跳过此版本测试。"
        echo "可以运行 'pyenv install $version' 来安装此版本。"
        continue
    fi
    
    echo "================================================================="
    echo "开始使用 Python $version 运行测试..."
    echo "================================================================="
    
    # 使用对应的Python版本
    export PYENV_VERSION=$version
    
    # 创建虚拟环境名
    VENV_NAME="venv-py$version"
    
    # 创建虚拟环境
    echo "创建Python $version 虚拟环境..."
    python -m venv "$VENV_NAME"
    
    # 激活虚拟环境
    source "$VENV_NAME/bin/activate"
    
    # 安装poetry（如果未安装）
    if ! command -v poetry &> /dev/null; then
        echo "安装 poetry..."
        pip install poetry
    fi
    
    # 安装项目依赖
    echo "安装项目依赖..."
    poetry install
    
    # 运行测试
    echo "运行测试..."
    TEST_LOG="logs/test-py$version.log"
    poetry run pytest -v | tee "$TEST_LOG"
    
    # 检查测试结果
    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        echo "Python $version 测试成功！"
        SUCCESS=$((SUCCESS+1))
    else
        echo "Python $version 测试失败！查看日志: $TEST_LOG"
        FAILED=$((FAILED+1))
    fi
    
    # 退出虚拟环境
    deactivate
    
    echo ""
done

# 输出总结
echo "================================================================="
echo "测试总结:"
echo "成功: $SUCCESS"
echo "失败: $FAILED"
echo "================================================================="

if [ $FAILED -gt 0 ]; then
    exit 1
fi

exit 0 