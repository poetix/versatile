# Versatile Dependency Injection

A lightweight, principled Python library for dependency injection using explicit resolution and scoped component graphs.

This library is inspired by the core ideas of Spring-style component management, but deliberately avoids runtime proxying and scope magic. Instead, it provides a disciplined, hierarchical resolution model based on immutable dependency bundles.

---

## Key Concepts

- **Component Providers**: Functions annotated with dependencies and registered under a unique name and type.
- **Bundles**: Instantiated graphs of components, built via topological resolution of dependencies.
- **Scopes**: Encoded via parent-child bundle relationships. You can define global singleton components, and layer in request-, session-, or job-specific components in subordinate bundles.
- **No Proxies**: Unlike Spring, a component in the global scope cannot resolve to a session-scoped instance via proxying. Resolution is static, disciplined, and explicit.

---

## Example

```python
from typing import Callable, Annotated
from versatile.registry import ComponentProviderRegistry
from versatile.bundle import make_bundle

# Define a registry and register providers
registry = ComponentProviderRegistry()

@registry.provides(name='db')
def make_db() -> Callable[[str], dict[str, str]]:
    return lambda user_id: {"name": "Arthur", "role": "admin"}

@registry.provides()
def make_service(db: Annotated[Callable[[str], dict[str, str]], 'db']) -> Callable[[str], str]:
    return lambda user_id: f"Welcome, {db(user_id)['name']}!"

# Build a global bundle
global_bundle = make_bundle(registry)

# Use the resolved service
service = global_bundle[Callable[[str], str]]
print(service("u001"))  # Welcome, Arthur
```

## Features

* Declarative component registration via decorators
* Support for named and typed dependencies, including Annotated qualifiers
* Scoped bundles with optional parent inheritance
* Detection of ambiguous, missing, or cyclic dependencies
* No external dependencies

## Scopes and Bundle Inheritance
You can model scopes like this:

```python
# Global bundle
global_bundle = make_bundle(global_registry)

# Session/request bundle layered on top
session_bundle = make_bundle(session_registry, parent=global_bundle)
```

Components defined in the session bundle can refer to global components, but not vice versa. No dynamic proxying or indirection is involved—resolution is static and predictable.

## Philosophy
This library enforces discipline over convenience:

* No hidden magic
* No runtime injection or interception
* Deterministic resolution at bundle-construction time
* Explicit scoping and layering

This makes it well-suited for backend services, job runners, and applications where clarity and testability matter.

## Status

This project is under active development. Contributions, suggestions, and criticisms are welcome.