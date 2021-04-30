
from ..variable import buf, IBufferContainerVariable, IConstVariable


class String(buf, IBufferContainerVariable):
    """
    String Variable that implements the IContainerVariable Interface
    """
    __slots__ = ()

    def get(self) -> str:
        return super().get().read_string()

    def read(self) -> str:
        super().read()
        super().get().resize(super().get().strlen())
        return super().get().read_string()

    def write(self, value: str):
        if len(value) > super().get().size:
            raise RuntimeError(f'str[{len(value)}] too large to fit in buffer[{super().get().size}]')
        super().get().write_string(0, value)

    def __getitem__(self, n):
        self._check_bounds(n)
        return chr(super().get().read_i8(n))

    def __setitem__(self, n, value):
        self._check_bounds(n)
        super().get().write_i8(n, ord(value))

    def __iter__(self):
        for i in range(super().get().strlen()):
            yield chr(super().get().read_i8(i))

    def __len__(self):
        return super().get().strlen()

    def __hash__(self):
        return hash(super().get().read_string())

    def __eq__(self, other):
        return isinstance(other, str) and len(other) == super().get().strlen() and super().get().read_string() == other

    def _check_bounds(self, i):
        assert i < super().get().size, f"String index {i} out of bounds ({super().get().size})"


class CString(IConstVariable, String):
    """

    """
    __slots__ = ()
