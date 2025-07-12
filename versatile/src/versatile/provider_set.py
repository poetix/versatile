"""Helpers for managing sets of providers.

This module provides utilities for collecting component providers into
validated sets, ensuring uniqueness constraints and resolving external
dependencies. The ProviderSet class represents a resolved collection of
providers ready for dependency graph analysis.
"""

from collections import defaultdict
from dataclasses import dataclass
from typing import FrozenSet

from versatile.errors import DependencyError
from versatile.registry import ComponentProvider

__all__ = ["ProviderSet", "make_provider_set"]


@dataclass(frozen=True)
class ProviderSet:
    """
    Represents a resolved set of component providers and their dependencies.

    Attributes:
        providers_by_name: Mapping from provider names to their ComponentProviders.
        providers_by_type: Index mapping from types to sets of provider names that can satisfy them.
            This allows efficient lookup of providers by the types they can provide.
        required_components: Set of dependencies that are required but not satisfied by the provider set.
    """

    providers_by_name: dict[str, ComponentProvider]
    providers_by_type: dict[type, set[str]]
    required_components: FrozenSet[str]


def make_provider_set(
    providers: list[ComponentProvider], profiles: set[str]
) -> ProviderSet:
    """
    Constructs a ProviderSet from a list of ComponentProviders and an active profile set.

    Validates that:
      - Each provider has a unique name.
      - Type-based dependencies do not refer to types for which multiple providers are available.

    The resulting ProviderSet includes a type index that maps each provided type to the
    set of provider names that can satisfy dependencies for that type. This enables
    efficient type-based lookups during dependency resolution.

    Raises:
        DependencyError: If provider names are duplicated or if a type-based dependency cannot be resolved due to multiple providers.

    Args:
        providers: List of ComponentProvider instances to include.
        profiles: Set of active profile names (used only for error context).

    Returns:
        A fully-resolved ProviderSet containing all providers, their provided types index, and unresolved dependencies.
    """
    providers_by_name: dict[str, ComponentProvider] = _providers_by_unique_name(
        providers, profiles
    )
    
    # Build type index: map each provided type to the set of provider names that can satisfy it
    providers_by_type: dict[type, set[str]] = defaultdict(set)
    for provider in providers:
        for provided_type in provider.provided_types:
            providers_by_type[provided_type].add(provider.name)

    qualified_dependencies = {
        dependency.component_name
        for provider in providers
        for dependency in provider.dependencies
    }

    return ProviderSet(
        providers_by_name,
        dict(providers_by_type),  # Convert defaultdict to regular dict
        frozenset(qualified_dependencies - providers_by_name.keys()),
    )


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
