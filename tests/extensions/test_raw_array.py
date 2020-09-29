import pytest
import pygamehack as gh
from pygamehack_extensions.raw_array import RawArray, RawArrayPod, RawArrayHackStruct


@pytest.fixture
def dynamic_addresses(arch):
    if arch == 32:
        return {
            'array': ('array', 'app', [0x40, 0x0]),
            'array_pod': ('array_pod', 'app', [0x58, 0x0]),
        }
    else:
        return {
            'array': ('array', 'app', [0x58, 0x0]),
            'array_pod': ('array_pod', 'app', [0x88, 0x0]),
        }


def test_read_write_basic_array(hack, program, static_addresses, dynamic_addresses, set_cleanup):
    app_a = hack.add_static_address(*static_addresses['app'])
    app_a.previous_holds_ptr = False  # Since 'App' is a static object, this is necessary unless defined as a buffer

    array_a = hack.add_dynamic_address(*dynamic_addresses['array'])
    array_v = RawArray(array_a, value_type=gh.uint32, size=17)

    def cleanup():
        nonlocal array_v
        array_v.write(list(range(17)))  # reset state for other tests
        array_v.write_contents()
    set_cleanup(cleanup)

    hack.attach()

    hack.load_addresses()

    array_v.read_contents()

    for i in range(17):
        assert array_v[i] == i

    for i in range(17):
        array_v[i] = 17 - i
        assert array_v[i] == 17 - i

    array_v.write_contents()
    array_v.read_contents()

    for i in range(17):
        assert array_v[i] == 17 - i

    array_v.write(list(range(16, -10, -1)))

    array_v.write_contents()
    array_v.read_contents()

    for i in range(17):
        assert array_v[i] == 16 - i


def test_read_write_pod_array(hack, program, static_addresses, dynamic_addresses, types, set_cleanup):
    app_a = hack.add_static_address(*static_addresses['app'])
    app_a.previous_holds_ptr = False  # Since 'App' is a static object, this is necessary unless defined as a buffer

    array_a = hack.add_dynamic_address(*dynamic_addresses['array_pod'])
    array_v = RawArrayPod(array_a, value_type=types.Level, size=7)

    def cleanup():
        nonlocal array_v
        for v in range(7):  # reset state for other tests
            array_v[v].id = 500 + 20 * v
        array_v.write_contents()
    set_cleanup(cleanup)

    hack.attach()

    hack.load_addresses()

    array_v.read_contents()

    for i in range(7):
        assert array_v[i].id == 500 + 20 * i

    for i in range(7):
        array_v[i].id = 200 + i
        assert array_v[i].id == 200 + i

    array_v.write_contents()
    array_v.read_contents()

    for i in range(7):
        assert array_v[i].id == 200 + i

    levels = [types.Level.dataclass() for _ in range(7)]
    for i, l in enumerate(levels):
        l.id = 100 + i * 5

    array_v.write(levels)

    array_v.write_contents()
    array_v.read_contents()

    for i in range(7):
        assert array_v[i].id == 100 + i * 5


# TODO: Test read write hackstruct array
