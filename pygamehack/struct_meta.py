import inspect
from abc import ABCMeta, abstractmethod
import cpygamehack as cgh


# TODO: Child variable is buffer when parent is not buffer

# region StructMeta


class StructMeta(ABCMeta):
    """
    Metaclass for defining a struct-like object that reads from memory addresses

    Root struct usage:
        import pygamehack as gh

        class MyStruct(metaclass=gh.StructMeta):
            value_1: gh.uint = 0x1C

        gh.StructMeta.define_types()

    Nested struct usage:
        import pygamehack as gh

        class MyStructChild(metaclass=gh.StructMeta):  # Child
            value_1: gh.uint = 0x4
            value_2: gh.uint = [0x8, 0xC]

        class MyStructParent(metaclass=gh.StructMeta): # Parent
            my_struct: MyStructChild = 0x1C

        gh.StructMeta.define_types()
    """

    _to_define = []
    _defined = {}
    _defined_by_name = {}
    _dependencies = {}
    _arch = cgh.Process.Arch.NONE
    _ptr_size = 0

    @staticmethod
    def define_types(arch: int):
        assert arch == 32 or arch == 64, "Architecture must be 32 or 64"
        StructMeta._ptr_size = 4 if arch == 32 else 8
        StructMeta._arch = cgh.Process.Arch.x86 if arch == 32 else cgh.Process.Arch.x64

        already_defined = {}

        for cls in StructMeta._to_define:
            if cls in StructMeta._defined:
                already_defined[cls] = True
                continue

            definition = StructDefinition(cls)
            StructMeta._defined[cls] = definition
            StructMeta._defined_by_name[cls.__name__] = definition
            StructMeta._dependencies[cls.__name__] = definition.parse_dependencies()

        _sort_by_dependency(StructMeta._to_define, StructMeta._dependencies,
                            lambda t: t.__name__)

        for cls in StructMeta._to_define:
            if cls in already_defined:
                continue
            StructMeta.struct(cls).parse_fields()

        for cls in StructMeta._to_define:
            if cls in already_defined:
                continue
            StructMeta.struct(cls).parse_size()

        StructMeta._to_define.clear()
        StructMeta._ptr_size = 0
        StructMeta._arch = cgh.Process.Arch.NONE

    @staticmethod
    def clear_types():
        StructMeta._to_define.clear()
        StructMeta._defined.clear()
        StructMeta._defined_by_name.clear()
        StructMeta._dependencies.clear()

    @staticmethod
    def is_struct(struct):
        return hasattr(struct, '__is_struct_type') or hasattr(struct.__class__, '__is_struct_type')

    @staticmethod
    def struct(cls):
        return StructMeta._defined.get(cls, None)

    @staticmethod
    def named(name: str):
        return StructMeta._defined_by_name.get(name, None)

    @staticmethod
    def iter_variables(struct):
        if hasattr(struct, 'buffer'):
            definition = StructMeta._defined.get(struct.__class__, None)
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

    # Called when a new TYPE is DEFINED (before anything interesting happens)
    def __new__(mcs, name, bases, attrs, **kwargs):
        if name == 'Struct' or not kwargs.get('define', True):
            return super().__new__(mcs, name, bases, attrs)

        definition = {k: v for k, v in attrs.items() if StructDefinition.is_struct_offset(v) or k == '__init__'}
        definition['_info'] = StructInfo()
        definition['__is_struct_type'] = True  # dummy property used to detect struct types

        subclass = super().__new__(mcs, name, bases, definition)
        return subclass

    # Called when a new TYPE is INSTANTIATED (where TYPE is defined, after this you can make instances of the TYPE)
    def __init__(cls, name, bases, attrs, **kwargs):
        if name == 'Struct':
            super().__init__(name, bases, attrs)
            return

        StructMeta._to_define.append(cls)

        cls.__annotations__ = attrs.get('__annotations__', {})
        cls._info = getattr(cls, '_info', StructInfo())
        cls._info.offsets = {k: v for k, v in attrs.items() if StructDefinition.is_struct_offset(v)}
        cls._info.line_defined = inspect.getouterframes(inspect.currentframe())[1].lineno  # gets line of class def
        cls._info.is_custom_type = kwargs.pop('custom', cls._info.is_custom_type)

        if not cls._info.is_custom_type:
            cls.__init__ = StructMethods.init
            cls.__repr__ = StructMethods.repr
            cls.read = StructMethods.read
            cls.write = StructMethods.write
            cls.read_contents = StructMethods.read_contents
            cls.write_contents = StructMethods.write_contents
            cls.dataclass = lambda **kw: StructData.create(cls, **kw)

        super().__init__(name, bases, attrs, **kwargs)


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

        field_indexes = {}

        # Parse offsets
        index = 0
        for name, offsets in self.info.offsets.items():
            self.offsets[name] = offsets if isinstance(offsets, list) else [offsets]
            field_indexes[name] = index
            index += 1

        # Parse types
        for name, t in self.cls.__annotations__.items():
            # Create field
            field = StructField(name, t, self, field_indexes[name])
            self.fields[name] = field

            # Create property for field
            prop = StructProperty(field, field.getter, field.setter)
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


