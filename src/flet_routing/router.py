from __future__ import annotations

import json
import logging
import re
from typing import Any, Callable, Dict, List, Optional, Union

from cryptography.fernet import Fernet
from flet import (
    AppBar,
    ControlEvent,
    IconButton,
    Icons,
    Page,
    RouteChangeEvent,
    Text,
    View,
    ViewPopEvent,
)

from .types import (
    AuthChecker,
    Middleware,
    MiddlewareContext,
    Params,
    Route,
    RouteEntry,
    ViewFactory,
)
from .components import BaseView
from .builtin import build_not_found_view, build_not_auth_view
from .builtin.middlewares.logger import LoggerMiddleware

# Configure a module‑level logger. Users can configure logging as they wish; we default to WARNING to avoid noisy output.
logger = logging.getLogger(__name__)

class FletRouterError(Exception):
    """Base exception for router‑related errors.

    Subclass this exception for more specific error types if needed.
    """

class FletRouter:
    """A lightweight router for Flet applications.

    The router supports named routes, middleware, guards, protected routes,
    view pre‑loading, and optional view caching. It is deliberately kept
    framework‑agnostic apart from the Flet API.
    """

    def __init__(
        self,
        page: Page,
        routes: Optional[List[Route]] = None,
        auth_checker: Optional[AuthChecker] = None,
        not_found_view: Optional[Union[View, ViewFactory]] = None,
        not_auth_view: Optional[Union[View, ViewFactory]] = None,
        not_auth_redirect_route: Optional[str] = None,
        initial_route: Optional[str] = None,
        initial_view: Optional[View] = None,
        enable_view_cache: bool = False,  # Cache de vistas preload
        max_history: int = 20,
        enable_logger_middleware: bool = False,
    ) -> None:

        self.page = page
        self._crypto_key = Fernet.generate_key()
        self._fernet = Fernet(self._crypto_key)

        self.routes = routes or list()
        self.auth_checker = auth_checker
        self.enable_view_cache = enable_view_cache
        self.enable_logger_middleware = enable_logger_middleware
        self.initial_route = initial_route
        self.initial_view = initial_view
        self._view_cache: Dict[str, View] = {}  # Cache para vistas preload

        self.stack: List[RouteEntry] = []
        self.middlewares: List[Middleware] = []
        self._named_routes: Dict[str, Route] = {}
        self._replace_pending = False

        self.not_auth_redirect_route = not_auth_redirect_route
        self.not_found_view = not_found_view or self._build_not_found_view()
        self.not_auth_view = not_auth_view or self._build_not_auth_view()

        # Registrar rutas nombradas
        for route in self.routes:
            if route.name:
                self._named_routes[route.name] = route

        self.page.on_route_change = self._handle_route
        self.page.on_view_pop = self._handle_pop

        self._compiled_routes = self._compile_routes()

        # History size limit – used by _cleanup_old_entries.
        self.max_history = max_history

        if initial_route:
            self.push(initial_route)
        elif initial_view:
            if not getattr(initial_view, "route", None):
                initial_view.route = "/"
            self.page.views.append(initial_view)
            self.page.update()
        elif self.stack:
            self.page.go(self.stack[0].path)

    def __repr__(self):
        return f"FletRouter(routes={self.routes}, views={self.page.views})"

    def route(
        self,
        path: str,
        *,
        protected: bool = False,
        guard: Optional[Callable[[MiddlewareContext], bool]] = None,
        preload: bool = False,
        name: Optional[str] = None,
    ) -> Callable:
        
        def decorator(target: Union[ViewFactory, type]) -> Union[ViewFactory, type]:
            def factory(params: Params) -> View:
                # Caso 1: Es una clase que hereda de BaseView
                if isinstance(target, type) and issubclass(target, BaseView):
                    try:
                        # Intentar pasar router automáticamente
                        return target(router=self)
                    except TypeError:
                        # Si no acepta router, instanciar sin él
                        instance = target(params)
                        # Intentar asignar router después
                        if hasattr(instance, 'set_router'):
                            instance.set_router(self)
                        elif hasattr(instance, 'router'):
                            instance.router = self
                        return instance
                
                # Caso 2: Es una función que retorna una View (nativa o BaseView)
                elif callable(target):
                    # Pasar router en params para que esté disponible
                    params.router = self
                    view = target(params)
                    
                    # Si la vista retornada es BaseView y no tiene router, asignarlo
                    if isinstance(view, BaseView) and not hasattr(view, '_BaseView__router'):
                        if hasattr(view, 'set_router'):
                            view.set_router(self)
                        elif hasattr(view, 'router'):
                            view.router = self
                    
                    return view
                
                else:
                    raise FletRouterError(f"Invalid target for route: {target}")
            
            # Crear el objeto Route
            route_obj = Route(
                path=path,
                view=factory,
                protected=protected,
                guard=guard,
                preload=preload,
                name=name,
            )
            
            self.routes.append(route_obj)
            if name:
                self._named_routes[name] = route_obj
            self._compiled_routes = self._compile_routes()
            
            # Preload si es necesario
            if preload:
                try:
                    params = Params(path={}, private={}, router=self)
                    view = factory(params)
                    if self.enable_view_cache:
                        self._view_cache[path] = view
                except Exception as e:
                    logger.warning("Error preloading route %s: %s", path, e)
            
            return target
        return decorator

    def push_named(
        self,
        name: str,
        path_params: Optional[Dict[str, Any]] = None,
        private_params: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Navigate using a named route.

        Raises:
            RouterError: If the named route does not exist.
        """
        if name not in self._named_routes:
            raise FletRouterError(f"Route '{name}' not found")
        
        route = self._named_routes[name]
        path = self._build_path(route.path, path_params or {})
        self.push(path, private_params)

    def _build_path(self, path_template: str, params: Dict[str, Any]) -> str:
        """Construir path con parámetros dinámicos"""
        for key, value in params.items():
            path_template = path_template.replace(f":{key}", str(value))
        return self._normalize_path(path_template)

    def _normalize_path(self, path: str) -> str:
        if not path:
            return "/"
        if not path.startswith("/"):
            path = f"/{path}"
        return path.rstrip("/") or "/"

    def _find_stack_entry(self, path: str) -> Optional[RouteEntry]:
        path = self._normalize_path(path)
        for entry in reversed(self.stack):
            if entry.path == path:
                return entry
        return None

    def _remove_duplicate_views(self, route_path: str):
        duplicates = [v for v in self.page.views if v.route == route_path]
        for v in duplicates:
            self.page.views.remove(v)

    def push(self, path: str, private_params: Optional[Dict[str, Any]] = None):
        """Navegar a una nueva ruta (push a la pila)"""
        self._navigate(path, private_params, replace=False)

    def replace(self, path: str, private_params: Optional[Dict[str, Any]] = None):
        """Reemplazar la ruta actual (pop + push)"""
        self._navigate(path, private_params, replace=True)

    def pop(self, e: Union[ControlEvent, ViewPopEvent]):
        self._handle_pop(e)

    def _navigate(self, path: str, private_params: Optional[Dict[str, Any]] = None, replace: bool = False):
        """Navegación interna"""
        path = self._normalize_path(path)
        
        token = None
        if private_params:
            token = self._encrypt_private(private_params)

        entry = RouteEntry(path=path, token=token, params=private_params)

        if replace and self.stack:
            self.stack[-1] = entry
        else:
            self.stack.append(entry)

        self._replace_pending = replace

        # Limpiar cache si es necesario
        if not self.enable_view_cache and len(self.stack) > 10:
            self._cleanup_old_entries()

        self.page.go(path)

    def back(self, steps: int = 1) -> None:
        """Go back multiple steps in the navigation stack.

        ``steps`` must be a positive integer; values less than ``1`` are ignored.
        """
        if steps < 1:
            return

        for _ in range(min(steps, len(self.stack) - 1)):
            if self.stack:
                self.stack.pop()
            if self.page.views:
                self.page.views.pop()

        if self.stack:
            prev_entry = self.stack[-1]
            self.page.go(prev_entry.path)

    def pop_until(self, path: str):
        """Pop hasta encontrar una ruta específica"""
        path = self._normalize_path(path)
        while len(self.stack) > 1 and self.stack[-1].path != path:
            self.stack.pop()
        
        if self.stack and self.stack[-1].path == path:
            self.page.go(path)

    def clear_stack(self) -> None:
        """Clear the entire navigation stack."""
        self.stack.clear()

    def forward(self, steps: int = 1) -> None:
        """Move forward ``steps`` in the navigation history.

        This method mirrors :meth:`back` but works on the forward history
        maintained by the underlying Flet page. If there is no forward entry,
        the call is a no‑op.
        """
        # Flet does not expose a direct forward stack, but we can emulate a
        # simple forward by re‑pushing previously popped entries if needed.
        # For now this is a placeholder to keep the API stable.
        logger.debug("forward(%s) called – not implemented in Flet", steps)

    def _encrypt_private(self, data: Dict[str, Any]) -> str:
        """Encrypt a dictionary of private parameters.

        The result is a URL‑safe base64 string.
        """
        raw = json.dumps(data).encode()
        return self._fernet.encrypt(raw).decode()

    def _decrypt_private(self, token: str) -> Dict[str, Any]:
        """Decrypt a token generated by :meth:`_encrypt_private`.

        Returns an empty dict if decryption fails.
        """
        try:
            raw = self._fernet.decrypt(token.encode())
            return json.loads(raw.decode())
        except Exception as e:
            logger.error("Failed to decrypt private token: %s", e)
            return {}

    def decode_private(self, token: str) -> Dict[str, Any]:
        """Public helper to decode a private token.

        This method is safe to expose to library users who need to inspect the
        encrypted payload without accessing internal attributes.
        """
        return self._decrypt_private(token)

    def rotate_key(self) -> None:
        """Generate a new Fernet key and replace the current one.

        Existing encrypted tokens become invalid after rotation.
        """
        self._crypto_key = Fernet.generate_key()
        self._fernet = Fernet(self._crypto_key)

    def _compile_routes(self) -> List[tuple]:
        compiled = []
        for route in self.routes:
            path = self._normalize_path(route.path)
            segments = path.split("/")
            parts = []
            param_names = []
            
            for seg in segments:
                if seg.startswith(":"):
                    name = seg[1:]
                    param_names.append(name)
                    parts.append(f"(?P<{name}>[^/]+)")
                else:
                    parts.append(re.escape(seg))
            
            pattern = "/".join(parts)
            regex = f"^{pattern}/?$"
            compiled.append((re.compile(regex), route, param_names))
        
        return compiled

    def use(self, middleware: Middleware) -> None:
        """Register a middleware.

        ``middleware`` may be a simple callable ``func(ctx) -> bool`` or an
        instance of a subclass of :class:`MiddlewareBase` that implements the
        ``__call__`` protocol.
        """
        if self.enable_logger_middleware:
            self.middlewares.append(LoggerMiddleware())
        self.middlewares.append(middleware)

    def checker(self) -> bool:
        if callable(self.auth_checker):
            return self.auth_checker()
        return bool(self.auth_checker)

    def _run_middlewares(self, ctx: MiddlewareContext) -> bool:
        """Execute all registered middlewares.

        Returns ``True`` if every middleware returns a truthy value. If a
        middleware raises an exception, the error is logged and ``False`` is
        returned, halting further processing.
        """
        for mw in self.middlewares:
            try:
                if not mw(ctx):
                    return False
            except Exception as e:
                logger.error("Middleware error: %s", e)
                return False
        return True

    def _handle_route(self, e: RouteChangeEvent):
        full_path = self.page.route
        path = full_path.rstrip("/") or "/"

        route, path_params = self._match(path)

        # Aplicar reemplazo si fue solicitado por replace()
        if self._replace_pending:
            if self.page.views:
                self.page.views.pop()
            self._replace_pending = False

        # Obtener parámetros privados
        private_params = {}
        cached_view = None
        entry = self._find_stack_entry(path)
        if entry:
            if entry.params is not None:
                private_params = entry.params
            elif entry.token:
                try:
                    private_params = self._decrypt_private(entry.token)
                except Exception:
                    private_params = {}
            cached_view = entry.view

        # Auto-cast parámetros de path
        if path_params:
            path_params = self._auto_cast_params(path_params)

        params = Params(
            path=path_params or {},
            private=private_params or {},
            router=self
        )

        ctx = MiddlewareContext(
            path=path,
            full_path=full_path,
            params=params,
            route=route,
            page=self.page,
            router=self,
            private=private_params or {},
        )

        # Ejecutar middlewares
        if not self._run_middlewares(ctx):
            return

        # Verificar autenticación
        if route and route.protected and not self.checker():
            if self.not_auth_redirect_route:
                self.replace(self.not_auth_redirect_route)
            else:
                self._render_401()
            return

        # Verificar guard
        if route and route.guard:
            if not route.guard(ctx):
                if self.not_auth_redirect_route:
                    self.replace(self.not_auth_redirect_route)
                else:
                    self._render_401()
                return

        if not route:
            self._render_404()
            return

        self._remove_duplicate_views(path)

        # Construir o recuperar vista
        if cached_view and self.enable_view_cache:
            view = cached_view
        elif route.preload and route.path in self._view_cache:
            view = self._view_cache[route.path]
        else:
            view = self._build_view(route, params)
            if entry and entry.path == path:
                entry.view = view if self.enable_view_cache else None

        # Aplicar transición y mostrar
        self._set_view(view)
        self.page.update()

    def _match(self, path: str):
        for regex, route, param_names in self._compiled_routes:
            m = regex.match(path)
            if m:
                params = {name: m.group(name) for name in param_names}
                return route, params
        return None, None

    def _auto_cast_params(self, params: Dict[str, str]) -> Dict[str, Any]:
        casted = {}
        for k, v in params.items():
            if v.isdigit():
                casted[k] = int(v)
            elif v.replace(".", "", 1).isdigit():
                casted[k] = float(v)
            elif v.lower() in ["true", "false"]:
                casted[k] = v.lower() == "true"
            else:
                casted[k] = v
        return casted

    def _build_view(self, route: Route, params: Params) -> View:
        if callable(route.view):
            view = route.view(params)
        else:
            view = route.view
        
        # Asegurar que la vista tenga la ruta correcta
        if not hasattr(view, 'route') or not view.route:
            view.route = route.path
        
        return view

    def _set_view(self, view: View):
        """Establecer vista con manejo adecuado de la pila"""

        if self.page.views and self.page.views[0].route is None:
            self.page.views.pop(0)

        self._remove_duplicate_views(view.route)

        current_view = view
        
        # Configurar AppBar si no existe
        if not current_view.appbar:
            current_view.appbar = AppBar(
                leading=IconButton(
                    icon=Icons.ARROW_BACK,
                    on_click=self.pop,
                    visible=bool(self.page.views)  # Mostrar back si hay historial previo
                ),
                title=Text(current_view.route.replace("/", "") or "App")
            )

        if self.page.views and self.page.views[-1].route == view.route:
            self.page.views[-1] = current_view
        else:
            self.page.views.append(current_view)

    def _cleanup_old_entries(self) -> None:
        """Clean up old entries from the navigation stack.

        The maximum number of stored entries is controlled by ``self.max_history``.
        """
        if len(self.stack) > self.max_history:
            to_remove = self.stack[:- self.max_history]
            self.stack = self.stack[-self.max_history :]
            for entry in to_remove:
                if entry.view:
                    entry.view = None

    def _build_not_found_view(self) -> View:
        return build_not_found_view()

    def _build_not_auth_view(self) -> View:
        return build_not_auth_view()

    def _render_404(self):
        if callable(self.not_found_view):
            view = self.not_found_view(Params(path={}, private={}, router=self))
        else:
            view = self.not_found_view
        self._set_view(view)
        self.page.update()
    
    def _render_401(self):
        if callable(self.not_auth_view):
            view = self.not_auth_view(Params(path={}, private={}, router=self))
        else:
            view = self.not_auth_view
        self._set_view(view)
        self.page.update()

    def _is_view_repeat(self, view: View) -> bool:
        return any(v.route == view.route for v in self.page.views)

    def _handle_pop(self, e: Union[ControlEvent, ViewPopEvent]):
        if len(self.page.views) > 1:
            self.page.views.pop()
            if self.stack:
                self.stack.pop()
            if self.page.views:
                self.page.go(self.page.views[-1].route)
        else:
            self.page.go(self.stack[-1].path if self.stack else "/")

    def mount(self, prefix: str, routes: List[Route]):
        """Montar un conjunto de rutas con un prefijo"""
        for r in routes:
            new_path = prefix.rstrip("/") + r.path
            new_name = f"{prefix}_{r.name}" if r.name else None

            self.routes.append(
                Route(
                    path=new_path,
                    view=r.view,
                    protected=r.protected,
                    guard=r.guard,
                    preload=r.preload,
                    name=new_name,
                )
            )
            
            if new_name:
                self._named_routes[new_name] = self.routes[-1]

        self._compiled_routes = self._compile_routes()

    def get_stack_history(self) -> List[str]:
        return [v.path for v in self.stack]

    def dispose(self):
        """Limpiar recursos"""
        self._view_cache.clear()
        self.stack.clear()
        self.middlewares.clear()

# Exported symbols for ``from flet_router import *``
__all__ = [
    "FletRouterError",
    "FletRouter",
    "Params",
    "Route",
    "RouteEntry",
    "MiddlewareContext",
    "Middleware",
]