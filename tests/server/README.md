# A2A服务器组件单元测试

这个目录包含了a2a/server包下核心组件的单元测试。

## 测试的组件

该测试套件覆盖了以下模块：

1. `test_types.py` - 测试Agent和GenericAgent类
2. `test_storage.py` - 测试TaskStorage接口的InMemoryStorage实现
3. `test_notification_handler.py` - 测试NotificationHandler功能
4. `test_response_processor.py` - 测试ResponseProcessor功能
5. `test_history_provider.py` - 测试ConversationHistoryProvider功能
6. `test_task_manager.py` - 测试TaskManager实现
7. `test_server.py` - 测试Server启动和基本功能

## 运行测试

从项目根目录运行以下命令执行所有测试：

```bash
pytest tests/server/
```

运行某个特定测试文件：

```bash
pytest tests/server/test_types.py
```

运行某个特定测试类或方法：

```bash
# 运行某个测试类
pytest tests/server/test_types.py::TestAgent

# 运行某个测试方法
pytest tests/server/test_types.py::TestAgent::test_agent_factory_creation
```

## 测试依赖

测试使用了以下主要依赖：

- `pytest` - 测试框架
- `pytest-asyncio` - 支持异步测试
- `aiohttp` - 异步HTTP客户端/服务器
- `unittest.mock` - 提供模拟对象

## 共享工具

`conftest.py`中定义了测试共享的fixtures：

- `mock_agent` - 提供模拟的Agent实现
- `storage` - 提供InMemoryStorage实例
- `history_provider` - 提供InMemoryHistoryProvider实例
- `response_processor` - 提供DefaultResponseProcessor实例
- `notification_handler` - 提供DefaultNotificationHandler实例
- `task_manager` - 提供InMemoryTaskManager实例

还提供了一些辅助函数：

- `create_test_task` - 创建测试用的Task对象
- `create_test_message` - 创建测试用的Message对象
- `async_gen_wrapper` - 将列表转换为异步迭代器

## 扩展测试

添加新测试时，请考虑重用`conftest.py`中的fixtures，以减少重复代码。 