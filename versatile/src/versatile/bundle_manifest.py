"""Utilities for constructing bundle build manifests.

This module provides the core dependency resolution logic for the Versatile
framework. It analyzes provider dependencies, performs topological sorting
to determine build order, and creates manifests that describe how to
construct component bundles.

The BundleManifest serves as a blueprint for bundle construction, containing
all the information needed to instantiate components in the correct order
while respecting dependency relationships.
"""

from collections import deque, defaultdict
from dataclasses import dataclass
from typing import Optional, FrozenSet, Iterable

from versatile.component_set import ComponentSet
from versatile.errors import DependencyError
from versatile.provider_set import ProviderSet
from versatile.registry import ComponentProvider


__all__ = ["ResolvedComponentProvider", "BundleManifest", "BundleManifestBuilder"]

@dataclass(frozen=True)
class ResolvedComponentProvider:
    provider: ComponentProvider
    resolved_dependencies: dict[str, str]

    @staticmethod
    def from_provider(
        provider: ComponentProvider, resolved_type_lookup: dict[type, str]
    ) -> "ResolvedComponentProvider":
        return ResolvedComponentProvider(provider, {
            dependency.parameter_name: (
                    dependency.component_name or resolved_type_lookup[dependency.declared_type]
            ) for dependency in provider.dependencies
        })


@dataclass(frozen=True)
class BundleManifest:
    """Description of how to build a :class:`~versatile.bundle.Bundle`."""

    parent: Optional[ComponentSet]
    """Components available from the parent bundle, if any."""

    required_from_scope: FrozenSet[str]
    """Names of dependencies that must be supplied by the caller."""

    resolved_providers: dict[str, ResolvedComponentProvider]
    """Provider functions keyed by the component name they produce."""

    build_order: list[str]
    """Ordered list of providers to invoke."""


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

            self._remove_dependency(next_item, ready_to_materialise)

        if len(self._dependencies) > 0:
            raise DependencyError(
                f"Unresolvable dependencies: {set(self._dependencies.keys())}"
            )

    def _remove_dependency(self, next_item, ready_to_materialise):
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


class BundleManifestBuilder:
    """Resolve providers into a :class:`BundleManifest`."""

    def __init__(self, parent: Optional[ComponentSet]):
        self._parent = parent

    def build(self, provider_set: ProviderSet, require_complete: bool = True) -> BundleManifest:
        """Build a BundleManifest from a validated ProviderSet.
        
        Performs dependency resolution and topological sorting to determine
        the order in which providers should be invoked. Validates that all
        dependencies can be satisfied either by providers in the set, by
        the parent bundle, or by externally-supplied scope.
        
        Args:
            provider_set: Validated set of providers to resolve.
            
        Returns:
            A BundleManifest describing how to build the bundle.
            
        Raises:
            DependencyError: If provider names conflict with parent components.
        """
        self._validate_compatibility_with_parent(provider_set)
        resolved_type_lookup = self._resolve_type_dependencies(provider_set)
        required_from_scope = self._get_required_from_scope(provider_set)

        resolved_providers: dict[str, ResolvedComponentProvider] = {
            provider_name: ResolvedComponentProvider.from_provider(provider, resolved_type_lookup)
            for provider_name, provider in provider_set.providers_by_name.items()
        }

        build_order = list(
            self._build_dependency_graph(
                resolved_providers, required_from_scope
            ).traverse()
        )

        if require_complete and len(required_from_scope) > 0:
            raise DependencyError(
                f"Missing dependencies {required_from_scope} - "
                "to allow dependencies to be supplied by a transient scope, "
                "call build with require_complete set to False."
            )

        return BundleManifest(
            self._parent,
            required_from_scope,
            resolved_providers,
            build_order,
        )

    def _get_required_from_scope(self, provider_set) -> FrozenSet[str]:
        """Determine which dependencies must be supplied externally.
        
        Args:
            provider_set: The ProviderSet containing dependency requirements.
            
        Returns:
            Frozen set of component names that must be provided by external scope.
        """
        return frozenset(
            {
                component_name
                for component_name in provider_set.unsatisfied_by_name_dependencies
                if component_name not in self._parent
            }
            if self._parent
            else provider_set.unsatisfied_by_name_dependencies
        )

    def _build_dependency_graph(
        self, resolved_providers: dict[str, ResolvedComponentProvider], provided_from_scope
    ) -> _DependencyGraph:
        """
        Construct a dependency graph where each provider maps to the set of provider names it depends on.

        Returns:
            A dependency graph mapping provider names to the names of their direct dependencies.

        Raises:
            DependencyError: If a dependency cannot be matched to a provider by name or type.
        """
        dependency_graph: _DependencyGraph = _DependencyGraph()

        for provider_name, resolved_provider in resolved_providers.items():
            dependency_names = resolved_provider.resolved_dependencies.values()
            dependency_graph.add_dependencies(
                provider_name,
                (
                    dependency_name
                    for dependency_name in dependency_names
                    if not (
                        (self._parent and dependency_name in self._parent)
                        or dependency_name in provided_from_scope
                    )
                ),
            )

        return dependency_graph

    def _validate_compatibility_with_parent(self, provider_set):
        """Ensure provider names don't conflict with parent bundle components.
        
        Args:
            provider_set: The ProviderSet to validate against the parent.
            
        Raises:
            DependencyError: If any provider names conflict with parent components.
        """
        if not self._parent:
            return

        parent_components = self._parent.components
        conflicts = [
            provider_name
            for provider_name in provider_set.providers_by_name
            if provider_name in parent_components
        ]
        if conflicts:
            raise DependencyError(
                f"Provider names {conflicts} conflict with component in parent bundle"
            )

    def _resolve_type_dependencies(self, provider_set) -> dict[type, str]:
        if not self._parent:
            if len(provider_set.unsatisfied_by_type_dependencies) > 0:
                raise DependencyError(
                    f"Unsatisfied type dependencies: {[dep.__name__ for dep in provider_set.unsatisfied_by_type_dependencies]}"
                )
            return provider_set.resolved_type_dependencies

        aliased_types = {
            resolved_type: (provider_name, self._parent.components_of_type(resolved_type))
            for resolved_type, provider_name
            in provider_set.resolved_type_dependencies.items()
            if self._parent.provides_type(resolved_type)
        }

        if len(aliased_types) > 0:
            raise DependencyError(
                f"Provider types {aliased_types} alias types also provided by parent bundle"
            )

        resolved_type_dependencies = dict(provider_set.resolved_type_dependencies)
        for unresolved_type in provider_set.unsatisfied_by_type_dependencies:
            candidates = self._parent.components_of_type(unresolved_type)
            if len(candidates) > 1:
                raise DependencyError(
                    f"Multiple candidates for dependency on type {unresolved_type}: {candidates}"
                )
            if len(candidates) == 1:
                resolved_type_dependencies[unresolved_type] = candidates[0].name

        if len(resolved_type_dependencies) < len(provider_set.unsatisfied_by_type_dependencies):
            raise DependencyError(
                f"Unsatisfied type dependencies: {provider_set.unsatisfied_by_type_dependencies - resolved_type_dependencies.keys()}"
            )

        return resolved_type_dependencies
