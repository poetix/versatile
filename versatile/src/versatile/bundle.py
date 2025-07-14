"""
Module for resolving and materialising component providers into a dependency-injected bundle.

This module defines a `make_bundle` entry point that builds a dictionary of components
by resolving dependencies between registered providers in a given `ComponentProviderRegistry`.

Each provider may declare dependencies on other components by name or by type.
The resolution process performs a topological sort and instantiates each provider in order.

Bundles may be layered via a parent-child relationship, enabling scoped resolution:
a child bundle may depend on components in its parent, but not vice versa.
"""

from typing import Any, Union

from versatile.bundle_manifest import BundleManifest
from versatile.component_builder import ComponentBuilder
from versatile.component_set import ComponentSet
from versatile.domain import MaterialisedComponent

from versatile.errors import DependencyError

__all__ = ["Bundle", "BundleBuilder", "ComponentKey"]


ComponentKey = Union[str, type]
"""Type alias for keys used to look up components in a Bundle.

Components can be retrieved either by their string name or by their type.
When using a type as a key, it's converted to its string representation
for internal lookup.

Example:
    >>> bundle["database"]     # Lookup by name
    >>> bundle[Database]       # Lookup by type (converted to str(Database))
"""


class Bundle:
    """
    A container of materialised components, resolved from a set of providers.

    Bundles may be layered: a child bundle may inherit and resolve dependencies from
    its parent, allowing scoped resolution across session or request boundaries.

    Components are registered by unique name and by type. If a component is requested by type,
    there must be a unique component of that type in the bundle; otherwise a KeyError will be raised.
    """

    def __init__(self, components: ComponentSet):
        self.components = components

    def __getitem__(self, key: ComponentKey) -> Any:
        if isinstance(key, str):
            return self.components[key].component
        candidates = self.components.components_of_type(key)
        if len(candidates) == 0:
            raise KeyError(key)
        if len(candidates) > 1:
            raise KeyError(f"No unique component found for type {key}")
        return candidates[0].component



class BundleBuilder:
    """Instantiate components from a :class:`BundleManifest`."""

    def __init__(self, manifest: BundleManifest, component_builder: ComponentBuilder):
        self._manifest = manifest
        self._component_builder = component_builder

    def build(self, scope: dict[str, Any]) -> Bundle:
        """Materialise all components defined by the manifest.

        Args:
            scope: Mapping of dependency names to objects supplied by the caller.

        Returns:
            A :class:`Bundle` containing the instantiated components.

        Raises:
            DependencyError: If required scope items are missing.
        """
        required_from_scope = self._manifest.required_from_scope
        _validate_scoped_values(required_from_scope, scope.keys())

        built: dict[str, Any] = {}
        parent = self._manifest.parent

        def get_component(name: str) -> tuple[str, Any]:
            if name in required_from_scope:
                return scope[name]
            if parent and name in parent:
                return parent[name].component
            return built[name].component

        for component_name in self._manifest.build_order:
            resolved_provider = self._manifest.resolved_providers[component_name]

            looked_up_components = {
                dependency_name: get_component(dependency_name)
                for dependency_name in resolved_provider.resolved_dependencies.values()
            }

            built[component_name] = self._component_builder.build(
                resolved_provider, looked_up_components
            )

        return Bundle(ComponentSet(built, parent))


def _validate_scoped_values(required_from_scope, scope_keys):
    """Validate that the provided scope contains exactly the required items.
    
    Args:
        required_from_scope: Set of dependency names that must be provided.
        scope_keys: Set of keys actually provided in the scope dictionary.
        
    Raises:
        DependencyError: If required items are missing or unexpected items are provided.
    """
    missing_from_scope = required_from_scope - scope_keys
    if missing_from_scope:
        raise DependencyError(f"Missing items {missing_from_scope} from provided scope")

    extraneous = scope_keys - required_from_scope
    if extraneous:
        raise DependencyError(f"Unexpected items {extraneous} in provided scope")
