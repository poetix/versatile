# Component Registration

## Basic Registration

### Function Providers

Register functions that create components:

```python
from versatile.registry import ComponentProviderRegistry

registry = ComponentProviderRegistry()

@registry.provides()
def make_database() -> Database:
    return Database("localhost", 5432)

@registry.provides(name="cache")
def make_redis_cache() -> Cache:
    return RedisCache("redis://localhost:6379")
```

### Class Providers

Register classes directly. Their `__init__` methods are used as provider functions.

```python
@registry.provides()
@dataclass()
class UserService:
    db: Database
    cache: Cache
    
    def get_user(self, user_id: str) -> User:
        # Implementation here
        pass
```

## Naming Strategies

### Automatic Names

- Functions: Name derived from function name, removing `make_` prefix
- Classes: Name is the class name

```python
@registry.provides()
def make_database() -> Database:  # Name: "database"
    return Database()

@registry.provides()
class UserService:  # Name: "UserService"
    pass
```

### Explicit Names

```python
@registry.provides(name="primary_db")
def make_database() -> Database:
    return Database()

@registry.provides(name="user_svc")
class UserService:
    pass
```

## Dependencies

### Type-Based Dependencies

Use standard type hints:

```python
@registry.provides()
def make_service(db: Database, cache: Cache) -> Service:
    return Service(db, cache)

@registry.provides()
class UserService:
    db: Database
    cache: Cache
```

### Name-Based Dependencies

Use `Annotated` types to specify component names:

```python
from typing import Annotated

@registry.provides()
def make_service(
    primary: Annotated[Database, "primary_db"],
    secondary: Annotated[Database, "secondary_db"]
) -> Service:
    return Service(primary, secondary)
```

### Mixed Dependencies

You can combine both approaches:

```python
@registry.provides()
def make_service(
    cache: Cache,  # Resolved by type
    db: Annotated[Database, "primary_db"]  # Resolved by name
) -> Service:
    return Service(db, cache)
```

## Type Hierarchies

Classes automatically provide all their parent types:

```python
class BaseService:
    pass

@registry.provides()
class UserService(BaseService):
    pass

# UserService can satisfy dependencies for both UserService and BaseService
```

## Metadata

TODO: explain how custom decorators can add metadata to providers, which is then passed through to their provided components.

[← Previous: Core Concepts](concepts.md) | [Next: Bundle Management →](bundles.md)