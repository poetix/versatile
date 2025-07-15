# Bundle Management

## Creating Bundles

### Basic Bundle Creation

```python
from versatile.builders import make_bundle

bundle = make_bundle(registry)
```

### Bundle with Profiles

```python
bundle = make_bundle(registry, profiles={"dev", "test"})
```

### Bundle with External Scope

```python
# Provide dependencies from external scope
bundle = make_bundle(registry, scope={"api_key": "secret123"})
```

## Hierarchical Bundles

Create parent-child relationships for layered dependency injection:

```python
# Global bundle
global_bundle = make_bundle(global_registry)

# Request-scoped bundle
request_bundle = make_bundle(request_registry, parent=global_bundle)

# Transaction-scoped bundle
transaction_bundle = make_bundle(transaction_registry, parent=request_bundle)
```

### Parent-Child Rules

- Child bundles can depend on parent components
- Parent bundles cannot depend on child components
- Child components can override parent components by type
- Name conflicts between parent and child are not allowed

## Accessing Components

### By Type

```python
service = bundle[UserService]
database = bundle[Database]
```

### By Name

```python
cache = bundle["redis_cache"]
config = bundle["app_config"]
```

### Check Existence

```python
if "optional_service" in bundle:
    service = bundle["optional_service"]
```

## Bundle Inspection

### List All Components

```python
for name, component in bundle.items():
    print(f"{name}: {type(component)}")
```

### Get Component Metadata

```python
component_set = bundle.components
for component in component_set:
    print(f"{component.name}: {component.declared_types}")
```

## Dependency Completion

### Fail-Fast by Default

Root bundles require all dependencies to be satisfied:

```python
# This will raise DependencyError if any dependencies are missing
bundle = make_bundle(registry)
```

### Allow Incomplete Dependencies

For child bundles or when using external scope:

```python
# Child bundles automatically allow parent dependencies
child_bundle = make_bundle(child_registry, parent=parent_bundle)

# Scoped bundles automatically allow scope dependencies
scoped_bundle = make_bundle(registry, scope={"external_dep": value})
```

## Error Handling

### Common Errors

```python
from versatile.errors import DependencyError

try:
    bundle = make_bundle(registry)
except DependencyError as e:
    print(f"Dependency error: {e}")
```

### Error Types

- **Missing Dependencies**: Required dependencies not found
- **Circular Dependencies**: Dependency cycles detected
- **Type Conflicts**: Multiple providers for same type
- **Name Conflicts**: Duplicate component names in same scope

[← Previous: Component Registration](registration.md) | [Next: Profiles and Scoping →](profiles.md)