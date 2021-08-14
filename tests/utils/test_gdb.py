import sys
import pytest
import pygamehack as gh
from pygamehack.gdb import GDB, Watch


# TODO: Test GDB remove and watch overflow


def pytest_generate_tests(metafunc):
    if "gdb" in metafunc.function.__name__:
        if metafunc.config.getoption("no_gdb"):
            pytest.skip('Skipping GDB test...')


@pytest.fixture
def gdb_path():
    if sys.platform == 'win32':
        return 'gdb.exe'
    # GDB should be installed on unix
    return None


def test_gdb(program_name, app_addresses, gdb_path):

    hack = gh.Hack()
    hack.attach(program_name)

    gdb = GDB(gdb_path)

    gdb.attach(hack.process.pid)

    previous, updated = 0, 1

    def assert_watch(watch, prev, upd, data):
        nonlocal previous, updated
        assert int(prev) == previous
        assert int(upd) == updated
        previous = (previous + 1) % 4
        updated = (updated + 1) % 4

    for i, addr in enumerate(app_addresses.roots):
        w = Watch('w' + str(i), addr + 8, assert_watch)
        w.c_type = 'unsigned int'

        gdb.add_watch(w)

        with gdb.continue_wait():
            hack.write_u32(addr + 8, 1)

        # with gdb.continue_wait():
        #     hack.write_u32(addr + 8, 1)
        #
        # with gdb.continue_wait():
        #     hack.write_u32(addr + 8, 1)
        #
        # with gdb.continue_wait():
        #     hack.write_u32(addr + 8, 1)

        gdb.remove_watch(w)

    gdb.detach()