# endregion

# region StructInfo

class StructInfo(object):
    def __init__(self):
        self.architecture = StructMeta._arch
        self.line_defined = 0
        self.is_custom_type = False
        self.is_pod_type = False
        self.offsets = {}

    def __repr__(self):
        return f'StructInfo(' \
               f'{self.architecture}, ' \
               f'custom={self.is_custom_type}, ' \
               f'POD={self.is_pod_type})'


# endregion

# region StructMethods

class StructMethods(object):

    # TODO: Equality and hashing

    @staticmethod
    def init(self, address, *args, **kwargs):
        self.address = address
        self.variables = {}
        is_buffer_type = kwargs.get('buffer', False)

        if address is None:
            StructMethods._check_buffer_view_kwargs(kwargs)

        struct = StructMeta.struct(self.__class__)
        if struct is None:
            raise RuntimeError("Forgot to call Struct.define_types() before creating an instance of a Struct")

        self.size = struct.size
        self._getters = [None for _ in struct.fields]
        self._setters = [None for _ in struct.fields]

        if is_buffer_type:
            if 'offset_in_parent' in kwargs:
                self.buffer = cgh.Buffer(kwargs['parent_buffer'], kwargs['offset_in_parent'], struct.size)
            else:
                self.buffer = cgh.Buffer(address.hack, struct.size)

        else:
            kwargs['parent_buffer'] = getattr(self, 'buffer', None)

            for name, field in struct.fields.items():
                self.variables[name] = StructLazyField(field, kwargs)

    @staticmethod
    def read(self):
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
            assert self_buffer.size == value_buffer.size, "Setting a buffer struct with a buffer struct of a different size"
            self_buffer.write(value_buffer)

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
    def read_contents(self):
        self.buffer.read_from(self.address.value)
        return self

    @staticmethod
    def write_contents(self):
        self.buffer.write_to(self.address.value)

    @staticmethod
    def repr(self):
        if getattr(self, 'address', None) is None:
            return self.__class__.__name__
        return f'{self.__class__.__name__}({cgh.Address.make_string(self.address.value, self.address.hack.process.arch)})'

    @staticmethod
    def _check_buffer_view_kwargs(kwargs):
        if kwargs.get('buffer', False):
            raise RuntimeError('You must either create a Struct with an address or the following kwargs:\n'
                               "\t'buffer': bool = True\n"
                               "\t'parent_buffer': Buffer = <parent>\n"
                               "\t'offset_in_parent': <offset_in_parent>")
        if 'parent_buffer' not in kwargs:
            raise RuntimeError("Buffer view kwargs missing 'parent_buffer': Buffer")
        if 'offset_in_parent' not in kwargs:
            raise RuntimeError("Buffer view kwargs missing 'offset_in_parent': int")


# endregion

# region StructType

class StructType(object):

    LAZY_SIZE = -1

    def __init__(self, t, element_size=LAZY_SIZE, element_count=1, detect_type=True, *, container_type=None):
        self.type = t if not detect_type else StructType.detect(t)
        self.is_basic = StructType.is_basic_type(t)
        self.is_container = container_type is not None
        self.is_pointer = element_size == cgh.ptr.Tag
        self.is_buffer_class = StructType.is_buffer_subclass(t)
        self.element_size = StructType.LAZY_SIZE if self.is_pointer else element_size
        self.element_count = element_count
        self.container_type = container_type

    def __call__(self, *args, **kwargs):
        if self.is_buffer_class:
            return self.type(*args, self.element_size)
        elif self.is_container:
            return self.container_type(self.type, *args, **kwargs)
        elif StructType.is_basic_type(self.type):
            return self.type(*args)
        else:
            return self.type(*args, **kwargs)

    @property
    def __name__(self):
        return self.type if isinstance(self.type, str) else self.type.__name__

    @property
    def size(self):
        if self.element_size == StructType.LAZY_SIZE:
            if self.is_pointer:
                return StructMeta._ptr_size
            else:
                return self.type.size * self.element_count
        else:
            return (self.element_size or self.type.size) * self.element_count

    @property
    def name(self):
        if self.is_pointer:
            return f'ptr[{self.type.__name__}]'
        else:
            return self.type.__name__

    @staticmethod
    def is_buffer_subclass(cls):
        return cls is cgh.buf or (isinstance(cls, type) and issubclass(cls, cgh.buf))

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
            # Forward defined basic type
            if StructType.is_basic_type(typ):
                t = getattr(cgh, typ)
                return StructType(t, t.size, 1, False)
            # Forward defined Struct
            else:
                t = StructMeta.named(typ).cls
                return StructType(t, t.size, 1)
        # Compound type from cpygamehack
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
            return StructType(typ, typ.size, 1, False)
        # Regular definition - Struct
        else:
            return StructType(typ, typ.size, 1, False)

    @staticmethod
    def from_tuple(typ: tuple):
        if len(typ) == 2:
            t, size = typ
            if not isinstance(size, int):
                raise RuntimeError('StructType tuple must be in the form tuple(type: Any, size: int)')
            return StructType(t, size, 1, not StructType.is_basic_type(t))
        elif len(typ) == 3:
            c, t, size = typ
            if not isinstance(size, int):
                raise RuntimeError('StructType tuple must be in the form tuple(container: Any, type: Any, size: int)')
            return StructType(t, StructType.LAZY_SIZE, size, not StructType.is_basic_type(t))


