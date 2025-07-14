"""Domain models used throughout the framework."""

from dataclasses import dataclass
from typing import Any, Optional
from uuid import UUID


@dataclass(frozen=True)
class Dependency:
    """Represents a dependency required by a component.

    Attributes:
        parameter_name: The parameter name of the dependency in the component builder's function signature.
        declared_type: The expected type of the dependency.
        component_name: The name of the component that fulfils this dependency.
    """

    parameter_name: str
    declared_type: Optional[type]
    component_name: Optional[str]


@dataclass(frozen=True)
class MaterialisedComponent:
    """
    Represents a resolved and instantiated component.

    Attributes:
        id: The unique id of this component instance.
        name: The provider name.
        declared_types: List of types this component can satisfy.
        component: The instantiated component object.
        dependencies: A list of provider names or keys this component depends on.
        metadata: Optional metadata declared on the provider.
    """

    id: UUID
    name: str
    declared_types: list[type]
    component: Any
    dependencies: list[str]
    metadata: dict[str, Any]
