# Examples

## Basic Web Service

```python
from versatile.registry import ComponentProviderRegistry
from versatile.builders import make_bundle
from typing import Annotated

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

```python
import pytest
from unittest.mock import Mock

# Production registry
prod_registry = ComponentProviderRegistry()

@prod_registry.provides()
def make_email_service() -> EmailService:
    return SMTPEmailService()

@prod_registry.provides()
def make_payment_service() -> PaymentService:
    return StripePaymentService()

@prod_registry.provides()
class OrderService:
    email_service: EmailService
    payment_service: PaymentService
    
    def process_order(self, order: Order) -> bool:
        # Process payment
        payment_result = self.payment_service.charge(order.total)
        if not payment_result.success:
            return False
        
        # Send confirmation email
        self.email_service.send_confirmation(order.customer_email, order)
        return True

# Test registry with mocks
def create_test_registry():
    test_registry = ComponentProviderRegistry()
    
    # Mock email service
    @test_registry.provides()
    def make_mock_email_service() -> EmailService:
        mock = Mock(spec=EmailService)
        mock.send_confirmation = Mock()
        return mock
    
    # Mock payment service
    @test_registry.provides()
    def make_mock_payment_service() -> PaymentService:
        mock = Mock(spec=PaymentService)
        mock.charge = Mock(return_value=PaymentResult(success=True))
        return mock
    
    # Use real OrderService
    test_registry.register(prod_registry.registered_providers()[2])  # OrderService
    
    return test_registry

def test_order_processing():
    test_registry = create_test_registry()
    bundle = make_bundle(test_registry)
    
    order_service = bundle[OrderService]
    email_service = bundle[EmailService]
    payment_service = bundle[PaymentService]
    
    # Create test order
    order = Order(customer_email="test@example.com", total=100.0)
    
    # Process order
    result = order_service.process_order(order)
    
    # Verify results
    assert result is True
    payment_service.charge.assert_called_once_with(100.0)
    email_service.send_confirmation.assert_called_once_with("test@example.com", order)
```

## Plugin System

```python
from abc import ABC, abstractmethod

# Plugin interface
class Plugin(ABC):
    @abstractmethod
    def initialize(self) -> None:
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        pass

# Plugin implementations
class LoggingPlugin(Plugin):
    def initialize(self) -> None:
        print("Logging plugin initialized")
    
    def get_name(self) -> str:
        return "logging"

class MetricsPlugin(Plugin):
    def initialize(self) -> None:
        print("Metrics plugin initialized")
    
    def get_name(self) -> str:
        return "metrics"

# Plugin registry
def create_plugin_registry(enabled_plugins: set[str]) -> ComponentProviderRegistry:
    registry = ComponentProviderRegistry()
    
    if "logging" in enabled_plugins:
        registry.register(ComponentProvider(
            "logging_plugin", LoggingPlugin, [], [Plugin, LoggingPlugin], [], {}
        ))
    
    if "metrics" in enabled_plugins:
        registry.register(ComponentProvider(
            "metrics_plugin", MetricsPlugin, [], [Plugin, MetricsPlugin], [], {}
        ))
    
    return registry

# Application with plugins
@registry.provides()
class Application:
    plugins: list[Plugin]
    
    def __init__(self):
        self.plugins = []
    
    def start(self):
        for plugin in self.plugins:
            plugin.initialize()
        print("Application started")

# Dynamic plugin loading
def create_app_with_plugins(enabled_plugins: set[str]) -> Application:
    plugin_registry = create_plugin_registry(enabled_plugins)
    bundle = make_bundle(plugin_registry)
    
    app = Application()
    
    # Collect all plugins
    for name, component in bundle.items():
        if isinstance(component, Plugin):
            app.plugins.append(component)
    
    return app

# Usage
app = create_app_with_plugins({"logging", "metrics"})
app.start()
```

## Async Components

```python
import asyncio
from typing import AsyncContextManager

# Async components
@registry.provides()
async def make_async_database() -> AsyncDatabase:
    db = AsyncDatabase()
    await db.connect()
    return db

@registry.provides()
class AsyncUserService:
    db: AsyncDatabase
    
    async def get_user(self, user_id: str) -> User:
        return await self.db.query("SELECT * FROM users WHERE id = $1", user_id)

# Async bundle creation
async def create_async_bundle():
    bundle = make_bundle(registry)
    
    # Initialize async components
    for name, component in bundle.items():
        if hasattr(component, '__aenter__'):
            await component.__aenter__()
    
    return bundle

# Usage
async def main():
    bundle = await create_async_bundle()
    service = bundle[AsyncUserService]
    user = await service.get_user("123")
    print(user)

asyncio.run(main())
```

[← Previous: API Reference](api.md) | [Back to Home](index.md)