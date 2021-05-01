from typing import Union

from pygamehack.c import buf
from ..variable import IBufferContainerVariable, IConstVariable


class String(buf, IBufferContainerVariable):
    """
    String Variable that implements the IContainerVariable Interface
    """
    __slots__ = ()

    def get(self) -> str:
        size = super().get().strlen()
        return super().get().read_string(0, size) if size else ''

    def read(self) -> str: # noqa
        super().read()
        size = super().get().strlen()
        super().get().resize(size)
        return super().get().read_string(0, size) if size else ''

    def write(self, value: str): # noqa
        if len(value) > super().get().size:
            raise RuntimeError(f'str[{len(value)}] too large to fit in buffer[{super().get().size}]')
        super().get().write_string(0, value)

    def __getitem__(self, i: Union[int, slice]):
        if isinstance(i, slice):
            start, stop, step = i.indices(super().get().size)
            assert step == 1, 'Do not support step>1 for string slicing'
            if step == 1:
                return super().get().read_string(start, stop)
            else:
                return super().get().read_string(start, stop)[0:-1:step]
        else:
            self._check_bounds(i)
            return chr(super().get().read_i8(i))

    def __setitem__(self, i: int, value: str):
        assert len(value) == 1
        self._check_bounds(i)
        super().get().write_i8(i, ord(value))

    def __iter__(self):
        for i in range(super().get().strlen()):
            yield chr(super().get().read_i8(i))

    def __len__(self):
        return super().get().strlen()

    def __hash__(self):
        return hash(super().get().read_string())

    def __eq__(self, other):
        if isinstance(other, String):
            return object.__eq__(self, other)
        else:
            return isinstance(other, str) and len(other) == super().get().strlen() and super().get().read_string() == other

    def _check_bounds(self, i):
        assert i < super().get().size, f"String index {i} out of bounds ({super().get().size})"


class CString(IConstVariable, String):
    """
    Const version of String Variable
    """
    __slots__ = ()
