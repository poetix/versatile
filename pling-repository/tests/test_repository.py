import pytest

from versatile.registry import ComponentProviderRegistry
from pling.repository import repository

@pytest.fixture
def registry():
    return ComponentProviderRegistry()

def test_decorator_tags_provider(registry):
    @registry.provides()
    @repository("db")
    def my_repo():
        pass

    repo = registry.registered_providers()[0]
    assert repo.metadata == { "db_name": "db", "is_repository": True }
