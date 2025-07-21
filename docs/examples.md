# Examples

TODO: verify these actually work.

## Basic Web Service

```python
from versatile.registry import ComponentProviderRegistry
from versatile.builders import make_bundle
from dataclasses import dataclass

# Create registry
registry = ComponentProviderRegistry()

# Configuration
@registry.provides()
def make_config() -> dict:
    return {
        "database_url": "postgresql://localhost/myapp",
        "redis_url": "redis://localhost:6379",
        "debug": True
    }

# Database connection
@registry.provides()
def make_database(config: dict) -> Database:
    return Database(config["database_url"])

# Cache service
@registry.provides()
def make_cache(config: dict) -> Cache:
    return Redis(config["redis_url"])

# Business services
@registry.provides()
@dataclass(frozen=True)
class UserService:
    db: Database
    cache: Cache
    
    def get_user(self, user_id: str) -> User:
        # Check cache first
        cached = self.cache.get(f"user:{user_id}")
        if cached:
            return User.from_json(cached)
        
        # Query database
        user = self.db.query("SELECT * FROM users WHERE id = %s", user_id)
        
        # Cache result
        self.cache.set(f"user:{user_id}", user.to_json(), ttl=300)
        
        return user

# Web controller
@registry.provides()
class UserController:
    user_service: UserService
    
    def get_user_endpoint(self, user_id: str) -> dict:
        user = self.user_service.get_user(user_id)
        return {"user": user.to_dict()}

# Create bundle
bundle = make_bundle(registry)
controller = bundle[UserController]
```

## Multi-Environment Configuration

```python
# Base registry
base_registry = ComponentProviderRegistry()

@base_registry.provides()
def make_logger() -> Logger:
    return Logger("myapp")

# Development environment
@base_registry.provides(profiles=["dev"])
def make_dev_database() -> Database:
    return SQLiteDatabase(":memory:")

@base_registry.provides(profiles=["dev"])
def make_dev_cache() -> Cache:
    return InMemoryCache()

# Production environment
@base_registry.provides(profiles=["prod"])
def make_prod_database() -> Database:
    return PostgreSQLDatabase(os.getenv("DATABASE_URL"))

@base_registry.provides(profiles=["prod"])
def make_prod_cache() -> Cache:
    return RedisCache(os.getenv("REDIS_URL"))

# Test environment
@base_registry.provides(profiles=["test"])
def make_test_database() -> Database:
    return SQLiteDatabase(":memory:")

@base_registry.provides(profiles=["test"])
def make_test_cache() -> Cache:
    return MockCache()

# Create environment-specific bundles
dev_bundle = make_bundle(base_registry, profiles={"dev"})
prod_bundle = make_bundle(base_registry, profiles={"prod"})
test_bundle = make_bundle(base_registry, profiles={"test"})
```

## Request-Scoped Components

NOTE: the below looks like it might work, but doesn't actually (thanks, Claude!).
TODO: make this actually work

```python
from flask import Flask, g, request

app = Flask(__name__)

# Global components
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
def make_request_context(
    request: Annotated[Request, "current_request"]
) -> RequestContext:
    return RequestContext(
        user_id=request.headers.get("X-User-Id"),
        session_id=request.headers.get("X-Session-Id")
    )

@request_registry.provides()
def make_audit_logger(
    context: RequestContext,
    logger: Logger
) -> AuditLogger:
    return AuditLogger(logger, context.user_id, context.session_id)

# Build global bundle once
global_bundle = make_bundle(global_registry, profiles={"prod"})

@app.before_request
def create_request_bundle():
    g.bundle = make_bundle(
        request_registry,
        parent=global_bundle,
        scope={"current_request": request}
    )

@app.route("/users/<user_id>")
def get_user(user_id):
    service = g.bundle[UserService]
    audit = g.bundle[AuditLogger]
    
    audit.log("get_user", {"user_id": user_id})
    user = service.get_user(user_id)
    
    return {"user": user.to_dict()}
```

## Testing with Mocks

TODO: show how this is easily done with profiles.

[← Previous: API Reference](api.md) | [Back to Home](index.md)