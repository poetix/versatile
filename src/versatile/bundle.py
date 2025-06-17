"""
Module for resolving and materialising component providers into a dependency-injected bundle.

This module defines a `make_bundle` entry point that builds a dictionary of components
by resolving dependencies between registered providers in a given `ComponentProviderRegistry`.

Each provider may declare dependencies on other components by name or by type.
The resolution process performs a topological sort and instantiates each provider in order.

Bundles may be layered via a parent-child relationship, enabling scoped resolution:
a child bundle may depend on components in its parent, but not vice versa.
"""

from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Optional, Any, Iterable, Union

from versatile.registry import (
    DependencyError,
    ComponentProvider,
    ComponentProviderRegistry,
    Dependency,
)

__all__ = ["make_bundle", "Bundle", "MaterialisedComponent", "ComponentKey"]


@dataclass(frozen=True)
class MaterialisedComponent:
    """
    Represents a resolved and instantiated component.

    Attributes:
        name: The provider name.
        component: The instantiated component object.
        dependencies: A list of provider names or keys this component depends on.
        metadata: Optional metadata declared on the provider.
    """

    name: str
    component: Any
    dependencies: list[str]
    metadata: dict[str, Any]


ComponentKey = Union[type, str]
"""
Represents a key used to look up a component in a bundle. This may be either a type
(e.g., `MyService`) or a string (e.g., 'logger'), depending on how the provider was registered.
"""


class Bundle:
    """
    A container of materialised components, resolved from a set of providers.

    Bundles may be layered: a child bundle may inherit and resolve dependencies from
    its parent, allowing scoped resolution across session or request boundaries.

    Components are registered by both name and type (where uniquely provided),
    and can be retrieved using either.
    """

    def __init__(self, parent: Optional["Bundle"] = None):
        self._materialised_components: dict[ComponentKey, MaterialisedComponent] = {}
        self._parent = parent

    def add_component(self, key: ComponentKey, value: MaterialisedComponent):
        """
        Add a component to the bundle under the given key.

        Args:
            key: The name or type of the component.
            value: The materialised component object.
        """
        self._materialised_components[key] = value

    def find_component(self, key: ComponentKey) -> MaterialisedComponent:
        """
        Find a component in this bundle or any parent bundle.

        Args:
            key: The name or type to look up.

        Returns:
            The matching `MaterialisedComponent`.

        Raises:
            KeyError: If no component with the given key is found.
        """
        if self._parent and key in self._parent:
            if key not in self._materialised_components:
                return self._parent.find_component(key)
            else:
                raise KeyError(key)

        return self._materialised_components[key]

    def __getitem__(self, key: ComponentKey) -> Any:
        return self.find_component(key).component

    def __contains__(self, item: ComponentKey) -> bool:
        if self._parent and item in self._parent:
            return item not in self._materialised_components
        return item in self._materialised_components


def make_bundle(
    registry: ComponentProviderRegistry,
    profiles: Optional[set[str]] = None,
    parent: Optional[Bundle] = None,
) -> Bundle:
    """
    Construct and return a fully materialised bundle of components.

    The function selects providers from the given registry, resolves their dependencies,
    and materialises them in dependency order.

    Args:
        registry: The component provider registry containing declared providers.
        profiles: An optional set of profile names used to filter active providers.
        parent: An optional parent bundle containing already-materialised components.

    Returns:
        A dictionary mapping provider names (and uniquely provided types) to
        materialised component instances.

    Raises:
        DependencyError: If dependencies are ambiguous, missing, or cyclic.
    """
    providers = registry.registered_providers(profiles)

    return _BundleBuilder(providers, parent or Bundle()).build_bundle()


class _DependencyGraph:
    """
    Internal helper to represent and traverse a directed acyclic graph of provider dependencies.

    Each node corresponds to a provider, and each edge indicates a required dependency.
    The graph supports topological traversal, raising an error if cycles remain.
    """

    def __init__(self):
        self._dependencies: dict[str, set[str]] = defaultdict(set)

    def add_dependencies(self, dependee: str, dependencies: Iterable[str]):
        """
        Add one or more dependencies to the graph for a given dependee node.

        Args:
            dependee: The provider name whose dependencies are being registered.
            dependencies: A list of provider names this dependee depends on.
        """
        self._dependencies[dependee].update(dependencies)

    def traverse(self):
        """
        Perform a topological traversal of the dependency graph.

        Yields:
            Provider names in an order where all dependencies of each node
            are yielded before the node itself.

        Raises:
            DependencyError: If any cycles or unsatisfied dependencies remain.
        """
        ready_to_materialise = deque(
            dependee
            for dependee, dependencies in self._dependencies.items()
            if len(dependencies) == 0
        )

        while len(ready_to_materialise) > 0:
            next_item = ready_to_materialise.popleft()
            yield next_item

            self.remove_dependency(next_item, ready_to_materialise)

        if len(self._dependencies) > 0:
            raise DependencyError(
                f"Unresolvable dependencies: {self._dependencies.keys()}"
            )

    def remove_dependency(self, next_item, ready_to_materialise):
        """
        Remove a resolved dependency from the graph and update readiness of dependents.

        Args:
            next_item: The provider name that has just been resolved.
            ready_to_materialise: A queue of provider names ready for resolution.
        """
        del self._dependencies[next_item]

        for dependee, dependencies in self._dependencies.items():
            if len(dependencies) > 0:
                dependencies.discard(next_item)
                if len(dependencies) == 0:
                    ready_to_materialise.append(dependee)


