# Core Concepts

## Overview

Versatile implements dependency injection through a three-stage validation pipeline that ensures all dependencies are resolved correctly before any components are created.

## Key Components

### ComponentProvider

A `ComponentProvider` encapsulates metadata about a registered component:

- **name**: Logical name of the component
- **func**: The callable that creates the component
- **profiles**: List of profiles under which the component is active
- **provided_types**: List of types this provider can satisfy
- **dependencies**: List of dependencies this provider needs

### Registry

The `ComponentProviderRegistry` is where you register all your components using decorators:

```python
registry = ComponentProviderRegistry()

@registry.provides()
def make_database() -> Database:
    return Database()

@registry.provides(name="user_service", profiles=["prod"])
class UserService:
    def __init__(self, db: Database):
        self.db = db
```

### Bundle

A `Bundle` is an immutable container of materialized components. Once created, it provides access to all registered components:

```python
bundle = make_bundle(registry)
service = bundle[UserService]
database = bundle["database"]
```

## Dependency Resolution

### Name-Based Dependencies

Use `Annotated` types to specify dependencies by name:

```python
from typing import Annotated

@registry.provides()
def make_service(db: Annotated[Database, "primary_db"]) -> Service:
    return Service(db)
```

### Type-Based Dependencies

Use regular type hints for automatic type-based resolution:

```python
@registry.provides()
def make_service(db: Database) -> Service:
    return Service(db)
```

## Validation Pipeline

Versatile uses a three-stage validation approach:

1. **ProviderSet**: Validates provided component-name uniqueness, and detects type-based dependencies that would be unresolvable for the given set of providers (since more than one provider in the set provides a component of the required type).
2. **BundleManifest**: Resolves dependencies and determines build order.
3. **Bundle**: Materializes components in dependency order.

## Fail-Fast Behavior

By default, Versatile requires all dependencies to be satisfied:

- Root bundles (no parent, no scope): All dependencies must be resolvable
- Child bundles: Can depend on parent components
- Scoped bundles: Can have dependencies injected from external scope

This ensures configuration errors are caught early in development.

[← Previous: Installation](installation.md) | [Next: Component Registration →](registration.md)