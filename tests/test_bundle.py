from typing import Callable, Annotated

import pytest

from versatile.bundle import make_bundle
from versatile.registry import DependencyError, ComponentProvider, Dependency, ComponentProviderRegistry

@pytest.fixture
def registry() -> ComponentProviderRegistry:
    return ComponentProviderRegistry()

def test_build_bundle(registry):
    printed = []
    @registry.provides()
    def make_db() -> Callable[[str], dict]:
        def db(_user_id: str) -> dict:
            return {'name': 'Arthur Putey', 'age': 42}
        return db

    @registry.provides()
    def make_printer() -> Callable[[dict], None]:
        def printer(details: dict):
            nonlocal printed
            for key, value in details.items():
                printed.append(f'{key}: {value}')
        return printer

    @registry.provides()
    def make_service(db: Annotated[Callable[[str], dict], "db"],
                     printer: Annotated[Callable[[dict], None], "printer"]) -> Callable[[str], None]:
        def service_func(user_id: str) -> None:
            user_details = db(user_id)
            printer(user_details)
        return service_func

    bundle = make_bundle(registry)
    service = bundle["service"]
    service("id123")

    assert printed == [
        'name: Arthur Putey',
        'age: 42'
    ]

