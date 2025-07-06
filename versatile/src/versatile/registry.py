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
    """Encapsulates metadata about a registered component.

    Attributes:
        name: Logical name of the component (may be derived from function name if not explicitly
            stated in the @register.provides decorator).
        func: The callable providing the component.
        profiles: Profiles under which the component is active.
        provided_type: Return type of the component function, if available.
        dependencies: List of dependencies inferred from the function signature.
        metadata: Metadata about the component.
    """

    name: str
    func: Callable
    profiles: list[str]
    provided_type: Optional[type]
    dependencies: list[Dependency]
    metadata: dict[str, Any]


NamingStrategy = Callable[[Any], str]
def constant_name(name: str) -> NamingStrategy:
    def strategy(target: Any) -> str:
        return name

    return strategy

def inferred_name(target: Any) -> str:
    if target.__name__.startswith("make_"):
        return target.__name__[5:]
    else:
        return target.__name__

def name_from_type(target: Any) -> str:
    if inspect.isfunction(target):
        return _get_name_from_return_type(target)
    return str(target)

def name_from_supertype(target: Any) -> str:
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
        naming_strategy = constant_name(name) if name else inferred_name
        return self._make_decorator(
            naming_strategy, profiles or []
        )

    def provides_type(self, profiles: list[str] = None) -> Callable:
        """Decorator to register a provider by its annotated return type.

        The returned decorator behaves like :meth:`provides` but derives the
        component name from the provider's return type annotation.

        Args:
            profiles: Optional list of profiles for which the component is active.

        Returns:
            A decorator registering the function under the name of its return type.

        Raises:
            DependencyError: If the function lacks an annotated return type.
        """
        return self._make_decorator(name_from_type, profiles or [])

    def provides_supertype(self, profiles: list[str] = None) -> Callable:
        """Decorator to register a provider by its annotated return type.

        The returned decorator behaves like :meth:`provides` but derives the
        component name from the provider's return type annotation.

        Args:
            profiles: Optional list of profiles for which the component is active.

        Returns:
            A decorator registering the function under the name of its return type.

        Raises:
            DependencyError: If the function lacks an annotated return type.
        """
        return self._make_decorator(name_from_supertype, profiles or [])

    def _make_decorator(
        self,
        naming_strategy: NamingStrategy,
        profiles: list[str]
    ) -> Callable:
        def decorator(obj: Any) -> Any:
            if inspect.isclass(obj):
                provider = _make_class_provider(obj, naming_strategy, profiles)
            elif inspect.isfunction(obj):
                provider = _make_function_provider(obj, naming_strategy, profiles)
            else:
                raise DependencyError(f"{obj} is not a class or function")

            self.register(provider)
            return obj

        return decorator


def _make_class_provider(cls: Any, naming_strategy: NamingStrategy, profiles: list[str]) -> ComponentProvider:
    name = naming_strategy(cls)
    return _make_function_provider(dataclass()(cls), constant_name(name), profiles)

def _make_function_provider(
    func: Callable, naming_strategy: NamingStrategy, profiles: list[str]
) -> ComponentProvider:
        return ComponentProvider(
            naming_strategy(func),
            func,
            profiles,
            get_type_hints(func).get("return", None),
            _get_dependencies(func),
            func.__provider_metadata__ if hasattr(func, '__provider_metadata__') else {},
        )

def _profiles_match(stated: list[str], selected: set[str]) -> bool:
    provided = [p for p in stated if not p.startswith("!")]
    excluded = [p[1:] for p in stated if p.startswith("!")]

    return not any(e in selected for e in excluded) and (
        not provided or any(p in selected for p in provided)
    )


def _get_dependencies(func: Callable) -> list[Dependency]:
    sig = inspect.signature(func)
    hints = get_type_hints(func, include_extras=True)
    result = []

    for name, param in sig.parameters.items():
        annotation = hints.get(name)
        if not annotation:
            raise DependencyError(
                f"Dependency '{name}' of provider '{func.__name__}' is not annotated"
            )

        if get_origin(annotation) is Annotated:
            base_type, *metadata = get_args(annotation)
        else:
            base_type, metadata = annotation, []

        component_name = next((m for m in metadata), str(base_type))

        result.append(Dependency(name, base_type, component_name))

    return result


def _get_name_from_return_type(func: Callable) -> str:
    return_type = get_type_hints(func).get("return", None)
    if return_type is not None:
        return str(return_type)
    raise DependencyError(
        f"Function {func.__name__} is decorated with @provides_type "
        "but does not have an annotated return type"
    )
