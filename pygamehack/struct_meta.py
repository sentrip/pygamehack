import inspect
from abc import ABCMeta, abstractmethod
import pygamehack.c as cgh

__all__ = [
    # Main API
    'StructMeta', 'StructType', 'TypeWrapper',
    # Info
    'StructInfo', 'StructDefinition',
    # Low level
    'StructData', 'StructDependencies'
]


# region StructMeta

class StructMeta(ABCMeta):
    """
    Metaclass for defining a struct-like object that reads from memory addresses

    Root struct usage:
        import pygamehack as gh

        class MyStruct(metaclass=gh.StructMeta):
            value_1: gh.uint = 0x1C

    Nested struct usage:
        import pygamehack as gh

        class MyStructChild(metaclass=gh.StructMeta):  # Child
            value_1: gh.uint = 0x4
            value_2: gh.uint = [0x8, 0xC]

        class MyStructParent(metaclass=gh.StructMeta): # Parent
            my_struct: MyStructChild = 0x1C
    """

    @staticmethod
    def clear_types():
        _StructDefinitions.to_define.clear()
        for definitions in [_defined_32, _defined_64]:
            definitions.defined.clear()
            definitions.defined_by_name.clear()
            definitions.dependencies.clear()

    @staticmethod
    def is_struct(cls) -> bool:
        return hasattr(cls, '__is_struct_type') or hasattr(cls.__class__, '__is_struct_type')

    @staticmethod
    def struct(cls: 'StructMeta', arch: int) -> 'StructDefinition':
        return _StructDefinitions.defs(arch).defined.get(cls, None)

    @staticmethod
    def named(name: str, arch: int) -> 'StructDefinition':
        return _StructDefinitions.defs(arch).defined_by_name.get(name, None)

    @staticmethod
    def iter_variables(struct):
        if hasattr(struct, 'buffer'):
            arch = 32 if struct.buffer.address.hack.process.arch == cgh.Process.Arch.x86 else 64
            definition = _StructDefinitions.defs(arch).defined.get(struct.__class__, None)
            if definition is not None:
                for name, field in definition.fields.items():
                    yield name, field
        if hasattr(struct, 'variables'):
            for name, variable in struct.variables.items():
                yield name, variable
        return None

    @staticmethod
    def walk(struct):
        def _recurse(k, s, p):
            yield k, s, p
            if StructMeta.is_struct(s) and not s._info.is_custom_type:
                for sk, sv in s.variables.items():
                    for gk, gv, gp in _recurse(sk, sv, s):
                        yield gk, gv, gp

        return _recurse(None, struct, None)

    @staticmethod
    def check_buffer_view_kwargs(address, kwargs):
        if address is None:
            if not kwargs.get('buffer', False):
                raise RuntimeError('You must either create a Struct with an address or the following kwargs:\n'
                                   "\t'buffer': bool = True\n"
                                   "\t'parent_buffer': buf = <parent>\n"
                                   "\t'offset_in_parent': <offset_in_parent>")
            if 'parent_buffer' not in kwargs:
                raise RuntimeError("Buffer view kwargs missing 'parent_buffer': Buffer")
            if 'offset_in_parent' not in kwargs:
                raise RuntimeError("Buffer view kwargs missing 'offset_in_parent': int")
            return True
        elif kwargs.get('buffer', False) and ('parent_buffer' in kwargs or 'offset_in_parent' in kwargs):
            raise RuntimeError("You must either provide an address, or buffer view kwargs, not both")
        return False

    @staticmethod
    def get_architecture_from_address_kwargs(address, kwargs) -> int:
        if address is not None:
            if not address.hack.process.attached:
                raise RuntimeError('You must first attach to a running process before creating instances of Structs')
            process = address.hack.process
        else:
            StructMeta.check_buffer_view_kwargs(address, kwargs)
            process = kwargs['parent_buffer'].address.hack.process
        return 32 if process.arch == cgh.Process.Arch.x86 else 64

    # Called when a new TYPE is DEFINED (before anything interesting happens)
    def __new__(mcs, name, bases, attrs, **kwargs):
        if name == 'Struct' or not kwargs.get('define', True):
            return super().__new__(mcs, name, bases, attrs)

        definition = {k: v for k, v in attrs.items() if StructDefinition.is_struct_offset(v) or k == '__init__'}
        definition['_info'] = StructInfo()
        definition['_info'].arch = kwargs.get('architecture', 'all')
        definition['__is_struct_type'] = True  # dummy property used to detect struct types

        subclass = super().__new__(mcs, name, bases, definition)
        return subclass

    # Called when a new TYPE is INSTANTIATED (where TYPE is defined, after this you can make instances of the TYPE)
    def __init__(cls, name, bases, attrs, **kwargs):
        if name == 'Struct':
            super().__init__(name, bases, attrs)
            return

        _StructDefinitions.to_define.append(cls)
        _StructDefinitions.add_definitions_for_class(cls)
        _StructDefinitions.configure_class(cls, attrs, kwargs)

        if not cls._info.is_custom_type:
            cls.__init__ = _StructMethods.init
            cls.__str__ = _StructMethods.str
            cls.read = _StructMethods.read
            cls.write = _StructMethods.write
            cls.flush = _StructMethods.flush
            cls.reset = _StructMethods.reset
            cls.dataclass = lambda **kw: StructData.create(cls, **kw)

        super().__init__(name, bases, attrs, **kwargs)

        _StructDefinitions.check_dependencies_define(cls)


