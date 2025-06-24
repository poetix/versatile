from typing import Optional

from versatile.domain import MaterialisedComponent


class ComponentSet:
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
