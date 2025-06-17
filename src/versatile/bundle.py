"""
Module for resolving and materialising component providers into a dependency-injected bundle.

This module defines a `make_bundle` entry point that builds a dictionary of components
by resolving dependencies between registered providers in a given `ComponentProviderRegistry`.

Each provider may declare dependencies on other components by name or by type.
The resolution process performs a topological sort and instantiates each provider in order.
"""

from collections import defaultdict
from dataclasses import dataclass
from typing import Optional, Any

from versatile.registry import (
    DependencyError,
    ComponentProvider,
    ComponentProviderRegistry,
    Dependency,
)


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


ComponentKey = type | str


class Bundle:
    def __init__(self, parent: Optional["Bundle"] = None):
        self._materialised_components: dict[ComponentKey, MaterialisedComponent] = {}
        self._parent = parent

    def add_component(self, key: ComponentKey, value: MaterialisedComponent):
        self._materialised_components[key] = value

    def find_component(self, key: ComponentKey) -> MaterialisedComponent:
        try:
            return self._materialised_components[key]
        except KeyError:
            if self._parent:
                return self._parent[key]
            raise KeyError(key)

    def __getitem__(self, key: type | str) -> Any:
        return self.find_component(key).component

    def __contains__(self, item) -> bool:
        return item in self._materialised_components or (
            self._parent and item in self._parent
        )


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


class _BundleBuilder:
    """
    Internal helper class that builds a dependency graph and resolves providers
    into a materialised component bundle.

    This class is not part of the public API.
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
            if len(providers_of_type) == 1 and not providers_of_type[0] in self._parent
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
        result = Bundle(self._parent)
        ready_to_materialise = [
            provider_name
            for provider_name, deps in dependency_graph.items()
            if len(deps) == 0
        ]

        while len(ready_to_materialise) > 0:
            ready_provider_name = ready_to_materialise.pop()
            del dependency_graph[ready_provider_name]

            materialised_component = self._materialise_component(
                ready_provider_name, result
            )
            result.add_component(ready_provider_name, materialised_component)

            provider = self._providers_by_name[ready_provider_name]
            if provider.provided_type in self._unique_provider_names_by_type:
                result.add_component(provider.provided_type, materialised_component)

            for provider_name, deps in dependency_graph.items():
                if len(deps) > 0:
                    deps.discard(ready_provider_name)
                    if len(deps) == 0:
                        ready_to_materialise.append(provider_name)

        if len(dependency_graph) > 0:
            raise DependencyError(
                f"Unresolvable dependencies: {dependency_graph.keys()}"
            )

        return result

    def _build_dependency_graph(self) -> dict[str, set[str]]:
        """
        Construct a dependency graph where each provider maps to the set of provider names it depends on.

        Returns:
            A dict mapping provider names to the names of their direct dependencies.

        Raises:
            DependencyError: If a dependency cannot be matched to a provider by name or type.
        """
        dependency_graph: dict[str, set[str]] = defaultdict(set)

        for provider_name, provider in self._providers_by_name.items():
            dependency_graph[provider.name].update(
                self._find_matching_provider_name(dependency, provider.name)
                for dependency in provider.dependencies
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

        try:
            return self._unique_provider_names_by_type[dependency.type]
        except KeyError:
            try:
                return self._parent[dependency.type].name
            except KeyError:
                pass
        raise DependencyError(
            f"No unique provider for type {dependency.type} found for dependency "
            f"{dependency.name} of provider {provider_name}"
        )

    def _materialise_component(
        self, provider_name: str, containing_bundle: Bundle
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
        provider = self._providers_by_name[provider_name]
        dependency_names = [
            self._find_matching_provider_name(dependency, provider_name)
            for dependency in provider.dependencies
        ]
        component_obj = provider.func(
            *(
                containing_bundle[dependency_name]
                for dependency_name in dependency_names
            )
        )

        return MaterialisedComponent(
            provider_name,
            component_obj,
            dependency_names,
            provider.metadata if hasattr(provider, "metadata") else {},
        )
