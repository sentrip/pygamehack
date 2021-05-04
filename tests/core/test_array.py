import pygamehack as gh

# TODO: Test array write


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
    hack.attach(app.pid)

    variable = gh.arr(gh.Address(hack, app.addr.marker), 4, type=gh.uint)

    assert variable[0] == 0

    variable.read()

    assert variable[0] == app.marker_value


# TODO: Better nested read test
def test_variable_array_read_nested(hack, app):
    hack.attach(app.pid)

    variable = gh.arr(gh.Address(hack, app.addr.marker), 2, type=gh.arr[gh.uint, 2])

    assert variable[0][0] == 0

    variable.read()

    assert variable[0][0] == app.marker_value
