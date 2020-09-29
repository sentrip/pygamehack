import pytest
from pygamehack_extensions.raw_string import RawString, CRawString


@pytest.fixture
def dynamic_addresses(arch):
    if arch == 32:
        return {
            'string': ('string', 'app', [0x38, 0x0]),
            'const_string': ('const_string', 'app', [0x3C, 0x0]),
        }
    else:
        return {
            'string': ('string', 'app', [0x48, 0x0]),
            'const_string': ('const_string', 'app', [0x50, 0x0]),
        }


def test_read_write_raw_string(hack, program, static_addresses, dynamic_addresses, set_cleanup):
    app_a = hack.add_static_address(*static_addresses['app'])
    app_a.previous_holds_ptr = False  # Since 'App' is a static object, this is necessary unless defined as a buffer
    string_a = hack.add_dynamic_address(*dynamic_addresses['string'])
    const_string_a = hack.add_dynamic_address(*dynamic_addresses['const_string'])

    string_expected = 'My very nice dynamic string'
    const_string_expected = 'My very nice constant string'

    string_v = RawString(string_a)
    const_string_v = CRawString(const_string_a)

    def cleanup():
        nonlocal string_v
        string_v.write(string_expected)  # reset state for other tests
    set_cleanup(cleanup)

    hack.attach()

    hack.load_addresses()

    assert string_v.read() == string_expected

    assert const_string_v.read() == const_string_expected

    assert string_v[1] == 'y'

    string_v.write('something else')

    assert string_v.read() == 'something else'

    string_v[1] = 'q'

    assert string_v.read() == 'sqmething else'
