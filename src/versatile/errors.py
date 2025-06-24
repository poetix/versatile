__all__ = ["DependencyError"]


class DependencyError(Exception):
    """Raised when a component's dependency cannot be resolved or is misannotated."""

    pass
