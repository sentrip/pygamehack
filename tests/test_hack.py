import pytest
import pygamehack as gh


# TODO: Test Hack methods


def test_iter_addresses():
    hack = gh.Hack('Test')

    hack.add_static_address('s1', 'S1', 0x1)
    hack.add_static_address('s2', 'S2', 0x2)
    hack.add_dynamic_address('d1', 's1', [0x1])
    hack.add_dynamic_address('d2', 's2', [0x2])

    for address, name in zip(hack.addresses(), ['s1', 's2', 'd1', 'd2']):
        assert address.name == name
