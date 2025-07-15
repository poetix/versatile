# Versatile

[![Documentation](https://img.shields.io/badge/docs-GitHub%20Pages-blue)](https://poetix.github.io/versatile/)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

A lightweight dependency injection framework for Python that brings Spring Boot-like capabilities to Python applications.

## Features

- **Declarative Component Registration**: Use decorators to register components with profile filtering
- **Type-Safe Dependency Injection**: Leverage standard Python type hints for dependency resolution
- **Hierarchical Bundle Scoping**: Create parent-child relationships for request/session isolation
- **Static Dependency Resolution**: Dependencies are resolved at build time with cycle detection
- **Fail-Fast Validation**: Catch configuration errors early with comprehensive validation
- **No Runtime Proxies**: Components are real objects, not proxies

## Quick Start

```python
from versatile.registry import ComponentProviderRegistry
from versatile.builders import make_bundle

# Create a registry
registry = ComponentProviderRegistry()

# Register components
@registry.provides()
def make_database() -> Database:
    return Database()

@registry.provides()
class UserService:
    def __init__(self, db: Database):
        self.db = db

# Build a bundle
bundle = make_bundle(registry)

# Use your components
service = bundle[UserService]
database = bundle[Database]
```

## Installation

```bash
git clone https://github.com/poetix/versatile.git
cd versatile
pip install -e .
```

## Documentation

Full documentation is available at: https://poetix.github.io/versatile/

## License

MIT License - see [LICENSE](LICENSE) file for details.