# endregion

# region StructField

class StructLazyField(object):
    def __init__(self, field, kwargs):
        self.field = field
        self.kwargs = kwargs

    def __repr__(self):
        return f'LazyField[{self.field}]'


class StructField(object):
    def __init__(self, name, typ, struct, index):
        self.name = name
        self.struct = struct
        self.index = index
        self.type = StructType.detect(typ)
        # self.type = StructTypez.detect(typ)
        # self.method_suffix = self.type.type_name
        self.method_suffix = self.type.__name__

    @property
    def size(self):
        return self.type.size

    def __repr__(self):
        return self.type.__name__

    def __call__(self, *args, **kwargs):
        return self.type(*args, **kwargs)

    @property
    def getter(self):
        # Closure that creates a variable and getter function if it does not exist
        index = self.index

        def _get(instance):
            getter = instance._getters[index]
            if not getter:
                is_buffer_type = hasattr(instance, 'buffer')
                if not is_buffer_type and isinstance(instance.variables[self.name], StructLazyField):
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
                if not is_buffer_type and isinstance(instance.variables[self.name], StructLazyField):
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
            address = cgh.Address(instance.address, self.struct.offsets[self.name], True)
        return self.type(address, **field_kwargs)

    def create_struct_or_buffer_getter(self, instance, is_buffer_type):
        # Closure that reads from buffer memory for buffer-types and from a variable otherwise
        variable = instance.variables.get(self.name, None)
        if is_buffer_type and not variable:
            offset = self.struct.offsets[self.name][0]
            method = getattr(instance.buffer, f'read_{self.method_suffix}')
            return lambda i: method(offset)
        return StructField.create_variable_getter(variable, is_buffer_type)

    def create_struct_or_buffer_setter(self, instance, is_buffer_type):
        # Closure that writes to buffer memory for buffer-types and to a variable otherwise
        variable = instance.variables.get(self.name, None)
        if is_buffer_type and not variable:
            offset = self.struct.offsets[self.name][0]
            method = getattr(instance.buffer, f'write_{self.method_suffix}')
            return lambda i, v: method(offset, v)
        return StructField.create_variable_setter(variable)

    @staticmethod
    def create_variable_getter(variable, is_buffer):
        # Closure that loads the variable's address if it has not been loaded
        if is_buffer:
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
            return variable.write(v)

        return _set


# endregion

# region StructProperty

class StructProperty(property):
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
        return '\n'.join([StructProperty.create_doc(f) for f in self._consume_dot_path()])

    def __getattribute__(self, item):
        if item in StructProperty._custom_props:
            return super().__getattribute__(item)
        else:
            self.dot_path.append(self.field)
            t = self.field.type.unwrapped
            v = t.__getattribute__(t, item)
            if isinstance(v, StructProperty):
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

# region TypeHintContainer

class TypeHintContainer(type):
    """
    Metaclass used to create a helper for defining types that require other types and a size -> List[uint, 8]

    Usage:
        import pygamehack as gh

        class Wrapper(metaclass=gh.TypeHintContainer):
            @classmethod
            def get_container_type(mcs, t):
                return gh.StructType(t)

        class List(metaclass=gh.TypeHintContainer):
            @classmethod
            def get_container_type(mcs, t):
                return gh.StructType(t[0], element_size=StructType.LAZY_SIZE, element_count=t[1])

        class MyStruct(metaclass=gh.Struct):
            size   : Wrapper[gh.uint]  = 0x00
            values : List[gh.uint, 16] = 0x1C
    """

    @classmethod
    @abstractmethod
    def get_container_type(mcs, t):
        raise NotImplementedError

    def __getitem__(cls, t):
        return cls.get_container_type(t)

    # Called when a new TYPE is INSTANTIATED (where TYPE is defined, after this you can make instances of the TYPE)
    def __init__(cls, name, bases, attrs, **kwargs):
        assert hasattr(cls, 'get_container_type'), \
            f"Did not define the 'get_container_type' classmethod on '{cls.__name__}'"
        super().__init__(name, bases, attrs, **kwargs)


# endregion

# region Dependency Sort

def _sort_by_dependency(definitions, dependencies, get_key=lambda v: v.__name__):
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
