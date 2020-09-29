from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, TypeVar, Generic

try:
    import tkinter as tk
except ImportError:
    # TODO: @UserInputError handle tkinter not installed
    class tk:
        Frame = None
        Widget = None


DebugView = TypeVar('DebugView', bound=tk.Widget)


@dataclass
class DebugConfig:
    can_modify: bool = False
    show_value: bool = False
    show_value_as_hex: bool = False
    show_updates: bool = False


class DebugViewFactory(ABC, Generic[DebugView]):

    @abstractmethod
    def create_view(self, master: tk.Frame) -> DebugView:
        raise NotImplementedError

    @abstractmethod
    def get_value(self, view: DebugView) -> Any:
        raise NotImplementedError

    def validate_value(self, view: DebugView) -> bool:
        return True


class DebuggableVariable(ABC):

    @abstractmethod
    def debug_config(self) -> DebugConfig:
        return DebugConfig()

    @abstractmethod
    def debug_address(self) -> int:
        return getattr(self, 'address', None).address

    @abstractmethod
    def debug_address_to_watch(self) -> int:
        return getattr(self, 'address', None).address

    @abstractmethod
    def debug_string(self, show_as_hex: bool) -> str:
        return repr(getattr(self, 'read')())

    def debug_view(self) -> DebugViewFactory:
        pass
