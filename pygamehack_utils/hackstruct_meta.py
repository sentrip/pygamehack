import inspect
from abc import ABC, ABCMeta
from typing import Optional, Union

from .debug_view import DebuggableVariable, DebugConfig
from .type_helpers import is_hackstruct_type, wrap_type, PtrType, Ptr, unwrap_type

import pygamehack as gh


__all__ = ['HackStructMeta', 'HackStructArgs', 'HackStructInfo', 'DataClass']


# region HackStructMeta

class HackStructMeta(ABCMeta):
    """
    Metaclass for defining a struct-like object that reads from memory addresses

    Root struct usage:
        import pygamehack as gh

        class MyStruct(metaclass=HackStructMeta):
            address = 'my_struct_address'

            value_1: gh.uint = 0x1C

        HackStructMeta.define_types()

    Nested struct usage:
        import pygamehack as gh

        class MyStruct(metaclass=HackStructMeta):  # Child
            value_1: gh.uint = 0x4
            value_2: gh.uint = [0x8, 0xC]

        class MyStructHolder(metaclass=HackStructMeta): # Parent
            address = 'my_struct_holder_address'

            my_struct: MyStruct = 0x1C

        HackStructMeta.define_types()
    """
    @staticmethod
    def define_types():
        for cls in HackStructMeta._to_define:
            HackStructMeta._defined[cls] = HackStructDefinition(cls)
            HackStructMeta._defined_by_name[cls.__name__] = HackStructMeta.struct(cls)

        HackStructMeta._to_define.reverse()

        for cls in HackStructMeta._to_define:
            HackStructMeta.struct(cls).parse_fields()

        HackStructMeta._to_define.reverse()

        for cls in HackStructMeta._to_define:
            HackStructMeta.struct(cls).parse_size()

        HackStructMeta._to_define = []

    @staticmethod
    def iter_variables(struct):
        def _recurse(k, s):
            yield k, s
            if is_hackstruct_type(s) and not s.__class__._info.is_custom_type:
                for k, v in s.variables.items():
                    for sk, sv in _recurse(k, v):
                        yield sk, sv
        return _recurse(None, struct)

    @staticmethod
    def set_architecture(t: int):
        """
        Set the set_architecture (32 or 64) for the defined structs
        NOTE: This must be called BEFORE defining any HackStructs
        """
        if t & 64:
            Ptr.size = 8
            HackStructMeta._architecture = 64
        elif t & 32:
            Ptr.size = 4
            HackStructMeta._architecture = 32
        else:
            raise RuntimeError(f'Invalid architecture {t} (32, 64)')

    @staticmethod
    def struct(cls):
        return HackStructMeta._defined.get(cls, None)

    @staticmethod
    def named(name: str):
        return HackStructMeta._defined_by_name.get(name, None)

    # MARK: Metaclass
    default_architecture = 64
    _architecture = default_architecture
    _defined = {}
    _defined_by_name = {}
    _to_define = []

    # Called when a new TYPE is DEFINED (before anything interesting happens)
    def __new__(mcs, name, bases, attrs, **kwargs):
        if name == 'HackStruct':
            return super().__new__(mcs, name, bases, attrs)

        definition = {k: v for k, v in attrs.items() if _is_hack_field(k) or k == '__init__'}
        definition['address'] = attrs.get('address', None)
        definition['_info'] = HackStructInfo()

        # Basic debug capabilities for hackstructs
        if DebuggableVariable not in bases:
            if ABC in bases:
                idx = list(bases).index(ABC)
                bases = (*bases[:idx], DebuggableVariable, ABC, *bases[idx+1:])
            else:
                bases = (*bases, DebuggableVariable)

        subclass = super().__new__(mcs, name, bases, definition)

        # This must be done after abc.ABCMeta creates a type otherwise it gets confused
        for name in _debug_methods:
            definition[name] = getattr(DebuggableVariable, name)
            definition[name].__isabstractmethod__ = False

        return subclass

    # Called when a new TYPE is INSTANTIATED (where TYPE is defined, after this you can make instances of the TYPE)
    def __init__(cls, name, bases, attrs, **kwargs):
        if name == 'HackStruct':
            super().__init__(name, bases, attrs)
            return

        cls.__annotations__ = attrs.get('__annotations__', {})
        cls._info = getattr(cls, '_info', None)

        cls._info.offsets = {k: v for k, v in attrs.items() if _is_hack_field(k)}
        cls._info.architecture = HackStructMeta._architecture
        cls._info.line_defined = inspect.getouterframes(inspect.currentframe())[1].lineno  # gets line of class def
        cls._info.is_custom_type = kwargs.pop('custom', cls._info.is_custom_type)
        cls._info.is_pod_type = False

        if not cls._info.is_custom_type:
            cls.dataclass = lambda: _dataclass(cls)
            cls.buffer = None  # Buffer types should have 'buffer' as part of the type info, but it is set at runtime
            cls.size = kwargs.get('size', 0)
            cls.read = _read
            cls.write = _write
            cls.__repr__ = _repr
            cls.__init__ = _init

        HackStructMeta._to_define.append(cls)
        super().__init__(name, bases, attrs, **kwargs)

