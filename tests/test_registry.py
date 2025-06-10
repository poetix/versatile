from typing import Callable, Annotated

import pytest

from versatile.registry import DependencyError, Component, Dependency, ComponentRegistry

@pytest.fixture
def registry():
    return ComponentRegistry()

@pytest.fixture
def component_finder(registry):
    def find(name: str) -> Component:
        return next(c for c in registry.components() if c.name == name)
    return find

@pytest.fixture
def greeter(registry, component_finder):
    @registry.provides(name='greeter', profiles=['test1'])
    def make_greeter() -> Callable[[str], str]:
        def greeter(name: str) -> str:
            return "Hello %s" % name

        return greeter
    return component_finder('greeter')

@pytest.fixture
def uppercase_greeter(registry, component_finder):
    @registry.provides(profiles=['test2'])
    def make_uppercase_greeter(greeter: Annotated[Callable[[str], str], 'greeter']) -> Callable[[str], str]:
        def uppercase_greeter(name: str) -> str:
            return (greeter(name)).upper()

        return uppercase_greeter
    return component_finder('uppercase_greeter')


def test_provider_is_registered(greeter: Component):
    assert greeter.profiles == ['test1']
    assert greeter.func()("Dominic") == 'Hello Dominic'
    assert greeter.provided_type == Callable[[str], str]


def test_name_resolution_from_declaring_function_name(uppercase_greeter: Component):
    assert uppercase_greeter.name == 'uppercase_greeter'


def test_provider_can_have_no_return_type(registry: ComponentRegistry, component_finder):
    @registry.provides(profiles=['test'])
    def make_foo():
        pass

    assert component_finder('foo').provided_type is None


def test_dependencies(uppercase_greeter):

    assert uppercase_greeter.dependencies == [
        Dependency('greeter', Callable[[str], str], 'greeter')
    ]


def test_retrieve_components_by_profile(registry):
    @registry.provides()
    def globally_defined(): pass

    @registry.provides(profiles = ['test'])
    def test_only(): pass

    @registry.provides(profiles = ['!test'])
    def not_test(): pass

    @registry.provides(profiles = ['prod', 'uat'])
    def prod_or_uat(): pass

    def components_in(*profiles):
        return { c.name for c in registry.components(set(profiles)) }

    assert components_in() == { 'globally_defined', 'not_test' }
    assert components_in('test') == { 'globally_defined', 'test_only' }
    assert components_in('prod') == { 'globally_defined', 'not_test', 'prod_or_uat' }
    assert components_in('uat') == { 'globally_defined', 'not_test', 'prod_or_uat' }
    assert components_in('empty') == { 'globally_defined', 'not_test' }


def test_throws_dependency_error_on_unannotated_provider_param(registry):
    with pytest.raises(DependencyError, match="Dependency.*is not annotated"):
        @registry.provides()
        def make_foo(bar):
            pass