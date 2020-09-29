import pygamehack as gh
from pygamehack_utils import ArrayVariable, ConstVariable, TypeHintContainer
from pygamehack_utils.hackstruct import HackStructArgs, HackStruct
from pygamehack_utils.type_helpers import is_basic_type, is_ptr_type, ContainerWrapper


__all__ = ['Array', 'CArray']

HackStruct.set_architecture(32 | 64)


class RawArray(ArrayVariable):

    @classmethod
    def get_type_size(cls):
        return 8

    def __init__(self, *args, value_type=None, size=None, **kwargs):
        self.is_buffer_type = True
        self.value_type = value_type
        self._auto_update = False

        args = HackStructArgs(self.__class__, args)

        self.address = args.address
        self.size = self._get_size_from_args(args) or size or RawArray.get_type_size()

        if args.src_buffer:
            self.buffer = gh.buffer(args.src_buffer, args.offset, self.size * self.value_type.size)
        else:
            self.buffer = gh.buffer(self.address, self.size * self.value_type.size)

        self.read_func = lambda i: getattr(self.buffer.get(), f'read_{self.value_type.__name__}')(i)
        self.write_func = lambda i, v: getattr(self.buffer.get(), f'write_{self.value_type.__name__}')(i, v)

    @property
    def auto_update(self) -> bool:
        return self._auto_update

    @auto_update.setter
    def auto_update(self, v):
        self._auto_update = v

    def write(self, values: list):
        super().write(values[:self.size])
        if self._auto_update:
            self.write_contents()

    def read_contents(self):
        self.buffer.read()

    def write_contents(self):
        self.buffer.write_contents()

    def __getitem__(self, key):
        self._check_bounds(key)
        if self._auto_update:
            self._read_element_from_memory(key)
        return self.read_func(key * self.value_type.size)

    def __setitem__(self, key, value):
        self._check_bounds(key)
        self.write_func(key * self.value_type.size, value)
        if self._auto_update:
            self._write_element_to_memory(key)

    def __iter__(self):
        for i in range(self.size):
            yield self[i]

    def __len__(self):
        return self.size

    def _check_bounds(self, i):
        assert i < self.size, f"List index {i} out of bounds ({self.size})"

    def _read_element_from_memory(self, index):
        self.buffer.get().read_slice(self.address.address, index * self.value_type.size, self.value_type.size)

    def _write_element_to_memory(self, index):
        self.buffer.get().write_slice(self.address.address, index * self.value_type.size, self.value_type.size)

    def _get_size_from_args(self, args):
        return int(args.size / self.value_type.size)


class RawArrayPod(RawArray):
    def __init__(self, *args, value_type=None, size=8, **kwargs):
        super().__init__(*args, value_type=value_type, size=size, **kwargs)
        self.variables = []
        self.read_func = lambda i: self.variables[int(i / value_type.size)].read()
        self.write_func = lambda i, v: self.variables[int(i / value_type.size)].write(v)

    def read_contents(self):
        super().read_contents()
        n_variables = len(self.variables)
        if n_variables < self.size:
            self._add_n(self.size - n_variables, starting_at=n_variables)
        elif n_variables > self.size:
            self.variables = self.variables[:self.size]

    def _add_n(self, n, starting_at=0):
        for i in range(starting_at, starting_at + n):
            self._add_variable(i)

    def _add_variable(self, i):
        value_size = self.value_type.size
        self.variables.append(self.value_type(self.buffer.get(), i * value_size, value_size,
                                              buffer=True, propagate=True))


class RawArrayHackStruct(RawArrayPod):

    def _add_variable(self, i):
        address = self.address.hack.get_or_add_dynamic_address(f'{self.address.name}/{i}', self.address, [])
        address.dynamic_offset = i * self.value_type.size
        self.variables.append(self.value_type(address))

    @property
    def auto_update(self) -> bool:
        return True  # HackStructs are always updated on reads and writes

    def _read_element_from_memory(self, index):
        pass

    def _write_element_to_memory(self, index):
        pass


class PtrArrayHackStruct(RawArrayHackStruct):
    def _add_variable(self, i):
        address = self.address.hack.get_or_add_dynamic_address(f'{self.address.name}/{i}', self.address, [])
        address.dynamic_offset = i * self.value_type.size
        self.variables.append(self.value_type(address))


class CRawArray(ConstVariable, RawArray):
    pass


class CRawArrayPod(ConstVariable, RawArrayPod):
    pass


class CRawArrayHackStruct(ConstVariable, RawArrayHackStruct):
    pass


class CPtrArrayHackStruct(ConstVariable, PtrArrayHackStruct):
    pass


def _get_array_for_type(t, arrays):
    if is_basic_type(t):
        return arrays[0]  # (C)RawArray
    elif getattr(t, 'is_pod_type'):
        return arrays[1]  # (C)RawArrayPod
    else:
        return arrays[2]  # (C)RawArrayHackStruct


class Array(metaclass=TypeHintContainer):

    @classmethod
    def get_container_type(cls, t):
        t, size = t if isinstance(t, tuple) else (t, t.get_type_size())
        assert not is_ptr_type(t), 'Arrays can only have basic or hackstruct value types, not Ptr'
        return ContainerWrapper(_get_array_for_type(t, [RawArray, RawArrayPod, RawArrayHackStruct]), t, size=size)


class CArray(metaclass=TypeHintContainer):

    @classmethod
    def get_container_type(cls, t):
        t, size = t if isinstance(t, tuple) else t, t.get_type_size()
        assert not is_ptr_type(t), 'Arrays can only have basic or hackstruct value types, not Ptr'
        return ContainerWrapper(_get_array_for_type(t, [CRawArray, CRawArrayPod, CRawArrayHackStruct]), t, size=size)


class PtrArray(metaclass=TypeHintContainer):

    @classmethod
    def get_container_type(cls, t):
        t, size = t if isinstance(t, tuple) else (t, t.get_type_size())
        assert not is_ptr_type(t), 'PtrArrays can only have basic or hackstruct value types, not Ptr'
        return ContainerWrapper(_get_array_for_type(t, [None, None, PtrArrayHackStruct]), t, size=size)


class CPtrArray(metaclass=TypeHintContainer):

    @classmethod
    def get_container_type(cls, t):
        t, size = t if isinstance(t, tuple) else t, t.get_type_size()
        assert not is_ptr_type(t), 'PtrArrays can only have basic or hackstruct value types, not Ptr'
        return ContainerWrapper(_get_array_for_type(t, [None, None, CPtrArrayHackStruct]), t, size=size)


HackStruct.set_architecture(HackStruct.default_architecture)
