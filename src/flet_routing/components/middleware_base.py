from ..types import MiddlewareContext


class MiddlewareBase:
    """Base class for class‑based middlewares.

    Subclass this and implement ``__call__(self, ctx: MiddlewareContext) -> bool``.
    Instances of the subclass can be registered with :meth:`use` just like a
    plain callable middleware.
    """

    def __call__(self, ctx: 'MiddlewareContext') -> bool:  # pragma: no cover
        raise NotImplementedError("MiddlewareBase subclasses must implement __call__")
