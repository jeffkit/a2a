# A2A SDK

Agent to Agent Protocol Python SDK - Supporting Python 3.8-3.13

*[中文文档](README_zh.md)*

## Installation

Install using pip:

```bash
pip install pya2a
```

## Features

- Implements Agent to Agent Protocol client and server
- Supports sending, retrieving, and canceling tasks
- Supports notification configuration
- Supports streaming responses
- Compatible with Python 3.8-3.13

## Usage Examples

### Client Example

```python
import asyncio
from a2a.client import A2AClient
from a2a.types import Message, TextPart

async def main():
    client = A2AClient(url="http://example.com/agent")
    
    # Create task
    task_response = await client.send_task({
        "id": "task-123",
        "message": Message(
            role="user",
            parts=[TextPart(text="Hello, this is a test")]
        )
    })
    
    print(f"Task created successfully: {task_response.result.id}")
    
    # Get task
    task = await client.get_task({"id": "task-123"})
    print(f"Task status: {task.result.status.state}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Streaming Response Example

```python
import asyncio
from a2a.client import A2AClient
from a2a.types import Message, TextPart

async def main():
    client = A2AClient(url="http://example.com/agent")
    
    # Send streaming task request
    async for response in client.send_task_streaming({
        "id": "task-123",
        "message": Message(
            role="user",
            parts=[TextPart(text="Please generate a long text")]
        )
    }):
        if response.result:
            print(response.result)

if __name__ == "__main__":
    asyncio.run(main())
```

## Development Setup

1. Clone the repository:

```bash
git clone https://github.com/your-username/a2a.git
cd a2a
```

2. Install Poetry (if not already installed):

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

3. Install dependencies:

```bash
poetry install
```

4. Activate the virtual environment:

```bash
poetry shell
```

## Testing

Run tests using pytest:

```bash
poetry run pytest
```

### Multi-Python Version Testing

This project supports testing on Python 3.8-3.13. There are several ways to run tests across multiple Python versions:

#### 1. Using tox (Recommended)

First, install tox and the tox-poetry plugin:

```bash
pip install tox tox-poetry
```

Then run the tests:

```bash
tox
```

This will run tests on all Python versions configured in `tox.ini`.

#### 2. Using the Script

We provide a script to automatically run tests on multiple Python versions:

```bash
./scripts/run_tests_multi_python.sh
```

This script requires pyenv to be installed with the appropriate Python versions.

#### 3. GitHub Actions

When you push code to the repository, GitHub Actions will automatically run tests on multiple Python versions. You can view the results in the Actions tab of the GitHub repository.

## Contribution Guidelines

Pull Requests are welcome! Please ensure before submitting:

1. Update tests to reflect your changes
2. Update documentation
3. Your code passes all tests
4. Format code with Black
5. Lint code with Ruff

## Origin

The initial code for this SDK was derived from the common parts of the Google A2A project samples.

## License

MIT
