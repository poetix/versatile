from dataclasses import dataclass
from typing import Callable, Any, Annotated

import pytest

from versatile.builders import make_bundle
from versatile.errors import DependencyError
from versatile.registry import ComponentProviderRegistry

DB = Callable[[str], dict[str, Any]]


class Printer:
    def print(self, line):
        pass


class MockPrinter(Printer):
    def __init__(self):
        self.printed = []

    def print(self, user_details):
        for k, v in user_details.items():
            self.printed.append(f"{k}: {v}")


@dataclass(frozen=True)
class Service:
    db: DB
    printer: Printer

    def print_user_details(self, user_id):
        user_details = self.db(user_id)
        self.printer.print(user_details)


@pytest.fixture
def registry() -> ComponentProviderRegistry:
    registry = ComponentProviderRegistry()

    @registry.provides(profiles=["test"])
    def make_test_db() -> DB:
        def db(_user_id: str) -> dict[str, Any]:
            return {"name": "Arthur Putey", "age": 42}

        return db

    @registry.provides(profiles=["uat"])
    def make_uat_db() -> DB:
        def db(_user_id: str) -> dict:
            return {"name": "Gawain of Camelot", "age": 23}

        return db

    registry.provides(profiles=["test"])(MockPrinter)
    registry.provides()(Service)

    return registry


def test_build_resolving_by_declared_type(registry):
    bundle = make_bundle(registry, {"test"})
    service = bundle[Service]
    printer = bundle[Printer]
    service.print_user_details("id123")

    assert printer.printed == ["name: Arthur Putey", "age: 42"]


def test_resolve_by_qualifier():
    registry = ComponentProviderRegistry()

    @registry.provides(name="foo")
    def make_foo() -> str:
        return "foo"

    @registry.provides(name="bar")
    def make_bar() -> str:
        return "bar"

    @registry.provides()
    def make_concat(foo: Annotated[str, "foo"], bar: Annotated[str, "bar"]) -> str:
        return foo + bar

    bundle = make_bundle(registry)
    assert bundle["concat"] == "foobar"


def test_dependency_cycle_detected():
    registry = ComponentProviderRegistry()

    @registry.provides(name="a")
    def make_a(b: Annotated[int, "b"]) -> int:
        return b + 1

    @registry.provides(name="b")
    def make_b(a: Annotated[int, "a"]) -> int:
        return a + 1

    with pytest.raises(DependencyError, match="Unresolvable dependencies"):
        make_bundle(registry)


def test_missing_dependency_raises():
    registry = ComponentProviderRegistry()

    @registry.provides()
    def make_service(printer: Printer) -> Service:
        return ...

    with pytest.raises(
        DependencyError,
        match="Provider set has unsatisfied dependencies: {'Printer'}",
    ):
        make_bundle(registry)


def test_name_conflict_between_profiles_raises():
    registry = ComponentProviderRegistry()

    @registry.provides(name="x", profiles=["a"])
    def x_a() -> int:
        return 1

    @registry.provides(name="x", profiles=["b"])
    def x_b() -> int:
        return 2

    with pytest.raises(DependencyError, match="Duplicate provider name 'x'"):
        make_bundle(registry, {"a", "b"})


def test_child_bundle_resolves_from_parent():
    global_registry = ComponentProviderRegistry()
    kid_a_registry = ComponentProviderRegistry()
    kid_b_registry = ComponentProviderRegistry()
    arithmetic_registry = ComponentProviderRegistry()

    @global_registry.provides("lhs")
    def global_lhs() -> int:
        return 42

    @kid_a_registry.provides("rhs")
    def kid_a() -> int:
        return 23

    @kid_b_registry.provides("rhs")
    def kid_b() -> int:
        return 19

    @arithmetic_registry.provides("result")
    def adder(a: Annotated[int, "lhs"], b: Annotated[int, "rhs"]) -> int:
        return a + b

    global_bundle = make_bundle(global_registry)

    kid_a_bundle = make_bundle(kid_a_registry, parent=global_bundle)
    kid_b_bundle = make_bundle(kid_b_registry, parent=global_bundle)

    adder_a_bundle = make_bundle(arithmetic_registry, parent=kid_a_bundle)
    adder_b_bundle = make_bundle(arithmetic_registry, parent=kid_b_bundle)

    assert adder_a_bundle["result"] == 65
    assert adder_b_bundle["result"] == 61


