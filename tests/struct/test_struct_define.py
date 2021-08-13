import pytest
import pygamehack as gh


#region Read/Write

#region Helpers

def expected_value(value, value_offset):
    if isinstance(value, str):
        return value if not value_offset else value[:-1] + str(abs(value_offset))
    elif isinstance(value, list):
        return value if not value_offset else [i + value_offset for i in value]
    else:
        return value + value_offset


def assert_basic_value(app, obj, start_address, name, type_name, value_offset=0):
    method = getattr(obj, 'read_' + type_name)
    value = getattr(app.values.Basic, name)
    offset = getattr(app.offsets.Basic, name)
    addr = start_address + offset
    expected = expected_value(value, value_offset)
    assert method(addr) == expected, 'Basic.' + name


def write_basic_value(app, obj, start_address, name, type_name, value_offset):
    method = getattr(obj, 'write_' + type_name)
    value = getattr(app.values.Basic, name)
    offset = getattr(app.offsets.Basic, name)
    addr = start_address + offset
    expected = expected_value(value, value_offset)
    method(addr, expected)


def create_variable(app, hack, start_address, name, type_name):
    offset = getattr(app.offsets.Basic, name)
    address = gh.Address(hack, start_address + offset)

    kwargs = {}
    if type_name == 'string':
        type_name = 'str'
        args = (address, 8)
    elif type_name == 'arr':
        args = (address, 4)
        kwargs['type'] = gh.u32
    else:
        args = (address,)

    variable_type = getattr(gh, type_name)
    return variable_type(*args, **kwargs)


#endregion

#region Read

def test_hack_read(hack, app, basic_name_type_pairs):
    for name, type_name in basic_name_type_pairs:
        for addr in app.addr.roots:
            assert_basic_value(app, hack, addr, name, type_name)


def test_buffer_read(hack, app, basic_name_type_pairs):
    buffer = gh.Buffer(hack, app.sizes.Program)

    for name, type_name in basic_name_type_pairs:
        for addr in app.addr.roots:
            buffer.read_from(addr)
            assert_basic_value(app, buffer, 0, name, type_name)


def test_variable_read(hack, app, basic_name_type_pairs):
    for name, type_name in basic_name_type_pairs + [('arr', 'arr')]:
        for addr in app.addr.roots:
            variable = create_variable(app, hack, addr, name, type_name)
            assert variable.read() == getattr(app.values.Basic, name)


def test_struct_read(hack, app, default_structs, basic_name_type_pairs):
    for name, type_name in basic_name_type_pairs + [('arr', 'arr')]:
        for addr in app.addr.roots:
            struct = default_structs.Basic(gh.Address(hack, addr))
            value = getattr(struct, name)
            if name == 'arr':
                value.read()
            expected = expected_value(getattr(app.values.Basic, name), 0)
            assert value == expected, 'Basic.' + name


#endregion

#region Write

def test_hack_write(hack, app, reset_app, basic_name_type_pairs):
    for name, type_name in basic_name_type_pairs:
        for addr in app.addr.roots:
            write_basic_value(app, hack, addr, name, type_name, -1)
            assert_basic_value(app, hack, addr, name, type_name, -1)


def test_buffer_write(hack, app, reset_app, basic_name_type_pairs):
    buffer = gh.Buffer(hack, app.sizes.Program)

    for name, type_name in basic_name_type_pairs:
        for addr in app.addr.roots:
            buffer.read_from(addr)
            write_basic_value(app, buffer, 0, name, type_name, -1)
            assert_basic_value(app, buffer, 0, name, type_name, -1)


def test_variable_write(hack, app, reset_app, basic_name_type_pairs):
    for name, type_name in basic_name_type_pairs + [('arr', 'arr')]:
        for addr in app.addr.roots:
            variable = create_variable(app, hack, addr, name, type_name)
            value = getattr(app.values.Basic, name)
            expected = expected_value(value, -1)
            variable.write(expected)
            if isinstance(variable, gh.str) or isinstance(variable, gh.arr):
                variable.flush()
            assert variable.read() == expected


def test_struct_write(hack, app, reset_app, default_structs, basic_name_type_pairs):
    for name, type_name in basic_name_type_pairs + [('arr', 'arr')]:
        for addr in app.addr.roots:
            struct = default_structs.Basic(gh.Address(hack, addr))
            expected = expected_value(getattr(app.values.Basic, name), -1)
            setattr(struct, name, expected)
            if name == 'arr':
                struct.arr.flush()
            value = getattr(struct, name)
            assert value == expected, 'Basic.' + name


#endregion

#endregion

#region Correct

