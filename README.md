# Versatile Dependency Injection

Versatile is a lightweight framework for dependency injection using explicit resolution and scoped component graphs.

Inspired by the core ideas of Spring component management, Versatile avoids runtime proxying or other hidden magic. Dependencies are resolved once into immutable bundles that can be layered to model global, request or other application scopes.

This approach is powerful because bundles are constructed deterministically and can be composed to match your application's scopes. It is elegant and Pythonic: providers are just plain functions annotated with type hints and registered via decorators, so everything remains explicit and easy to reason about.

---

## Key Concepts

- **Component Providers** – functions registered with `ComponentProviderRegistry`
  using `@provides` or `@provides_type`.  Dependencies are declared via typing
  annotations and optional `Annotated` qualifiers.
- **Bundles** – materialised graphs of components created via `make_bundle`.
- **Scopes** – bundles may have parents, allowing you to layer request or
  session components on top of global ones.
- **Explicit Resolution** – dependencies are resolved once during bundle
  construction; there are no runtime proxies or hidden lookups.

---

## Example

```python
from typing import Callable, Annotated
from versatile.registry import ComponentProviderRegistry
from versatile.builders import make_bundle

# Define a registry and register providers
registry = ComponentProviderRegistry()
DB = Callable[[str], dict[str, str]]
Service = Callable[[str], str]

@registry.provides(name='db', profiles=['test'])
def make_test_db() -> DB:
    return lambda user_id: {"name": "Arthur", "role": "admin"}

@registry.provides(name='db', profiles=['!test'])
def make_real_db() -> DB:
    return lambda user_id: {"name": "Martha", "role": "admin"}

@registry.provides()
def make_service(db: Annotated[DB, 'db']) -> Service:
    return lambda user_id: f"Welcome, {db(user_id)['name']}!"

# Build a bundle for the active profile
bundle = make_bundle(
    registry,
    {"test"},  # use {'prod'} for the real database
)

# Use the resolved service (lookup works by name or by type)
service = bundle[Service]
print(service("u001"))  # Welcome, Arthur
```

## Features

* Declarative component registration with optional profile filtering
* Named or typed dependencies using standard type hints and `Annotated`
* Bundles can inherit from a parent bundle to model scopes
* Detection of ambiguous, missing or cyclic dependencies
* Minimal runtime dependencies

## Scopes and Bundle Inheritance
You can model scopes like this:

```python
# Global bundle
global_bundle = make_bundle(global_registry)

# Session/request bundle layered on top
session_bundle = make_bundle(session_registry, parent=global_bundle)
```

Components defined in the session bundle can refer to global components, but not vice versa. No dynamic proxying or indirection is involved—resolution is static and predictable.

### Introspecting with manifests

If you only need to examine the dependency graph or defer component creation
until later, call `make_manifest` instead of `make_bundle`.  The returned
`BundleManifest` describes the build order and which components must be supplied
from an external scope.

## Philosophy
This library enforces discipline over convenience:

* No hidden magic
* No runtime injection or interception
* Deterministic resolution at bundle-construction time
* Explicit scoping and layering

This makes it well-suited for backend services, job runners, and applications where clarity and testability matter.

## Status

This project is under active development. Contributions, suggestions, and criticisms are welcome.