def test_raises_if_child_component_aliases_parent():
    parent_registry = ComponentProviderRegistry()
    child_registry = ComponentProviderRegistry()

    @parent_registry.provides("it")
    def parent() -> int:
        return 23

    @child_registry.provides("it")
    def child() -> int:
        return 23

    parent_bundle = make_bundle(parent_registry)
    with pytest.raises(
        DependencyError,
        match=r"Provider names .* conflict with component in parent bundle",
    ):
        make_bundle(child_registry, parent=parent_bundle)


def test_keyword_only_dependency():
    registry = ComponentProviderRegistry()

    @registry.provides("foo")
    def make_foo() -> str:
        return "foo"

    @registry.provides("bar")
    def make_bar(*, foo: Annotated[str, "foo"]) -> str:
        return f"bar-{foo}"

    bundle = make_bundle(registry)
    assert bundle["bar"] == "bar-foo"


def test_scope_supplies_required_dependencies():
    registry = ComponentProviderRegistry()

    @registry.provides("result")
    def make_result(lhs: Annotated[int, "lhs"], rhs: Annotated[int, "rhs"]) -> int:
        return lhs + rhs

    bundle = make_bundle(registry, scope={"lhs": 2, "rhs": 3})

    assert bundle["result"] == 5


def test_scope_missing_dependency_raises():
    registry = ComponentProviderRegistry()

    @registry.provides("result")
    def make_result(lhs: Annotated[int, "lhs"]) -> int:
        return lhs

    with pytest.raises(DependencyError, match="Missing items {'lhs'}"):
        make_bundle(registry, scope={})


def test_scope_extraneous_dependency_raises():
    registry = ComponentProviderRegistry()

    @registry.provides("result")
    def make_result(lhs: Annotated[int, "lhs"]) -> int:
        return lhs

    with pytest.raises(DependencyError, match="Unexpected items {'foo'}"):
        make_bundle(registry, scope={"lhs": 1, "foo": 2})


def test_raises_if_child_provider_aliases_parent_type_for_type_dependency():
    """Test that providing the same type as parent raises error when type-based dependency exists."""
    parent_registry = ComponentProviderRegistry()
    child_registry = ComponentProviderRegistry()
    consumer_registry = ComponentProviderRegistry()

    # Parent provides a Printer component
    class Printer:
        def print(self, msg: str) -> str:
            return f"Parent: {msg}"

    @parent_registry.provides("parent_printer")
    def make_parent_printer() -> Printer:
        return Printer()

    # Child also provides a Printer component (different name, same type)
    @child_registry.provides("child_printer")
    def make_child_printer() -> Printer:
        return Printer()

    # Consumer has type-based dependency on Printer (no name specified)
    @consumer_registry.provides("service")
    def make_service(printer: Printer) -> str:  # Type-based dependency, no Annotated
        return printer.print("hello")

    parent_bundle = make_bundle(parent_registry)
    child_bundle = make_bundle(child_registry, parent=parent_bundle)

    # This should fail because consumer needs Printer by type,
    # but both parent and child provide Printer type, making it ambiguous
    with pytest.raises(
        DependencyError,
        match=r"Multiple candidates for dependency on type",
    ):
        make_bundle(consumer_registry, parent=child_bundle)


def test_raises_if_child_provider_aliases_parent_type_for_satisfied_dependency():
    """Test early detection when child provides type that parent also provides for a type dependency."""
    parent_registry = ComponentProviderRegistry()
    child_registry = ComponentProviderRegistry()

    class Service:
        pass

    # Parent provides Service
    @parent_registry.provides("parent_service")
    def make_parent_service() -> Service:
        return Service()

    # Child also provides Service, and has a type-based dependency on it
    @child_registry.provides("child_service")
    def make_child_service() -> Service:
        return Service()

    @child_registry.provides("consumer")
    def make_consumer(service: Service) -> str:  # Type-based dependency on Service
        return "result"

    parent_bundle = make_bundle(parent_registry)

    # This should fail because:
    # 1. Child registry has unsatisfied type dependency on Service
    # 2. Child registry also provides Service type
    # 3. Parent bundle also provides Service type
    # This creates ambiguity for the type-based dependency resolution
    with pytest.raises(
        DependencyError,
        match=r"Provider types .* alias types also provided by parent bundle",
    ):
        make_bundle(child_registry, parent=parent_bundle)
