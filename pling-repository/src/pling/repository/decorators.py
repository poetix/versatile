from typing import Callable

__all__ = ['repository']

from versatile.domain import MaterialisedComponent


def set_metadata(func: Callable, **kwargs) -> Callable:
    metadata = func.__provider_metadata__ if hasattr(func, '__provider_metadata__') else {}
    metadata.update(kwargs)
    func.__provider_metadata__ = metadata
    return func


def repository() -> Callable:
    def decorator(func: Callable) -> Callable:
        return set_metadata(func, is_repository=True)

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
            component.declared_type,
            make_repository(component.component, db),
            component.dependencies,
            component.metadata,
        )

    return build

