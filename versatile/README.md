# Versatile

A Python dependency injection framework that emphasizes explicit dependency management, type safety, and hierarchical scoping.

## What It Does

Versatile solves the problem of managing complex object graphs in Python applications by providing:

- **Explicit dependency resolution** using standard Python type hints
- **Hierarchical component scoping** for modeling global, session, and request-level dependencies
- **Profile-based component selection** for different environments (dev, prod, test)
- **Static dependency resolution** that builds immutable component bundles
- **Comprehensive validation** with clear error messages for misconfigurations

## Core Concepts

### Component Registration

Register components using decorators on functions or classes:

```python
from versatile.registry import ComponentProviderRegistry

registry = ComponentProviderRegistry()

# Function providers
@registry.provides()
def make_database() -> Database:
    return Database()

# Class providers  
@registry.provides()
class UserService:
    def __init__(self, db: Database):
        self.db = db
```

### Dependency Resolution

Components can depend on others by type or by name:

```python
# Type-based dependency
@registry.provides()
def make_service(db: Database) -> Service:
    return Service(db)

# Name-based dependency
from typing import Annotated

@registry.provides()
def make_service(db: Annotated[Database, "primary_db"]) -> Service:
    return Service(db)
```

### Bundle Creation

Build immutable containers of resolved components:

```python
from versatile.builders import make_bundle

bundle = make_bundle(registry)
service = bundle[UserService]  # Access by type
database = bundle["database"]  # Access by name
```

### Profile System

Conditionally activate components based on environment:

```python
@registry.provides(profiles=["dev"])
def make_dev_database() -> Database:
    return InMemoryDatabase()

@registry.provides(profiles=["prod"])
def make_prod_database() -> Database:
    return PostgreSQLDatabase()

@registry.provides(profiles=["!test"])  # Active when NOT in test
def make_secure_service() -> Service:
    return SecureService()

# Activate specific profiles
dev_bundle = make_bundle(registry, profiles={"dev"})
prod_bundle = make_bundle(registry, profiles={"prod"})
```

### Hierarchical Scoping

Create parent-child bundle relationships for layered dependency injection:

```python
# Global application components
global_bundle = make_bundle(global_registry)

# Request-scoped components that can depend on global ones
request_bundle = make_bundle(request_registry, parent=global_bundle)

# Session-scoped components
session_bundle = make_bundle(session_registry, parent=request_bundle)
```

## Key Features

### Type Safety
- Uses standard Python type hints for dependency resolution
- Validates type compatibility at bundle creation time
- Provides clear error messages for type mismatches

### Immutable Bundles
- Bundles are immutable once created
- Components are instantiated once in dependency order
- No runtime proxying or lazy loading

### Comprehensive Validation
- Detects circular dependencies
- Validates that all dependencies can be satisfied
- Checks for naming conflicts and type ambiguities
- Provides detailed error messages with resolution suggestions

### External Scope Injection
```python
# Inject dependencies from external scope
bundle = make_bundle(registry, scope={
    "user_id": current_user.id,
    "request_id": request.id
})
```

## Architecture

### Three-Stage Resolution Process

1. **ProviderSet**: Validates provider uniqueness and detects unresolvable type conflicts
2. **BundleManifest**: Resolves dependencies and determines instantiation order
3. **Bundle**: Materializes components in dependency order

### Dependency Graph Resolution
- Builds directed acyclic graph of component dependencies
- Performs topological sort to determine build order
- Detects and reports circular dependencies
- Validates that all dependencies can be satisfied

### Hierarchical Component Lookup
- Child bundles can access parent components
- Components are looked up by name with fallback to parent
- Type-based resolution searches the entire hierarchy
- Prevents parent-child naming conflicts

## Example Usage

### Basic Web Service

```python
from versatile.registry import ComponentProviderRegistry
from versatile.builders import make_bundle

registry = ComponentProviderRegistry()

@registry.provides()
def make_config() -> dict:
    return {"database_url": "postgresql://localhost/app"}

@registry.provides()
def make_database(config: dict) -> Database:
    return Database(config["database_url"])

@registry.provides()
class UserService:
    def __init__(self, db: Database):
        self.db = db
    
    def get_user(self, user_id: str) -> User:
        return self.db.query_user(user_id)

@registry.provides()
class UserController:
    def __init__(self, user_service: UserService):
        self.user_service = user_service
    
    def get_user_endpoint(self, user_id: str) -> dict:
        user = self.user_service.get_user(user_id)
        return {"user": user.to_dict()}

# Create bundle and use components
bundle = make_bundle(registry)
controller = bundle[UserController]
```

### Multi-Environment Configuration

```python
# Base components
@registry.provides()
def make_logger() -> Logger:
    return Logger("app")

# Environment-specific components
@registry.provides(profiles=["dev"])
def make_dev_database() -> Database:
    return SQLiteDatabase(":memory:")

@registry.provides(profiles=["prod"])
def make_prod_database() -> Database:
    return PostgreSQLDatabase(os.getenv("DATABASE_URL"))

@registry.provides(profiles=["test"])
def make_test_database() -> Database:
    return MockDatabase()

# Create environment-specific bundles
dev_bundle = make_bundle(registry, profiles={"dev"})
prod_bundle = make_bundle(registry, profiles={"prod"})
test_bundle = make_bundle(registry, profiles={"test"})
```

### Request Scoping

```python
# Global components
global_registry = ComponentProviderRegistry()

@global_registry.provides()
def make_database() -> Database:
    return Database()

# Request-scoped components
request_registry = ComponentProviderRegistry()

@request_registry.provides()
def make_request_context(
    request: Annotated[Request, "current_request"]
) -> RequestContext:
    return RequestContext(request.user_id, request.session_id)

@request_registry.provides()
def make_user_service(
    db: Database, 
    context: RequestContext
) -> UserService:
    return UserService(db, context)

# Create hierarchical bundles
global_bundle = make_bundle(global_registry)
request_bundle = make_bundle(
    request_registry, 
    parent=global_bundle,
    scope={"current_request": request}
)
```

## Error Handling

The framework provides comprehensive error detection:

```python
from versatile.errors import DependencyError

try:
    bundle = make_bundle(registry)
except DependencyError as e:
    # Handle configuration errors:
    # - Missing dependencies
    # - Circular dependencies  
    # - Type conflicts
    # - Naming conflicts
    # - Parent-child conflicts
    print(f"Configuration error: {e}")
```

## Installation

```bash
git clone https://github.com/poetix/versatile.git
cd versatile
pip install -e .
```

## Requirements

- Python 3.9+
- No external dependencies for core functionality

## License

MIT License