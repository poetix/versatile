"""Registration and introspection utilities for component providers."""

import inspect
from abc import abstractmethod
from dataclasses import dataclass
from typing import (
    Callable,
    get_type_hints,
    get_origin,
    Annotated,
    get_args,
    Optional,
    Any, Literal, Union,
)

from versatile.domain import Dependency
from versatile.errors import DependencyError

__all__ = [
    "Dependency",
    "ComponentProvider",
    "ComponentProviderRegistry",
]


@dataclass(frozen=True)
class ComponentProvider:
    """Encapsulates metadata about a registered component provider.

    ComponentProvider instances represent functions or classes that can create
    components for dependency injection. They contain all the metadata needed
    to understand what the provider creates, what it depends on, and under
    what conditions it should be active.

    Attributes:
        name: Logical name of the component (may be derived from function name
            if not explicitly stated in the registration decorator).
        func: The callable providing the component (function or class constructor).
        profiles: List of profile names under which the component is active.
            Empty list means active in all profiles.
        provided_types: List of types this provider can satisfy. For functions,
            contains the return type annotation (if present). For classes,
            contains the class itself plus all its base classes.
        dependencies: List of Dependency objects describing what this provider needs.
        metadata: Dictionary of arbitrary metadata attached to the provider.
    
    Example:
        >>> @registry.provides(name="database", profiles=["prod"])
        >>> def make_database() -> Database:
        ...     return Database()
        >>> 
        >>> # Creates ComponentProvider with:
        >>> # - name: "database"
        >>> # - func: make_database
        >>> # - profiles: ["prod"]
        >>> # - provided_types: [Database]
        >>> # - dependencies: []
        
        >>> @registry.provides()
        >>> class UserService(Service):
        ...     pass
        >>> 
        >>> # Creates ComponentProvider with:
        >>> # - provided_types: [UserService, Service, object]
    """

    name: str
    func: Callable
    profiles: list[str]
    provided_types: list[type]
    dependencies: list[Dependency]
    metadata: dict[str, Any]


def inferred_name(target: Any) -> str:
    """Derive component name from class or function name, removing 'make_' prefix if present.
    
    Args:
        target: The function or class to derive a name from.
        
    Returns:
        The class name, or the function name with any 'make_' prefix removed.
        
    Example:
        >>> inferred_name(Database)       # Returns "Database"
        >>> inferred_name(make_database)  # Returns "database"
        >>> inferred_name(my_service)     # Returns "my_service"
    """
    if inspect.isclass(target):
        return target.__name__

    if target.__name__.startswith("make_"):
        return target.__name__[5:]
    else:
        return target.__name__


def name_from_supertype(target: Any) -> str:
    """Derive component name from the first base class.
    
    Args:
        target: The class to extract base class name from.
        
    Returns:
        String representation of the first base class.
        
    Raises:
        ValueError: If target is not a class.
        
    Example:
        >>> class DatabaseService(Service): ...
        >>> name_from_supertype(DatabaseService)  # Returns "<class 'Service'>"
    """
    if not inspect.isclass(target):
        raise ValueError(f"{target} is not a class")
    return str(target.__bases__[0])

class ComponentProviderRegistry:
    """Registry for components, supporting registration and profile-based filtering."""

    def __init__(self):
        self._providers = []

    def register(self, provider: ComponentProvider):
        """Register a component explicitly.

        Args:
            provider: The Component instance to be registered.
        """
        self._providers.append(provider)

    def registered_providers(
        self, profiles: set[str] = None
    ) -> list[ComponentProvider]:
        """Retrieve components, optionally filtered by active profiles.

        Args:
            profiles: A set of active profile names. If None, returns all components.

        Returns:
            A list of components whose profiles match the given profile set.
        """
        if profiles is None:
            return self._providers
        return [c for c in self._providers if _profiles_match(c.profiles, profiles)]

    def provides(
        self, name: Optional[str] = None, profiles: Optional[list[str]] = None
    ) -> Callable:
        """Decorator to register a function as a component provider.

        Args:
            name: Optional logical name to assign; defaults to function name with 'make_'
                prefix removed.
            profiles: Optional list of profiles for which the component is active.

        Returns:
            A decorator that registers the function as a component.

        Example:
            @registry.provides(profiles=["dev"])
            def make_thing() -> Thing:
                return Thing()
        """
        def decorator(obj):
            provided_name = name or inferred_name(obj)
            if inspect.isclass(obj):
                obj = dataclass()(obj)
                provider = _make_class_provider(obj, provided_name, profiles or [])
            elif inspect.isfunction(obj):
                provider = _make_function_provider(obj, provided_name, profiles or [])
            else:
                raise DependencyError(f"{obj} is not a class or function")

            self.register(provider)
            return obj

        return decorator


