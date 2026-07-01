from flet import (
    View,
    Container,
    Column,
    Icon,
    Icons,
    Colors,
    Text,
    CrossAxisAlignment,
    FontWeight,
    MainAxisAlignment,
    alignment
)

def build_not_found_view() -> View:
    return View(
        route="/404",
        controls=[
            Container(
                content=Column(
                    controls=[
                        Icon(Icons.ERROR_OUTLINE, size=80, color=Colors.RED_400),
                        Text("404 - Page Not Found", size=30, weight=FontWeight.BOLD),
                        Text("The page you're looking for doesn't exist.", size=16),
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