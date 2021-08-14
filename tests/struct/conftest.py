import pytest
import pygamehack as gh


def get_default_structs(app_offsets):
    o = app_offsets.Basic

    class Basic(gh.Struct):
        i8: gh.i8 = o.i8
        i16: gh.i16 = o.i16
        i32: gh.i32 = o.i32
        i64: gh.i64 = o.i64
        u8: gh.u8 = o.u8
        u16: gh.u16 = o.u16
        u32: gh.u32 = o.u32
        u64: gh.u64 = o.u64
        b: gh.bool = o.b
        f: gh.float = o.f
        d: gh.double = o.d
        str: gh.str[8] = o.str
        arr: gh.arr[gh.u32, 4] = o.arr
        sz: gh.usize = o.sz
        ptr: gh.ptr = o.ptr

    o = app_offsets.Driver

    class Driver(gh.Struct):
        dinc: gh.u64 = o.dinc
        cnt: gh.u64 = o.cnt

    o = app_offsets.Program

    class Program(gh.Struct):
        basic: Basic = o.basic
        driver: Driver = o.driver

    class Dummy:
        pass

    structs = Dummy()
    structs.Basic = Basic
    structs.Driver = Driver
    structs.Program = Program
    return structs


@pytest.fixture
def default_structs(app_offsets):
    return get_default_structs(app_offsets)


"""
@pytest.fixture(scope='function')
def test_program_types(app):
    class Dummy:
        pass

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

    types = Dummy()
    types.TestProgram = TestProgram
    types.IntTypes = IntTypes

    yield types

    gh.Struct.clear_types()
"""