# endregion

# region DataClass


class DataClass:
    is_buffer_type = False
    _cls = None

    def __repr__(self):
        return f'Data[{self._cls.__name__}]'


def _dataclass(cls):
    data = DataClass()
    data._cls = cls
    for k, t in cls.__annotations__.items():
        factory = _default_factories.get(t, getattr(t, 'default_factory', lambda: None))
        setattr(data, k, factory())
    return data


_default_factories = {
    gh.bool: bool,
    gh.float: float,
    gh.double: float,
    gh.int8: int,
    gh.int16: int,
    gh.int32: int,
    gh.int64: int,
    gh.uint8: int,
    gh.uint16: int,
    gh.uint32: int,
    gh.uint64: int,
}

# endregion

# region Helper functions

_default_props = {
    'address', '_info',
    "__module__", "__qualname__", "__annotations__",
    "__init__", "__dict__", "__weakref__", "__doc__",
}


def _is_hack_field(name):
    return name not in _default_props


def _get_names_of_variables_to_propagate_args(cls, exclude_list, include_list):
    if not exclude_list and not include_list:
        return list(HackStructMeta.struct(cls).fields.keys())

    # TODO: @UserInputError Ensure only exclude_list or include_list is passed, not both

    # Gets all properties prefixed with the current class name -> 'NAME.FIELD' where cls.__name__ == 'NAME'
    def _get_relevant_fields(fields):
        return set(v.split('.')[1] for v in fields if v.split('.')[0] == cls.__name__)

    included = set()

    # TODO: @UserInputError Error handling for incorrect input
    if include_list:
        include_list.update(_get_relevant_fields(include_list))
    else:
        excluded = _get_relevant_fields(exclude_list)
        for name in HackStructMeta.struct(cls).fields:
            if name not in excluded:
                included.add(name)

    return included

# endregion

# region HackStruct methods


def _init(self, v: Union[gh.Hack, gh.Address, gh.Buffer], *args, **kwargs: dict):
    include = _get_names_of_variables_to_propagate_args(
        self.__class__,
        kwargs.get('exclude', []),
        kwargs.get('include', [])
    )
    is_buffer_type = kwargs.get('buffer', False)
    kwargs = kwargs if kwargs.get('propagate', False) else {}

    parsed_args = HackStructArgs(self.__class__, (v,) + args)

    self.is_buffer_type = is_buffer_type
    self._getters = [None for _ in parsed_args.struct.fields]
    self._setters = [None for _ in parsed_args.struct.fields]
    self.variables = {}

    if is_buffer_type:
        self.buffer = _create_buffer(self, parsed_args)

    for name, field in parsed_args.struct.fields.items():

        if not is_buffer_type or is_hackstruct_type(field.type):
            actual_kwargs = kwargs if name in include else {}

            self.variables[name] = _create_field(
                self,
                parsed_args,
                name,
                field,
                parsed_args.struct.offsets[name],
                **actual_kwargs
            )


# TODO: Equality and hashing


def _repr(self):
    # TODO: __repr__ for view variables
    if self.address is None:
        return self.__class__.__name__
    return f'{self.__class__.__name__}({hex(self.address.address)})'


def _read(self):
    return self


def _write(self, value):
    assert isinstance(value, self.__class__) or (isinstance(value, DataClass) and value._cls == self.__class__), \
        f"Cannot write varable {value} to variable of type '{self.__class__}'"

    # Write buffer with buffer
    if self.is_buffer_type and value.is_buffer_type:
        self.buffer.write(value)
    # Write buffer with hackstruct or hackstruct-dataclass
    elif self.is_buffer_type:
        # Write buffer with hackstruct
        if is_hackstruct_type(value):
            for k, variable in value.variables.items():
                setattr(self, k, variable.read())
        # Write buffer with hackstruct-dataclass
        else:
            for k in self.__class__.__annotations__:
                v = getattr(value, k)
                if v:
                    setattr(self, k, v)
        self.buffer.write_contents()
    # Write hackstruct with buffer or hackstruct-dataclass
    else:
        for k, variable in self.variables.items():
            v = getattr(value, k)
            if value:
                variable.write(v)


