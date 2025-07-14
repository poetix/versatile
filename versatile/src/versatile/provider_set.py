"""Helpers for managing sets of providers.

This module provides utilities for collecting component providers into
validated sets, ensuring uniqueness constraints and resolving external
dependencies. The ProviderSet class represents a resolved collection of
providers ready for dependency graph analysis.
"""

from collections import defaultdict
from dataclasses import dataclass
from typing import FrozenSet

from versatile.domain import Dependency
from versatile.errors import DependencyError
from versatile.registry import ComponentProvider

__all__ = ["ProviderSet", "make_provider_set"]


@dataclass(frozen=True)
class ProviderSet:
    """
    Represents a resolved set of component providers and their dependencies.

    Attributes:
        providers_by_name: Mapping from provider names to their ComponentProviders.
        resolved_type_dependencies: Mapping from types to provider names for type-based dependencies
            that were resolved within this provider set.
        unsatisfied_by_name_dependencies: Set of by-name dependencies that are not satisfied by the provider set.
        unsatisfied_by_type_dependencies: Set of by-type dependencies that are not satisfied by the provider set.
    """

    providers_by_name: dict[str, ComponentProvider]
    resolved_type_dependencies: dict[type, str]
    unsatisfied_by_name_dependencies: FrozenSet[str]
    unsatisfied_by_type_dependencies: FrozenSet[type]


def make_provider_set(
    providers: list[ComponentProvider], profiles: set[str], require_complete: bool = True
) -> ProviderSet:
    """
    Constructs a ProviderSet from a list of ComponentProviders and an active profile set.

    Validates that:
      - Each provider has a unique name.
      - Type-based dependencies do not refer to types for which multiple providers are available.

    Raises:
        DependencyError: If provider names are duplicated or if a type-based dependency cannot be
        resolved due to multiple providers.

    Args:
        providers: List of ComponentProvider instances to include.
        profiles: Set of active profile names (used only for error context).
        require_complete: If True (default), then all providers' dependencies must be satisfiable by
        other providers in the resulting ProviderSet. If False, then dependencies may be satisfied
        by a parent bundle or transient scope.

    Returns:
        A fully-resolved ProviderSet containing all providers, their provided types index, and unresolved dependencies.
    """
    providers_by_name: dict[str, ComponentProvider] = _providers_by_unique_name(
        providers, profiles
    )

    by_name_dependencies = {
        dependency.component_name
        for provider in providers
        for dependency in provider.dependencies
        if dependency.component_name is not None
    }

    by_type_dependencies = _by_type_dependencies(providers)
    resolved_type_dependencies = _resolved_type_dependencies(by_type_dependencies, providers, profiles)

    unsatisfied_by_name_dependencies = by_name_dependencies - providers_by_name.keys()
    unsatisfied_by_type_dependencies = by_type_dependencies - resolved_type_dependencies.keys()

    if require_complete:
        if len(unsatisfied_by_name_dependencies) > 0 or len(unsatisfied_by_type_dependencies) > 0:
            unsatisfied = unsatisfied_by_name_dependencies.union(
                type.__name__ for type in unsatisfied_by_type_dependencies
            )
            raise DependencyError(
                f"Provider set has unsatisfied dependencies: {unsatisfied} - "
                "to allow dependencies to be supplied by a parent bundle or transient scope, "
                "call make_provider_set with require_complete set to False."
            )

    return ProviderSet(
        providers_by_name,
        resolved_type_dependencies,
        frozenset(unsatisfied_by_name_dependencies),
        frozenset(unsatisfied_by_type_dependencies)
    )


def _resolved_type_dependencies(by_type_dependencies, providers, profiles):
    """Resolve type-based dependencies to unique provider names.
    
    Args:
        by_type_dependencies: Mapping of types to dependencies that need them.
        providers: List of available providers.
        profiles: Active profiles (for error reporting).
        
    Returns:
        Dictionary mapping types to the unique provider names that satisfy them.
        
    Raises:
        DependencyError: If multiple providers can satisfy the same type dependency.
    """
    providers_by_type: dict[type, set[str]] = defaultdict(set)
    for provider in providers:
        for provided_type in provider.provided_types:
            providers_by_type[provided_type].add(provider.name)

    resolved_type_dependencies: dict[type, str] = {}
    for depended_on_type, dependencies in by_type_dependencies.items():
        provider_names = providers_by_type[depended_on_type]
        if len(provider_names) > 1:
            dependency_list = ", ".join(
                f"{provider_name}.{dependency.parameter_name}"
                for provider_name, dependency in dependencies
            )
            raise DependencyError(
                f"Dependencies {dependency_list} depend on type {depended_on_type}, "
                f"but multiple providers provide this type: {provider_names} "
                f"in profiles {profiles}"
            )
        if len(provider_names) == 1:
            resolved_type_dependencies[depended_on_type] = next(iter(provider_names))
    return resolved_type_dependencies


def _by_type_dependencies(providers):
    by_type_dependencies: dict[type, set[tuple[str, Dependency]]] = defaultdict(set)
    for provider in providers:
        for dependency in provider.dependencies:
            if dependency.component_name is None:
                by_type_dependencies[dependency.declared_type].add(
                    (provider.name, dependency)
                )
    return by_type_dependencies


def _providers_by_unique_name(
    providers: list[ComponentProvider], profiles: set[str]
) -> dict[str, ComponentProvider]:
    providers_by_name = {}

    for provider in providers:
        provider_name = provider.name
        if provider_name in providers_by_name:
            raise DependencyError(
                f"Duplicate provider name '{provider_name}' "
                f"for providers {[p.name for p in providers]} "
                f"in profiles {profiles}"
            )
        providers_by_name[provider.name] = provider

    return providers_by_name
