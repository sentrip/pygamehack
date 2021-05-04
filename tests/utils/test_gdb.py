import pytest
from pygamehack.gdb import GDB, Watch


# TODO: Test GDB remove and watch overflow

@pytest.fixture
def gdb_path():
    # TODO: Proper GDB path
    return 'C:\\MinGW\\bin\\gdb.exe'


# @pytest.mark.skip
def test_gdb(hack, app, gdb_path):
    hack.attach(app.pid)
    
    gdb = GDB(gdb_path)
    
    gdb.attach(hack.process.pid)

    previous, updated = 0, 1

    def assert_watch(watch, prev, upd, data):
        nonlocal previous, updated
        assert int(prev) == previous
        assert int(upd) == updated
        previous = (previous + 1) % 4
        updated = (updated + 1) % 4

    w = Watch('w1', app.addr.marker + 12, assert_watch)
    w.c_type = 'unsigned int'

    gdb.add_watch(w)
    
    with gdb.continue_wait():
        hack.write_u32(app.addr.marker + 8, 1)

    # with gdb.continue_wait():
    #     hack.write_u32(app.addr.marker + 8, 1)
    #
    # with gdb.continue_wait():
    #     hack.write_u32(app.addr.marker + 8, 1)
    #
    # with gdb.continue_wait():
    #     hack.write_u32(app.addr.marker + 8, 1)
    
    gdb.remove_watch(w)

    gdb.detach()