class _BundleBuilder:
    """
    Internal utility that coordinates the resolution of component providers
    into a materialised `Bundle`. Not part of the public API.

    Operates by building a dependency graph from registered providers, resolving each
    in topological order, and injecting resolved dependencies into each provider function.
    """

    def __init__(self, providers, parent: Bundle):
        self._parent = parent
        self._build_indices(providers)

    def _build_indices(self, providers):
        """
        Construct lookup tables for providers by name and by type, and validate uniqueness.

        Builds and stores in the object:
            - A dictionary of providers by name.
            - A dictionary of unique provider names by type, for use in unqualified resolution.

        Raises:
            DependencyError: If duplicate provider names are found.
        """
        providers_by_name: dict[str, ComponentProvider] = {}
        provider_names_by_type: dict[type, list[str]] = defaultdict(list)

        for provider in providers:
            if provider.name in providers_by_name or provider.name in self._parent:
                raise DependencyError(f"Duplicate provider name {provider.name}")
            providers_by_name[provider.name] = provider
            provider_names_by_type[provider.provided_type].append(provider.name)

        unique_provider_names_by_type: dict[type, str] = {
            provider_type: providers_of_type[0]
            for provider_type, providers_of_type in provider_names_by_type.items()
            if len(providers_of_type) == 1
        }

        self._providers_by_name = providers_by_name
        self._unique_provider_names_by_type = unique_provider_names_by_type

    def build_bundle(self) -> Bundle:
        """
        Materialise all providers by resolving their dependencies.

        Performs a topological traversal of the dependency graph, instantiating each
        provider in turn and injecting its resolved dependencies.

        Returns:
            A dictionary mapping provider names and unique types to component instances.

        Raises:
            DependencyError: If the dependency graph contains cycles or unsatisfiable dependencies.
        """
        dependency_graph = self._build_dependency_graph()
        bundle = Bundle(self._parent)

        for ready_provider_name in dependency_graph.traverse():
            self._materialise_and_add_to_bundle(bundle, ready_provider_name)

        return bundle

    def _materialise_and_add_to_bundle(self, bundle, ready_provider_name):
        """
        Materialise a single provider and add its result to the bundle under name and type.

        Args:
            bundle: The bundle under construction.
            ready_provider_name: The name of the provider to instantiate.
        """
        provider = self._providers_by_name[ready_provider_name]
        materialised_component = self._materialise_component(provider, bundle)

        bundle.add_component(ready_provider_name, materialised_component)

        if self._provides_unique_type(provider):
            bundle.add_component(provider.provided_type, materialised_component)

    def _provides_unique_type(self, provider: ComponentProvider) -> bool:
        """
        Check whether a provider uniquely provides its return type.

        Returns:
            True if this provider is the only one for its type (not overridden by parent).
        """
        return provider.provided_type in self._unique_provider_names_by_type

    def _build_dependency_graph(self) -> _DependencyGraph:
        """
        Construct a dependency graph where each provider maps to the set of provider names it depends on.

        Returns:
            A dependency graph mapping provider names to the names of their direct dependencies.

        Raises:
            DependencyError: If a dependency cannot be matched to a provider by name or type.
        """
        dependency_graph: _DependencyGraph = _DependencyGraph()

        for provider_name, provider in self._providers_by_name.items():
            matched_providers = (
                self._find_matching_provider_name(dependency, provider.name)
                for dependency in provider.dependencies
            )
            dependency_graph.add_dependencies(
                provider_name,
                (
                    dependency_name
                    for dependency_name in matched_providers
                    if not dependency_name in self._parent
                ),
            )

        return dependency_graph

    def _find_matching_provider_name(
        self, dependency: Dependency, provider_name: str
    ) -> str:
        """
        Resolve the name of the provider that satisfies a given dependency.

        If the dependency specifies a qualifier, the corresponding provider name must exist.
        If the dependency is unqualified, it must have a uniquely identified provider by type.

        Args:
            dependency: The declared dependency.
            provider_name: The provider declaring the dependency (used for error context).

        Returns:
            The name of the matching provider.

        Raises:
            DependencyError: If no matching provider can be found.
        """
        if dependency.qualifier:
            if (
                dependency.qualifier in self._providers_by_name
                or dependency.qualifier in self._parent
            ):
                return dependency.qualifier

            raise DependencyError(
                f"No provider with qualifier {dependency.qualifier} found for dependency "
                f"{dependency.name} of provider {provider_name}"
            )

        if dependency.type in self._parent:
            if dependency.type not in self._unique_provider_names_by_type:
                return self._parent[dependency.type].name
            else:
                raise DependencyError(
                    f"Ambiguous providers for type {dependency.type} "
                    f"in this bundle and its parent"
                )

        try:
            return self._unique_provider_names_by_type[dependency.type]
        except KeyError:
            raise DependencyError(
                f"No unique provider for type {dependency.type} found for dependency "
                f"{dependency.name} of provider {provider_name}"
            )

    def _materialise_component(
        self, provider: ComponentProvider, containing_bundle: Bundle
    ) -> MaterialisedComponent:
        """
        Instantiate a component by invoking its provider function with resolved dependencies.

        Args:
            provider_name: The name of the provider to invoke.
            containing_bundle: A bundle of already materialised components.

        Returns:
            The instantiated component.

        Raises:
            DependencyError: If any dependency cannot be resolved.
        """
        dependency_names = [
            self._find_matching_provider_name(dependency, provider.name)
            for dependency in provider.dependencies
        ]
        component_obj = provider.func(
            *(
                containing_bundle[dependency_name]
                for dependency_name in dependency_names
            )
        )

        return MaterialisedComponent(
            provider.name, component_obj, dependency_names, provider.metadata
        )
