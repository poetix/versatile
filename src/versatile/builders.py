from typing import Optional

from versatile.bundle import Bundle, BundleBuilder
from versatile.bundle_manifest import BundleManifestBuilder, BundleManifest
from versatile.component_builder import ComponentBuilder
from versatile.provider_set import make_provider_set
from versatile.registry import ComponentProviderRegistry


def make_manifest(
    registry: ComponentProviderRegistry,
    profiles: Optional[set[str]] = None,
    parent: Optional[Bundle] = None,
) -> BundleManifest:
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
    providers_for_profiles = registry.registered_providers(profiles)
    provider_set = make_provider_set(providers_for_profiles, profiles)
    manifest_builder = BundleManifestBuilder(parent.components if parent else None)
    return manifest_builder.build(provider_set)


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
    manifest = make_manifest(registry, profiles, parent)
    bundle_builder = BundleBuilder(manifest, ComponentBuilder([]))

    return bundle_builder.build({})
