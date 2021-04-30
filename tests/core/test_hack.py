import pygamehack as gh


# TODO: Test iter regions
# TODO: Test arbitrary regex scan


def test_hack_attach(hack, app):
    hack.attach(app.program_name)
    assert hack.process.attached
    assert hack.process.pid > 0
    assert hack.process.arch == (gh.Process.Arch.x64 if app.arch == 64 else gh.Process.Arch.x86)
    hack.detach()
    assert not hack.process.attached


def test_hack_protect(hack, app):
    hack.attach(app.program_name)
    with hack.process.protect(app.addr.marker, 4):
        assert hack.read_u32(app.addr.marker) == app.marker_value


def test_hack_read_basic(hack, app):
    hack.attach(app.program_name)
    assert hack.read_u32(app.addr.marker) == app.marker_value
    assert hack.read_i8( app.addr.int_types.value +  0) == -15
    assert hack.read_i16(app.addr.int_types.value +  2) == -300
    assert hack.read_i32(app.addr.int_types.value +  4) == -2100000000
    assert hack.read_i64(app.addr.int_types.value +  8) == -10000000000
    assert hack.read_u8( app.addr.int_types.value + 16) == 15
    assert hack.read_u16(app.addr.int_types.value + 18) == 300
    assert hack.read_u32(app.addr.int_types.value + 20) == 2100000000
    assert hack.read_u64(app.addr.int_types.value + 24) == 10000000000


def test_hack_write_basic(hack, app, set_cleanup):
    hack.attach(app.program_name)
    hack.write_i8( app.addr.int_types.value +  0, -15 + 5)
    hack.write_i16(app.addr.int_types.value +  2, -300 + 5)
    hack.write_i32(app.addr.int_types.value +  4, -2100000000 + 5)
    hack.write_i64(app.addr.int_types.value +  8, -10000000000 + 5)
    hack.write_u8( app.addr.int_types.value + 16, 15 + 5)
    hack.write_u16(app.addr.int_types.value + 18, 300 + 5)
    hack.write_u32(app.addr.int_types.value + 20, 2100000000 + 5)
    hack.write_u64(app.addr.int_types.value + 24, 10000000000 + 5)

    assert hack.read_i8( app.addr.int_types.value +  0) == (-15 + 5)
    assert hack.read_i16(app.addr.int_types.value +  2) == (-300 + 5)
    assert hack.read_i32(app.addr.int_types.value +  4) == (-2100000000 + 5)
    assert hack.read_i64(app.addr.int_types.value +  8) == (-10000000000 + 5)
    assert hack.read_u8( app.addr.int_types.value + 16) == (15 + 5)
    assert hack.read_u16(app.addr.int_types.value + 18) == (300 + 5)
    assert hack.read_u32(app.addr.int_types.value + 20) == (2100000000 + 5)
    assert hack.read_u64(app.addr.int_types.value + 24) == (10000000000 + 5)

    def cleanup():
        hack.write_i8( app.addr.int_types.value +  0, -15)
        hack.write_i16(app.addr.int_types.value +  2, -300)
        hack.write_i32(app.addr.int_types.value +  4, -2100000000)
        hack.write_i64(app.addr.int_types.value +  8, -10000000000)
        hack.write_u8( app.addr.int_types.value + 16, 15)
        hack.write_u16(app.addr.int_types.value + 18, 300)
        hack.write_u32(app.addr.int_types.value + 20, 2100000000)
        hack.write_u64(app.addr.int_types.value + 24, 10000000000)

    set_cleanup(cleanup)


def test_hack_read_string(hack, app):
    hack.attach(app.program_name)
    assert hack.read_string(app.addr.str_types.value, len("TestString")) == "TestString"
    assert hack.read_bytes(app.addr.str_types.value, len("TestString")) == b"TestString"


def test_hack_write_string(hack, app, set_cleanup):
    hack.attach(app.program_name)
    
    hack.write_string(app.addr.str_types.value, "StringTest")
    
    assert hack.read_string(app.addr.str_types.value, len("StringTest")) == "StringTest"
    
    def cleanup():
        hack.write_string(app.addr.str_types.value, "TestString")
    
    set_cleanup(cleanup)


def test_hack_read_buffer(hack, app):
    hack.attach(app.program_name)
    
    buffer = gh.Buffer(hack, len("TestString"))
    hack.read_buffer(app.addr.str_types.value, buffer)
    assert buffer.read_string() == "TestString"


def test_hack_write_buffer(hack, app, set_cleanup):
    hack.attach(app.program_name)
    
    buffer = gh.Buffer(hack, len("StringTest"))
    buffer.write_string(0, "StringTest")

    hack.write_buffer(app.addr.str_types.value, buffer)
    
    assert hack.read_string(app.addr.str_types.value, len("StringTest")) == "StringTest"
    
    def cleanup():
        hack.write_string(app.addr.str_types.value, "TestString")

    set_cleanup(cleanup)


def test_hack_read_ptr(hack, app):
    hack.attach(app.program_name)
    address = hack.read_ptr(app.addr.ptr_types.marker)
    assert hack.read_u32(address) == app.marker_value


def test_hack_write_ptr(hack, app, set_cleanup):
    hack.attach(app.program_name)
    
    address = hack.read_ptr(app.addr.ptr_types.marker)
    hack.write_ptr(app.addr.ptr_types.marker, address + 4)

    assert hack.read_u32(hack.read_ptr(app.addr.ptr_types.marker)) == 0

    def cleanup():
        hack.write_ptr(app.addr.ptr_types.marker, address)

    set_cleanup(cleanup)


def test_hack_find(hack, app):
    hack.attach(app.program_name)

    assert hack.find(-15, app.addr.int_types.value, 32) == 0
    assert hack.find(15, app.addr.int_types.value, 32) == 16
    assert hack.strlen(app.addr.str_types.value) == len("TestString")


def test_hack_scan_type(hack, app):
    hack.attach(app.program_name)

    results = hack.scan_u32(app.marker_value, app.addr.int_types.value - 100000, 32 + 10000000, 1)
    assert len(results) == 1
    assert results[0] == app.addr.marker
