import sys
import os
from typing import Optional

# Append the path to include the FletRouter module from src directory
sys.path.append(os.path.join(os.getcwd(), "src", "flet_router", "router.py"))

from flet_routing import FletRouter, MiddlewareContext, Params, MiddlewareBase, BaseView
from flet import * # <- Bad practice, but for simplicity in this example. In production, import only what you need.
import httpx
import asyncio

class Session:
    def __init__(self):
        self.authenticated = False
        self.user = None
        self.token = None
        self.user_id = None

session = Session()

class AuthMiddleware(MiddlewareBase):
    """Redirect unauthenticated users to the login page for protected routes."""

    def __call__(self, ctx: MiddlewareContext) -> bool:
        # If the route is protected and the user is not authenticated, redirect.
        if ctx.route and ctx.route.protected and not session.authenticated:
            # Preserve the original destination so we can return after login.
            ctx.router.replace(
                "/unauthorized",
                {"redirect": ctx.full_path},
            )
            return False
        return True

class UserGuard(MiddlewareBase):
    def __call__(self, ctx: MiddlewareContext):
        if not session.authenticated:
            return False
        
        # Get user ID from route params and compare with session user_id
        user_id = ctx.params.path.get("id")
        if user_id and str(session.user_id) != str(user_id):
            # Is not the same user, deny access
            return False
        
        return True

