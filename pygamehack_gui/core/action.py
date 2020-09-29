from abc import ABC, abstractmethod
from typing import Callable, Optional
from tkinter import BaseWidget


class Action(ABC):

    on_complete: Optional[Callable]

    def __init__(self):
        self.on_complete = None
        self.did_begin = False

    @abstractmethod
    def is_complete(self) -> bool:
        raise NotImplementedError

    def on_begin(self):
        pass

    def on_end(self):
        pass

    def update(self, dt: float):
        pass


class ConditionAction(Action):

    condition: Callable[[], bool]

    def __init__(self, condition: Callable[[], bool]):
        super().__init__()
        self.condition = condition

    def is_complete(self) -> bool:
        return self.condition()


class DurationAction(Action):

    duration: float
    elapsed: float

    def __init__(self, duration: float = 0.0):
        super().__init__()
        self.duration = duration
        self.elapsed = 0

    def is_complete(self) -> bool:
        return self.elapsed >= self.duration

    def update(self, dt: float):
        self.elapsed += dt


class Function(DurationAction):

    begin: Optional[Callable]
    end: Optional[Callable]

    def __init__(self, begin: Optional[Callable] = None, end: Optional[Callable] = None, *, duration: float = 0.0):
        super().__init__(duration)
        self.begin = begin
        self.end = end

    def on_begin(self):
        if self.begin:
            self.begin()

    def on_end(self):
        if self.end:
            self.end()


def _run_action(self, action: Action):
    def update():
        if not action.did_begin:
            action.did_begin = True
            action.on_begin()

        action.update(10 / 1000)

        if action.is_complete():
            action.on_end()
            if action.on_complete:
                action.on_complete()
        else:
            self.after(10, update)

    update()


BaseWidget.run = _run_action
