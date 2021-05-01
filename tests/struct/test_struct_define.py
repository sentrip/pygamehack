import pytest
import pygamehack as gh

# TODO: Test struct define nested types


@pytest.fixture
def cleanup_struct_types(set_cleanup):
    set_cleanup(lambda: gh.Struct.clear_types())


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

    gh.Struct.define_types(app.arch)

    assert IntTypes.size == 32
    assert TestProgram.size == 48

    n = IntTypes(gh.Address(hack, app.addr.int_types.value))
    t = TestProgram(gh.Address(hack, app.addr.marker))

    assert n.size == 32
    assert t.size == 48

    hack.attach(app.pid)

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

    gh.Struct.define_types(app.arch)
    
    assert IntTypes.size == 32
    assert TestProgram.size == 48

    n = IntTypes(gh.Address(hack, app.addr.int_types.value))
    t = TestProgram(gh.Address(hack, app.addr.marker))

    assert n.size == 32
    assert t.size == 48

    hack.attach(app.pid)

    assert t.marker  == app.marker_value
    assert n.num_i8  == -15
    assert n.num_i16 == -300
    assert n.num_i32 == -2100000000
    assert n.num_i64 == -10000000000
    assert n.num_u8  == 15
    assert n.num_u16 == 300
    assert n.num_u32 == 2100000000
    assert n.num_u64 == 10000000000
    

def test_define_struct_circular_dependency(hack, app, cleanup_struct_types):

    class TypeA(gh.Struct):
        b: 'TypeB' = 0x0

    class TypeB(gh.Struct):
        a: 'TypeA' = 0x0

    gh.Struct.define_types(app.arch)
    
    a = TypeA(gh.Address(hack, 0))
    b = TypeB(gh.Address(hack, 0))

    assert isinstance(a.b, TypeB)
    assert isinstance(b.a, TypeA)


def test_define_struct_unnamed_buffer(hack, app, cleanup_struct_types):
    
    class TestProgram(gh.Struct):
        marker: 'uint'          = 0x0
        n     : gh.buf[32]      = 0x10
        
    gh.Struct.define_types(app.arch)
    
    hack.attach(app.pid)
    
    t = TestProgram(gh.Address(hack, app.addr.marker))
    
    assert t.size == 48

    assert t.n.read_i8(0) == -15


def test_define_struct_buffer_with_no_size(hack, app, cleanup_struct_types):

    class TestProgram(gh.Struct):
        marker: 'uint'          = 0x0
        n     : gh.buf          = 0x10

    with pytest.raises(RuntimeError):
        gh.Struct.define_types(app.arch)


def test_define_struct_inline_string(hack, app, cleanup_struct_types):

    class TestProgram(gh.Struct):
        marker: 'uint'          = 0x0
        s     : gh.str[32]      = 0x30

    gh.Struct.define_types(app.arch)

    hack.attach(app.pid)
    t = TestProgram(gh.Address(hack, app.addr.marker))
    
    assert t.size == 80

    assert t.s == "TestString"


def test_define_nested_ptr(hack, app, cleanup_struct_types):

    class TestS(gh.Struct):
        value: gh.ptr[gh.ptr['uint']] = 0x10

    gh.Struct.define_types(app.arch)

    assert gh.Struct.struct(TestS).offsets['value'] == [16, 0, 0]


def test_user_defined_struct_type(hack, app, cleanup_struct_types):

    class Wrapper(metaclass=gh.TypeWrapper):
        @classmethod
        def get_type(mcs, t):
            return gh.StructType(t)

    class TestProgram(gh.Struct):
        marker: Wrapper['uint'] = 0x0

    gh.Struct.define_types(app.arch)

    hack.attach(app.pid)
    ts = TestProgram(gh.Address(hack, app.addr.marker))

    assert ts.size == 4
    assert ts.marker == app.marker_value
