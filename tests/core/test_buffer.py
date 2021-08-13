import pygamehack as gh
import pytest


def test_buffer_create():
    hack = gh.Hack()

    # Owning
    buf1 = gh.Buffer(hack, 32)
    assert 32 == buf1.size

    assert 0 == buf1.read_u32(16)
    buf1.write_u32(16, 10)
    assert 10 == buf1.read_u32(16)

    # View
    buf2 = gh.Buffer(buf1, 16, 16)
    assert 16 == buf2.size

    assert 10 == buf2.read_u32(0)
    buf2.write_u32(0, 4)
    assert 4 == buf1.read_u32(16)
    assert 4 == buf2.read_u32(0)

    # Clear
    buf1.clear()
    assert 0 == buf1.read_u32(16)
    assert 0 == buf2.read_u32(0)


def test_buffer_create_incorrect():
    hack = gh.Hack()
    buf1 = gh.Buffer(hack, 32)

    # Buffer with size=0
    with pytest.raises(RuntimeError):
        buf2 = gh.Buffer(hack, 0)

    # View with size=0
    with pytest.raises(RuntimeError):
        buf2 = gh.Buffer(buf1, 16, 0)

    # View that exceeds memory range of parent
    with pytest.raises(RuntimeError):
        buf2 = gh.Buffer(buf1, 32, 16)

    with pytest.raises(RuntimeError):
        buf2 = gh.Buffer(buf1, 16, 32)

# read_from/write_to
# read_buffer/write_buffer
# read_string/write_string/strlen


"""
def test_buffer_read_basic(hack, app):
    hack.attach(app.pid)
    
    buffer = gh.Buffer(hack, 64)
    buffer.read_from(app.addr.int_types.value, buffer.size)
    
    assert buffer.read_i8(  0) == -15
    assert buffer.read_i16( 2) == -300
    assert buffer.read_i32( 4) == -2100000000
    assert buffer.read_i64( 8) == -10000000000
    assert buffer.read_u8( 16) == 15
    assert buffer.read_u16(18) == 300
    assert buffer.read_u32(20) == 2100000000
    assert buffer.read_u64(24) == 10000000000


def test_buffer_write(hack, app, set_cleanup):
    def cleanup():
        buffer.write_i8(0, -15)
        buffer.write_i16(2, -300)
        buffer.write_i32(4, -2100000000)
        buffer.write_i64(8, -10000000000)
        buffer.write_u8(16, 15)
        buffer.write_u16(18, 300)
        buffer.write_u32(20, 2100000000)
        buffer.write_u64(24, 10000000000)

        buffer.write_to(app.addr.int_types.value, buffer.size)

    set_cleanup(cleanup)

    hack.attach(app.pid)
    
    buffer = gh.Buffer(hack, 64)
    buffer.read_from(app.addr.int_types.value, buffer.size)

    buffer.write_i8(  0, -15 + 5)
    buffer.write_i16( 2, -300 + 5)
    buffer.write_i32( 4, -2100000000 + 5)
    buffer.write_i64( 8, -10000000000 + 5)
    buffer.write_u8( 16, 15 + 5)
    buffer.write_u16(18, 300 + 5)
    buffer.write_u32(20, 2100000000 + 5)
    buffer.write_u64(24, 10000000000 + 5)

    assert buffer.read_i8(  0) == (-15 + 5)
    assert buffer.read_i16( 2) == (-300 + 5)
    assert buffer.read_i32( 4) == (-2100000000 + 5)
    assert buffer.read_i64( 8) == (-10000000000 + 5)
    assert buffer.read_u8( 16) == (15 + 5)
    assert buffer.read_u16(18) == (300 + 5)
    assert buffer.read_u32(20) == (2100000000 + 5)
    assert buffer.read_u64(24) == (10000000000 + 5)


def test_buffer_read_string(hack, app):
    hack.attach(app.pid)
    
    buffer = gh.Buffer(hack, 64)
    buffer.read_from(app.addr.int_types.value, buffer.size)

    assert buffer.read_string(32, len("TestString")) == "TestString"
    assert buffer.read_bytes(32, len("TestString")) == b"TestString"


def test_buffer_write_string(hack, app, set_cleanup):
    def cleanup():
        buffer.write_string(32, "TestString")

        buffer.write_to(app.addr.int_types.value, buffer.size)

    set_cleanup(cleanup)

    hack.attach(app.pid)
    
    buffer = gh.Buffer(hack, 64)
    buffer.read_from(app.addr.int_types.value, buffer.size)
    
    buffer.write_string(32, "StringTest")
    assert buffer.read_string(32, len("StringTest")) == "StringTest"


def test_buffer_read_buffer(hack, app):
    hack.attach(app.pid)
    
    buffer = gh.Buffer(hack, 64)
    other_buffer = gh.Buffer(hack, len("TestString"))
    buffer.read_from(app.addr.int_types.value, buffer.size)

    buffer.read_buffer(32, other_buffer)
    assert other_buffer.read_string() == "TestString"


def test_buffer_write_buffer(hack, app):
    hack.attach(app.pid)
    
    buffer = gh.Buffer(hack, 64)
    other_buffer = gh.Buffer(hack, 32)
    buffer.read_from(app.addr.int_types.value, buffer.size)
    
    other_buffer.write_string(0, "StringTest")

    buffer.write_buffer(32, other_buffer)
    
    assert buffer.read_string(32, len("StringTest")) == "StringTest"
"""
