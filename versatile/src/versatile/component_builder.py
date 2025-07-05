"""Utilities for constructing MaterialisedComponent objects."""

import uuid
from functools import reduce
from typing import Callable, Any

from versatile.domain import MaterialisedComponent
from versatile.registry import ComponentProvider


class ComponentBuilder:
    """Build :class:`MaterialisedComponent` instances from providers."""

    def __init__(
        self,
        transformers: list[Callable[[MaterialisedComponent], MaterialisedComponent]],
    ):
        self._transformers = transformers

    def build(
        self, provider: ComponentProvider, dependencies: dict[str, Any]
    ) -> MaterialisedComponent:
        """Invoke a provider and apply transformers to the result.

        Args:
            provider: The provider being executed.
            dependencies: Mapping of dependency names to resolved components.

        Returns:
            The resulting :class:`MaterialisedComponent`.
        """
        call_kwargs = {
            dep.parameter_name: dependencies[dep.component_name]
            for dep in provider.dependencies
        }
        component_obj = provider.func(**call_kwargs)

        untransformed = MaterialisedComponent(
            uuid.uuid4(),
            provider.name,
            provider.provided_type,
            component_obj,
            list(dependencies.keys()),
            provider.metadata,
        )
        return reduce(
            lambda component, transformer: transformer(component),
            self._transformers,
            untransformed,
        )
