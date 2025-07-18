from typing import Callable, Annotated

from versatile.builders import make_bundle
from versatile.registry import ComponentProviderRegistry

# Define a registry and register providers
registry = ComponentProviderRegistry()
DB = Callable[[str], dict[str, str]]
Service = Callable[[str], str]


@registry.provides(name="db", profiles=["test"])
def make_test_db() -> DB:
    return lambda user_id: {"name": "Arthur", "role": "admin"}


@registry.provides(name="db", profiles=["!test"])
def make_real_db() -> DB:
    return lambda user_id: {"name": "Martha", "role": "admin"}


@registry.provides()
def make_service(db: DB) -> Service:
    return lambda user_id: f"Welcome, {db(user_id)['name']}!"


# Build a global bundle
global_bundle = make_bundle(registry, {"test"})  # Change to e.g. 'prod' for non-test db

# Use the resolved service
service = global_bundle[Service]
print(service("u001"))  # Welcome, Arthur!
