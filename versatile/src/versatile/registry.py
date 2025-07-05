"""Registration and introspection utilities for component providers."""

import inspect
from dataclasses import dataclass
from typing import (
    Callable,
    get_type_hints,
    get_origin,
    Annotated,
    get_args,
    Optional,
    Any,
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
        return self._make_decorator(
            name, profiles or [], lambda func: _infer_name_from(func.__name__)
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
        return self._make_decorator(None, profiles or [], _get_name_from_return_type)

    def _make_decorator(
        self,
        name: Optional[str],
        profiles: list[str],
        name_from_func: Callable[[Callable], str],
    ) -> Callable:
        def decorator(func: Callable) -> Callable:
            inferred_name = name if name else name_from_func(func)

            provider = ComponentProvider(
                inferred_name,
                func,
                profiles,
                get_type_hints(func).get("return", None),
                _get_dependencies(func),
                func.__provider_metadata__ if hasattr(func, '__provider_metadata__') else {},
            )
            self.register(provider)

            return func

        return decorator


def _profiles_match(stated: list[str], selected: set[str]) -> bool:
    provided = [p for p in stated if not p.startswith("!")]
    excluded = [p[1:] for p in stated if p.startswith("!")]

    return not any(e in selected for e in excluded) and (
        not provided or any(p in selected for p in provided)
    )


def _infer_name_from(name: str) -> str:
    if name.startswith("make_"):
        return name[5:]
    else:
        return name


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
