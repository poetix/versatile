from collections import defaultdict
from typing import Optional

from versatile.registry import DependencyError, ComponentProvider, Dependency, ComponentProviderRegistry

def make_bundle(registry: ComponentProviderRegistry, profiles: Optional[set[str]]=None) -> dict:
    providers = registry.registered_providers(profiles)
    
    provider_lookup = _ProviderLookup(providers)
    dependency_graph = provider_lookup.get_dependency_graph()

    materialised = {}
    ready_to_materialise = [provider_name for provider_name, deps in dependency_graph.items()
                          if len(deps) == 0]

    while len(ready_to_materialise) > 0:
        ready_provider_name = ready_to_materialise.pop()
        del dependency_graph[ready_provider_name]

        materialised[ready_provider_name] = provider_lookup.materialise_component(
            ready_provider_name, materialised)

        for provider_name, deps in dependency_graph.items():
            if len(deps) > 0:
                deps.discard(ready_provider_name)
                if len(deps) == 0:
                    ready_to_materialise.append(provider_name)

    if len(dependency_graph) > 0:
        raise DependencyError(f"Unresolvable dependencies: {dependency_graph.keys()}")

    return materialised


class _ProviderLookup:
    def __init__(self, providers):
        providers_by_name: dict[str, ComponentProvider] = {}
        provider_names_by_type: dict[type, list[str]] = defaultdict(list)

        for provider in providers:
            if provider.name in providers_by_name:
                raise DependencyError(f"Duplicate provider name {provider.name}")
            providers_by_name[provider.name] = provider
            provider_names_by_type[provider.provided_type].append(provider.name)

        unique_provider_names_by_type: dict[type, str] = {
            provider_type: providers_of_type[0]
            for provider_type, providers_of_type in provider_names_by_type.items()
            if len(providers) == 1
        }

        self.providers_by_name = providers_by_name
        self.unique_provider_names_by_type = unique_provider_names_by_type


    def get_dependency_graph(self) -> dict[str, set[str]]:
        dependency_graph: dict[str, set[str]] = defaultdict(set)

        for provider_name, provider in self.providers_by_name.items():
            dependency_graph[provider.name].update(
                self.find_matching_provider_name(dependency, provider)
                for dependency in provider.dependencies
            )

        return dependency_graph


    def find_matching_provider_name(self, dependency, provider) -> str:
        if dependency.qualifier:
            if not dependency.qualifier in self.providers_by_name:
                raise DependencyError(
                    f"No provider with qualifier {dependency.qualifier} found for dependency "
                    f"{dependency.name} of provider {provider.name}")
            else:
                return dependency.qualifier
        else:
            try:
                return self.unique_provider_names_by_type[dependency.type]
            except KeyError:
                raise DependencyError(
                    f"No unique provider for type {dependency.type} found for dependency "
                    f"{dependency.name} of provider {provider.name}"
                )

    def materialise_component(self, provider_name: str, materialised_components: dict):
        provider = self.providers_by_name[provider_name]
        materialised_component = provider.func(*(
            materialised_components[self.find_matching_provider_name(dependency, provider)]
            for dependency in provider.dependencies))
        return materialised_component


