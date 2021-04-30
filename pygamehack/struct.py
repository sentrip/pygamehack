from abc import ABC
from typing import Optional, Union

from cpygamehack import Address
from .struct_meta import StructMeta, StructInfo, StructData


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

        gh.Struct.define_types()

    #########################################################################################
    ########## Nested struct usage: #########################################################
    #########################################################################################
        import pygamehack as gh

        class MyStructChild(gh.Struct):  # Child
            value_1: gh.uint = 0x4
            value_2: gh.uint = [0x8, 0xC]

        class MyStructParent(gh.Struct): # Parent
            my_struct: MyStructChild = 0x1C

        gh.Struct.define_types()

    #########################################################################################
    ########## Nested struct with forward declarations usage: ###############################
    #########################################################################################
        import pygamehack as gh

        class MyStructParent(gh.Struct): # Parent
            my_struct: 'MyStructChild' = 0x1C

        class MyStructChild(gh.Struct):  # Child
            value_1: gh.uint = 0x4
            value_2: gh.uint = [0x8, 0xC]

        gh.Struct.define_types()
    """
    
    size = 0
    _info = StructInfo()

    @staticmethod
    def define_types(arch: int):
        StructMeta.define_types(arch)

    @staticmethod
    def clear_types():
        StructMeta.clear_types()

    @staticmethod
    def is_struct(struct):
        return StructMeta.is_struct(struct)

    @staticmethod
    def iter_variables(struct):
        return StructMeta.iter_variables(struct)

    @staticmethod
    def walk(struct):
        return StructMeta.walk(struct)

    def __init__(self, address: Optional[Address], *args, **kwargs):
        raise NotImplementedError

    def dataclass(self, **properties) -> StructData:
        raise NotImplementedError

    def read(self) -> 'Struct':
        raise NotImplementedError

    def write(self, value: Union['Struct', StructData]):
        raise NotImplementedError

    def read_contents(self) -> 'Struct':
        raise NotImplementedError

    def write_contents(self):
        raise NotImplementedError
