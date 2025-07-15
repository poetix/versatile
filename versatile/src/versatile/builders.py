"""High level entry points for constructing bundles."""

from typing import Optional, Any
from versatile.bundle import Bundle, BundleBuilder
from versatile.bundle_manifest import BundleManifestBuilder, BundleManifest
from versatile.component_builder import ComponentBuilder
from versatile.provider_set import make_provider_set
from versatile.registry import ComponentProviderRegistry

__all__ = ["make_manifest", "make_bundle"]


def make_manifest(
    registry: ComponentProviderRegistry,
    profiles: Optional[set[str]] = None,
    parent: Optional[Bundle] = None,
    require_complete: bool = True,
) -> BundleManifest:
    """Create a :class:`BundleManifest` for the given registry.

    The registry is filtered by the optional profile set and combined with the
    parent bundle's components (if provided) to determine the order in which
    providers should be invoked.

    Args:
        registry: The component provider registry containing declared providers.
        profiles: An optional set of profile names used to filter active providers.
            If None, all providers are included regardless of profile.
        parent: An optional parent bundle containing already-materialised components.
            Child bundles can depend on parent components but not vice versa.

    Returns:
        The resolved :class:`BundleManifest` describing provider build order
        and external dependencies.

    Raises:
        DependencyError: If dependencies are ambiguous, missing, or cyclic.

    Example:
        >>> registry = ComponentProviderRegistry()
        >>> manifest = make_manifest(registry, {"dev"})
        >>> print(manifest.build_order)
    """
    providers_for_profiles = registry.registered_providers(profiles)
    provider_set = make_provider_set(
        providers_for_profiles, profiles, parent is None and require_complete
    )
    manifest_builder = BundleManifestBuilder(parent.components if parent else None)
    return manifest_builder.build(provider_set, require_complete)


def make_bundle(
    registry: ComponentProviderRegistry,
    profiles: Optional[set[str]] = None,
    parent: Optional[Bundle] = None,
    scope: Optional[dict[str, Any]] = None,
) -> Bundle:
    """Construct and return a fully materialised :class:`Bundle`.

    Providers are selected from the registry, resolved into a manifest and then
    instantiated in dependency order.

    Args:
        registry: The component provider registry containing declared providers.
        profiles: An optional set of profile names used to filter active providers.
        parent: An optional parent bundle containing already-materialised components.
        scope: Optional mapping supplying objects for dependencies that are
            required from the external scope.

    Returns:
        The instantiated :class:`Bundle`.

    Raises:
        DependencyError: If dependencies are ambiguous, missing, or cyclic.
    """
    manifest = make_manifest(
        registry, profiles, parent, parent is None and scope is None
    )
    bundle_builder = BundleBuilder(manifest, ComponentBuilder([]))

    return bundle_builder.build(scope or {})
