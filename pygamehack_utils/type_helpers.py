from abc import abstractmethod
from typing import Any, Optional, Dict
import sys


__all__ = [
    'is_basic_type', 'is_hackstruct_type', 'is_ptr_type',
    'wrap_type', 'unwrap_type',
    'TypeHintContainer', 'Ptr',
    'PtrType', 'ContainerType', 'RegularType',
    'PtrWrapper', 'ContainerWrapper'
]


# region Type functions

def is_basic_type(t: Any):
    return type(unwrap_type(t)).__name__ == 'pybind11_type'


def is_hackstruct_type(t: Any):
    return hasattr(unwrap_type(t), '_info')


def is_container_type(t: Any):
    return isinstance(t, ContainerWrapper)


def is_ptr_type(t: Any):
    return isinstance(t, PtrWrapper)


def unwrap_type(t: Any, definitions: Optional[Dict] = None):
    while hasattr(t, 'type'):
        t = t.type
    # TODO: Clean up usage of strings to when defining types
    if isinstance(t, str):
        t_str = t
        t = (definitions or {}).get(t, None)
        if t is None:
            raise RuntimeError(f"'{t_str}' cannot be found in {definitions}")
        else:
            t = t.cls
    return t


def wrap_type(t: Any):
    if is_ptr_type(t):
        return PtrType(t.type)
    elif is_container_type(t):
        return ContainerType(t.container, t.value_type, t.size)
    elif isinstance(t, BaseType):
        return t
    else:
        return RegularType(t)


# endregion


# region TypeHintContainer & Ptr

class TypeHintContainer(type):
    types = {}
    buffer = None  # so ContainerType[T] does not give a warning for accessing '.buffer'
    """
    Metaclass used to create a helper for defining types that require other types and a size -> List[uint, 8]

    Usage:
        import pygamehack as gh

        class List(metaclass=TypeHintContainer):
            types = {
                8: List8,
                16: List16,
                ...
            }
            # This method is not required, but an example implementation is included here so you can see how it works
            # 't' is what is passed in between the brackets into the type 'List' below (gh.uint, 16) 
            # NOTE: If more than one thing is between the brackets, then 't' is a tuple of those things
            @classmethod

        class Struct(metaclass=HackStruct):
            address = 'my_address'

            values : List[gh.uint, 16] = 0x1C

    """

    @classmethod
    @abstractmethod
    def get_container_type(mcs, t) -> Any:
        raise NotImplementedError

    def __getitem__(cls, t):
        return cls.get_container_type(t)

    # Called when a new TYPE is INSTANTIATED (where TYPE is defined, after this you can make instances of the TYPE)
    def __init__(cls, name, bases, attrs, **kwargs):
        assert hasattr(cls, 'get_container_type'), \
            f"Did not define the 'get_container_type' classmethod on '{cls.__name__}'"

        # Ensure container types do not give warnings when calling methods defined by the actual types
        cls.read, cls.write = None, None
        cls.read_contents, cls.write_contents = None, None
        cls.__getitem__, cls.__setitem__ = None, None
        cls.__iter__ = None
        cls.__len__ = None
        super().__init__(name, bases, attrs, **kwargs)


class Ptr(metaclass=TypeHintContainer):
    """"""
    size = 8
    buffer = None  # Buffer types should have 'buffer' as part of the type info, but it is set at runtime

    @classmethod
    def get_container_type(cls, t):
        return PtrWrapper(t)

# endregion


# region Wrapper types

class BaseType(object):
    def __init__(self, t):
        self.type = t

    @property
    def __name__(self):
        return self.type.__name__

    def __repr__(self):
        return f"{self.__class__.__name__}[{self.type.__name__}]"


class ContainerType(BaseType):

    def __init__(self, container, value_type, size):
        super().__init__(value_type)
        self.container = container
        self.type = wrap_type(self.type)
        self.size = size or self.container.size

    @property
    def __name__(self):
        return f'{self.container.__name__}[{self.type.__name__}, {self.size}]'

    def __call__(self, *args, **kwargs):
        return self.container(*args, size=self.size, value_type=unwrap_type(self.type), **kwargs)


class PtrType(BaseType):

    def __init__(self, t):
        super().__init__(t)
        self.type = wrap_type(self.type)

    def __call__(self, *args, **kwargs):
        instance = self.type(*args, **kwargs)
        # TODO: Find out why everything seems to need 'previous_holds_ptr'
        instance.address.previous_holds_ptr = False
        return instance

    @property
    def __name__(self):
        return f'Ptr[{self.type.__name__}]'

    @property
    def size(self):
        return Ptr.size  # set at runtime


class RegularType(BaseType):
    def __init__(self, t):
        super().__init__(t)

    @property
    def size(self):
        return self.type.size

    def __call__(self, *args, **kwargs):
        instance = self.type(*args, **kwargs)
        instance.address.previous_holds_ptr = False
        return instance


# Wrappers for the derived classes with metaclass=TypeHintContainer

class PtrWrapper:
    def __init__(self, t):
        self.type = t


class ContainerWrapper:
    def __init__(self, t, value_type, size=0):
        self.container = t
        self.value_type = value_type
        self.size = size
        # Unwrap compatibility
        self.type = t


# endregion