def test_define_ptr(arch, reset_structs):

    class Ptr(gh.Struct):
        depth1: gh.ptr[gh.u32] = 0x8
        depth2: gh.ptr[gh.ptr[gh.u32]] = 0x10
        depth3: gh.ptr[gh.ptr[gh.ptr[gh.u32]]] = 0x18
        depth4: gh.ptr[gh.ptr[gh.ptr[gh.ptr[gh.u32]]]] = 0x20

    assert gh.Struct.struct(Ptr, arch).offsets['depth1'] == [8, 0]
    assert gh.Struct.struct(Ptr, arch).offsets['depth2'] == [16, 0, 0]
    assert gh.Struct.struct(Ptr, arch).offsets['depth3'] == [24, 0, 0, 0]
    assert gh.Struct.struct(Ptr, arch).offsets['depth4'] == [32, 0, 0, 0, 0]


def test_define_struct_forward_declaration(hack, reset_structs):

    class Parent(gh.Struct):
        u32: 'u32' = 0x0
        child: 'Child' = 0x4

    class Child(gh.Struct):
        value: gh.u32 = 0x0

    parent = Parent(gh.Address(hack, 1))
    assert isinstance(parent.u32, int)
    assert isinstance(parent.child, Child)
    assert isinstance(parent.variables['u32'], gh.u32)
    assert isinstance(parent.variables['child'], Child)


def test_define_struct_circular_dependency(hack, reset_structs):

    class TypeA(gh.Struct):
        b: 'TypeB' = 0x0

    class TypeB(gh.Struct):
        a: 'TypeA' = 0x0

    a = TypeA(gh.Address(hack, 0))
    b = TypeB(gh.Address(hack, 0))

    assert isinstance(a.b, TypeB)
    assert isinstance(b.a, TypeA)


def test_struct_derived_class(arch, default_structs, reset_structs):
    class Derived(default_structs.Basic):
        pass

    base = gh.Struct.struct(default_structs.Basic, arch)
    derived = gh.Struct.struct(Derived, arch)

    assert derived.offsets == base.offsets
    for k in base.offsets:
        assert derived.fields[k].type == base.fields[k].type


def test_user_defined_struct_type(hack, reset_structs):

    class Wrapper(metaclass=gh.TypeWrapper):
        @classmethod
        def get_type(cls, t):
            return gh.StructType(t)

    class C1(gh.Struct):
        norm: Wrapper[gh.u32] = 0x0
        fwd: Wrapper['u32'] = 0x4

    parent = C1(gh.Address(hack, 1))
    assert isinstance(parent.norm, int)
    assert isinstance(parent.fwd, int)


#endregion

#region Incorrect

def test_define_struct_duplicate_offset(reset_structs):
    with pytest.raises(RuntimeError):
        class C1(gh.Struct):
            v0: gh.u32 = 0x4
            v1: gh.u32 = 0x4


def test_define_struct_no_offset(reset_structs):
    with pytest.raises(RuntimeError):
        class C1(gh.Struct):
            v: gh.u32


def test_define_struct_buffer_string_with_no_size_or_incorrect_size(reset_structs):
    with pytest.raises(RuntimeError):
        class C1(gh.Struct):
            v: gh.buf = 0x0

    with pytest.raises(RuntimeError):
        class C2(gh.Struct):
            v: gh.str = 0x0

    with pytest.raises(RuntimeError):
        class C3(gh.Struct):
            v: gh.buf[2.5] = 0x0

    with pytest.raises(RuntimeError):
        class C4(gh.Struct):
            v: gh.str[2.5] = 0x0


def test_define_array_no_type_type_size_or_incorrect_type_size(reset_structs):
    with pytest.raises(RuntimeError):
        class C1(gh.Struct):
            v: gh.arr[0] = 0x0

    with pytest.raises(RuntimeError):
        class C2(gh.Struct):
            v: gh.arr[gh.u32] = 0x0

    with pytest.raises(RuntimeError):
        class C3(gh.Struct):
            v: gh.arr[(0,)] = 0x0

    with pytest.raises(RuntimeError):
        class C4(gh.Struct):
            v: gh.arr[(gh.u32,)] = 0x0


#endregion


