# Advanced Usage

## Component Lifecycle Management

While Versatile focuses on dependency injection, you can implement lifecycle management by leveraging component metadata and introspection.

### Context Manager Components

```python
@registry.provides()
class DatabaseConnection:
    def __init__(self):
        self.connection = None
    
    def __enter__(self):
        self.connection = create_connection()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.connection:
            self.connection.close()

# Use with context manager
with bundle["DatabaseConnection"] as db:
    # Use database connection
    pass
```

### Startup/Shutdown Hooks

```python
class ComponentManager:
    def __init__(self, bundle):
        self.bundle = bundle
        self.startup_order = []
        self.shutdown_order = []
        
    def start_all(self):
        # Inspect components for startup methods
        for name, component in self.bundle.items():
            if hasattr(component, 'startup'):
                component.startup()
                self.startup_order.append(name)
    
    def shutdown_all(self):
        # Shutdown in reverse order
        for name in reversed(self.startup_order):
            component = self.bundle[name]
            if hasattr(component, 'shutdown'):
                component.shutdown()
```

## Bundle Composition

### Modular Registries

```python
# Database module
database_registry = ComponentProviderRegistry()

@database_registry.provides()
def make_database() -> Database:
    return Database()

# Cache module
cache_registry = ComponentProviderRegistry()

@cache_registry.provides()
def make_cache() -> Cache:
    return Cache()

# Compose registries
main_registry = ComponentProviderRegistry()
main_registry._providers.extend(database_registry._providers)
main_registry._providers.extend(cache_registry._providers)
```

### Registry Factories

```python
def create_database_registry(config: dict) -> ComponentProviderRegistry:
    registry = ComponentProviderRegistry()
    
    if config.get("database_type") == "postgres":
        @registry.provides()
        def make_database() -> Database:
            return PostgreSQLDatabase(config["database_url"])
    else:
        @registry.provides()
        def make_database() -> Database:
            return SQLiteDatabase(config["database_path"])
    
    return registry
```

## Error Handling Strategies

### Graceful Degradation

```python
@registry.provides(profiles=["!degraded"])
def make_external_service() -> ExternalService:
    return RealExternalService()

@registry.provides(profiles=["degraded"])
def make_fallback_service() -> ExternalService:
    return FallbackService()

# Switch to degraded mode on errors
try:
    bundle = make_bundle(registry, profiles={"prod"})
except DependencyError:
    bundle = make_bundle(registry, profiles={"prod", "degraded"})
```

### Partial Bundle Creation

```python
def create_partial_bundle(registry, profiles):
    required_components = ["database", "cache"]
    optional_components = ["monitoring", "analytics"]
    
    try:
        return make_bundle(registry, profiles)
    except DependencyError as e:
        # Remove optional components and retry
        filtered_registry = filter_registry(registry, required_components)
        return make_bundle(filtered_registry, profiles)
```

## Testing Strategies

### Test-Specific Components

```python
@registry.provides(profiles=["test"])
class MockEmailService:
    def __init__(self):
        self.sent_emails = []
    
    def send_email(self, to, subject, body):
        self.sent_emails.append((to, subject, body))

@registry.provides(profiles=["!test"])
class RealEmailService:
    def send_email(self, to, subject, body):
        # Actually send email
        pass
```

### Test Bundles

```python
def create_test_bundle(overrides=None):
    test_registry = ComponentProviderRegistry()
    
    # Add test-specific components
    test_registry._providers.extend(production_registry._providers)
    
    # Apply overrides
    if overrides:
        for name, component in overrides.items():
            test_registry.register(ComponentProvider(
                name, lambda: component, [], [type(component)], [], {}
            ))
    
    return make_bundle(test_registry, profiles={"test"})
```

## Performance Considerations

### Bundle Caching

```python
class BundleCache:
    def __init__(self):
        self._cache = {}
    
    def get_bundle(self, registry, profiles=None):
        key = (id(registry), frozenset(profiles or []))
        if key not in self._cache:
            self._cache[key] = make_bundle(registry, profiles)
        return self._cache[key]
```

### Lazy Component Creation

```python
class LazyComponent:
    def __init__(self, factory):
        self._factory = factory
        self._instance = None
    
    def __getattr__(self, name):
        if self._instance is None:
            self._instance = self._factory()
        return getattr(self._instance, name)

@registry.provides()
def make_expensive_component() -> ExpensiveComponent:
    return LazyComponent(lambda: ExpensiveComponent())
```

## Integration Patterns

### Flask Integration

```python
from flask import Flask, g

app = Flask(__name__)

@app.before_request
def create_request_bundle():
    g.bundle = make_bundle(
        request_registry,
        parent=app.global_bundle,
        scope={"request": request}
    )

@app.teardown_request
def cleanup_request_bundle(error):
    if hasattr(g, 'bundle'):
        # Cleanup resources
        pass
```

### FastAPI Integration

```python
from fastapi import FastAPI, Depends

app = FastAPI()

def get_bundle():
    return make_bundle(registry, profiles={"prod"})

@app.get("/users/{user_id}")
async def get_user(user_id: str, bundle: Bundle = Depends(get_bundle)):
    service = bundle[UserService]
    return service.get_user(user_id)
```

[← Previous: Profiles and Scoping](profiles.md) | [Next: API Reference →](api.md)