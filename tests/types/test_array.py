import pygamehack as gh
from pygamehack.types.array import Array

# TODO: Test array write


def test_array_type():
    assert Array[gh.int, 2].size == 8
    assert Array[gh.int, 2].name == 'Array[i32, 2]'

    assert Array[gh.ptr[gh.int], 2].size == 0
    assert Array[gh.ptr[gh.int], 2].name == 'Array[ptr[i32], 2]'

    assert Array[Array[gh.int, 2], 2].size == 16
    assert Array[Array[gh.int, 2], 2].name == 'Array[Array[i32, 2], 2]'

    assert Array[Array[gh.ptr[gh.int], 2], 2].size == 0
    assert Array[Array[gh.ptr[gh.int], 2], 2].name == 'Array[Array[ptr[i32], 2], 2]'


def test_variable_array_read_basic(hack, app):
    hack.attach(app.pid)

    variable = Array(gh.Address(hack, app.addr.marker), 4, type=gh.uint)

    assert variable[0] == 0

    variable.read()

    assert variable[0] == app.marker_value


# TODO: Better nested read test
def test_variable_array_read_nested(hack, app):
    hack.attach(app.pid)

    variable = Array(gh.Address(hack, app.addr.marker), 2, type=Array[gh.uint, 2])

    assert variable[0][0] == 0

    variable.read()

    assert variable[0][0] == app.marker_value