"""
def test_define_struct(hack, app, cleanup_struct_types):

    class IntTypes(gh.Struct):
        num_i8 : gh.i8  =  0
        num_i16: gh.i16 =  2
        num_i32: gh.i32 =  4
        num_i64: gh.i64 =  8
        num_u8 : gh.u8  = 16
        num_u16: gh.u16 = 18
        num_u32: gh.u32 = 20
        num_u64: gh.u64 = 24

    class TestProgram(gh.Struct):
        marker: gh.uint         = 0x0
        n     : IntTypes        = 0x10

    assert IntTypes.size == 32
    assert TestProgram.size == 48

    hack.attach(app.pid)
    n = IntTypes(gh.Address(hack, app.addr.int_types.value))
    t = TestProgram(gh.Address(hack, app.addr.marker))

    assert n.size == 32
    assert t.size == 48

    assert t.marker  == app.marker_value
    assert n.num_i8  == -15
    assert n.num_i16 == -300
    assert n.num_i32 == -2100000000
    assert n.num_i64 == -10000000000
    assert n.num_u8  == 15
    assert n.num_u16 == 300
    assert n.num_u32 == 2100000000
    assert n.num_u64 == 10000000000

    with pytest.raises(RuntimeError):
        TestProgram(None)


def test_define_struct_string_forward_declaration(hack, app, cleanup_struct_types):

    class TestProgram(gh.Struct):
        marker: 'uint'          = 0x0
        n     : 'IntTypes'      = 0x10

    class IntTypes(gh.Struct):
        num_i8 : 'i8'  =  0
        num_i16: 'i16' =  2
        num_i32: 'i32' =  4
        num_i64: 'i64' =  8
        num_u8 : 'u8'  = 16
        num_u16: 'u16' = 18
        num_u32: 'u32' = 20
        num_u64: 'u64' = 24

    assert IntTypes.size == 32
    assert TestProgram.size == 48

    hack.attach(app.pid)
    n = IntTypes(gh.Address(hack, app.addr.int_types.value))
    t = TestProgram(gh.Address(hack, app.addr.marker))

    assert n.size == 32
    assert t.size == 48

    assert t.marker  == app.marker_value
    assert n.num_i8  == -15
    assert n.num_i16 == -300
    assert n.num_i32 == -2100000000
    assert n.num_i64 == -10000000000
    assert n.num_u8  == 15
    assert n.num_u16 == 300
    assert n.num_u32 == 2100000000
    assert n.num_u64 == 10000000000
    


def test_define_struct_unnamed_buffer(hack, app, cleanup_struct_types):
    
    class TestProgram(gh.Struct):
        marker: 'uint'          = 0x0
        n     : gh.buf[32]      = 0x10

    hack.attach(app.pid)
    
    t = TestProgram(gh.Address(hack, app.addr.marker))
    
    assert t.size == 48

    assert t.n.read_i8(0) == -15


def test_define_struct_buffer_with_no_size(hack, app, cleanup_struct_types):
    with pytest.raises(RuntimeError):
        class TestProgram(gh.Struct):
            marker: 'uint'          = 0x0
            n     : gh.buf          = 0x10


def test_define_struct_inline_string(hack, app, cleanup_struct_types):

    class TestProgram(gh.Struct):
        marker: 'uint'          = 0x0
        s     : gh.str[32]      = 0x30

    hack.attach(app.pid)
    t = TestProgram(gh.Address(hack, app.addr.marker))

    assert t.size == 80

    assert t.s == "TestString"


def test_define_nested_ptr(hack, app, cleanup_struct_types):

    class TestS(gh.Struct):
        value: gh.ptr[gh.ptr['uint']] = 0x10

    assert gh.Struct.struct(TestS, app.arch).offsets['value'] == [16, 0, 0]


def test_user_defined_struct_type(hack, app, cleanup_struct_types):

    class Wrapper(metaclass=gh.TypeWrapper):
        @classmethod
        def get_type(cls, t):
            return gh.StructType(t)

    class TestProgram(gh.Struct):
        marker: Wrapper['uint'] = 0x0

    hack.attach(app.pid)
    ts = TestProgram(gh.Address(hack, app.addr.marker))

    assert ts.size == 4
    assert ts.marker == app.marker_value


def test_struct_derived_class(hack, app, cleanup_struct_types):
    class TestProgram(gh.Struct):
        marker: gh.uint = 0x0

    class TestProgramDerived(TestProgram):
        pass

    hack.attach(app.pid)
    t = TestProgram(gh.Address(hack, app.addr.marker))
    d = TestProgramDerived(gh.Address(hack, app.addr.marker))

    assert t.size == 4
    assert d.size == 4

    assert t.marker == app.marker_value
    assert d.marker == app.marker_value


def test_struct_pointer_to_struct(hack, app, cleanup_struct_types):

    class Game(gh.Struct):
        marker: gh.u64 = 0x8

    class TestProgram(gh.Struct):
        game: gh.ptr[Game] = 0x68

    hack.attach(app.pid)
    t = TestProgram(gh.Address(hack, app.addr.marker))

    print(t.game.marker)
"""
