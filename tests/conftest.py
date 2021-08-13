import pytest
import os
import time
import pygamehack as gh
import subprocess

class Dummy:
    pass


def pytest_generate_tests(metafunc):
    if 'arch' in metafunc.fixturenames:
        metafunc.parametrize('arch', [32, 64], scope='session')


def get_program_name(arch):
    return f'TestProgram-{arch}.exe'


@pytest.fixture
def set_cleanup():
    def cleanup_func():
        pass

    def _set(v):
        nonlocal cleanup_func
        cleanup_func = v

    yield _set

    cleanup_func()


@pytest.fixture(scope='session')
def program_name(arch):
    return get_program_name(arch)


@pytest.fixture(scope='session')
def program(arch):
    program = subprocess.Popen([f"tests/test_program/{get_program_name(arch)}"], stdout=subprocess.DEVNULL, cwd='tests/test_program')
    yield program
    program.kill()


@pytest.fixture(scope='session')
def marker_address_file(arch, program):
    address_path = f"tests/test_program/MarkerAddress-{arch}.txt"
    total_time = 0
    while not os.path.exists(address_path):
        time.sleep(0.001)
        total_time += 0.001
        if total_time >= 1.0:
            raise RuntimeError("Did not generate address file")
    return address_path


@pytest.fixture(scope='session')
def marker_address(marker_address_file):
    with open(marker_address_file) as f:
        address = int(f.read())
    return address


def get_basic_name_type_pairs():
    return [
        ('i8', 'i8'), ('i16', 'i16'), ('i32', 'i32'), ('i64', 'i64'),
        ('u8', 'u8'), ('u16', 'u16'), ('u32', 'u32'), ('u64', 'u64'),
        ('b', 'bool'), ('f', 'float'), ('d', 'double'),
        ('str', 'string'), ('sz', 'usize'), ('ptr', 'ptr')
    ]


def get_app_offsets():
    offsets = Dummy()

    offsets.static = 32768 # TODO: Find out how the static program is layout out in memory

    offsets.Basic = Dummy()
    offsets.Driver = Dummy()
    offsets.Program = Dummy()

    offsets.Basic.i8 = 0x0
    offsets.Basic.i16 = 0x8
    offsets.Basic.i32 = 0x10
    offsets.Basic.i64 = 0x18
    offsets.Basic.u8 = 0x20
    offsets.Basic.u16 = 0x28
    offsets.Basic.u32 = 0x30
    offsets.Basic.u64 = 0x38
    offsets.Basic.b = 0x40
    offsets.Basic.f = 0x48
    offsets.Basic.d = 0x50
    offsets.Basic.str = 0x58
    offsets.Basic.arr = 0x60
    offsets.Basic.sz = 0x70
    offsets.Basic.ptr = 0x78

    offsets.Driver.dinc = 0x0
    offsets.Driver.cnt = 0x8

    offsets.Program.basic = 0
    offsets.Program.driver = 0x80

    return offsets


def get_default_structs():
    offsets = get_app_offsets()
    o = offsets.Basic

    class Basic(gh.Struct):
        i8: gh.i8 = o.i8
        i16: gh.i16 = o.i16
        i32: gh.i32 = o.i32
        i64: gh.i64 = o.i64
        u8: gh.u8 = o.u8
        u16: gh.u16 = o.u16
        u32: gh.u32 = o.u32
        u64: gh.u64 = o.u64
        b: gh.bool = o.b
        f: gh.float = o.f
        d: gh.double = o.d
        str: gh.str[8] = o.str
        arr: gh.arr[gh.u32, 4] = o.arr
        sz: gh.usize = o.sz
        ptr: gh.ptr = o.ptr

    o = offsets.Driver

    class Driver(gh.Struct):
        dinc: gh.u64 = o.dinc
        cnt: gh.u64 = o.cnt

    o = offsets.Program

    class Program(gh.Struct):
        basic: Basic = o.basic
        driver: Driver = o.driver

    structs = Dummy()
    structs.Basic = Basic
    structs.Driver = Driver
    structs.Program = Program
    return structs


@pytest.fixture
def basic_name_type_pairs():
    return get_basic_name_type_pairs()


@pytest.fixture
def default_structs():
    return get_default_structs()


@pytest.fixture
def reset_structs(set_cleanup):
    set_cleanup(lambda: gh.Struct.clear_types())


@pytest.fixture(scope='session')
def app_addresses(marker_address_file):
    with open(marker_address_file) as f:
        static, stack, heap = tuple(int(v) for v in f.read().split(','))

    addresses = Dummy()
    addresses.root = Dummy()

    addresses.root.static = static
    addresses.root.stack = stack
    addresses.root.heap = heap
    addresses.roots = [static, stack, heap]

    yield addresses

    os.remove(marker_address_file)


@pytest.fixture(scope='session')
def app_type_sizes():
    sizes = Dummy()
    sizes.Basic = 128
    sizes.Driver = 16
    sizes.Program = 128 + 16
    return sizes


@pytest.fixture(scope='session')
def app_offsets():
    return get_app_offsets()


@pytest.fixture(scope='session')
def app_values():
    values = Dummy()

    value = 0b10100101
    value_f = 4.0
    value_ptr = 0xdeadbeef
    str8 = 'TestStr'

    values.Basic = Dummy()
    values.Basic.i8 = 3
    values.Basic.i16 = value
    values.Basic.i32 = value
    values.Basic.i64 = value
    values.Basic.u8 = value
    values.Basic.u16 = value
    values.Basic.u32 = value
    values.Basic.u64 = value
    values.Basic.b = True
    values.Basic.f = value_f
    values.Basic.d = value_f
    values.Basic.str = str8
    values.Basic.arr = [4, 3, 2, 1]
    values.Basic.sz = value
    values.Basic.ptr = value_ptr

    return values


@pytest.fixture(scope='session')
def app_default_memory():
    return b'\x03\x00\x00\x00\x00\x00\x00\x00\xa5\x00\x00\x00\x00\x00\x00\x00' \
           b'\xa5\x00\x00\x00\x00\x00\x00\x00\xa5\x00\x00\x00\x00\x00\x00\x00' \
           b'\xa5\x00\x00\x00\x00\x00\x00\x00\xa5\x00\x00\x00\x00\x00\x00\x00' \
           b'\xa5\x00\x00\x00\x00\x00\x00\x00\xa5\x00\x00\x00\x00\x00\x00\x00' \
           b'\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x80@\x00\x00\x00\x00' \
           b'\x00\x00\x00\x00\x00\x00\x10@TestStr\x00' \
           b'\x04\x00\x00\x00\x03\x00\x00\x00\x02\x00\x00\x00\x01\x00\x00\x00' \
           b'\xa5\x00\x00\x00\x00\x00\x00\x00\xef\xbe\xad\xde\x00\x00\x00\x00' \
           b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'


@pytest.fixture(scope='session')
def app(arch, program, program_name, app_addresses, app_type_sizes, app_offsets, app_values, app_default_memory):
    app = Dummy()

    app.arch = arch
    app.pid = program.pid
    app.program_name = program_name
    app.default_memory = app_default_memory

    app.addr = app_addresses
    app.offsets = app_offsets
    app.sizes = app_type_sizes
    app.values = app_values

    return app


@pytest.fixture
def hack(app):
    hack = gh.Hack()
    hack.attach(app.pid)
    yield hack
    hack.detach()


@pytest.fixture
def reset_app(hack, app, app_default_memory):
    yield
    for addr in app.addr.roots:
        hack.write_string(addr, app_default_memory)


"""
@pytest.fixture
def hack():
    hack = gh.Hack()
    return hack


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
"""