# endregion

# region StructData

class StructData(object):

    def __init__(self, cls):
        self._cls = cls

    def __repr__(self):
        return f'Data[{self._cls.__name__}]'

    @staticmethod
    def create(cls, **kwargs):
        data = StructData(cls)
        for k, t in cls.__annotations__.items():
            if k not in kwargs:
                defined_factory = getattr(t, 'default_factory', lambda: None)
                factory = StructData._default_factories.get(t, defined_factory)
                setattr(data, k, factory())
            else:
                setattr(data, k, kwargs[k])
        return data

    _default_factories = {
        k: {
            'i': int, 'u': int, 'p': int,
            'b': bool, 'f': float, 'd': float
        }[k[0]] for k in
        ['i8', 'i16', 'i32', 'i64', 'u8', 'u16', 'u32', 'u64',
         'int', 'uint', 'bool', 'float', 'double', 'ptr']
    }


# endregion

# region StructDefinition

class StructDefinition(object):

    def __init__(self, cls):
        self.size = 0
        self.cls = cls
        self.info = self.cls._info
        self.fields = {}
        self.offsets = {}

    def __repr__(self):
        s = self.cls.__name__ + f'(size={self.size}):\n'
        for name, field in self.fields.items():
            s += f'\t{name:32}: {str(field):32} = [{", ".join(cgh.Address.make_string(i) for i in self.offsets[name])}]\n'
        return s

    def parse_dependencies(self):
        dependencies = set()

        # Ensure derived inherit the fields of their parents
        StructDefinition._update_with_dicts_of_bases(
            self.cls, _StructDefinitions.arch,
            self.cls.__annotations__, lambda s: s.cls.__annotations__)

        StructDefinition._update_with_dicts_of_bases(
            self.cls, _StructDefinitions.arch,
            self.offsets, lambda s: s.offsets)

        # Parse dependencies
        for name, t in self.cls.__annotations__.items():
            if StructType.is_basic_type(t):
                continue

            if isinstance(t, str):
                dependencies.add(t)

            elif StructMeta.is_struct(t):
                dependencies.add(t.__name__)

        return dependencies

    # This must be called after definitions have been sorted by dependency order
    def parse_fields(self):
        # Detect POD (Plain-Old-Data) types
        has_struct_properties = any(StructMeta.is_struct(t) for t in self.cls.__annotations__.values())
        self.info.is_pod_type = not has_struct_properties and not self.info.is_custom_type

        seen_offsets = {}
        field_indexes = {}

        # Parse offsets
        index = 0
        for name, offsets in self.offsets.items():
            offsets = offsets if isinstance(offsets, list) else [offsets]

            if offsets[0] in seen_offsets:
                raise RuntimeError(f'Duplicate offsets: {self.cls.__name__}.{name} and '
                                   f'{self.cls.__name__}.{seen_offsets[offsets[0]]} - {hex(offsets[0])}')

            seen_offsets[offsets[0]] = name
            self.offsets[name] = offsets
            field_indexes[name] = index
            index += 1

        # Parse types
        for name, t in self.cls.__annotations__.items():
            if name not in self.offsets:
                raise RuntimeError(f'Did not define offset for property: {self.cls.__name__}.{name}')

            # Create field
            field = _StructField(name, t, self, field_indexes[name])
            self.fields[name] = field

            # Create property for field
            prop = _StructProperty(field, field.getter, field.setter)
            setattr(self.cls, name, prop)

            # Pointers require an extra read with no offset to get the value pointed at by the address
            t = field.type
            while t and getattr(t, 'is_pointer', False):
                self.offsets[name].append(0x0)
                t = getattr(t, 'type', None)

    # This must be called after definitions have been sorted by dependency order
    def parse_size(self):
        for name, offsets in self.offsets.items():
            self.size = max(self.size, self.offsets[name][0] + self.fields[name].size)
        self.cls.size = max(self.cls.size, self.size)

    @staticmethod
    def is_struct_offset(value):
        return isinstance(value, int) or (isinstance(value, list) and all(isinstance(i, int) for i in value))

    @staticmethod
    def _update_with_dicts_of_bases(cls, arch, all_data, get_dict):
        for child in cls.__bases__:
            if StructMeta.is_struct(child):
                all_data.update(get_dict(StructMeta.struct(child, arch)))
                StructDefinition._update_with_dicts_of_bases(child, arch, all_data, get_dict)


