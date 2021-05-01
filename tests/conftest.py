import pytest
import os
import time
import pygamehack as gh
import subprocess


def pytest_generate_tests(metafunc):
    if 'arch' in metafunc.fixturenames:
        metafunc.parametrize('arch', [32, 64], scope='session')


def get_program_name(arch):
    return f'TestProgram-{arch}.exe'


@pytest.fixture
def program_name(arch):
    return get_program_name(arch)


@pytest.fixture
def hack():
    hack = gh.Hack()
    return hack


@pytest.fixture(scope='session')
def program(arch):
    program = subprocess.Popen([f"tests/{get_program_name(arch)}"], stdout=subprocess.DEVNULL, cwd='tests/')
    yield program
    program.kill()


@pytest.fixture(scope='session')
def marker_address(arch, program):
    address_path = f"tests/MarkerAddress-{arch}.txt"
    total_time = 0
    while not os.path.exists(address_path):
        time.sleep(0.001)
        total_time += 0.001
        if total_time >= 0.1:
            raise RuntimeError("Did not generate address file")

    with open(address_path) as f:
        address = int(f.read())

    return address


@pytest.fixture
def app(arch, program, program_name, marker_address):
    class Dummy:
        pass
    
    a = Dummy()
    a.arch = arch
    a.pid = program.pid
    a.program_name = program_name
    a.program = program
    a.marker_value = 1234567898
    a.addr = Dummy()
    
    a.addr.entry = marker_address & 0xffffffffffff0000
    a.addr.entry_offset = marker_address & 0x000000000000ffff
    a.addr.marker = marker_address
    
    a.addr.int_types = Dummy()
    a.addr.int_types.value = marker_address + 16
    
    a.addr.str_types = Dummy()
    a.addr.str_types.value = marker_address + 16 + 32

    a.addr.ptr_types = Dummy()
    a.addr.ptr_types.value = marker_address + 16 + 64
    a.addr.ptr_types.marker = a.addr.ptr_types.value

    return a


@pytest.fixture
def set_cleanup():
    def cleanup_func():
        pass

    def _set(v):
        nonlocal cleanup_func
        cleanup_func = v

    yield _set

    cleanup_func()
