from typing import Callable, Any

__all__ = ['repository']

from versatile.domain import MaterialisedComponent


def set_metadata(func: Callable, **kwargs) -> Callable:
    metadata = func.__provider_metadata__ if hasattr(func, '__provider_metadata__') else {}
    metadata.update(kwargs)
    func.__provider_metadata__ = metadata
    return func


def repository(db_name: str) -> Callable:
    def decorator(target: type) -> Callable:
        return set_metadata(target, is_repository=True, db_name = db_name)

    return decorator

def sql(query: str) -> Callable:
    def decorator(target: Any) -> Any:
        target.__sql__ = query
        return target

    return decorator


def make_repository(component, db):
    return component


def repository_builder(db):
    def build(component: MaterialisedComponent) -> MaterialisedComponent:
        if not component.metadata.get("is_repository"):
            return component

        return MaterialisedComponent(
            component.id,
            component.name,
            component.declared_types,
            make_repository(component.component, db),
            component.dependencies,
            component.metadata,
        )

    return build

