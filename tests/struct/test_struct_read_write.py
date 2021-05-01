import pygamehack as gh

# TODO: Test struct read/write bool/float/double/ptr/usize
# TODO: Test struct read/write with all things


def test_struct_read_basic(hack, app, test_program_types):
    n = test_program_types.IntTypes(gh.Address(hack, app.addr.int_types.value))
    t = test_program_types.TestProgram(gh.Address(hack, app.addr.marker))

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


def test_struct_read_buffer(hack, app, test_program_types):

    n = test_program_types.IntTypes(gh.Address(hack, app.addr.int_types.value), buffer=True)
    t = test_program_types.TestProgram(gh.Address(hack, app.addr.marker), buffer=True)

    assert n.size == 32
    assert t.size == 48

    hack.attach(app.pid)
    
    assert t.marker  == 0
    
    t.read()

    assert t.marker  == app.marker_value

    n.read()

    assert n.num_i8  == -15
    assert n.num_i16 == -300
    assert n.num_i32 == -2100000000
    assert n.num_i64 == -10000000000
    assert n.num_u8  == 15
    assert n.num_u16 == 300
    assert n.num_u32 == 2100000000
    assert n.num_u64 == 10000000000
