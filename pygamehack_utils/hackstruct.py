from abc import ABC

from typing import Union

import pygamehack as gh

from .hackstruct_meta import HackStructMeta, HackStructInfo, DataClass, HackStructArgs

__all__ = ['HackStruct', 'HackStructArgs', 'HackStructInfo', 'DataClass']


class HackStruct(ABC, metaclass=HackStructMeta):

    default_architecture = HackStructMeta.default_architecture

    _info = HackStructInfo()

    def __init__(self, v: Union[gh.Hack, gh.Address, gh.Buffer], *args, **kwargs: dict):
        super().__init__()

    def dataclass(self) -> DataClass:
        pass

    def read(self) -> 'HackStruct':
        pass

    def write(self, v: Union['HackStruct', DataClass]):
        pass

    @staticmethod
    def define_types():
        HackStructMeta.define_types()

    @staticmethod
    def iter_variables(struct):
        return HackStructMeta.iter_variables(struct)

    @staticmethod
    def set_architecture(t: int):
        return HackStructMeta.set_architecture(t)

    @staticmethod
    def struct(cls: 'HackStruct'):
        return HackStructMeta.struct(cls)

    @staticmethod
    def named(name: str):
        return HackStructMeta.named(name)


# This is some old brainstorming that was left here because it might be cleaned up in the future
# It contains outdated information
"""

Hackstruct definition steps (internal)

############# ON IMPORT ##############

- 1. Define types with 'class' keyword                                (HackStruct.__new__, HackStruct.__init__)
    - 1.1. Detect custom variables                                    VARIABLES (cls.is_custom_type) 
    - 1.2. Add class and attributes to list for later parsing 

######################################


############# ON DEFINE ##############                                (HackStruct.define_types)

- 2. Determine which types are POD types from list of definitions     (HackStructDefinition.parse_pod_type)     REQUIRES attrs
    - 2.1. Record definition for later use                            VARIABLES (HackStructDefinition._to_define)
    - 2.2. Detect POD type variables                                  VARIABLES (cls.is_pod_type) 

- 3. Parse properties from class attributes                           (HackStructDefinition.parse_attrs)        REQUIRES attrs
    - 3.1. Save offsets for each property                             VARIABLES (struct.offsets) 
    - 3.2. Save the HackStructField for each property                 VARIABLES (struct.fields) 
    - 3.3. Create HackStructProperty for each property                VARIABLES (cls.NAME)

- 4. Parse class sizes from offsets                                   (HackStructDefinition.parse_size)         REQUIRES attrs, offsets
    - 4.1. Update size based on offsets and size of properties        VARIABLES (cls.size)

######################################


############# ON CREATE ##############                                (HackStruct.__call__)                     REQUIRES

1. detect buffer
2. parse args and modify kwargs based on buffer and propagation

3. add buffer to instance if is_buffer_type based on parsed args
    3.1. detect buffer view
    3.2. create appropriate buffer

4. for each property:
    create_variable




create_variable:

1. parse args
2. if variable is root create address from cls.address otherwise use address in parsed args to create variable
3. add dynamic address for variable in hack based on name and offset
4. propagate keyword arguments to nested hackstruct objects
5. create variable



######################################

"""
