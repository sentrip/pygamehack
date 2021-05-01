import copy
from typing import Any, List, Optional, TypeVar, Tuple, Union

from pygamehack.c import Address, buf
from ..struct_meta import StructMeta, StructType
from ..variable import IBufferContainerVariable, IConstVariable


T = TypeVar('T')


class Array(buf, IBufferContainerVariable):
    """
    Array Variable that implements the IContainerVariable Interface
    """
    __slots__ = ('__value_type', '__values', '__read', '__write')

    @property
    def value_type(self) -> StructType:
        return copy.copy(self.__value_type)

    def get(self) -> 'Array':
        return self

    def read(self, n: int = 0, starting_at: int = 0) -> 'Array':
        super().read(starting_at * self.__value_type.size, n * self.__value_type.size)
        return self

    def write(self, values: List[T], starting_at: int = 0):
        if self.__values is None:
            self._write_buffer(values, starting_at)
        else:
            self._write_values(values, starting_at)

    def flush(self, n: int = 0, starting_at: int = 0):
        super().flush(n * self.__value_type.size, starting_at * self.__value_type.size)

    def reset(self):
        if self.__values is not None:
            self.__values = [_ArrayLazyElement() for _ in range(len(self))]
        super().get().clear()

    @classmethod
    def __class_getitem__(cls, item: Tuple[Any, int]):
        if not isinstance(item, tuple) or StructType.is_compound_type_tuple(item):
            raise RuntimeError('Forgot to provide size in array definition')
        return StructType(item[0], StructType.LAZY_SIZE, item[1], container_type=cls)

    def __init__(self, address: Optional[Address], size: int, **kwargs):
        assert 'type' in kwargs, 'Must provide a value type when initializing an Array'

        self.__value_type = kwargs['type']

        if StructMeta.check_buffer_view_kwargs(address, kwargs):
            super().__init__(kwargs['parent_buffer'], kwargs['offset_in_parent'], size * self.__value_type.size)  # noqa
        else:
            super().__init__(address, size * self.__value_type.size)

        if StructType.is_basic_type(self.value_type):
            self.__values: Optional[List[Any]] = None
            type_name = self.value_type.__name__
            type_size = self.__value_type.size
            read_method = getattr(super().get(), 'read_' + type_name)
            write_method = getattr(super().get(), 'write_' + type_name)
            self.__read = lambda i: read_method(i * type_size)
            self.__write = lambda i, v: write_method(i * type_size, v)
        else:
            self.__values = [_ArrayLazyElement() for _ in range(size)]
            self.__read = None
            self.__write = None

    def __getitem__(self, i: Union[int, slice]) -> T:
        if self.__values is None:
            return self._getitem_buffer(i)
        else:
            return self._getitem_values(i)

    def __setitem__(self, i: int, value: T):
        if self.__values is None:
            self._setitem_buffer(i, value)
        else:
            self._setitem_values(i, value)

    def __iter__(self):
        if self.__values is not None:
            return self.__values.__iter__()
        else:
            return self._iter_buffer()

    def __len__(self):
        return super().get().size / self.__value_type.size

    def __hash__(self):
        return hash(tuple(v for v in self))

    def __eq__(self, other):
        if isinstance(other, Array):
            return object.__eq__(self, other)
        else:
            return isinstance(other, list) \
                   and len(other) == len(self) \
                   and all(v == other[i] for i, v in enumerate(self))

    def _check_bounds(self, i):
        assert i < super().get().size, f"Array index {i} out of bounds ({super().get().size})"

    def _create_element(self, i):
        return self.__value_type(None, buffer=True, parent_buffer=self, offset_in_parent=i * self.__value_type.size)

    def _exists(self, i):
        return not isinstance(self.__values[i], _ArrayLazyElement)

    def _iter_buffer(self, sl: slice = slice(0, -1)):
        start, stop, step = sl.indices(len(self))
        for idx in range(start, stop, step):
            yield self.__read(idx)

    def _getitem_buffer(self, i):
        if isinstance(i, slice):
            return self._iter_buffer(i)
        else:
            return self.__read(i)

    def _setitem_buffer(self, i, value):
        self.__write(i, value)

    def _getitem_values(self, i):
        if isinstance(i, slice):
            return self.__values[i]
        else:
            self._check_bounds(i)

            if not self._exists(i):
                self.__values[i] = self._create_element(i)

            if StructType.is_buffer_subclass(self.__value_type)\
                    or (isinstance(self.__value_type, StructType) and self.__value_type.is_container):
                return self.__values[i].get()
            else:
                return self.__values[i].read()

    def _setitem_values(self, i, value):
        self._check_bounds(i)

        if i >= len(self.__values):
            self.__values.extend(_ArrayLazyElement() for _ in range(i - len(self.__values) + 1))

        if not self._exists(i):
            self.__values[i] = self._create_element(i)

        self.__values[i].write(value)

    def _write_buffer(self, values, starting_at):
        for i, v in enumerate(values):
            self.__write(starting_at + i, v)

    def _write_values(self, values, starting_at):
        for i in range(len(values), starting_at + len(values)):
            self.__values.append(self._create_element(i))

        for i, v in enumerate(values):
            self.__values[starting_at + i].write(v)


class CArray(IConstVariable, Array):
    """
    Const version of Array Variable
    """
    __slots__ = ()


class _ArrayLazyElement(object):
    __slots__ = ()

    def get(self):
        raise RuntimeError('Attempt to access _ArrayLazyElement')

    def read(self):
        raise RuntimeError('Attempt to access _ArrayLazyElement')

    def write(self, v):
        raise RuntimeError('Attempt to access _ArrayLazyElement')
