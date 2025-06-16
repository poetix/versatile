from typing import Callable, Any, Annotated

import pytest

from versatile.bundle import make_bundle
from versatile.registry import ComponentProviderRegistry, DependencyError

DB = Callable[[str], dict[str, Any]]
Service = Callable[[str], None]

class Printer:
    def print(self, line):
        pass


class TestPrinter(Printer):
    def __init__(self):
        self.printed = []

    def print(self, user_details):
        for k, v in user_details.items():
            self.printed.append(f"{k}: {v}")


@pytest.fixture
def registry() -> ComponentProviderRegistry:
    registry =  ComponentProviderRegistry()

    @registry.provides(name='db', profiles=['test'])
    def make_test_db() -> DB:
        def db(_user_id: str) -> dict[str, Any]:
            return {'name': 'Arthur Putey', 'age': 42}
        return db

    @registry.provides(name='db', profiles=['uat'])
    def make_uat_db() -> DB:
        def db(_user_id: str) -> dict:
            return {'name': 'Gawain of Camelot', 'age': 23}

        return db

    @registry.provides(name='printer', profiles=['test'])
    def make_test_printer() -> Printer:
        return TestPrinter()

    @registry.provides()
    def make_service(db: DB,
                     printer: Printer) -> Service:
        def service_func(user_id: str) -> None:
            user_details = db(user_id)
            printer.print(user_details)
        return service_func
    return registry


def test_build_resolving_by_declared_type(registry):
    bundle = make_bundle(registry, {'test'})
    service = bundle[Service]
    printer = bundle[Printer]
    service("id123")

    assert printer.printed == [
        'name: Arthur Putey',
        'age: 42'
    ]



def test_resolve_by_qualifier():
    registry = ComponentProviderRegistry()

    @registry.provides(name='foo')
    def make_foo() -> str:
        return "foo"

    @registry.provides(name='bar')
    def make_bar() -> str:
        return "bar"

    @registry.provides()
    def make_concat(foo: Annotated[str, 'foo'], bar: Annotated[str, 'bar']) -> str:
        return foo + bar

    bundle = make_bundle(registry)
    assert bundle['concat'] == "foobar"


def test_dependency_cycle_detected():
    registry = ComponentProviderRegistry()

    @registry.provides(name='a')
    def make_a(b: Annotated[int, 'b']) -> int:
        return b + 1

    @registry.provides(name='b')
    def make_b(a: Annotated[int, 'a']) -> int:
        return a + 1

    with pytest.raises(DependencyError, match="Unresolvable dependencies"):
        make_bundle(registry)


def test_missing_dependency_raises():
    registry = ComponentProviderRegistry()

    @registry.provides()
    def make_service(printer: Printer) -> Service:
        return lambda _: None

    with pytest.raises(DependencyError, match="No unique provider for type.*Printer"):
        make_bundle(registry)


def test_name_conflict_between_profiles_raises():
    registry = ComponentProviderRegistry()

    @registry.provides(name='x', profiles=['a'])
    def x_a() -> int: return 1

    @registry.provides(name='x', profiles=['b'])
    def x_b() -> int: return 2

    with pytest.raises(DependencyError, match="Duplicate provider name"):
        make_bundle(registry, {'a', 'b'})
