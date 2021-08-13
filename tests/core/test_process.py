import pytest
import pygamehack as gh


def test_process_functionalities(app):
    hack = gh.Hack()

    # Unattached
    assert not hack.process.attached
    assert hack.process.arch == gh.Process.Arch.NONE
    assert hack.process.pid == 0

    # Read-Write
    hack.attach(app.pid)

    assert hack.process.attached
    assert not hack.process.read_only
    assert hack.process.arch == gh.Process.Arch.x86 if app.arch == 32 else gh.Process.Arch.x64
    assert hack.process.pid == app.pid
    assert hack.process.ptr_size == app.arch / 8
    assert hack.process.max_ptr == (0xffffffffffffffff >> (64 - app.arch))
    assert len(hack.process.modules) > 0
    assert app.program_name in hack.process.modules

    # Read only
    hack.detach()
    hack.attach(app.pid, read_only=True)

    assert hack.process.attached
    assert hack.process.read_only

    # Base modules
    assert hack.process.get_base_address(app.program_name) == hack.process.modules[app.program_name][0]

    with pytest.raises(RuntimeError):
        x = hack.process.get_base_address("SomeStupidModuleThatDoesntExist")

# TODO: Test process follow
# def test_process_follow(hack, app):
#     pass

# TODO: Test process follow
# def test_process_iter_regions(hack, app):
#     pass

# entry = gh.Process.entry_point("tests/test_program/" + app.program_name)


def test_process_protect(hack, app):
    for addr in app.addr.roots:
        addr_u32 = addr + app.offsets.Basic.u32
        with hack.process.protect(addr_u32, 4):
            assert hack.read_u32(addr_u32) == app.values.Basic.u32


def test_process_created_at(app):
    import time
    now = time.time()

    hack = gh.Hack()
    hack.attach(app.pid)

    assert gh.Process.created_at(app.pid) >= now

    hack.detach()


def test_process_iter(program_name):
    found = False
    for info in gh.Process.all():
        found = found or info.name == program_name
    assert found


def test_process_kill(program_name):
    import subprocess, time
    program = subprocess.Popen([f"tests/test_program/{program_name}"], stdout=subprocess.DEVNULL,
                               cwd='tests/test_program')

    hack = gh.Hack()
    hack.attach(program.pid)

    assert hack.process.attached

    gh.Process.kill(program.pid)

    time.sleep(0.01)

    assert not hack.process.attached


"""
def test_process_protect(hack, app):
    hack.attach(app.pid)
    with hack.process.protect(app.addr.marker, 4):
        assert hack.read_u32(app.addr.marker) == app.marker_value
"""
