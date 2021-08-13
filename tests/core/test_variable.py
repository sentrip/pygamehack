import pygamehack as gh


def test_buffer_variable_getitem():
    assert gh.buf[8] == (gh.buf, 8)
    # assert gh.p_buf[8] == (gh.p_buf, 8)


# get/reset

#region Variable<Buffer>

# Buffer - create view/size/view tests
# Buffer - read/write/flush with size/offset
# Buffer - Nested read/write/flush with size/offset

#endregion

#region Variable<String>

# String - read/write/flush with strings
# String - slice/strlen

#endregion


"""
def test_variable_basic_read(hack, app):
    hack.attach(app.pid)

    assert gh.i8( gh.Address(hack, app.addr.int_types.value +  0)).read() == -15
    assert gh.i16(gh.Address(hack, app.addr.int_types.value +  2)).read() == -300
    assert gh.i32(gh.Address(hack, app.addr.int_types.value +  4)).read() == -2100000000
    assert gh.i64(gh.Address(hack, app.addr.int_types.value +  8)).read() == -10000000000
    assert gh.u8( gh.Address(hack, app.addr.int_types.value + 16)).read() == 15
    assert gh.u16(gh.Address(hack, app.addr.int_types.value + 18)).read() == 300
    assert gh.u32(gh.Address(hack, app.addr.int_types.value + 20)).read() == 2100000000
    assert gh.u64(gh.Address(hack, app.addr.int_types.value + 24)).read() == 10000000000


def test_variable_basic_write(hack, app, set_cleanup):
    hack.attach(app.pid)

    gh.i8( gh.Address(hack, app.addr.int_types.value +  0)).write(-15 + 5)
    gh.i16(gh.Address(hack, app.addr.int_types.value +  2)).write(-300 + 5)
    gh.i32(gh.Address(hack, app.addr.int_types.value +  4)).write(-2100000000 + 5)
    gh.i64(gh.Address(hack, app.addr.int_types.value +  8)).write(-10000000000 + 5)
    gh.u8( gh.Address(hack, app.addr.int_types.value + 16)).write(15 + 5)
    gh.u16(gh.Address(hack, app.addr.int_types.value + 18)).write(300 + 5)
    gh.u32(gh.Address(hack, app.addr.int_types.value + 20)).write(2100000000 + 5)
    gh.u64(gh.Address(hack, app.addr.int_types.value + 24)).write(10000000000 + 5)

    assert gh.i8( gh.Address(hack, app.addr.int_types.value +  0)).read() == -15 + 5
    assert gh.i16(gh.Address(hack, app.addr.int_types.value +  2)).read() == -300 + 5
    assert gh.i32(gh.Address(hack, app.addr.int_types.value +  4)).read() == -2100000000 + 5
    assert gh.i64(gh.Address(hack, app.addr.int_types.value +  8)).read() == -10000000000 + 5
    assert gh.u8( gh.Address(hack, app.addr.int_types.value + 16)).read() == 15 + 5
    assert gh.u16(gh.Address(hack, app.addr.int_types.value + 18)).read() == 300 + 5
    assert gh.u32(gh.Address(hack, app.addr.int_types.value + 20)).read() == 2100000000 + 5
    assert gh.u64(gh.Address(hack, app.addr.int_types.value + 24)).read() == 10000000000 + 5

    def cleanup():
        gh.i8( gh.Address(hack, app.addr.int_types.value +  0)).write(-15)
        gh.i16(gh.Address(hack, app.addr.int_types.value +  2)).write(-300)
        gh.i32(gh.Address(hack, app.addr.int_types.value +  4)).write(-2100000000)
        gh.i64(gh.Address(hack, app.addr.int_types.value +  8)).write(-10000000000)
        gh.u8( gh.Address(hack, app.addr.int_types.value + 16)).write(15)
        gh.u16(gh.Address(hack, app.addr.int_types.value + 18)).write(300)
        gh.u32(gh.Address(hack, app.addr.int_types.value + 20)).write(2100000000)
        gh.u64(gh.Address(hack, app.addr.int_types.value + 24)).write(10000000000)
    
    set_cleanup(cleanup)


def test_variable_buffer_read(hack, app):
    hack.attach(app.pid)

    variable = gh.buf(gh.Address(hack, app.addr.int_types.value), 32)

    buffer = variable.read()

    assert buffer.read_i8(  0) == -15
    assert buffer.read_i16( 2) == -300
    assert buffer.read_i32( 4) == -2100000000
    assert buffer.read_i64( 8) == -10000000000
    assert buffer.read_u8( 16) == 15
    assert buffer.read_u16(18) == 300
    assert buffer.read_u32(20) == 2100000000
    assert buffer.read_u64(24) == 10000000000


def test_variable_buffer_write(hack, app, set_cleanup):
    def cleanup():
        buffer.write_i8(  0, -15)
        buffer.write_i16( 2, -300)
        buffer.write_i32( 4, -2100000000)
        buffer.write_i64( 8, -10000000000)
        buffer.write_u8( 16, 15)
        buffer.write_u16(18, 300)
        buffer.write_u32(20, 2100000000)
        buffer.write_u64(24, 10000000000)

        variable.write(buffer)
        variable.flush()

    set_cleanup(cleanup)

    hack.attach(app.pid)

    variable = gh.buf(gh.Address(hack, app.addr.int_types.value), 32)

    buffer = variable.read()

    buffer.write_i8(  0, -15 + 5)
    buffer.write_i16( 2, -300 + 5)
    buffer.write_i32( 4, -2100000000 + 5)
    buffer.write_i64( 8, -10000000000 + 5)
    buffer.write_u8( 16, 15 + 5)
    buffer.write_u16(18, 300 + 5)
    buffer.write_u32(20, 2100000000 + 5)
    buffer.write_u64(24, 10000000000 + 5)

    variable.write(buffer)
    variable.flush()
    variable.read()

    assert buffer.read_i8(  0) == -15 + 5
    assert buffer.read_i16( 2) == -300 + 5
    assert buffer.read_i32( 4) == -2100000000 + 5
    assert buffer.read_i64( 8) == -10000000000 + 5
    assert buffer.read_u8( 16) == 15 + 5
    assert buffer.read_u16(18) == 300 + 5
    assert buffer.read_u32(20) == 2100000000 + 5
    assert buffer.read_u64(24) == 10000000000 + 5


# def test_variable_ptr_to_buffer_read(hack, app):
#     hack.attach(app.pid)
#
#     variable = gh.p_buf(gh.Address(hack, app.addr.ptr_types.marker), 32)
#
#     buffer = variable.read()
#
#     assert buffer.read_u32( 0) == app.marker_value
#     assert buffer.read_u32( 4) == 0
#
#
# def test_variable_ptr_to_buffer_write(hack, app, set_cleanup):
#     def cleanup():
#         buffer.write_u32(0, app.marker_value)
#         buffer.write_u32(4, 0)
#
#         variable.write(buffer)
#         variable.flush()
#
#     set_cleanup(cleanup)
#
#     hack.attach(app.pid)
#
#     variable = gh.p_buf(gh.Address(hack, app.addr.ptr_types.marker), 32)
#
#     buffer = variable.read()
#
#     assert buffer.read_u32( 0) == app.marker_value
#     assert buffer.read_u32( 4) == 0
#
#     buffer.write_u32(0, 10)
#     buffer.write_u32(4, 20)
#
#     variable.write(buffer)
#     variable.flush()
#     variable.read()
#
#     assert buffer.read_u32( 0) == 10
#     assert buffer.read_u32( 4) == 20
"""
