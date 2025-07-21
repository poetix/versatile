# Profiles and Scoping

## Profile-Based Component Selection

Profiles allow you to conditionally activate components based on environment or configuration.

### Basic Profiles

```python
@registry.provides(profiles=["dev"])
def make_dev_database() -> Database:
    return InMemoryDatabase()

@registry.provides(profiles=["prod"])
def make_prod_database() -> Database:
    return PostgreSQLDatabase()

# Activate dev profile
bundle = make_bundle(registry, profiles={"dev"})
```

### Multiple Profiles

Components can be active in multiple profiles:

```python
@registry.provides(profiles=["dev", "test"])
def make_mock_service() -> ExternalService:
    return MockExternalService()

@registry.provides(profiles=["prod", "staging"])
def make_real_service() -> ExternalService:
    return RealExternalService()
```

### Profile Exclusion

Use `!` prefix to exclude profiles:

```python
@registry.provides(profiles=["!test"])
def make_real_database() -> Database:
    return PostgreSQLDatabase()

@registry.provides(profiles=["test"])
def make_test_database() -> Database:
    return InMemoryDatabase()
```

### Default Components

Components without profiles are active in all profiles:

```python
@registry.provides()  # Active in all profiles
def make_config() -> Config:
    return Config()
```

## Scoping with External Dependencies

### Transient Scope

Provide dependencies from external scope for transient components:

```python
@registry.provides()
def make_request_handler(request: Annotated[Request, "current_request"]) -> Handler:
    return Handler(request)

# Provide request from external scope
bundle = make_bundle(registry, scope={"current_request": request})
```

### Validation

Scoped bundles validate that all required scope dependencies are provided:

```python
try:
    bundle = make_bundle(registry, scope={})  # Missing required scope
except DependencyError as e:
    print(f"Missing scope dependencies: {e}")
```

## Hierarchical Scoping

### Global → Request → Transaction

```python
# Global application components
global_registry = ComponentProviderRegistry()

@global_registry.provides()
def make_database() -> Database:
    return Database()

@global_registry.provides()
def make_cache() -> Cache:
    return Cache()

# Request-scoped components
request_registry = ComponentProviderRegistry()

@request_registry.provides()
def make_session(request: Annotated[Request, "current_request"]) -> Session:
    return Session(request)

# Transaction-scoped components
transaction_registry = ComponentProviderRegistry()

@transaction_registry.provides()
def make_transaction(db: Database) -> Transaction:
    return db.begin_transaction()

# Build hierarchy
global_bundle = make_bundle(global_registry)
request_bundle = make_bundle(
    request_registry, 
    parent=global_bundle,
    scope={"current_request": request}
)
transaction_bundle = make_bundle(
    transaction_registry,
    parent=request_bundle
)
```

### Scope Isolation

Each scope level has access to:
- Its own components
- Parent components
- Explicitly provided scope dependencies

Transient scope dependencies are _not_ visible to children of the scope into which they were injected.

## Profile Combinations

### Complex Profile Logic

```python
@registry.provides(profiles=["dev", "!ci"])
def make_dev_tool() -> Tool:
    return InteractiveTool()

@registry.provides(profiles=["prod", "staging"])
def make_production_tool() -> Tool:
    return ProductionTool()

# Active in dev but not in CI
bundle = make_bundle(registry, profiles={"dev"})

# Not active in dev + CI
bundle = make_bundle(registry, profiles={"dev", "ci"})
```

[← Previous: Bundle Management](bundles.md) | [Next: Advanced Usage →](advanced.md)