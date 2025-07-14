"""Utilities for constructing MaterialisedComponent objects.

This module provides the ComponentBuilder class, which is responsible for
invoking component provider functions and transforming the results into
MaterialisedComponent instances. It supports a transformer pattern that
allows post-processing of components after creation.
"""

import uuid
from functools import reduce
from typing import Callable, Any

from versatile.bundle_manifest import ResolvedComponentProvider
from versatile.domain import MaterialisedComponent


class ComponentBuilder:
    """Build :class:`MaterialisedComponent` instances from providers."""

    def __init__(
        self,
        transformers: list[Callable[[MaterialisedComponent], MaterialisedComponent]],
    ):
        self._transformers = transformers

    def build(
        self, resolved_provider: ResolvedComponentProvider, dependencies: dict[str, Any]
    ) -> MaterialisedComponent:
        """Invoke a provider and apply transformers to the result.

        Args:
            resolved_provider: The provider being executed.
            dependencies: Mapping of dependency names to resolved components.

        Returns:
            The resulting :class:`MaterialisedComponent`.
        """
        call_kwargs = {
            parameter_name: dependencies[component_name]
            for parameter_name, component_name in resolved_provider.resolved_dependencies.items()
        }
        component_obj = resolved_provider.provider.func(**call_kwargs)

        untransformed = MaterialisedComponent(
            uuid.uuid4(),
            resolved_provider.provider.name,
            resolved_provider.provider.provided_types,
            component_obj,
            list(dependencies.keys()),
            resolved_provider.provider.metadata,
        )
        return reduce(
            lambda component, transformer: transformer(component),
            self._transformers,
            untransformed,
        )
