import uuid
from functools import reduce
from typing import Callable, Any

from versatile.domain import MaterialisedComponent
from versatile.registry import ComponentProvider


class ComponentBuilder:
    def __init__(
        self,
        transformers: list[Callable[[MaterialisedComponent], MaterialisedComponent]],
    ):
        self._transformers = transformers

    def build(
        self, provider: ComponentProvider, dependencies: dict[str, Any]
    ) -> MaterialisedComponent:
        component_obj = provider.func(*dependencies.values())

        untransformed = MaterialisedComponent(
            uuid.uuid4(),
            provider.name,
            provider.provided_type,
            component_obj,
            list(dependencies.keys()),
            provider.metadata,
        )
        return reduce(
            lambda component, transformer: transformer(component),
            self._transformers,
            untransformed,
        )