def main(page: Page):
    page.title = "Auth Demo with DummyJSON"
    page.theme_mode = ThemeMode.DARK
    page.scroll = "adaptive"
    
    router = FletRouter(
        page,
        enable_view_cache=False,
        auth_checker=lambda: session.authenticated,
        not_auth_redirect_route="/unauthorized",
        enable_logger_middleware=True
    )
    
    router.use(AuthMiddleware())

    @router.route("/test", name="test")
    class TestBaseView(BaseView):
        def __init__(self, params: Params):
            super().__init__()
            self.controls = [
                Text(params)
            ]

        def did_mount(self):
            return super().did_mount()

    # --- Login Page ---
    @router.route("/login", name="login")
    def login_view(params: Params):
        redirect_url = params.private.get("redirect", "/")
        username_field = TextField(
            label="Username",
            hint_text="Enter username (e.g., 'kminchelle')",
            prefix_icon=Icons.PERSON,
        )
        password_field = TextField(
            label="Password",
            hint_text="Enter password (e.g., '0lelplR')",
            password=True,
            can_reveal_password=True,
            prefix_icon=Icons.LOCK,
        )
        error_text = Text("", color=Colors.RED_400, visible=False)
        login_button = ElevatedButton("Login", icon=Icons.LOGIN, disabled=False)
        
        async def do_login(e):
            # Disable button and hide error while processing
            login_button.disabled = True
            error_text.visible = False
            page.update()
            
            # Call DummyJSON API for authentication
            async with httpx.AsyncClient() as client:
                try:
                    response = await client.post(
                        "https://dummyjson.com/auth/login",
                        json={
                            "username": username_field.value,
                            "password": password_field.value,
                            "expiresInMins": 60,  # Expires in 1 hour
                        }
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        # Save Sessin Data
                        session.authenticated = True
                        session.token = data["accessToken"]
                        session.user_id = data["id"]
                        session.user = data["username"]
                        
                        # Save Session on page.session
                        page.session.set("token", session.token)
                        page.session.set("user_id", session.user_id)
                        
                        # Redirect
                        router.replace(redirect_url, private_params={"redirect": "/"})
                    else:
                        error_text.value = "Invalid credentials. Try: kminchelle / 0lelplR"
                        error_text.visible = True
                        login_button.disabled = False
                        page.update()
                        
                except Exception as ex:
                    error_text.value = f"Connection error: {str(ex)}"
                    error_text.visible = True
                    login_button.disabled = False
                    page.update()
        
        login_button.on_click = lambda e: asyncio.run(do_login(e))
        
        return View(
            route="/login",
            controls=[
                Container(
                    content=Column(
                        [
                            Icon(Icons.LOGIN, size=60, color=Colors.BLUE_400),
                            Text("Login to DummyJSON", size=30, weight=FontWeight.BOLD),
                            Text("Use demo credentials:", size=14, color=Colors.GREY_400),
                            Text("Username: kminchelle", size=12),
                            Text("Password: 0lelplR", size=12),
                            Divider(height=20, color=Colors.TRANSPARENT),
                            username_field,
                            password_field,
                            error_text,
                            login_button,
                            TextButton("Go back", on_click=lambda e: router.back()),
                        ],
                        spacing=20,
                        horizontal_alignment=CrossAxisAlignment.CENTER,
                    ),
                    alignment=alignment.center,
                    # expand=True,
                    padding=20,
                    border_radius=20,
                    width=400,
                    height=550,
                    bgcolor=Colors.BLUE_GREY_800,
                ),
            ],
            vertical_alignment=MainAxisAlignment.CENTER,
            horizontal_alignment=CrossAxisAlignment.CENTER,
        )

    # --- Logout Page ---
    @router.route("/logout")
    def logout_view(params: Params):
        # Clean Session
        session.authenticated = False
        session.token = None
        session.user = None
        session.user_id = None
        page.session.clear()
        router.replace("/")
        return View(controls=[Text("Logging out...")])

    # --- Home Page (public) ---
    @router.route("/", name="home")
    def home_view(params: Params):
        return View(
            route="/",
            appbar=AppBar(
                title=Text("DummyJSON Demo"),
                center_title=False,
                bgcolor=Colors.SURFACE,
                actions=[
                    Container(
                        content=Row([
                            Text(f"👤 {session.user}" if session.authenticated else "👤 Guest"),
                            IconButton(
                                icon=Icons.EXIT_TO_APP if session.authenticated else Icons.LOGIN,
                                on_click=lambda e: router.push(
                                    "/logout" if session.authenticated else "/login"
                                ),
                                tooltip="Logout" if session.authenticated else "Login",
                            ),
                        ], spacing=5),
                        padding=padding.only(right=10),
                    )
                ],
            ),
            controls=[
                Container(
                    content=Column(
                        controls=[
                            Text("Welcome to DummyJSON Integration", size=28, weight=FontWeight.BOLD),
                            Text("This demo shows authentication and protected routes", size=16, color=Colors.GREY_400),
                            Divider(),
                            
                            # Features Cards
                            Row([
                                Card(
                                    content=Container(
                                        content=Column(
                                            controls=[
                                                Button("Throw Error To Test Unauthorized", on_click=lambda e: router.push("/user/9999")),
                                                Button("Throw Error To Test Not Found", on_click=lambda e: router.push("/posts")),
                                                Button("Go To Test", on_click=lambda e: router.push("/test")),
                                            ]
                                        ),
                                        padding=padding.symmetric(10,10),
                                        width=250,
                                    ),
                                ),
                                Card(
                                    content=Container(
                                        content=Column([
                                            Icon(Icons.PERSON, size=40, color=Colors.BLUE_400),
                                            Text("User Profile", size=18, weight=FontWeight.BOLD),
                                            Text("View your protected profile data"),
                                            ElevatedButton(
                                                "View Profile",
                                                on_click=lambda e: router.push(f"/user/{session.user_id}" if session.user_id else "/login"),
                                                disabled=not session.authenticated,
                                            ),
                                        ], spacing=10, horizontal_alignment=CrossAxisAlignment.CENTER),
                                        padding=20,
                                        width=250,
                                    ),
                                ),
                                Card(
                                    content=Container(
                                        content=Column([
                                            Icon(Icons.LIST_ALT, size=40, color=Colors.GREEN_400),
                                            Text("Products", size=18, weight=FontWeight.BOLD),
                                            Text("View public product catalog"),
                                            ElevatedButton(
                                                "View Products",
                                                on_click=lambda e: router.push("/products"),
                                            ),
                                        ], spacing=10, horizontal_alignment=CrossAxisAlignment.CENTER),
                                        padding=20,
                                        width=250,
                                    ),
                                ),
                                Card(
                                    content=Container(
                                        content=Column([
                                            Icon(Icons.SHOPPING_CART, size=40, color=Colors.ORANGE_400),
                                            Text("Cart", size=18, weight=FontWeight.BOLD),
                                            Text("View your shopping cart"),
                                            ElevatedButton(
                                                "View Cart",
                                                on_click=lambda e: router.push("/cart"),
                                                disabled=not session.authenticated,
                                            ),
                                        ], spacing=10, horizontal_alignment=CrossAxisAlignment.CENTER),
                                        padding=20,
                                        width=250,
                                    ),
                                ),
                            ], alignment=MainAxisAlignment.CENTER, spacing=20, wrap=True, expand=True),
                            
                            Card(
                                content=Container(
                                    content=Column([
                                        Icon(Icons.LOCK, size=40),
                                        Text("Protected Content", size=16),
                                        Text("Login to access user-specific data"),
                                        ElevatedButton(
                                            "Login Now",
                                            icon=Icons.LOGIN,
                                            on_click=lambda e: router.push("/login"),
                                        ),
                                    ], spacing=10, horizontal_alignment=CrossAxisAlignment.CENTER),
                                    padding=20,
                                ),
                                color=Colors.SURFACE,
                                visible=not session.authenticated,
                            ),
                        ],
                        spacing=30,
                        horizontal_alignment=CrossAxisAlignment.CENTER,
                    ),
                    alignment=alignment.center,
                    expand=True,
                    padding=20,
                )
            ],
            scroll="adaptive",
        )

    # --- Product Catalog (public) ---
    @router.route("/products", name="products")
    def products_view(params: Params):
        products_list = Column(spacing=10, scroll="adaptive")
        loading_text = Text("Loading products...")
        error_text = Text("", color=Colors.RED_400, visible=False)
        
        async def load_products():
            async with httpx.AsyncClient() as client:
                try:
                    response = await client.get("https://dummyjson.com/products?limit=10")
                    if response.status_code == 200:
                        data = response.json()
                        products_list.controls.clear()
                        for product in data["products"]:
                            products_list.controls.append(
                                Card(
                                    content=Container(
                                        content=Row([
                                            Container(
                                                content=Image(
                                                    src=product["thumbnail"],
                                                    width=80,
                                                    height=80,
                                                    fit=ImageFit.COVER,
                                                ),
                                                border_radius=10,
                                            ),
                                            Column([
                                                Text(product["title"], weight=FontWeight.BOLD, size=16),
                                                Text(f"${product['price']}", color=Colors.GREEN_400),
                                                Text(product["description"][:80] + "...", size=12, color=Colors.GREY_400),
                                            ], spacing=5, expand=True),
                                        ], spacing=10),
                                        padding=10,
                                    ),
                                )
                            )
                        loading_text.visible = False
                        page.update()
                    else:
                        error_text.value = "Failed to load products"
                        error_text.visible = True
                        loading_text.visible = False
                        page.update()
                except Exception as ex:
                    error_text.value = f"Error: {str(ex)}"
                    error_text.visible = True
                    loading_text.visible = False
                    page.update()
        
        # Load products when the page asynchronously
        page.run_task(load_products)
        
        return View(
            route="/products",
            appbar=AppBar(
                title=Text("Products"),
                leading=IconButton(icon=Icons.ARROW_BACK, on_click=lambda e: router.back()),
            ),
            controls=[
                Container(
                    content=Column([
                        Text("Product Catalog", size=30, weight=FontWeight.BOLD),
                        loading_text,
                        error_text,
                        products_list,
                    ], spacing=20),
                    padding=20,
                    expand=True,
                )
            ],
            scroll="adaptive",
        )

    # --- User Profile (protected) ---
    @router.route("/user/:id", name="user", protected=True, guard=UserGuard())
    def user_view(params: Params):
        user_id = params.path["id"]
        redirect_url = params.private["redirect"]
        user_info = Column(spacing=15)
        loading_text = Text("Loading user data...")
        
        async def load_user_data():
            async with httpx.AsyncClient() as client:
                try:
                    # Obtener datos del usuario
                    response = await client.get(f"https://dummyjson.com/users/{user_id}")
                    if response.status_code == 200:
                        user = response.json()
                        
                        # También obtener los posts del usuario
                        posts_response = await client.get(f"https://dummyjson.com/users/{user_id}/posts")
                        posts = posts_response.json().get("posts", []) if posts_response.status_code == 200 else []
                        
                        user_info.controls.clear()
                        user_info.controls.extend([
                            Row([
                                CircleAvatar(
                                    content=Text(user.get("firstName", "U")[0]),
                                    bgcolor=Colors.BLUE_400,
                                    radius=40,
                                ),
                                Column([
                                    Text(f"{user.get('firstName', '')} {user.get('lastName', '')}", 
                                         size=24, weight=FontWeight.BOLD),
                                    Text(f"@{user.get('username', '')}", color=Colors.GREY_400),
                                    Text(f"📧 {user.get('email', '')}"),
                                    Text(f"📱 {user.get('phone', '')}"),
                                ], spacing=5),
                            ], spacing=20),
                            Divider(),
                            Container(
                                content=Column([
                                    Text("User Information", size=18, weight=FontWeight.BOLD),
                                    Text(f"Age: {user.get('age', 'N/A')}"),
                                    Text(f"Gender: {user.get('gender', 'N/A')}"),
                                    Text(f"Birth Date: {user.get('birthDate', 'N/A')}"),
                                    Text(f"Blood Group: {user.get('bloodGroup', 'N/A')}"),
                                ], spacing=8),
                                padding=10,
                                bgcolor=Colors.SURFACE,
                                border_radius=10,
                            ),
                            Container(
                                content=Column([
                                    Text("Address", size=18, weight=FontWeight.BOLD),
                                    Text(f"{user.get('address', {}).get('address', 'N/A')}"),
                                    Text(f"{user.get('address', {}).get('city', 'N/A')}, {user.get('address', {}).get('state', 'N/A')}"),
                                    Text(f"Postal Code: {user.get('address', {}).get('postalCode', 'N/A')}"),
                                    Text(f"Country: {user.get('address', {}).get('country', 'N/A')}"),
                                ], spacing=8),
                                padding=10,
                                bgcolor=Colors.SURFACE,
                                border_radius=10,
                            ),
                            Container(
                                content=Column([
                                    Text("Recent Posts", size=18, weight=FontWeight.BOLD),
                                    Column([Text(post.get('title', 'No title'), size=14) for post in posts[:3]], spacing=5),
                                ], spacing=8),
                                padding=10,
                                bgcolor=Colors.SURFACE,
                                border_radius=10,
                            ),
                        ])
                        loading_text.visible = False
                        page.update()
                    else:
                        loading_text.visible = False
                        user_info.controls.clear()
                        user_info.controls.append(Text("Failed to load user data", color=Colors.RED_400))
                        page.update()
                except Exception as ex:
                    loading_text.visible = False
                    user_info.controls.clear()
                    user_info.controls.append(Text(f"Error: {str(ex)}", color=Colors.RED_400))
                    page.update()
        
        page.run_task(load_user_data)
        
        return View(
            route=f"/user/{user_id}",
            appbar=AppBar(
                title=Text(f"User Profile"),
                leading=IconButton(icon=Icons.ARROW_BACK, on_click=lambda e: router.replace(redirect_url)),
                actions=[
                    IconButton(icon=Icons.LOGOUT, on_click=lambda e: router.push("/logout"), tooltip="Logout"),
                ],
            ),
            controls=[
                Container(
                    content=Column([
                        Text(f"Profile", size=28, weight=FontWeight.BOLD),
                        loading_text,
                        user_info,
                    ], spacing=20,scroll="adaptive"),
                    padding=20,
                    expand=True,
                )
            ],
        )

    # --- Show Cart (protected) ---
    @router.route("/cart", name="cart", protected=True)
    def cart_view(params: Params):
        cart_items = Column(spacing=10)
        loading_text = Text("Loading cart...")
        total_text = Text("", size=18, weight=FontWeight.BOLD)
        
        async def load_cart():
            async with httpx.AsyncClient() as client:
                try:
                    # DummyJSON require user ID (1-10)
                    cart_id = session.user_id if session.user_id and session.user_id <= 10 else 1
                    response = await client.get(f"https://dummyjson.com/carts/user/{cart_id}")
                    
                    if response.status_code == 200:
                        data = response.json()
                        carts = data.get("carts", [])
                        if carts:
                            cart = carts[0]
                            items = cart.get("products", [])
                            
                            cart_items.controls.clear()
                            total = 0
                            for item in items:
                                product_response = await client.get(f"https://dummyjson.com/products/{item['id']}")
                                product = product_response.json() if product_response.status_code == 200 else {}
                                
                                subtotal = item['price'] * item['quantity']
                                total += subtotal
                                
                                cart_items.controls.append(
                                    Card(
                                        content=Container(
                                            content=Row([
                                                Container(
                                                    content=Image(
                                                        src=product.get("thumbnail", ""),
                                                        width=60,
                                                        height=60,
                                                        fit=ImageFit.COVER,
                                                    ) if product.get("thumbnail") else Icon(Icons.SHOPPING_CART),
                                                    border_radius=5,
                                                ),
                                                Column([
                                                    Text(product.get("title", f"Product {item['id']}"), weight=FontWeight.BOLD),
                                                    Text(f"Quantity: {item['quantity']}"),
                                                    Text(f"Price: ${item['price']}"),
                                                    Text(f"Subtotal: ${subtotal}", color=Colors.GREEN_400),
                                                ], spacing=5, expand=True),
                                            ], spacing=10),
                                            padding=10,
                                        ),
                                    )
                                )
                            
                            total_text.value = f"Total: ${total:.2f}"
                            loading_text.visible = False
                        else:
                            loading_text.visible = False
                            cart_items.controls.append(Text("Cart is empty", color=Colors.GREY_400))
                    else:
                        loading_text.visible = False
                        cart_items.controls.append(Text("Failed to load cart", color=Colors.RED_400))
                    page.update()
                except Exception as ex:
                    loading_text.visible = False
                    cart_items.controls.append(Text(f"Error: {str(ex)}", color=Colors.RED_400))
                    page.update()
        
        page.run_task(load_cart)
        
        return View(
            route="/cart",
            appbar=AppBar(
                title=Text("My Cart"),
                leading=IconButton(icon=Icons.ARROW_BACK, on_click=lambda e: router.back()),
            ),
            controls=[
                Container(
                    content=Column([
                        Text("Shopping Cart", size=28, weight=FontWeight.BOLD),
                        loading_text,
                        cart_items,
                        Divider(),
                        total_text,
                        ElevatedButton("Continue Shopping", on_click=lambda e: router.push("/")),
                    ], spacing=20, scroll="adaptive",),
                    padding=20,
                    expand=True,
                )
            ],
        )

    # --- Not Authorized View ---
    class UnauthorizedView(View):
        def __init__(self):
            super().__init__()
            self.route = "/unauthorized"
            self.controls = [
                Container(
                    content=Column(
                        [
                            Icon(Icons.LOCK, size=80, color=Colors.RED_400),
                            Text("Access Denied", size=30, weight=FontWeight.BOLD),
                            Text("You don't have permission to view this page."),
                            ElevatedButton("Go to Login", on_click=lambda e: router.replace("/login")),
                            ElevatedButton("Go to Home", on_click=lambda e: router.replace("/")),
                        ],
                        spacing=20,
                        horizontal_alignment=CrossAxisAlignment.CENTER,
                    ),
                    alignment=alignment.center,
                    expand=True,
                )
            ]
            self.appbar = AppBar(title=Text("Unauthorized"))

    @router.route("/unauthorized", name="unauthorized")
    def unauthorized_view(params: Params):
        return UnauthorizedView()

    # Goto home on app start
    router.push("/")

app(main)