# endregion

# region StructInfo

class StructInfo(object):
    def __init__(self):
        self.arch = 'all'
        self.line_defined = 0
        self.is_custom_type = False
        self.is_pod_type = False

    def __repr__(self):
        return f'StructInfo(' \
               f'arch={self.arch}' \
               f'custom={self.is_custom_type}, ' \
               f'POD={self.is_pod_type})'


# endregion

# region StructType

class StructType(object):

    LAZY_SIZE = -1

    def __init__(self, t, element_size=LAZY_SIZE, element_count=1, detect_type=True, *, container_type=None):
        self.type = t if not detect_type else StructType.detect(t)
        self.is_container = container_type is not None
        self.is_basic = StructType.is_basic_type(t) and not self.is_container
        self.is_pointer = element_size == cgh.ptr.Tag
        self.is_buffer_class = StructType.is_buffer_subclass(t)
        self.element_size = StructType.LAZY_SIZE if self.is_pointer else element_size
        self.element_count = element_count
        self.container_type = container_type

    def __str__(self):
        return self.name

    def __call__(self, *args, **kwargs):
        t = self.type

        if self.is_container:
            kwargs['type'] = self.type
            t = self.container_type
            args = (*args, self.element_count)

        elif self.is_buffer_class:
            args = (*args, self.element_size)

        return t(*args, **kwargs)

    def __eq__(self, other):
        if isinstance(other, StructType):
            return self.type == other.type
        elif self.is_basic and not self.is_container and not self.is_pointer and isinstance(other, type):
            return self.type == other
        else:
            return False

    @property
    def __name__(self):
        if isinstance(self.type, str):
            return StructType.from_string(self.type).name
        elif isinstance(self.type, StructType):
            return self.type.name
        else:
            return self.type.__name__

    @property
    def size(self):
        if self.element_size == StructType.LAZY_SIZE:
            if self.is_pointer:
                return _StructDefinitions.ptr_size
            else:
                # ptr and usize do not have the 'size' property defined at compile time
                element_size = getattr(self.type, 'size', _StructDefinitions.ptr_size)
                return element_size * self.element_count
        else:
            return (self.element_size or self.type.size) * self.element_count

    @property
    def name(self):
        if self.is_pointer:
            return f'ptr[{self.__name__}]'
        elif self.is_container:
            if self.element_count > 1:
                return f'{self.container_type.__name__}[{self.__name__}, {self.element_count}]'
            else:
                return f'{self.container_type.__name__}[{self.__name__}]'
        else:
            return self.__name__

    @staticmethod
    def is_buffer_subclass(cls):
        if isinstance(cls, StructType):
            return cls.is_buffer_class
        elif isinstance(cls, type):
            return any(issubclass(getattr(cgh, n, object), cls) for n in ['buf', 'p_buf', 'str', 'c_str'])
        return False

    @staticmethod
    def is_compound_type_tuple(typ: tuple):
        return len(typ) == 2 and (typ[1] == cgh.ptr.Tag or StructType.is_buffer_subclass(typ[0]))

    @staticmethod
    def is_primitive_class(cls):
        return hasattr(cgh, cls.__name__) and type(cls).__name__ == 'pybind11_type'

    @staticmethod
    def is_basic_type(t):
        if isinstance(t, tuple):
            return False
        elif isinstance(t, str):
            return hasattr(cgh, t)
        elif isinstance(t, StructType):
            return getattr(t, 'is_basic', False)
        elif isinstance(t, type) and (StructType.is_buffer_subclass(t) or StructType.is_primitive_class(t)):
            return True
        else:
            return False

    @staticmethod
    def detect(typ):
        # Forward definition
        if isinstance(typ, str):
            return StructType.from_string(typ)
        # Compound type from pygamehack.c
        elif isinstance(typ, tuple):
            return StructType.from_tuple(typ)
        # User-defined compound type
        elif isinstance(typ, StructType):
            return typ
        # Regular definition - buffer subclass with no size
        elif StructType.is_buffer_subclass(typ):
            # return StructType(typ, typ.size, 1, False)
            raise RuntimeError('Buffer variable definition incorrect, must include size')
        # Regular definition - basic type
        elif StructType.is_basic_type(typ):
            return StructType(typ, StructType.LAZY_SIZE, 1, False)
        # Regular definition - Struct
        else:
            return StructType(typ, StructType.LAZY_SIZE, 1, False)

    @staticmethod
    def from_tuple(typ: tuple):
        if len(typ) == 3:
            return StructType(typ[1], StructType.LAZY_SIZE, typ[2], container_type=typ[0])

        if not isinstance(typ, tuple) \
                or len(typ) != 2 \
                or not isinstance(typ[1], int):
            raise RuntimeError('StructType tuple must be in the form tuple(type: Any, size: int)')

        t, size = typ

        # Pointer to buffer
        if size == cgh.ptr.Tag \
                and StructType.is_buffer_subclass(t):
            raise RuntimeError('Forgot to provide size in buffer field')
        # Empty/un-sized buffer/buffer of pointers?
        elif StructType.is_buffer_subclass(t) \
                and (not size or size == cgh.ptr.Tag):
            raise RuntimeError('Forgot to provide size in buffer field')

        return StructType(t, size, 1, not StructType.is_basic_type(t))

    @staticmethod
    def from_string(typ: str):
        # Forward defined basic type
        if StructType.is_basic_type(typ):
            t = getattr(cgh, typ)
            return StructType(t, t.size, 1, False)
        # Forward defined Struct
        else:
            t = StructMeta.named(typ, _StructDefinitions.arch)
            if t is None:
                raise RuntimeError(f"Undefined struct used in forward declaration: '{typ}'")
            return StructType(t.cls, t.cls.size, 1)


