"""Versatile dependency injection framework.

Versatile is a lightweight framework for dependency injection using explicit resolution
and scoped component graphs. Inspired by Spring's component management, it avoids
runtime proxying or hidden magic, instead resolving dependencies once into immutable
bundles that can be layered to model global, request, or other application scopes.

Key Features:
    - Declarative component registration with profile filtering
    - Type-safe dependency injection using standard type hints
    - Hierarchical bundle scoping for request/session isolation
    - Static dependency resolution with cycle detection
    - No runtime proxies or dynamic lookups

Basic Usage:
    >>> from versatile.registry import ComponentProviderRegistry
    >>> from versatile.builders import make_bundle
    >>> 
    >>> registry = ComponentProviderRegistry()
    >>> 
    >>> @registry.provides()
    >>> def make_database() -> Database:
    ...     return Database()
    >>> 
    >>> bundle = make_bundle(registry)
    >>> db = bundle[Database]

The framework consists of several core modules:
    - registry: Component provider registration and introspection
    - builders: High-level bundle construction functions
    - bundle: Bundle containers and materialization logic
    - domain: Core domain models (Dependency, MaterialisedComponent)
    - errors: Framework-specific exceptions
"""