# endregion

# region HackStruct factory

def _create_buffer(instance, parsed_args):
    # Create a buffer view if the instance is a pod-type buffer hackstruct inside another buffer hackstruct
    if parsed_args.src_buffer and instance.is_buffer_type and parsed_args.struct.info.is_pod_type:
        return gh.buffer(parsed_args.src_buffer, parsed_args.offset, parsed_args.size)
    # Otherwise just create a new buffer from the instance address
    else:
        _set_hackstruct_address(instance, parsed_args)
        return gh.buffer(instance.address, parsed_args.struct.size)


def _create_field(instance, parsed_args, name, field, offsets, **kwargs):
    # Set address from args
    _set_hackstruct_address(instance, parsed_args)

    # Create address that depends on instance address
    address = parsed_args.hack.get_or_add_dynamic_address(
        f"{instance.address.name}/{name}",
        instance.address,
        offsets
    )

    # Propagate kwargs to nested hackstruct objects
    actual_kwargs = kwargs if is_hackstruct_type(field) else {}

    # Create the variable
    return field(address, **actual_kwargs)


def _set_hackstruct_address(instance, parsed_args):
    if not instance.address or isinstance(instance.address, str):
        instance.address = parsed_args.address
        if parsed_args.struct.info.architecture != instance.address.hack.get_architecture():
            raise RuntimeError(f'Architecture mismatch: Hack ({instance.address.hack.architecture}) '
                               f'and {parsed_args.struct.cls.__name__} ({parsed_args.struct.info.architecture})')


def _create_field_doc(field):
    return f'{field.struct.cls.__name__}.{field.name}: ' \
           f'{field.type.__name__} = ' \
           f'[{", ".join([hex(v) for v in field.struct.offsets[field.name]])}]' \
           f''  # - fucking.py line {field.struct.info.line_defined}'

# endregion

# region HackStruct definition helper classes


class HackStructDefinition(object):

    def __init__(self, cls):
        self.cls = cls
        self.info = self.cls._info
        self.fields = {}
        self.field_indexes = {}
        self.offsets = {}
        self.size = 0
        self.address_path = None
        # Detect Plain-Old-Data types
        has_hackstruct_properties = any(is_hackstruct_type(t) for t in self.cls.__annotations__.values())
        self.info.is_pod_type = not has_hackstruct_properties and not self.info.is_custom_type

    def __repr__(self):
        return f"HackStruct[{self.cls.__name__}]"

    def parse_fields(self):
        # TODO: Handle methods defined in hackstructs
        if self.info.is_custom_type:
            return

        self.address_path = self.cls.__dict__.get('address', None)

        # Parse offsets
        index = 0
        for name, offsets in self.info.offsets.items():
            if _is_hack_field(name):
                self.offsets[name] = offsets if isinstance(offsets, list) else [offsets]
                self.field_indexes[name] = index
                index += 1

        # Parse types
        for name, t in self.cls.__annotations__.items():
            # Create field
            field = HackStructField(name, t, self)
            self.fields[name] = field

            # Create property for field
            prop = HackStructProperty(field, field.getter, field.setter)
            setattr(self.cls, name, prop)

            # Pointers require an extra read with no offset (this is how GuidedHacking's FindDMAAddy function works)
            if isinstance(field.type, PtrType):
                self.offsets[name].append(0x0)

    def parse_size(self):
        # This must be called after every class is defined in reverse order
        # to allow child classes to define their size before they are used in their parents
        for name, offsets in self.offsets.items():
            self.size = max(self.size, self.offsets[name][0] + self.fields[name].type.size)
        self.cls.size = max(self.cls.size, self.size)


class HackStructProperty(property):
    _custom_props = {
        'field', '__doc__', 'size', 'dot_path', '_consume_dot_path',
        "__class__", "__name__", "__bases__", "__mro__", "__module__", '__repr__'
    }

    def __init__(self, field, fget, fset):
        super().__init__(fget, fset, lambda: None, "")
        self.field = field
        self.dot_path = []

    def __getattribute__(self, item):
        if item in HackStructProperty._custom_props:
            return super().__getattribute__(item)
        else:
            self.dot_path.append(self.field)
            t = unwrap_type(self.field.type, definitions=HackStructMeta._defined_by_name)
            v = t.__getattribute__(t, item)
            if isinstance(v, HackStructProperty):
                v.dot_path = self.dot_path
            return v

    def __repr__(self):
        return f"Property({self.field.type.__name__})"

    @property
    def __doc__(self):
        return '\n'.join([_create_field_doc(v) for v in self._consume_dot_path()])

    @property
    def size(self):
        return self.field.type.size

    def _consume_dot_path(self):
        path = [i for i in self.dot_path] + [self.field]
        self.dot_path.clear()
        return path