# endregion

# region TypeWrapper

class TypeWrapper(type):
    """
    Metaclass used to create a helper for defining types that require other types and a size -> List[uint, 8]

    Usage:
        import pygamehack as gh

        class Wrapper(metaclass=gh.TypeWrapper):
            @classmethod
            def get_type(cls, t):
                return gh.StructType(t)

        class List(metaclass=gh.TypeWrapper):
            @classmethod
            def get_type(cls, t):
                return gh.StructType(t[0], element_size=StructType.LAZY_SIZE, element_count=t[1])

        class MyStruct(metaclass=gh.Struct):
            size   : Wrapper[gh.uint]  = 0x00
            values : List[gh.uint, 16] = 0x1C
    """

    @classmethod
    @abstractmethod
    def get_type(mcs, t):
        raise NotImplementedError

    def __getitem__(cls, t):
        return cls.get_type(t)

    # Called when a new TYPE is INSTANTIATED (where TYPE is defined, after this you can make instances of the TYPE)
    def __init__(cls, name, bases, attrs, **kwargs):
        assert hasattr(cls, 'get_type'), \
            f"Did not define the 'get_type' classmethod on '{cls.__name__}'"
        super().__init__(name, bases, attrs, **kwargs)


# endregion

# region _StructDefinitions

class _StructDefinitions(object):

    arch = 0
    ptr_size = 0
    to_define = []

    def __init__(self):
        self.defined = {}
        self.defined_by_name = {}
        self.dependencies = {}

    @staticmethod
    def defs(arch):
        return _defined_32 if arch == 32 else _defined_64

    @staticmethod
    def define_types(arch: int):
        assert arch == 32 or arch == 64, "Architecture must be 32 or 64"
        _StructDefinitions.ptr_size = 4 if arch == 32 else 8
        _StructDefinitions.arch = arch

        definitions = _StructDefinitions.defs(arch)

        for cls in _StructDefinitions.to_define:
            definition = definitions.defined[cls]
            definitions.defined_by_name[cls.__name__] = definition
            definitions.dependencies[cls.__name__] = definition.parse_dependencies()

        StructDependencies.sort(_StructDefinitions.to_define, definitions.dependencies,
                                 get_key=lambda t: t.__name__)

        for cls in _StructDefinitions.to_define:
            StructMeta.struct(cls, arch).parse_fields()

        for cls in _StructDefinitions.to_define:
            StructMeta.struct(cls, arch).parse_size()

        _StructDefinitions.ptr_size = 0
        _StructDefinitions.arch = 0

    @staticmethod
    def add_definitions_for_class(cls: 'StructMeta'):
        arches = [32, 64]
        defs = [StructDefinition(cls), StructDefinition(cls)]
        for d, arch in zip(defs, arches):
            _StructDefinitions.defs(arch).defined[cls] = d

    @staticmethod
    def configure_class(cls: 'StructMeta', attrs, kwargs):
        cls.__annotations__ = attrs.get('__annotations__', {})
        cls._info = getattr(cls, '_info', StructInfo())
        cls._info.line_defined = inspect.getouterframes(inspect.currentframe())[1].lineno  # gets line of class def
        cls._info.is_custom_type = kwargs.pop('custom', cls._info.is_custom_type)
        for arch in [32, 64]:
            offsets_from_attrs = {k: v for k, v in attrs.items() if StructDefinition.is_struct_offset(v)}
            StructMeta.struct(cls, arch).offsets.update(offsets_from_attrs)

    @staticmethod
    def check_dependencies_define(cls: 'StructMeta'):
        if not StructDependencies.has_unresolved(
                _StructDefinitions.to_define,
                get_key=lambda c: c.__name__,
                get_types=lambda c: c.__annotations__
        ):
            if cls._info.arch not in ['all', 'x86', 'x64']:
                raise RuntimeError(f"Invalid architecture: {cls._info.arch} - must be one of ['all', 'x86', 'x64']")

            if cls._info.arch == 'all' or cls._info.arch == 'x86':
                _StructDefinitions.define_types(32)

            if cls._info.arch == 'all' or cls._info.arch == 'x64':
                _StructDefinitions.define_types(64)

            _StructDefinitions.to_define.clear()


