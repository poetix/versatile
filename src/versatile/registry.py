import inspect
from dataclasses import dataclass
from typing import Callable, get_type_hints, get_origin, Annotated, get_args, Optional

__all__ = [
    "DependencyError",
    "Dependency",
    "ComponentProvider",
    "ComponentProviderRegistry",
]


class DependencyError(Exception):
    """Raised when a component's dependency cannot be resolved or is misannotated."""

    pass


@dataclass(frozen=True)
class Dependency:
    """Represents a dependency required by a component.

    Attributes:
        name: The parameter name in the function signature.
        type: The expected type of the dependency.
        qualifier: An optional string used to disambiguate dependencies of the same type.
    """

    name: str
    type: type
    qualifier: Optional[str]


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
    """

    name: str
    func: Callable
    profiles: list[str]
    provided_type: Optional[type]
    dependencies: list[Dependency]


class ComponentProviderRegistry:
    """Registry for components, supporting registration and profile-based filtering."""

    def __init__(self):
        self._components = []

    def register(self, component: ComponentProvider):
        """Register a component explicitly.

        Args:
            component: The Component instance to be registered.
        """
        self._components.append(component)

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
            return self._components
        return [c for c in self._components if _profiles_match(c.profiles, profiles)]

    def provides(
        self, name: str = None, profiles: Optional[list[str]] = None
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
        if profiles is None:
            profiles = []

        def decorator(func: Callable) -> Callable:
            inferred_name = name or _infer_name_from(func.__name__)

            component = ComponentProvider(
                inferred_name,
                func,
                profiles,
                get_type_hints(func).get("return", None),
                _get_dependencies(func),
            )
            self.register(component)
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
        try:
            annotation = hints[name]
        except KeyError:
            raise DependencyError(
                "Dependency <%s> of provider <%s> is not annotated"
                % (name, func.__name__)
            )

        if get_origin(annotation) is Annotated:
            base_type, *metadata = get_args(annotation)
        else:
            base_type, metadata = annotation, []

        result.append(Dependency(name, base_type, next((m for m in metadata), None)))

    return result
