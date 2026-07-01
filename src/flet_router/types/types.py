from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Union
from flet import View, Page

@dataclass
class Params:
    path: Dict[str, Any]
    private: Dict[str, Any]
    router: 'FletRouter'


ViewFactory = Callable[['Params'], 'View']
AuthChecker = Union[bool, Callable[[], bool]]


@dataclass
class MiddlewareContext:
    path: str
    full_path: str
    params: 'Params'
    route: Optional["Route"]
    page: 'Page'
    router: "FletRouter"
    private: Dict[str, Any] = field(default_factory=dict)


Middleware = Union[Callable[['MiddlewareContext'], bool], 'MiddlewareBase']


@dataclass
class Route:
    path: str
    view: Union['View', 'ViewFactory']
    protected: bool = False
    guard: Optional[Callable[['MiddlewareContext'], bool]] = None
    preload: bool = False
    name: Optional[str] = None


@dataclass
class RouteEntry:
    path: str
    token: Optional[str] = None
    view: Optional['View'] = None
    params: Optional[Dict[str, Any]] = None
