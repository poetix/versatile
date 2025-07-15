# Advanced Usage

## Component Lifecycle Management

TODO: Implement and describe component lifecycle manager.

## Bundle Composition

### Modular Registries

TODO - implement and describe mechanism for merging registries.

### Registry Factories

An alternative to registering different components under different profiles, and selecting a profile based on runtime configuration.

Instead, you can simply control at runtime what providers are registered, using whatever selection logic makes sense.

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

## Testing Strategies

### Test-Specific Components

Use profiles to switch out real components for test stubs.

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

## Integration Patterns

TODO: show integrations with Flask and FastAPI.


[← Previous: Profiles and Scoping](profiles.md) | [Next: API Reference →](api.md)