import pygamehack as gh


def test_hack_attach_detach(app):
    hack = gh.Hack()

    # Unattached
    assert not hack.process.attached

    # Attach different ways
    for arg in [app.pid, app.program_name]:
        for read_only in [False, True]:
            hack.detach()
            hack.attach(arg, read_only=read_only)

            assert hack.process.attached
            assert hack.process.read_only == read_only
            assert hack.process.pid == app.pid

    # Attach/detach repeatedly
    hack.detach()
    for i in range(10):
        assert not hack.process.attached
        hack.attach(app.pid)
        assert hack.process.attached
        hack.detach()
        assert not hack.process.attached


def test_hack_find_strlen(hack, app):
    for addr in app.addr.roots:
        assert hack.find(app.values.Basic.i16, addr + app.offsets.Basic.i16, 32) == 0
        assert hack.find(app.values.Basic.i16, addr + app.offsets.Basic.i16 - 16, 32) == 16
        assert hack.strlen(addr + app.offsets.Basic.str) == len(app.values.Basic.str)


def test_hack_scan_type(hack, app):
    for addr in app.addr.roots:
        results = hack.scan(getattr(gh.MemoryScan, 'u' + str(app.arch))(
            app.values.Basic.ptr,
            addr - 64,
            128,
            max_results=1))

        assert len(results) == 1
        assert results[0] == addr + app.offsets.Basic.ptr

# TODO: Test Hack scan string/regex
# def test_hack_scan(hack, app):
#     pass

# TODO: Test Hack scan modify
# def test_hack_scan_modify(hack, app):
#     pass


"""
def test_hack_attach(hack, app):
    for item in [app.pid, app.program_name]:
        hack.attach(item)
        assert hack.process.attached
        assert hack.process.pid == app.pid
        assert hack.process.arch == (gh.Process.Arch.x64 if app.arch == 64 else gh.Process.Arch.x86)
        hack.detach()
        assert not hack.process.attached


def test_hack_read_basic(hack, app):
    hack.attach(app.pid)
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
    hack.attach(app.pid)
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
    hack.attach(app.pid)
    assert hack.read_string(app.addr.str_types.value, len("TestString")) == "TestString"
    assert hack.read_bytes(app.addr.str_types.value, len("TestString")) == b"TestString"


def test_hack_write_string(hack, app, set_cleanup):
    hack.attach(app.pid)
    
    hack.write_string(app.addr.str_types.value, "StringTest")
    
    assert hack.read_string(app.addr.str_types.value, len("StringTest")) == "StringTest"
    
    def cleanup():
        hack.write_string(app.addr.str_types.value, "TestString")
    
    set_cleanup(cleanup)


def test_hack_read_buffer(hack, app):
    hack.attach(app.pid)
    
    buffer = gh.Buffer(hack, len("TestString"))
    hack.read_buffer(app.addr.str_types.value, buffer)
    assert buffer.read_string() == "TestString"


def test_hack_write_buffer(hack, app, set_cleanup):
    hack.attach(app.pid)
    
    buffer = gh.Buffer(hack, len("StringTest"))
    buffer.write_string(0, "StringTest")

    hack.write_buffer(app.addr.str_types.value, buffer)
    
    assert hack.read_string(app.addr.str_types.value, len("StringTest")) == "StringTest"
    
    def cleanup():
        hack.write_string(app.addr.str_types.value, "TestString")

    set_cleanup(cleanup)


def test_hack_read_ptr(hack, app):
    hack.attach(app.pid)
    address = hack.read_ptr(app.addr.ptr_types.marker)
    assert hack.read_u32(address) == app.marker_value


def test_hack_write_ptr(hack, app, set_cleanup):
    hack.attach(app.pid)
    
    address = hack.read_ptr(app.addr.ptr_types.marker)
    hack.write_ptr(app.addr.ptr_types.marker, address + 4)

    assert hack.read_u32(hack.read_ptr(app.addr.ptr_types.marker)) == 0

    def cleanup():
        hack.write_ptr(app.addr.ptr_types.marker, address)

    set_cleanup(cleanup)


def test_hack_find(hack, app):
    hack.attach(app.pid)

    assert hack.find(-15, app.addr.int_types.value, 32) == 0
    assert hack.find(15, app.addr.int_types.value, 32) == 16
    assert hack.strlen(app.addr.str_types.value) == len("TestString")


def test_hack_scan_type(hack, app):
    hack.attach(app.pid)
    results = hack.scan(gh.MemoryScan.u32(
        app.marker_value,
        app.addr.int_types.value - 100000,
        32 + 10000000,
        max_results=1)
    )
    assert len(results) == 1
    assert results[0] == app.addr.marker
"""
