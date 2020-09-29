import tkinter as tk
import tkinter.ttk as ttk
from abc import ABC, abstractmethod
from typing import Any, Optional


class PopupDelegate(ABC):

    @abstractmethod
    def handle_event(self, event: str, data: Optional[Any] = None):
        raise NotImplementedError


class Popup(tk.Tk):
    def __init__(self, delegate: PopupDelegate, title: str):
        super().__init__()
        self.delegate = delegate
        self.running = True
        self.wm_title(title)

        self.ok_button = ttk.Button(self, text="OK", command=self._update_and_kill).pack(side=tk.BOTTOM)

        self.bind('<Escape>', lambda *a: self._kill())
        self.bind('<Return>', lambda *a: self._update_and_kill())
        self.protocol('WM_DELETE_WINDOW', self._kill)

    def get_data(self) -> Optional[Any]:
        return None

    def popup(self):
        self._force_focus()
        self.mainloop()

    def _kill(self):
        self.running = False
        self.destroy()

    def _update_and_kill(self):
        self.delegate.handle_event('update', self.get_data())
        self._kill()

    def _force_focus(self):
        if self.running:
            if self.focus_get() is None:
                self.focus_force()
            #self.delegate.after(10, self._force_focus)
