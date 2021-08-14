import pytest
import pygamehack as gh


def test_variable_str_type():
    assert gh.str[32] == (gh.str, 32)


def test_variable_str_read(hack, app):
    for addr in app.addr.roots:
        variable = gh.str(gh.Address(hack, addr + app.offsets.Basic.str), 8)

        assert variable.read() == "TestStr"


def test_variable_str_write(hack, app, reset_app):
    for addr in app.addr.roots:
        variable = gh.str(gh.Address(hack, addr + app.offsets.Basic.str), 8)

        variable.write("StrTest")

        variable.flush()

        assert variable.read() == "StrTest"

        variable.reset()
        assert variable.get() == ""

        with pytest.raises(RuntimeError):
            variable.write("0" * 100)
