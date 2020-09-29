from abc import ABC, abstractmethod
from .hackstruct import HackStruct

__all__ = ['Variable', 'ConstVariable', 'ArrayVariable', 'DictVariable']


class Variable(HackStruct, custom=True):
    """
    Abstract interface to be extended to implement your own custom variables
    """
    size = 0

    def __init_subclass__(cls, *args, **kwargs):
        cls._info.is_custom_type = True
        return super().__init_subclass__(*args, **kwargs)

    @classmethod
    @abstractmethod
    def get_type_size(cls):
        raise NotImplementedError

    @abstractmethod
    def read(self) -> object:
        raise NotImplementedError

    @abstractmethod
    def write(self, value):
        raise NotImplementedError


class ConstVariable(Variable, ABC):
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

    def write_contents(self):
        raise RuntimeError('Cannot write to a constant variable')

    def __setitem__(self, key, value):
        raise RuntimeError('Cannot write to a constant variable')


class ArrayVariable(Variable, ABC):
    """
    Abstract interface to be extended to implement your own custom array-like variables
    """
    def read(self) -> object:
        return self

    def write(self, values: list):
        assert len(values) <= len(self)
        for i, v in enumerate(values):
            self[i] = v

    @abstractmethod
    def read_contents(self):
        raise NotImplementedError

    @abstractmethod
    def write_contents(self):
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


class DictVariable(ArrayVariable, ABC):
    """
    Abstract interface to be extended to implement your own custom dict-like variables
    """
    def write(self, values: dict):
        for k, v in values.items():
            self[k] = v
