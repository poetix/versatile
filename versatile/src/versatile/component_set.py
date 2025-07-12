"""Container for resolved components with optional parent lookup.

Provides hierarchical component lookup, allowing child component sets to
inherit components from parent sets while maintaining isolation. This enables
scoped dependency injection where request-level components can depend on
global components, but not vice versa.

The component set acts as a dictionary-like container where components are
accessed by name, with automatic fallback to parent components when a
component is not found locally.
"""

from typing import Optional

from versatile.domain import MaterialisedComponent


class ComponentSet:
    """Collection of components with hierarchical lookup.
    
    Supports parent-child relationships for scoped component resolution.
    Child sets can access components from their parent, enabling layered
    dependency injection patterns.
    
    Attributes:
        components: Dictionary mapping component names to MaterialisedComponent instances.
        _parent: Optional parent ComponentSet for hierarchical lookup.
    
    Example:
        >>> global_components = ComponentSet({"db": db_component})
        >>> request_components = ComponentSet({"service": service_component}, global_components)
        >>> request_components["db"]  # Found in parent
        >>> request_components["service"]  # Found locally
    """

    def __init__(
        self,
        components: dict[str, MaterialisedComponent],
        parent: Optional["ComponentSet"] = None,
    ):
        self.components = components
        self._parent = parent

    def __getitem__(self, item: str) -> MaterialisedComponent:
        if item in self.components:
            return self.components[item]
        if self._parent and item in self._parent:
            return self._parent[item]
        raise KeyError(item)

    def __contains__(self, item: str) -> bool:
        return item in self.components or (self._parent and item in self._parent)