def _make_class_provider(cls: Any, component_name: str, profiles: list[str]) -> ComponentProvider:
    """Create a ComponentProvider from a class by wrapping it with @dataclass.
    
    For classes, the provided_types list includes the class itself and all its base classes,
    allowing the class to satisfy dependencies for any of its parent types.
    
    Args:
        cls: The class to convert to a provider.
        component_name: the name to give the provided component.
        profiles: List of profiles for which the provider is active.
        
    Returns:
        ComponentProvider wrapping the dataclass-decorated class with full type hierarchy.
    """
    
    # Get the class hierarchy: the class itself plus all its base classes
    provided_types = [cls] + list(cls.__bases__)
    
    return ComponentProvider(
        component_name,
        cls,
        profiles,
        provided_types,
        _get_dependencies(cls),
        getattr(cls, '__provider_metadata__', {}),
    )

def _make_function_provider(
    func: Callable, component_name: str, profiles: list[str]
) -> ComponentProvider:
    """Create a ComponentProvider from a function.
    
    Args:
        func: The function to convert to a provider.
        naming_strategy: Strategy for determining the component name.
        profiles: List of profiles for which the provider is active.
        
    Returns:
        ComponentProvider with analyzed dependencies and metadata.
    """
    return_type = get_type_hints(func).get("return", None)
    provided_types = [return_type] if return_type is not None else []
    
    return ComponentProvider(
        component_name,
        func,
        profiles,
        provided_types,
        _get_dependencies(func),
        getattr(func, '__provider_metadata__', {}),
    )

def _profiles_match(stated: list[str], selected: set[str]) -> bool:
    """Check if a provider's profile requirements match the selected profiles.
    
    Profile matching supports inclusion and exclusion patterns:
    - Normal profiles ("dev", "prod") must be in the selected set
    - Exclusion profiles ("!test") must NOT be in the selected set
    - Empty stated profiles match all selected profiles
    
    Args:
        stated: List of profile patterns from the provider.
        selected: Set of currently active profile names.
        
    Returns:
        True if the provider should be active for the selected profiles.
        
    Example:
        >>> _profiles_match(["dev"], {"dev"})          # True
        >>> _profiles_match(["!test"], {"dev"})        # True  
        >>> _profiles_match(["!test"], {"test"})       # False
        >>> _profiles_match(["prod"], {"dev"})         # False
    """
    provided = [p for p in stated if not p.startswith("!")]
    excluded = [p[1:] for p in stated if p.startswith("!")]

    return not any(e in selected for e in excluded) and (
        not provided or any(p in selected for p in provided)
    )


def _get_dependencies(func: Callable) -> list[Dependency]:
    """Extract dependency information from a function's type annotations.
    
    Analyzes the function signature to create Dependency objects for each
    parameter. Supports both simple type annotations and Annotated types
    with qualifier metadata.
    
    Args:
        func: The function to analyze for dependencies.
        
    Returns:
        List of Dependency objects describing each parameter.
        
    Example:
        >>> def service(untyped, db: Database, cache: Annotated[Cache, "redis"]) -> Service:
        ...     pass
        >>> deps = _get_dependencies(service)
        >>> # Returns:
        >>> # [Dependency("untyped", None, "untyped"),
        >>> #  Dependency("db", Database, "<class 'Database'>"),
        >>> #  Dependency("cache", Cache, "redis")]
    """
    sig = inspect.signature(func)
    hints = get_type_hints(func, include_extras=True)
    return [_make_dependency(hints.get(name), name) for name in sig.parameters]


def _make_dependency(annotation, name) -> Dependency:
    if not annotation:
        return Dependency(name, None, name)

    if get_origin(annotation) is Annotated:
        base_type, *metadata = get_args(annotation)
        component_name = next((m for m in metadata), None)
        return Dependency(name, base_type, component_name)
    else:
        return Dependency(name, annotation, None)




def _get_name_from_return_type(func: Callable) -> str:
    """Extract component name from a function's return type annotation.
    
    Args:
        func: The function to analyze.
        
    Returns:
        String representation of the return type.
        
    Raises:
        DependencyError: If the function has no return type annotation.
    """
    return_type = get_type_hints(func).get("return", None)
    if return_type is not None:
        return str(return_type)
    raise DependencyError(
        f"Function {func.__name__} is decorated with @provides_type "
        "but does not have an annotated return type"
    )
