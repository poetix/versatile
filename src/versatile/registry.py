from collections import defaultdict
from dataclasses import dataclass
from typing import Callable


__all__ = ['register_component', 'components_registered_in', 'provides', 'DEFAULT_CONTEXT']

DEFAULT_CONTEXT = 'default'

@dataclass
class Component:
    name: str
    func: Callable
    profiles: list[str]


_registered_components: dict[str, list[Component]] = defaultdict(list)


def register_component(context: str, component: Component):
    _registered_components[context].append(component)
    return component


def components_registered_in(context: str) -> list[Component]:
    return _registered_components[context]


def provides(name: str, profiles=None, context: str = DEFAULT_CONTEXT) -> Callable:
    if profiles is None:
        profiles = []

    def decorator(func):
        register_component(context, Component(name, func, profiles))
        return func

    return decorator
