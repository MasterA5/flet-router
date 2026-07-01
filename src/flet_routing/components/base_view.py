from __future__ import annotations

from typing import Optional, Sequence

from flet import (
    AppBar,
    BottomAppBar,
    ColorValue,
    Colors,
    Control,
    ControlEvent,
    CupertinoAppBar,
    CupertinoNavigationBar,
    FloatingActionButton,
    FloatingActionButtonLocation,
    Icon,
    IconButton,
    Icons,
    MainAxisAlignment,
    NavigationBar,
    NavigationDrawer,
    OffsetValue,
    OptionalControlEventCallable,
    OptionalEventCallable,
    OptionalNumber,
    OnScrollEvent,
    PaddingValue,
    ScrollMode,
    Text,
    View,
)
from flet import *


class BaseView(View):
    def __init__(
        self,
        router: Optional['FletRouter'] = None,
        route: str | None = None,
        controls: Sequence[Control] | None = None,
        appbar: AppBar | CupertinoAppBar | None = None,
        bottom_appbar: BottomAppBar | None = None,
        floating_action_button: FloatingActionButton | None = None,
        floating_action_button_location: OffsetValue | FloatingActionButtonLocation = None,
        navigation_bar: NavigationBar | CupertinoNavigationBar | None = None,
        drawer: NavigationDrawer | None = None,
        end_drawer: NavigationDrawer | None = None,
        vertical_alignment: MainAxisAlignment | None = None,
        horizontal_alignment: CrossAxisAlignment | None = None,
        spacing: OptionalNumber = None,
        padding: PaddingValue | None = None,
        bgcolor: ColorValue | None = None,
        decoration: BoxDecoration | None = None,
        foreground_decoration: BoxDecoration | None = None,
        can_pop: bool | None = None,
        on_confirm_pop: OptionalControlEventCallable = None,
        scroll: ScrollMode | None = None,
        auto_scroll: bool | None = None,
        fullscreen_dialog: bool | None = None,
        on_scroll_interval: OptionalNumber = None,
        on_scroll: OptionalEventCallable[OnScrollEvent] = None,
        adaptive: bool | None = None
    ):
        super().__init__(
            route=route,
            controls=controls,
            appbar=appbar,
            bottom_appbar=bottom_appbar,
            floating_action_button=floating_action_button,
            floating_action_button_location=floating_action_button_location,
            navigation_bar=navigation_bar,
            drawer=drawer,
            end_drawer=end_drawer,
            vertical_alignment=vertical_alignment,
            horizontal_alignment=horizontal_alignment,
            spacing=spacing,
            padding=padding,
            bgcolor=bgcolor,
            decoration=decoration,
            foreground_decoration=foreground_decoration,
            can_pop=can_pop,
            on_confirm_pop=on_confirm_pop,
            scroll=scroll,
            auto_scroll=auto_scroll,
            fullscreen_dialog=fullscreen_dialog,
            on_scroll_interval=on_scroll_interval,
            on_scroll=on_scroll,
            adaptive=adaptive,
        )
        self.__router = router
        
    def build(self):
        if not self.appbar:
            self.appbar = AppBar(
                leading=IconButton(
                    icon=Icons.ARROW_BACK,
                    on_click=self.pop,
                    visible=bool(self.page.views)
                ),
                title=Text(self.route.replace("/", "") or "App")
            )
        return super().build()

    @property
    def router(self) -> 'FletRouter':
        return self.__router 
    
    @router.setter
    def router(self, new: 'FletRouter') -> None:
        self.__router = new
