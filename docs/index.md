# Versatile

A lightweight dependency injection framework for Python that brings Spring Boot-like capabilities to Python applications.

## Overview

Versatile is a framework for dependency injection using explicit resolution and scoped component graphs. It avoids runtime proxying or hidden magic, instead resolving dependencies once into immutable bundles that can be layered to model global, request, or other application scopes.

## Key Features

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

# Register a component
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

## Documentation

- [Installation](installation.md)
- [Core Concepts](concepts.md)
- [Component Registration](registration.md)
- [Bundle Management](bundles.md)
- [Profiles and Scoping](profiles.md)
- [Advanced Usage](advanced.md)
- [API Reference](api.md)

## Getting Help

- [GitHub Issues](https://github.com/poetix/versatile/issues)
- [Examples](examples.md)