class HackStructField(object):

    def __init__(self, name, t, struct):
        self.name = name
        self.struct = struct
        self.index = struct.field_indexes[name]
        self.type = wrap_type(t)
        # Buffer
        self.offset = struct.offsets[self.name][0]  # buffers can only have a single offset
        self.method_suffix = f"{unwrap_type(t, definitions=HackStructMeta._defined_by_name).__name__}" \
                             f"{'_ptr' if isinstance(self.type, PtrType) else ''}"

    def __repr__(self):
        return f"{self.type.__class__.__name__}[{self.type.__name__}]"

    def __call__(self, *args, **kwargs):
        return self.type(*args, **kwargs)

    @property
    def getter(self):
        index = self.index

        def _get(instance):
            getter = instance._getters[index]
            if not getter:
                getter = self.create_getter(instance)
                instance._getters[index] = getter
            return getter(instance)

        return _get

    @property
    def setter(self):
        index = self.index

        def _set(instance, value):
            setter = instance._setters[index]
            if not setter:
                setter = self.create_setter(instance)
                instance._setters[index] = setter
            setter(instance, value)

        return _set

    def create_getter(self, instance):
        variable = instance.variables.get(self.name, None)

        if instance.is_buffer_type:
            if not variable:
                offset = self.offset
                method = getattr(instance.buffer.get(), f'read_{self.method_suffix}')
                return lambda i: method(offset)
            else:
                return lambda i: variable
        else:
            return lambda i: variable.read()

    def create_setter(self, instance):
        variable = instance.variables.get(self.name, None)

        if instance.is_buffer_type:
            if not variable:
                offset = self.offset
                method = getattr(instance.buffer.get(), f'write_{self.method_suffix}')
                return lambda i, v: method(offset, v)
            else:
                return lambda i, v: variable.write(v)
        else:
            return lambda i, v: variable.write(v)


class HackStructArgs(object):
    def __init__(self, cls, args: tuple):
        self.hack = None
        self.address = None
        self.src_buffer = None
        self.offset = 0
        self.size = 0
        self.struct = HackStructMeta.struct(cls)

        # TODO: @UserInputError assert args are correct

        arg_0_type = args[0].__class__.__name__

        # Regular variable
        if arg_0_type == 'Address':
            self.hack = args[0].hack
            self.address = args[0]
        elif arg_0_type == 'Hack':
            if self.struct.info.is_custom_type:
                raise TypeError(f"Cannot initialize custom variable '{cls.__name__}' with an argument of type 'Hack'")
            self.hack = args[0]
            self.address = self._get_root_address(HackStructMeta.struct(cls))
        # Variable view
        elif arg_0_type == 'Buffer':
            self.address = None
            self.src_buffer = args[0]
            self.hack = self.src_buffer.hack
            self.offset = args[1]
            self.size = args[2]

    def _get_root_address(self, struct: Optional[HackStructDefinition]):
        path = struct.address_path
        used_in = struct.cls.__name__
        try:
            return self.hack.address(path)
        except IndexError:
            raise RuntimeError(f"Address not been added - {path} used in {used_in}")


class HackStructInfo(object):
    def __init__(self):
        self.architecture = 0
        self.line_defined = 0
        self.is_custom_type = False
        self.is_pod_type = False
        self.offsets = {}

    def __repr__(self):
        return f'HackStructInfo(' \
               f'{"x86" if self.architecture == 32 else "x64"}, '\
               f'custom={self.is_custom_type}, '\
               f'POD={self.is_pod_type})'


# endregion

# region Standard variable debugging extensions

_debug_methods = list(k for k in DebuggableVariable.__dict__.keys() if k.startswith('debug_'))
_default_props.update(_debug_methods)


def _debug_config(self):
    return DebugConfig(
        can_modify=True,
        show_value=True,
        show_value_as_hex=False,
        show_updates=True
    )


def _debug_string_basic(self, show_as_hex):
    return str(self.read()) if not show_as_hex else f'{self.read():0{2 * self.address.hack.ptr_size}x}'


_integer_type_names = ['int8', 'int16', 'int32', 'int64']
_misc_type_names = ['bool', 'float', 'double']

for type_name in _misc_type_names + _integer_type_names + [f'u{v}' for v in _integer_type_names]:
    type_ = getattr(gh, type_name)
    type_.debug_config = _debug_config
    type_.debug_address = DebuggableVariable.debug_address
    type_.debug_address_to_watch = DebuggableVariable.debug_address_to_watch
    type_.debug_string = _debug_string_basic


# endregion
