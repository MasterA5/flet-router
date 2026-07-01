from flet import (
    Column,
    Colors,
    Container,
    CrossAxisAlignment,
    FontWeight,
    Icon,
    Icons,
    MainAxisAlignment,
    Text,
    View,
    alignment,
)

def build_not_auth_view() -> View:
    return View(
        route="/401",
        controls=[
            Container(
                content=Column(
                    controls=[
                        Icon(Icons.LOCK, size=80, color=Colors.RED_400),
                        Text("401 - Unauthorized", size=30, weight=FontWeight.BOLD),
                        Text("You don't have permission to access this page.", size=16),
                    ],
                    horizontal_alignment=CrossAxisAlignment.CENTER,
                    spacing=20,
                ),
                alignment=alignment.center,
                expand=True,
            ),
        ],
        horizontal_alignment=CrossAxisAlignment.CENTER,
        vertical_alignment=MainAxisAlignment.CENTER,
    )
