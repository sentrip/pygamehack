import pygamehack as gh


def test_array_type():
    assert gh.arr[gh.int, 2].size == 8
    assert gh.arr[gh.int, 2].name == 'arr[i32, 2]'

    assert gh.arr[gh.ptr[gh.int], 2].size == 0
    assert gh.arr[gh.ptr[gh.int], 2].name == 'arr[ptr[i32], 2]'

    assert gh.arr[gh.arr[gh.int, 2], 2].size == 16
    assert gh.arr[gh.arr[gh.int, 2], 2].name == 'arr[arr[i32, 2], 2]'

    assert gh.arr[gh.arr[gh.ptr[gh.int], 2], 2].size == 0
    assert gh.arr[gh.arr[gh.ptr[gh.int], 2], 2].name == 'arr[arr[ptr[i32], 2], 2]'


def test_variable_array_read_basic(hack, app):
    for addr in app.addr.roots:
        variable = gh.arr(gh.Address(hack, addr + app.offsets.Basic.arr), 4, type=gh.uint)

        for i in range(4):
            assert variable[0] == 0

        variable.read()

        for i in range(4):
            assert variable[i] == 4 - i


def test_variable_array_write_basic(hack, app, reset_app):
    for addr in app.addr.roots:
        variable = gh.arr(gh.Address(hack, addr + app.offsets.Basic.arr), 4, type=gh.uint)

        # Write - No flush
        variable.read()

        for i in range(4):
            variable[i] = i + 1

        for i in range(4):
            assert variable[i] == i + 1

        variable.read()

        for i in range(4):
            assert variable[i] == 4 - i

        # Write - Flush
        for i in range(4):
            variable[i] = i + 1

        variable.flush()
        variable.read()

        for i in range(4):
            assert variable[i] == i + 1

        # Write - List
        variable.write([4, 3, 2, 1])

        for i in range(4):
            assert variable[i] == 4 - i


"""
# TODO: Better nested read test
def test_variable_array_read_nested(hack, app):
    hack.attach(app.pid)

    variable = gh.arr(gh.Address(hack, app.addr.marker), 2, type=gh.arr[gh.uint, 2])

    assert variable[0][0] == 0

    variable.read()

    assert variable[0][0] == app.marker_value
"""
