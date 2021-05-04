import pytest
import pygamehack as gh


def test_variable_str_type():
    assert gh.str[32] == (gh.str, 32)


def test_variable_str_read(hack, app):
    hack.attach(app.pid)

    variable = gh.str(gh.Address(hack, app.addr.int_types.value + 32), 32)

    assert variable.read() == "TestString"


def test_variable_str_write(hack, app, set_cleanup):
    def cleanup():
        variable.write("TestString")
        variable.flush()

    set_cleanup(cleanup)

    hack.attach(app.pid)

    variable = gh.str(gh.Address(hack, app.addr.int_types.value + 32), 32)

    variable.write("StringTest")

    variable.flush()

    assert variable.read() == "StringTest"

    variable.reset()
    assert variable.get() == ""

    with pytest.raises(RuntimeError):
        variable.write("0" * 100)