_defined_32 = _StructDefinitions()
_defined_64 = _StructDefinitions()


# endregion

# region _StructMethods

class _StructMethods(object):

    # TODO: Equality and hashing

    @staticmethod
    def init(self, address, *args, **kwargs):
        self.address = address
        self.variables = {}
        is_buffer_type = kwargs.get('buffer', False)

        StructMeta.check_buffer_view_kwargs(address, kwargs)

        arch = StructMeta.get_architecture_from_address_kwargs(address, kwargs)
        struct = StructMeta.struct(self.__class__, arch)
        if struct is None:
            raise RuntimeError("Struct is not defined. Since struct definition is automatic now we need a better error message here")

        self.size = struct.size
        self._getters = [None for _ in struct.fields]
        self._setters = [None for _ in struct.fields]

        if is_buffer_type:
            if 'offset_in_parent' in kwargs:
                self.buffer = cgh.buf(kwargs['parent_buffer'], kwargs['offset_in_parent'], struct.size)
            else:
                self.buffer = cgh.buf(address, struct.size)

        else:
            kwargs['parent_buffer'] = getattr(self, 'buffer', None)

            for name, field in struct.fields.items():
                self.variables[name] = _StructLazyField(field, kwargs)

    @staticmethod
    def read(self):
        if hasattr(self, 'buffer'):
            # TODO: Read nested buffers
            # print(self.buffer, self.buffer.get())
            self.buffer.get().read_from(self.address.value)
        return self

    @staticmethod
    def write(self, value):
        self_buffer = getattr(self, 'buffer', None)

        # Struct = [Struct, Struct<Buffer>, StructData]
        if self_buffer is None:
            for k, variable in self.variables.items():
                v = getattr(value, k)
                if value:
                    variable.write(v)
            return

        value_buffer = getattr(value, 'buffer', None)

        # Struct<Buffer> = Struct<Buffer>
        if value_buffer is not None:
            assert self_buffer.get().size == value_buffer.get().size, "Setting a buffer struct with a buffer struct of a different size"
            self_buffer.write(value_buffer.get())

        # Struct<Buffer> = [Struct, StructData]
        else:
            # Struct<Buffer> = Struct
            if StructMeta.is_struct(value):
                for k, variable in value.variables.items():
                    setattr(self, k, variable.read())

            # Struct<Buffer> = StructData
            else:
                for k in self.__class__.__annotations__:
                    v = getattr(value, k)
                    if v:
                        setattr(self, k, v)

    @staticmethod
    def flush(self):
        if not hasattr(self, 'buffer'):
            raise RuntimeError("'write_contents' can only be called on structs created with 'buffer=True'")
        # TODO: Write nested buffers
        self.buffer.get().write_to(self.address.value)

    @staticmethod
    def reset(self):
        buffer = getattr(self, 'buffer', None)
        if buffer is not None:
            buffer.clear()
        else:
            for v in self.variables.items():
                v.reset()

    @staticmethod
    def str(self):
        if getattr(self, 'address', None) is None:
            return self.__class__.__name__
        return f'{self.__class__.__name__}({cgh.Address.make_string(self.address.value, self.address.hack.process.arch)})'


