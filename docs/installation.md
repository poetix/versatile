# Installation

## Requirements

- Python 3.9 or higher
- No external dependencies for core functionality

## Installation

Currently, Versatile is not published to PyPI. To install from source:

```bash
git clone https://github.com/poetix/versatile.git
cd versatile
pip install -e .
```

## Development Setup

If you want to contribute to Versatile:

```bash
git clone https://github.com/poetix/versatile.git
cd versatile
pip install -e ".[dev]"
```

This installs the package in development mode with additional tools:
- `pytest` for testing
- `mypy` for type checking
- `ruff` for linting
- `black` for formatting

## Verifying Installation

```python
from versatile.registry import ComponentProviderRegistry
from versatile.builders import make_bundle

registry = ComponentProviderRegistry()

@registry.provides()
def hello() -> str:
    return "Hello, Versatile!"

bundle = make_bundle(registry)
print(bundle["hello"])  # Should print: Hello, Versatile!
```

[← Back to Home](index.md) | [Next: Core Concepts →](concepts.md)