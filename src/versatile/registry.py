import inspect
from dataclasses import dataclass
from typing import Callable, get_type_hints, get_origin, Annotated, get_args, Optional

__all__ = [
    'DependencyError',
    'Dependency',
    'Component',
    'ComponentRegistry']

class DependencyError(Exception):
    pass

@dataclass
class Dependency:
    name: str
    type: type
    qualifier: Optional[str]


@dataclass
class Component:
    name: str
    func: Callable
    profiles: list[str]
    provided_type: Optional[type]
    dependencies: list[Dependency]


class ComponentRegistry:
    def __init__(self):
        self._components = []

    def register(self, component: Component):
        self._components.append(component)

    def components(self, profiles: set[str] = None) -> list[Component]:
        if profiles is None:
            return self._components
        return [c for c in self._components if profiles_match(c.profiles, profiles)]

    def provides(self, name: str=None, profiles=None) -> Callable:
        if profiles is None:
            profiles = []

        def decorator(func: Callable) -> Callable:
            inferred_name = name or infer_name_from(func.__name__)

            component = Component(
                inferred_name,
                func,
                profiles,
                get_type_hints(func).get('return', None),
                get_dependencies(func)
            )
            self.register(component)
            return func

        return decorator


def profiles_match(stated: list[str], selected: set[str]) -> bool:
    provided = [p for p in stated if not p.startswith('!')]
    excluded = [p[1:] for p in stated if p.startswith('!')]

    if any(e for e in excluded if e in selected):
        return False

    if len(provided) == 0: return True

    return any(p for p in provided if p in selected)


def infer_name_from(name: str) -> str:
    if name.startswith('make_'):
        return name[5:]
    else:
        return name


def get_dependencies(func: Callable) -> list[Dependency]:
    sig = inspect.signature(func)
    hints = get_type_hints(func, include_extras=True)
    result = []

    for name, param in sig.parameters.items():
        try:
            annotation = hints[name]
        except KeyError:
            raise DependencyError("Dependency <%s> of provider <%s> is not annotated" %
                                  (name, func.__name__))

        if get_origin(annotation) is Annotated:
            base_type, *metadata = get_args(annotation)
        else:
            base_type, metadata = annotation, []

        result.append(Dependency(name, base_type, next((m for m in metadata), None)))

    return result