# endregion

# region _StructField

class _StructLazyField(object):
    def __init__(self, field, kwargs):
        self.field = field
        self.kwargs = kwargs

    def __repr__(self):
        return f'LazyField[{self.field}]'

    def __bool__(self):
        return False


class _StructField(object):
    def __init__(self, name, typ, struct, index):
        self.name = name
        self.struct = struct
        self.index = index
        self.type = StructType.detect(typ)
        self.method_suffix = self.type.__name__

    @property
    def size(self):
        return self.type.size

    def __repr__(self):
        return self.type.__name__

    @property
    def getter(self):
        # Closure that creates a variable and getter function if it does not exist
        index = self.index

        def _get(instance):
            getter = instance._getters[index]
            if not getter:
                is_buffer_type = hasattr(instance, 'buffer')
                if not is_buffer_type and isinstance(instance.variables[self.name], _StructLazyField):
                    kwargs = instance.variables[self.name].kwargs
                    instance.variables[self.name] = self.create_field_variable(instance, kwargs)
                getter = self.create_struct_or_buffer_getter(instance, is_buffer_type)
                instance._getters[index] = getter
            return getter(instance)

        return _get

    @property
    def setter(self):
        # Closure that creates a variable and setter function if it does not exist
        index = self.index

        def _set(instance, value):
            setter = instance._setters[index]
            if not setter:
                is_buffer_type = hasattr(instance, 'buffer')
                if not is_buffer_type and isinstance(instance.variables[self.name], _StructLazyField):
                    kwargs = instance.variables[self.name].kwargs
                    instance.variables[self.name] = self.create_field_variable(instance, kwargs)
                setter = self.create_struct_or_buffer_setter(instance, is_buffer_type)
                instance._setters[index] = setter
            setter(instance, value)

        return _set

    def create_field_variable(self, instance, kwargs):
        kwargs['offset_in_parent'] = True
        field_kwargs = kwargs if StructMeta.is_struct(self.type) else {}
        address = None
        if getattr(instance, 'address', None) is not None:
            address = cgh.Address(instance.address, self.struct.offsets[self.name])
        return self.type(address, **field_kwargs)

    def create_struct_or_buffer_getter(self, instance, is_buffer_type):
        # Closure that reads from buffer memory for buffer-types and from a variable otherwise
        variable = instance.variables.get(self.name, None)
        if is_buffer_type and not variable:
            offset = self.struct.offsets[self.name][0]
            method = getattr(instance.buffer.get(), f'read_{self.method_suffix}')
            return lambda i: method(offset)
        return _StructField.create_variable_getter(variable, is_buffer_type)

    def create_struct_or_buffer_setter(self, instance, is_buffer_type):
        # Closure that writes to buffer memory for buffer-types and to a variable otherwise
        variable = instance.variables.get(self.name, None)
        if is_buffer_type and not variable:
            offset = self.struct.offsets[self.name][0]
            method = getattr(instance.buffer.get(), f'write_{self.method_suffix}')
            return lambda i, v: method(offset, v)
        return _StructField.create_variable_setter(variable)

    @staticmethod
    def create_variable_getter(variable, is_buffer):
        # Closure that loads the variable's address if it has not been loaded
        if is_buffer or isinstance(variable, cgh.arr) or isinstance(variable, cgh.c_arr):
            def _get(s):
                if not variable.address.loaded:
                    variable.address.load()
                return variable

            return _get

        else:
            def _get(s):
                if not variable.address.loaded:
                    variable.address.load()
                return variable.read()

            return _get

    @staticmethod
    def create_variable_setter(variable):
        # Closure that loads the variable's address if it has not been loaded
        def _set(s, v):
            if not variable.address.loaded:
                variable.address.load()

            variable.write(v)

            if isinstance(variable, cgh.str):
                variable.flush()

        return _set


