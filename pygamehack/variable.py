from abc import ABC, abstractmethod
from typing import Optional

from pygamehack.c import Address, buf
from .struct import Struct


__all__ = [
    'IVariable', 'IConstVariable', 'IContainerVariable', 'IListVariable', 'IDictVariable',
    'IBufferVariable', 'IBufferContainerVariable',
    'Variable', 'ConstVariable', 'ContainerVariable', 'ListVariable', 'DictVariable'
]


#region Interfaces

class IVariable(object):
    """
    Abstract interface to be extended to implement your own custom variable types
    """

    def __init__(self, address: Optional[Address], **kwargs):
        raise NotImplementedError

    def get(self) -> 'IVariable':
        return self

    @abstractmethod
    def read(self) -> 'IVariable':
        raise NotImplementedError

    @abstractmethod
    def write(self, value):
        raise NotImplementedError

    @abstractmethod
    def reset(self):
        raise NotImplementedError


class IConstVariable(object):
    """
    Mixin for preventing writes to constant variables (like constant strings - const char*)

    Usage:
        class MyFancyVariable(Variable):
            ...

        class CMyFancyVariable(ConstVariable, MyFancyVariable):
            pass
    """
    def write(self, value):
        raise RuntimeError('Cannot write to a constant variable')

    def flush(self):
        raise RuntimeError('Cannot write to a constant variable')

    def reset(self):
        raise RuntimeError('Cannot write to a constant variable')

    def __setitem__(self, key, value):
        raise RuntimeError('Cannot write to a constant variable')


class IContainerVariable(IVariable):
    """
    Abstract interface to be extended to implement your own custom container-like variables
    """
    def __init__(self, element_type: type, address: Optional[Address], **kwargs):  # noqa
        raise NotImplementedError

    def get(self) -> 'IContainerVariable':
        return self

    @abstractmethod
    def read(self) -> 'IContainerVariable':
        raise NotImplementedError

    @abstractmethod
    def flush(self):
        raise NotImplementedError

    @abstractmethod
    def __getitem__(self, key):
        raise NotImplementedError

    @abstractmethod
    def __setitem__(self, key, value):
        raise NotImplementedError

    @abstractmethod
    def __iter__(self):
        raise NotImplementedError

    @abstractmethod
    def __len__(self):
        raise NotImplementedError


class IListVariable(IContainerVariable):
    """
    Abstract interface to be extended to implement your own custom list-like variable types
    """
    def write(self, values: list):
        assert len(values) <= len(self)
        for i, v in enumerate(values):
            self[i] = v


class IDictVariable(IContainerVariable):
    """
    Abstract interface to be extended to implement your own custom dict-like variables
    """
    def write(self, values: dict):
        for k, v in values.items():
            self[k] = v


class IBufferVariable(object):
    """
    Abstract interface to be extended to implement your own custom buffer-based variables
    """
    __slots__ = ()

    def __init__(self, address: Optional[Address], size: int, **kwargs):
        super().__init__(address, size)

    def get(self) -> buf:
        return self

    def read(self) -> buf:
        return buf.read(self)

    def write(self, value):
        buf.write(self, value)

    def flush(self):
        buf.flush(self)

    def reset(self):
        buf.get(self).clear()

    def __init_subclass__(cls, **kwargs):
        def check_bases(c):
            if buf in c.__bases__:
                return True
            for cl in c.__bases__:
                if check_bases(cl):
                    return True
            return False

        if cls.__name__ != 'IBufferContainerVariable':
            if not check_bases(cls):
                raise RuntimeError("A variable class that implements 'IBufferVariable' must inherit from 'buf'")


class IBufferContainerVariable(IBufferVariable):
    """
    Abstract interface to be extended to implement your own custom buffer-based container-like variables
    """
    __slots__ = ()

    @abstractmethod
    def __getitem__(self, key):
        raise NotImplementedError

    @abstractmethod
    def __setitem__(self, key, value):
        raise NotImplementedError

    @abstractmethod
    def __iter__(self):
        raise NotImplementedError

    @abstractmethod
    def __len__(self):
        raise NotImplementedError


#endregion


#region Variables

class Variable(Struct, IVariable, ABC, custom=True, define=False):
    """
    Abstract interface to be extended to implement your own struct-based custom variable types
    """
    pass


class ConstVariable(Struct, IVariable, ABC, custom=True, define=False):
    """
    Mixin for preventing writes to struct-based constant variables (like constant strings - const char*)

    Usage:
        class MyFancyVariable(Variable):
            ...

        class CMyFancyVariable(ConstVariable, MyFancyVariable):
            pass
    """
    pass


class ContainerVariable(Struct, IContainerVariable, ABC, custom=True, define=False):
    """
    Abstract interface to be extended to implement your own struct-based custom container-like variables
    """
    pass


class ListVariable(Struct, IListVariable, ABC, custom=True, define=False):
    """
    Abstract interface to be extended to implement your own struct-based custom list-like variable types
    """
    pass


class DictVariable(Struct, IDictVariable, ABC, custom=True, define=False):
    """
    Abstract interface to be extended to implement your own struct-based custom dict-like variables
    """
    pass

#endregion
