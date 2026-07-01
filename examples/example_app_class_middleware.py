import sys
import os
from typing import Any

# Ensure the src package is on the path
sys.path.append(os.path.join(os.getcwd(), "src"))

from flet_router import FletRouter, MiddlewareBase, MiddlewareContext, Params
from flet import (
    Page,
    View,
    AppBar,
    IconButton,
    Icons,
    Text,
    TextField,
    Container,
    Column,
    Row,
    Card,
    Image,
    ImageFit,
    ElevatedButton,
    TextButton,
    padding,
    alignment,
    MainAxisAlignment,
    CrossAxisAlignment,
    Colors,
    FontWeight,
    ThemeMode,
)

# Simple session object for demo purposes
class Session:
    def __init__(self) -> None:
        self.authenticated: bool = False
        self.user: str | None = None

session = Session()

# ---------------------------------------------------------------------------
# Class‑based middlewares
# ---------------------------------------------------------------------------
class AuthMiddleware(MiddlewareBase):
    """Redirect unauthenticated users to the login page for protected routes."""

    def __call__(self, ctx: MiddlewareContext) -> bool:
        # If the route is protected and the user is not authenticated, redirect.
        if ctx.route and ctx.route.protected and not session.authenticated:
            # Preserve the original destination so we can return after login.
            ctx.router.replace(
                "/login",
                {"redirect": ctx.full_path},
            )
            return False
        return True

class LoggingMiddleware(MiddlewareBase):
    """Log every navigation event (useful for debugging)."""

    def __call__(self, ctx: MiddlewareContext) -> bool:
        print(f"[LOG] Navigating to {ctx.full_path} (protected={ctx.route.protected if ctx.route else False})")
        return True

# ---------------------------------------------------------------------------
# Application entry point
# ---------------------------------------------------------------------------
def main(page: Page) -> None:
    page.title = "Flet Router – Class Middleware Demo"
    page.theme_mode = ThemeMode.LIGHT
    page.scroll = "adaptive"

    router = FletRouter(
        page,
        enable_view_cache=True,
        auth_checker=lambda: session.authenticated,
        not_auth_redirect_route="/login",
    )

    # Register class‑based middlewares
    router.use(AuthMiddleware())
    router.use(LoggingMiddleware())

    # -----------------------------------------------------------------------
    # Public Home page
    # -----------------------------------------------------------------------
    @router.route("/", name="home")
    def home_view(params: Params) -> View:
        return View(
            route="/",
            appbar=AppBar(
                title=Text("Home – Material Design"),
                bgcolor=Colors.BLUE_600,
                actions=[
                    IconButton(
                        icon=Icons.LOGIN if not session.authenticated else Icons.EXIT_TO_APP,
                        on_click=lambda e: router.push("/login" if not session.authenticated else "/logout"),
                    )
                ],
            ),
            controls=[
                Container(
                    content=Column(
                        controls=[
                            Text("Welcome to the demo app!", size=24, weight=FontWeight.BOLD),
                            Text("This page is public and uses Material Design components."),
                            ElevatedButton(
                                "Go to Dashboard (protected)",
                                on_click=lambda e: router.push("/dashboard"),
                            ),
                        ],
                        spacing=20,
                        horizontal_alignment=CrossAxisAlignment.CENTER,
                    ),
                    alignment=alignment.center,
                    expand=True,
                )
            ],
        )

    # -----------------------------------------------------------------------
    # Login page (public)
    # -----------------------------------------------------------------------
    @router.route("/login", name="login")
    def login_view(params: Params) -> View:
        redirect = params.private.get("redirect", "/")
        username_field = TextField(label="Username", prefix_icon=Icons.PERSON)
        password_field = TextField(label="Password", password=True, prefix_icon=Icons.LOCK)
        error_msg = Text("", color=Colors.RED_400, visible=False)

        def do_login(e):
            # Very simple mock authentication – any non‑empty values succeed.
            if username_field.value and password_field.value:
                session.authenticated = True
                session.user = username_field.value
                router.replace(redirect)
            else:
                error_msg.value = "Please provide both username and password."
                error_msg.visible = True
                page.update()

        return View(
            route="/login",
            appbar=AppBar(title=Text("Login"), bgcolor=Colors.BLUE_600),
            controls=[
                Container(
                    content=Column(
                        controls=[
                            Text("Enter any credentials to simulate login."),
                            username_field,
                            password_field,
                            error_msg,
                            Row(
                                controls=[
                                    ElevatedButton("Login", on_click=do_login),
                                    TextButton("Back", on_click=lambda e: router.back()),
                                ],
                                spacing=10,
                            ),
                        ],
                        spacing=15,
                        horizontal_alignment=CrossAxisAlignment.CENTER,
                    ),
                    alignment=alignment.center,
                    expand=True,
                )
            ],
        )

    # -----------------------------------------------------------------------
    # Logout route (protected – but we allow it to be called when logged in)
    # -----------------------------------------------------------------------
    @router.route("/logout", name="logout", protected=True)
    def logout_view(params: Params) -> View:
        session.authenticated = False
        session.user = None
        router.replace("/")
        return View(route="/logout", controls=[Text("Logging out…")])

    # -----------------------------------------------------------------------
    # Protected Dashboard page
    # -----------------------------------------------------------------------
    @router.route("/dashboard", name="dashboard", protected=True)
    def dashboard_view(params: Params) -> View:
        return View(
            route="/dashboard",
            appbar=AppBar(
                title=Text(f"Dashboard – {session.user}"),
                leading=IconButton(icon=Icons.ARROW_BACK, on_click=lambda e: router.back()),
                bgcolor=Colors.GREEN_600,
            ),
            controls=[
                Container(
                    content=Column(
                        controls=[
                            Text("Protected content visible only to authenticated users.", size=20),
                            Card(
                                content=Container(
                                    content=Column(
                                        controls=[
                                            Text("📊 Analytics placeholder"),
                                            Text("🛠️ Settings placeholder"),
                                        ],
                                        spacing=10,
                                    ),
                                    padding=padding.all(15),
                                ),
                                elevation=4,
                            ),
                        ],
                        spacing=25,
                        horizontal_alignment=CrossAxisAlignment.CENTER,
                    ),
                    alignment=alignment.center,
                    expand=True,
                )
            ],
        )

    # Start the router – the initial route defaults to "/"
    if not router.stack:
        router.push("/")

# Run the app when executed directly
if __name__ == "__main__":
    import flet
    flet.app(target=main)