# endregion

# region _StructProperty

class _StructProperty(property):
    def __init__(self, field, fget, fset):
        super().__init__(fget, fset, lambda: None, "")
        self.field = field
        self.dot_path = []

    @property
    def size(self):
        return self.field.size

    def __repr__(self):
        return f"Property({self.field.type.full_name})"

    @property
    def __doc__(self):
        return '\n'.join([_StructProperty.create_doc(f) for f in self._consume_dot_path()])

    def __getattribute__(self, item):
        if item in _StructProperty._custom_props:
            return super().__getattribute__(item)
        else:
            self.dot_path.append(self.field)
            t = self.field.type.unwrapped
            v = t.__getattribute__(t, item)
            if isinstance(v, _StructProperty):
                v.dot_path = self.dot_path
            return v

    def _consume_dot_path(self):
        path = [i for i in self.dot_path] + [self.field]
        self.dot_path.clear()
        return path

    @staticmethod
    def create_doc(field):
        return f'{field.struct.cls.__name__}.{field.name}: ' \
               f'{field.type.__name__} = ' \
               f'[{", ".join([cgh.Address.make_string(v) for v in field.struct.offsets[field.name]])}]'

    _custom_props = {
        'field', '__doc__', 'size', 'dot_path', '_consume_dot_path',
        "__class__", "__name__", "__bases__", "__mro__", "__module__", '__repr__'
    }


# endregion

# region StructDependencies

class StructDependencies:
    @staticmethod
    def has_unresolved(
            definitions,
            get_key=lambda v: v.__name__,
            get_types=lambda v: v.__annotations__
    ):
        ready = set()
        did_make_progress = True
        remaining = [c for c in definitions]

        while did_make_progress:
            did_make_progress = False

            for i, cls in enumerate(remaining):
                has_dependencies = False

                for t in get_types(cls).values():
                    if isinstance(t, str) and not hasattr(cgh, t) and t not in ready:
                        has_dependencies = True
                        break

                if has_dependencies:
                    continue
                else:
                    did_make_progress = True
                    remaining.pop(i)
                    ready.add(get_key(cls))
                    break

        # If any definitions contain unknown types, there are still unresolved dependencies
        remaining_names = set(get_key(v) for v in remaining)
        for cls in remaining:
            for t in get_types(cls).values():
                if isinstance(t, str) and not hasattr(cgh, t) and t not in ready and t not in remaining_names:
                    return True

        return False

    @staticmethod
    def sort(definitions, dependencies, get_key=lambda v: v.__name__):
        def get_score_single(dep, level=0, seen=None):
            seen = seen or set()
            score = level * 10000
            for d in dependencies.get(dep, set()):
                if d not in seen:
                    seen.add(d)
                    score += get_score_single(d, level + 1, seen)
            return score

        def get_score(k, i):
            if not dependencies.get(k, set()):
                return i
            return get_score_single(k) + i

        scores = {
            get_key(v): get_score(get_key(v), i) for i, v in enumerate(definitions)
        }

        definitions.sort(key=lambda v: scores[get_key(v)])

# endregion
