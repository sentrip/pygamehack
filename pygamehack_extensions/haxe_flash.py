import pygamehack as gh
from pygamehack_utils import ConstVariable, TypeHintContainer, Ptr
from pygamehack_utils.hackstruct import HackStructArgs, HackStruct
from pygamehack_utils.type_helpers import is_basic_type, is_ptr_type, ContainerWrapper
from .raw_array import PtrArrayHackStruct


HackStruct.set_architecture(32 | 64)


class HaxeVectorHackStruct(PtrArrayHackStruct):

    def __init__(self, *args, first_offset=0x1C, **kwargs):
        super().__init__(*args, **kwargs)
        self.element_address = None
        self.hack = None
        if self.address:
            self.hack = self.address.hack
            self.element_address = self.address.hack.get_or_add_dynamic_address(
                f'{self.address.name}/e',
                self.address,
                [first_offset, 0x8]
            )
            self.element_address.previous_holds_ptr = True

    def _add_variable(self, i):
        array_address = self.hack.get_or_add_dynamic_address(f'{self.element_address.name}/{i}', self.element_address, [])
        array_address.dynamic_offset = i * Ptr.size
        address = self.hack.get_or_add_dynamic_address(f'{array_address.name}/ptr', array_address, [0x0])
        address.dynamic_offset = 0xFFFFFFFFFFFFFFFF
        address.previous_holds_ptr = False
        self.variables.append(self.value_type(address))

    def _get_size_from_args(self, args):
        return int(args.size / Ptr.size)


class CHaxeVectorHackStruct(ConstVariable, HaxeVectorHackStruct):
    pass


class HaxeVector(metaclass=TypeHintContainer):

    @classmethod
    def get_container_type(cls, t):
        t, size = t if isinstance(t, tuple) else (t, t.get_type_size())
        assert not is_ptr_type(t), 'HaxeVectors can only have basic or hackstruct value types, not Ptr'
        return ContainerWrapper(HaxeVectorHackStruct, t, size=size)


class CHaxeVector(metaclass=TypeHintContainer):

    @classmethod
    def get_container_type(cls, t):
        t, size = t if isinstance(t, tuple) else t, t.get_type_size()
        assert not is_ptr_type(t), 'HaxeVectors can only have basic or hackstruct value types, not Ptr'
        return ContainerWrapper(HaxeVectorHackStruct, t, size=size)


HackStruct.set_architecture(HackStruct.default_architecture)
