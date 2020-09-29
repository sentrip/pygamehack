from typing import Any

import pygamehack as gh
from pygamehack_utils import HackStruct, ArrayVariable, ConstVariable, Ptr
from pygamehack_utils.hackstruct import HackStructArgs
from pygamehack_utils.debug_view import *

__all__ = ['RawString', 'CRawString', 'c_str', 'const_c_str']


HackStruct.set_architecture(32 | 64)


class RawString(ArrayVariable, DebuggableVariable):

    @classmethod
    def get_type_size(cls):
        return 1  # strings have a dynamic size

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_buffer_type = True
        self.is_pod_type = True

        args = HackStructArgs(self.__class__, args)
        self.address = args.address
        self.size = args.size or 32

        if args.src_buffer:
            self.buffer = gh.buffer(args.src_buffer, args.offset, self.size)
        else:
            self.buffer = gh.buffer(self.address, self.size)

    def read(self) -> str:
        self.read_contents()
        return self.buffer.get().read_string()[:self.size]

    def write(self, value: str):
        self.size = len(value)
        self.buffer.get()\
            .resize(self.size)\
            .write_string(value)
        self.buffer.write_contents()

    def read_contents(self):
        self.buffer.read()
        self._update_size_from_current_buffer()

    def write_contents(self):
        self.buffer.write_contents()

    def __getitem__(self, key):
        self._check_bounds(key)
        return chr(self.buffer.get().read_int8(key))

    def __setitem__(self, key, value):
        self._check_bounds(key)
        self.buffer.get().write_int8(key, ord(value))
        self.buffer.write_contents()

    def __iter__(self):
        for i in range(self.size):
            yield self[i]

    def __len__(self):
        return self.size

    def _check_bounds(self, i):
        assert i < self.size, f"String index {i} out of bounds ({self.size})"

    def _update_size_from_current_buffer(self):
        if not self.address:  # views cannot be updated from inside the view
            return
        begin = self.address.address
        end = self.buffer.get().hack.scan_char(begin, 0)  # poor-man's strlen
        self.size = (0 if not end else end - begin) or self.size

    # Debug

    def debug_config(self) -> DebugConfig:
        return DebugConfig()

    def debug_address(self) -> int:
        return super().debug_address()

    def debug_address_to_watch(self) -> int:
        return super().debug_address_to_watch()

    def debug_string(self, show_as_hex: bool) -> str:
        return self.read()

    def debug_view(self) -> DebugViewFactory:
        return DebugViewFactoryRawString()


class CRawString(ConstVariable, RawString):
    pass


# Aliases for pointers
c_str = Ptr[RawString]
const_c_str = Ptr[CRawString]


HackStruct.set_architecture(HackStruct.default_architecture)


import tkinter as tk


class DebugViewFactoryRawString(DebugViewFactory):
    def create_view(self, master: tk.Frame) -> DebugView:
        label = tk.Label(master, text='Text')
        label.pack()
        return label

    def get_value(self, view: DebugView) -> Any:
        return 0
