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

from versatile.errors import DependencyError

__all__ = ["Bundle", "BundleBuilder", "ComponentKey"]


ComponentKey = Union[str, type]


class Bundle:
    """
    A container of materialised components, resolved from a set of providers.

    Bundles may be layered: a child bundle may inherit and resolve dependencies from
    its parent, allowing scoped resolution across session or request boundaries.

    Components are registered by both name and type (where uniquely provided),
    and can be retrieved using either.
    """

    def __init__(self, components: ComponentSet):
        self.components = components

    def __getitem__(self, key: ComponentKey) -> Any:
        return self.components[key if isinstance(key, str) else str(key)].component


class BundleBuilder:
    def __init__(self, manifest: BundleManifest, component_builder: ComponentBuilder):
        self._manifest = manifest
        self._component_builder = component_builder

    def build(self, scope: dict[str, Any]) -> Bundle:
        required_from_scope = self._manifest.required_from_scope
        missing_from_scope = required_from_scope - scope.keys()
        if missing_from_scope:
            raise DependencyError(
                f"Missing items {missing_from_scope} from provided scope"
            )
        extraneous = scope.keys() - required_from_scope
        if extraneous:
            raise DependencyError(
                f"Unexpected items {extraneous} in provided scope"
            )

        built: dict[str, Any] = {}
        parent = self._manifest.parent

        def get_dependency(name: str) -> Any:
            if name in required_from_scope:
                return scope[name]
            if parent and name in parent:
                return parent[name].component
            return built[name].component

        for component_name, dependency_names in self._manifest.build_order:
            looked_up_dependencies = {
                dependency_name: get_dependency(dependency_name)
                for dependency_name in dependency_names
            }
            built[component_name] = self._component_builder.build(
                self._manifest.providers[component_name], looked_up_dependencies
            )

        return Bundle(ComponentSet(built, parent))
