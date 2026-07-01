from __future__ import annotations

from ...types.types import MiddlewareContext
from ...components import MiddlewareBase

class LoggerMiddleware(MiddlewareBase):
    def __call__(self, ctx: 'MiddlewareContext'):
        print("-----------------------------------")
        print(f"[LOG]: Route -> {ctx.route}")
        print(f"[LOG]: Private -> {ctx.private}")
        print(f"[LOG]: Path -> {ctx.path}")
        print(f"[LOG]: Params -> {ctx.params}")
        print(f"[LOG]: Full Path -> {ctx.full_path}")
        print(f"[LOG]: Router -> {ctx.router}")
        print("-----------------------------------")
        return True