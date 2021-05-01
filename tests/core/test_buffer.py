import pygamehack as gh

# TODO: Test buffer read/write bool/float/double/ptr/usize


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
