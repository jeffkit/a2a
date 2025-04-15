# Contributing Guidelines

*[中文版](CONTRIBUTING_zh.md)*

Thank you for your interest in the A2A SDK project! Here are the guidelines for contributing.

## Development Environment Setup

1. Clone the repository

```bash
git clone https://github.com/your-username/a2a.git
cd a2a
```

2. Install Poetry (if not already installed)

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

3. Install dependencies

```bash
poetry install
```

4. Activate virtual environment

```bash
poetry shell
```

## Development Workflow

1. Create a new branch

```bash
git checkout -b feature/your-feature-name
```

2. Implement your changes

Please ensure:
- Code follows PEP 8 standards
- New features include appropriate tests
- All tests pass
- Documentation is updated

3. Code formatting and checking

```bash
# Format code with black
poetry run black a2a tests examples

# Sort imports with isort
poetry run isort a2a tests examples

# Check code with ruff
poetry run ruff a2a tests examples

# Run type checking
poetry run mypy a2a
```

4. Run tests

```bash
poetry run pytest
```

5. Commit your changes

```bash
git add .
git commit -m "Describe your changes"
```

6. Push your code and create a Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub.

## Release Process

1. Update version number

Update the version number in the `a2a/__init__.py` file.

2. Update CHANGELOG.md

3. Create a new release tag

```bash
git tag v0.1.0
git push origin v0.1.0
```

4. The CI system will automatically build and publish to PyPI

## Code Standards

- Follow PEP 8 coding standards
- Use type annotations
- Write clear docstrings
- Add tests for new features
- Maintain backward compatibility

Thank you for your contribution! 