from dataclasses import dataclass
from typing import Callable, Annotated

import pytest

from versatile.registry import (
    DependencyError,
    ComponentProvider,
    Dependency,
    ComponentProviderRegistry,
)


@pytest.fixture
def registry():
    return ComponentProviderRegistry()


@pytest.fixture
def component_finder(registry):
    def find(name: str) -> ComponentProvider:
        return next(c for c in registry.registered_providers() if c.name == name)

    return find


@pytest.fixture
def greeter(registry, component_finder):
    @registry.provides(name="greeter", profiles=["test1"])
    def make_greeter() -> Callable[[str], str]:
        def greeter(name: str) -> str:
            return "Hello %s" % name

        return greeter

    return component_finder("greeter")


@pytest.fixture
def uppercase_greeter(registry, component_finder):
    @registry.provides(profiles=["test2"])
    def make_uppercase_greeter(
        greeter: Annotated[Callable[[str], str], "greeter"],
    ) -> Callable[[str], str]:
        def uppercase_greeter(name: str) -> str:
            return (greeter(name)).upper()

        return uppercase_greeter

    return component_finder("uppercase_greeter")


def test_provider_is_registered(greeter: ComponentProvider):
    assert greeter.profiles == ["test1"]
    assert greeter.func()("Dominic") == "Hello Dominic"
    assert greeter.provided_types == [Callable[[str], str]]


def test_name_can_be_resolved_from_declaring_function_name(
    uppercase_greeter: ComponentProvider,
):
    assert uppercase_greeter.name == "uppercase_greeter"


def test_provider_can_have_no_return_type(
    registry: ComponentProviderRegistry, component_finder
):
    @registry.provides(profiles=["test"])
    def make_foo():
        pass

    assert component_finder("foo").provided_types == []


def test_dependencies_can_be_identified_by_annotated_name(registry):
    @registry.provides(name="foo")
    def foo(name: Annotated[str, "bar"]) -> str:
        pass

    print(registry.registered_providers())
    assert registry.registered_providers()[0].dependencies[0].component_name == "bar"


def test_dependencies_can_be_identified_by_type_name(registry):
    @registry.provides(name="foo")
    def foo(name: str) -> str:
        pass

    dependency = registry.registered_providers()[0].dependencies[0]
    assert dependency.component_name is None
    assert dependency.declared_type == str


def test_retrieve_components_by_profile(registry):
    @registry.provides()
    def globally_defined():
        pass

    @registry.provides(profiles=["test"])
    def test_only():
        pass

    @registry.provides(profiles=["!test"])
    def not_test():
        pass

    @registry.provides(profiles=["prod", "uat"])
    def prod_or_uat():
        pass

    def components_in(*profiles):
        return {c.name for c in registry.registered_providers(set(profiles))}

    assert components_in() == {"globally_defined", "not_test"}
    assert components_in("test") == {"globally_defined", "test_only"}
    assert components_in("prod") == {"globally_defined", "not_test", "prod_or_uat"}
    assert components_in("uat") == {"globally_defined", "not_test", "prod_or_uat"}
    assert components_in("empty") == {"globally_defined", "not_test"}


def test_unannotated_parameter_maps_to_untyped_dependency_with_parameter_name(registry):
    @registry.provides()
    def make_foo(_ignored):
        pass

    dependency = registry.registered_providers()[0].dependencies[0]
    assert dependency.component_name == "_ignored"
    assert dependency.declared_type is None


def test_registers_class_by_name(registry):
    @registry.provides("user_service")
    @dataclass(frozen=True)
    class UserService:
        user_name: Annotated[str, "user_name"]

    provider = registry.registered_providers()[0]
    assert provider.name == "user_service"
    assert provider.dependencies == [Dependency("user_name", str, "user_name")]

    built = provider.func("Bob")
    assert built.user_name == "Bob"


def test_registers_class_by_type(registry):
    @registry.provides()
    class UserService:
        user_name: Annotated[str, "user_name"]

    provider = registry.registered_providers()[0]
    assert provider.name == "UserService"
