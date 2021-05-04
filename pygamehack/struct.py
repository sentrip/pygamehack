from abc import ABC
from typing import Optional, Union

from pygamehack.c import Address
from .struct_meta import StructMeta, StructInfo, StructData, StructDefinition


__all__ = ['StructMeta', 'StructInfo', 'Struct']


class Struct(ABC, metaclass=StructMeta):
    """
    Class defining a struct-like object that reads from memory addresses

    #########################################################################################
    ########## Root struct usage: ###########################################################
    #########################################################################################
        import pygamehack as gh

        class MyStruct(gh.Struct):
            value_1: gh.uint = 0x1C

    #########################################################################################
    ########## Nested struct usage: #########################################################
    #########################################################################################
        import pygamehack as gh

        class MyStructChild(gh.Struct):  # Child
            value_1: gh.uint = 0x4
            value_2: gh.uint = [0x8, 0xC]

        class MyStructParent(gh.Struct): # Parent
            my_struct: MyStructChild = 0x1C

    #########################################################################################
    ########## Nested struct with forward declarations usage: ###############################
    #########################################################################################
        import pygamehack as gh

        class MyStructParent(gh.Struct): # Parent
            my_struct: 'MyStructChild' = 0x1C

        class MyStructChild(gh.Struct):  # Child
            value_1: gh.uint = 0x4
            value_2: gh.uint = [0x8, 0xC]
    """
    @staticmethod
    def clear_types():
        StructMeta.clear_types()

    @staticmethod
    def is_struct(o: Union['Struct', StructMeta]):
        return StructMeta.is_struct(o)

    @staticmethod
    def named(name: str, arch: int) -> StructDefinition:
        return StructMeta.named(name, arch)

    @staticmethod
    def iter_variables(struct: 'Struct'):
        return StructMeta.iter_variables(struct)

    @staticmethod
    def walk(struct: 'Struct'):
        return StructMeta.walk(struct)

    # These definitions are never used, they are provided for documentation purposes

    size = 0
    _info = StructInfo()

    def __init__(self, address: Optional[Address], *args, **kwargs):
        pass

    def dataclass(self, **properties) -> StructData:
        return StructData(self.__class__)

    def get(self) -> 'Struct':
        return self

    def read(self) -> 'Struct':
        return self

    def write(self, value: Union['Struct', StructData]):
        return

    def flush(self):
        return

    def reset(self):
        return
