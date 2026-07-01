# Flet Router

[![PyPI version](https://badge.fury.io/py/flet-router.svg)](https://pypi.org/project/flet-router/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

A powerful and flexible routing library for Flet applications, enabling seamless navigation between pages and views with support for deep linking, route parameters, authentication, and middleware.

## Overview

Flet Router simplifies navigation management in Flet applications by providing a declarative routing system. It handles page transitions, state management, and URL-based navigation, allowing developers to build multi-page applications with ease. Built with type safety, performance, and extensibility in mind.

## Features

- **Declarative Routing**: Define routes using a clean, intuitive API
- **Page Navigation**: Seamless transitions between different pages and views
- **Route Parameters**: Support for dynamic URL parameters with automatic type casting
- **Query Parameters**: Handle URL query strings
- **Private Parameters**: Securely pass sensitive data between routes using encryption
- **Deep Linking**: Navigate directly to specific routes with parameters
- **History Management**: Built-in back/forward navigation support with stack management
- **Authentication & Guards**: Protect routes with authentication checks and custom guards
- **Middleware Support**: Execute custom logic before route transitions
- **Named Routes**: Navigate using human-readable route names
- **Route Preloading**: Preload views for improved performance
- **View Caching**: Optional caching system for frequently accessed views
- **Session Management**: Built-in session handling for user state
- **Async Support**: Full support for asynchronous operations and data loading
- **Type Safety**: Full type hints for better IDE support and error detection
- **Lightweight**: Minimal dependencies and overhead
- **Extensible**: Plugin system with middleware and guards

## Installation

Install Flet Router using pip:

```bash
pip install flet-router
```

### Requirements

- Python 3.9+
- Flet 0.28.3+

### Async Support

Flet Router fully supports asynchronous operations in your route handlers and middleware. Use `page.run_task()` or `asyncio.run()` for async data loading:

```python
import httpx
import asyncio

@router.route("/products")
def products_view(params):
    products_list = ft.Column()
    
    async def load_products():
        async with httpx.AsyncClient() as client:
            response = await client.get("https://api.example.com/products")
            products = response.json()
            # Update UI with loaded data
            products_list.controls = [ft.Text(p["name"]) for p in products]
            params.page.update()
    
    # Start async task
    params.page.run_task(load_products)
    
    return ft.View(
        route="/products",
        controls=[
            ft.Text("Products", size=30),
            products_list,
        ]
    )
```

## Quick Start

### Basic Usage with Decorators

```python
import flet as ft
from flet_router import FletRouter

def main(page: ft.Page):
    router = FletRouter(page=page)
    
    @router.route("/")
    def home_view(params):
        return ft.View(
            route="/",
            controls=[
                ft.Text("Home Page", size=30),
                ft.ElevatedButton(
                    "Go to About", 
                    on_click=lambda e: router.push("/about")
                )
            ]
        )
    
    @router.route("/about")
    def about_view(params):
        return ft.View(
            route="/about",
            controls=[
                ft.Text("About Page", size=30),
                ft.ElevatedButton(
                    "Go Back", 
                    on_click=lambda e: router.back()
                )
            ]
        )
    
    router.push("/")
    
ft.app(target=main)
```

### Alternative: Using Route Class

```python
from flet_router import FletRouter, Route

def main(page: ft.Page):
    def home_view(params):
        return ft.View(route="/", controls=[ft.Text("Home Page")])
    
    def about_view(params):
        return ft.View(route="/about", controls=[ft.Text("About Page")])
    
    router = FletRouter(
        page=page,
        routes=[
            Route("/", home_view),
            Route("/about", about_view),
        ]
    )
    
    router.push("/")
    
ft.app(target=main)
```

### Route Parameters

```python
def user_view(params):
    user_id = params.path["id"]
    return ft.View(
        route="/user/:id",
        controls=[
            ft.Text(f"User Profile: {user_id}", size=30),
            ft.ElevatedButton("Back", on_click=lambda e: params.router.back())
        ]
    )

router = FletRouter(
    page=page,
    routes=[
        Route("/user/:id", user_view),
    ]
)

# Navigate with parameters
router.push("/user/123")
```

### Authentication & Protected Routes

```python
import flet as ft
from flet_router import FletRouter, Route, MiddlewareContext

# Session state
class Session:
    def __init__(self):
        self.authenticated = False
        self.user = None

session = Session()

# Authentication middleware
def auth_middleware(ctx: MiddlewareContext) -> bool:
    if ctx.route and ctx.route.protected and not session.authenticated:
        ctx.router.replace("/login", {"redirect": ctx.full_path})
        return False
    return True

# Custom guard for user profiles
def user_profile_guard(ctx: MiddlewareContext) -> bool:
    if not session.authenticated:
        return False
    # Users can only view their own profile
    user_id = ctx.params.path.get("id")
    return str(session.user_id) == str(user_id)

def login_view(params):
    username_field = ft.TextField(label="Username")
    password_field = ft.TextField(label="Password", password=True)
    
    def do_login(e):
        # Your authentication logic here
        session.authenticated = True
        session.user = username_field.value
        # Redirect to intended page or home
        redirect_to = params.private.get("redirect", "/")
        params.router.replace(redirect_to)
    
    return ft.View(
        route="/login",
        controls=[
            ft.Text("Login", size=30),
            username_field,
            password_field,
            ft.ElevatedButton("Login", on_click=do_login),
        ]
    )

def dashboard_view(params):
    return ft.View(
        route="/dashboard",
        controls=[
            ft.Text(f"Welcome, {session.user}!", size=30),
            ft.ElevatedButton("Logout", on_click=lambda e: logout_and_redirect(params.router)),
        ]
    )

def user_profile_view(params):
    user_id = params.path["id"]
    return ft.View(
        route=f"/user/{user_id}",
        controls=[
            ft.Text(f"Profile for user {user_id}", size=30),
        ]
    )

def logout_and_redirect(router):
    session.authenticated = False
    session.user = None
    router.replace("/")

router = FletRouter(
    page=page,
    routes=[
        Route("/login", login_view),
        Route("/dashboard", dashboard_view, protected=True),
        Route("/user/:id", user_profile_view, protected=True, guard=user_profile_guard),
    ],
    auth_checker=lambda: session.authenticated,
    not_auth_redirect_route="/login"
)

router.use(auth_middleware)
```

### Middleware

```python
def logging_middleware(ctx):
    print(f"Navigating to: {ctx.path}")
    return True  # Continue navigation

def auth_middleware(ctx):
    if ctx.route and ctx.route.protected and not ctx.router.checker():
        return False  # Block navigation
    return True

router = FletRouter(page=page, routes=routes)
router.use(logging_middleware)
router.use(auth_middleware)
```

### Named Routes

```python
router = FletRouter(
    page=page,
    routes=[
        Route("/user/:id", user_view, name="user_profile"),
    ]
)

# Navigate using name
router.push_named("user_profile", path_params={"id": "123"})
```

#### Decorators vs Route Class

You can define routes using either decorators or the `Route` class. Both approaches are equivalent:

**Using Decorators (Recommended):**
```python
@router.route("/user/:id", protected=True, name="user_profile")
def user_view(params):
    return ft.View(route=f"/user/{params.path['id']}", ...)
```

**Using Route Class:**
```python
def user_view(params):
    return ft.View(route=f"/user/{params.path['id']}", ...)

routes = [
    Route("/user/:id", user_view, protected=True, name="user_profile"),
]

router = FletRouter(page=page, routes=routes)
```

**When to use decorators:**
- When you have many routes in one file
- For cleaner, more readable code
- When routes are closely tied to their view functions
- For dynamic route registration

**When to use Route class:**
- When defining routes in configuration files
- When routes are defined separately from view functions
- For programmatic route generation
- When working with route metadata

#### Integration with Guards and Middleware

Decorated routes work seamlessly with the authentication and middleware system:

```python
def admin_guard(ctx: MiddlewareContext) -> bool:
    """Only allow admin users"""
    return session.user_role == "admin"

def logging_middleware(ctx: MiddlewareContext) -> bool:
    """Log all navigation"""
    print(f"Navigating to: {ctx.path}")
    return True

# Routes with guards
@router.route("/admin", protected=True, guard=admin_guard)
def admin_panel(params):
    return ft.View(route="/admin", controls=[ft.Text("Admin Panel")])

@router.route("/user/:id", protected=True, guard=user_owns_resource)
def user_profile(params):
    return ft.View(route=f"/user/{params.path['id']}", ...)

# Add global middleware
router.use(logging_middleware)
```

The `protected=True` parameter automatically applies authentication checks, while custom `guard` functions provide additional authorization logic.

#### Async Routes with Decorators

Decorators work perfectly with async view functions for data loading:

```python
import httpx

@router.route("/products", name="products")
def products_view(params):
    products_list = ft.Column(scroll="auto")
    loading = ft.Text("Loading products...")
    
    async def load_products():
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("https://api.example.com/products")
                products = response.json()
                
                products_list.controls = [
                    ft.Card(
                        content=ft.Container(
                            content=ft.Text(product["name"]),
                            padding=10
                        )
                    ) for product in products
                ]
                loading.visible = False
                params.page.update()
        except Exception as e:
            loading.value = f"Error: {e}"
            params.page.update()
    
    # Start async loading
    params.page.run_task(load_products)
    
    return ft.View(
        route="/products",
        controls=[
            ft.Text("Products", size=30, weight=ft.FontWeight.BOLD),
            loading,
            products_list,
        ]
    )
```

## API Reference

### FletRouter Class

The main router class that manages navigation and routing.

#### Constructor Parameters

- `page` (Page): The Flet page instance
- `routes` (List[Route]): List of route definitions
- `auth_checker` (Optional[AuthChecker]): Authentication checker function or boolean
- `not_found_view` (Optional[ViewFactory]): Custom 404 view
- `not_auth_view` (Optional[ViewFactory]): Custom 401 view
- `not_auth_redirect_route` (Optional[str]): Route to redirect on auth failure
- `initial_route` (Optional[str]): Initial route to navigate to
- `enable_view_cache` (bool): Enable view caching (default: False)

#### Methods

- `push(path, private_params)`: Navigate to a new route
- `replace(path, private_params)`: Replace current route
- `back(steps)`: Go back in navigation history
- `push_named(name, path_params, private_params)`: Navigate using route name
- `use(middleware)`: Add middleware
- `route(path, **options)`: Decorator for defining routes (alternative to Route class)

#### Decorator Usage

The `@router.route()` decorator provides a clean, Pythonic way to define routes. It's an alternative to creating `Route` objects manually.

```python
router = FletRouter(page=page)

# Basic route
@router.route("/home")
def home_view(params):
    return ft.View(route="/home", controls=[ft.Text("Home Page")])

# Route with parameters
@router.route("/user/:id")
def user_view(params):
    user_id = params.path["id"]
    return ft.View(route=f"/user/{user_id}", controls=[ft.Text(f"User {user_id}")])

# Protected route with authentication
@router.route("/dashboard", protected=True)
def dashboard_view(params):
    return ft.View(route="/dashboard", controls=[ft.Text("Dashboard")])

# Named route for easy navigation
@router.route("/profile", name="user_profile")
def profile_view(params):
    return ft.View(route="/profile", controls=[ft.Text("Profile")])

# Route with custom guard
@router.route("/admin", protected=True, guard=admin_guard)
def admin_view(params):
    return ft.View(route="/admin", controls=[ft.Text("Admin Panel")])

# Route with preloading for better performance
@router.route("/settings", preload=True)
def settings_view(params):
    return ft.View(route="/settings", controls=[ft.Text("Settings")])

# Combined options
@router.route("/user/:id/posts", 
              name="user_posts", 
              protected=True, 
              guard=user_owns_resource)
def user_posts_view(params):
    user_id = params.path["id"]
    return ft.View(route=f"/user/{user_id}/posts", 
                  controls=[ft.Text(f"Posts by user {user_id}")])
```

#### Decorator Parameters

- `path` (str): Route path pattern (required)
- `protected` (bool): Requires authentication (default: False)
- `guard` (Callable): Custom guard function for additional checks
- `preload` (bool): Preload view on router initialization (default: False)
- `name` (str): Named route identifier for `push_named()` navigation

#### Navigation with Named Routes

```python
# Navigate using route names
router.push_named("user_profile")
router.push_named("user_posts", path_params={"id": "123"})
```

### Route Class

Defines a route configuration.

#### Parameters

- `path` (str): Route path pattern (e.g., "/user/:id")
- `view` (ViewFactory): View factory function
- `protected` (bool): Whether route requires authentication
- `guard` (Optional[Callable]): Custom guard function
- `preload` (bool): Whether to preload the view
- `name` (Optional[str]): Named route identifier

### Params Class

Container for route parameters.

#### Attributes

- `path` (Dict[str, Any]): URL path parameters
- `private` (Dict[str, Any]): Encrypted private parameters
- `router` (FletRouter): Router instance

## Examples

The `examples` directory contains sample applications demonstrating various features:

### Complete Demo Application

The `examples/example_app.py` provides a comprehensive demonstration of Flet Router's capabilities:

- **Authentication Integration**: Login/logout with DummyJSON API
- **Protected Routes**: User profiles and cart pages with authentication guards
- **Route Guards**: Custom logic to verify user permissions (e.g., users can only view their own profiles)
- **Middleware**: Global authentication middleware
- **Named Routes**: Navigation using human-readable route names
- **Async Data Loading**: Fetching data from APIs with httpx
- **Session Management**: Persistent user sessions across navigation
- **Error Handling**: Proper error states and user feedback
- **Real-world UI**: Cards, images, avatars, and responsive layouts

#### Running the Example

```bash
# Install additional dependencies for the example
pip install httpx

# Run the example application
python examples/example_app.py
```

**Demo Credentials:**
- Username: `kminchelle`
- Password: `0lelplR`

The example includes:
- Public pages (home, products)
- Protected pages (user profile, cart)
- Authentication flow with redirects
- API integration with real data
- Responsive design with dark theme

### Basic Examples

- Basic navigation between pages
- Route parameters and query strings
- Authentication flows with guards
- Middleware usage for logging and validation
- Named routes for cleaner navigation
- Dynamic page creation with data fetching

## Contributing

We welcome contributions! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Write tests for your changes
4. Ensure all tests pass
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Development Setup

```bash
git clone https://github.com/MasterA5/flet_router.git
cd flet_router
pip install -e .[dev]
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- 📖 [Documentation](https://github.com/MasterA5/flet_router/wiki)
- 🐛 [Issue Tracker](https://github.com/MasterA5/flet_router/issues)
- 💬 [Discussions](https://github.com/MasterA5/flet_router/discussions)

For questions or suggestions, please open an issue on GitHub.

## Changelog

### v0.1.0
- Initial release
- Basic routing functionality
- Authentication support with guards and middleware
- Route parameters and private parameters with encryption
- View caching and preloading
- Named routes for cleaner navigation
- Session management
- Async support for data loading
- Comprehensive example application with DummyJSON API integration
- Type safety with full type hints

## Acknowledgments

Built with [Flet](https://flet.dev) - A framework for building beautiful multi-platform apps with Python.
