import pytest
import pygamehack as gh
from pygamehack_utils import HackStruct, Ptr
from pygamehack_utils.hackstruct import HackStructMeta
import subprocess


def pytest_generate_tests(metafunc):
    if 'arch' in metafunc.fixturenames:
        metafunc.parametrize('arch', [32, 64], scope='session')


# region Fixture aliases


@pytest.fixture
def static_addresses(arch):
    return static_addresses32(program_name(arch)) if arch == 32 else static_addresses64(program_name(arch))


@pytest.fixture
def dynamic_addresses(arch):
    return dynamic_addresses32() if arch == 32 else dynamic_addresses64()


# endregion

# region Global

@pytest.fixture
def hack(arch):
    hack = gh.Hack(program_name(arch))
    return hack


@pytest.fixture(scope='session')
def program(arch):
    program = subprocess.Popen([f"tests/core/{program_name(arch)}"], stdout=subprocess.DEVNULL)
    yield program
    program.kill()


@pytest.fixture
def set_cleanup():
    def cleanup_func():
        pass

    def _set(v):
        nonlocal cleanup_func
        cleanup_func = v

    yield _set

    cleanup_func()

# endregion


# region Types

class Types:
    _custom, _definitions, _defined_32, _defined_64 = [], [], False, False

    @staticmethod
    def define(arch):

        if not Types._defined_64 and not Types._defined_32:
            HackStructMeta._to_define = Types._custom
            HackStruct.define_types()
            Types._custom.clear()

        if arch == 64 and not Types._defined_64:
            HackStructMeta._to_define = Types._definitions[int(len(Types._definitions)/2):]
            Types._defined_64 = True
        elif arch == 32 and not Types._defined_32:
            HackStructMeta._to_define = Types._definitions[:int(len(Types._definitions)/2)]
            Types._defined_32 = True

        HackStruct.define_types()

        if Types._defined_64 and Types._defined_32:
            Types._definitions.clear()


@pytest.fixture
def types(arch):
    types = Types()
    if arch == 32:
        types.App = App32
        types.Game = Game32
        types.Level = Level32
        types.Powers = Powers32
    else:
        types.App = App64
        types.Game = Game64
        types.Level = Level64
        types.Powers = Powers64
    types.define = lambda: Types.define(arch)
    return types


# endregion


def program_name(arch):
    return f'TestProgram-{arch}.exe'


# region Application structure - 32 bits

# region Addresses


def static_addresses32(process_name):
    return {
        'marker': ('marker', process_name, 0x9000),
        'app': ('app', process_name, 0x90A0),
    }


def dynamic_addresses32():
    return {
        'powers': ('powers', 'app', []),
        'power_1': ('power_1', 'app', [0x4]),
        'game': ('game', 'app', [0x34]),
        'level': ('level', 'game', [0x4]),

    }

# endregion


HackStruct.set_architecture(32)


class Level32(HackStruct):
    id: gh.uint32 = 0x0
    duration: gh.float = 0x4
    long_thing: gh.double = 0x8


class Game32(HackStruct):
    selected_index: gh.uint = 0x0
    previous_level: Ptr[Level32] = 0x4
    level: Level32 = 0x8


class Powers32(HackStruct):
    power_0: gh.uint = 0x0
    power_1: gh.uint = 0x4
    power_2: gh.uint = 0x8
    power_3: gh.uint = 0xC
    power_4: gh.uint = 0x10


class App32(HackStruct):
    address = 'app'

    # Grouped
    powers: Powers32 = 0x0
    # Separate
    power_0: gh.uint = 0x0
    power_1: gh.uint = 0x4
    power_2: gh.uint = 0x8
    power_3: gh.uint = 0xC
    power_4: gh.uint = 0x10

    game: Game32 = 0x18
    v_ptr: Ptr[gh.uint] = 0x30
    game_ptr: Ptr[Game32] = 0x34


# endregion


# region Application structure - 64 bits

# region Addresses

def static_addresses64(process_name):
    return {
        'marker': ('marker', process_name, 0xA000),
        'app': ('app', process_name, 0xA100),
    }


def dynamic_addresses64():
    return {
        'powers': ('powers', 'app', []),
        'power_1': ('power_1', 'app', [0x4]),
        'game': ('game', 'app', [0x40]),
        'level': ('level', 'game', [0x8]),
    }

# endregion


HackStruct.set_architecture(64)


class Level64(HackStruct):
    id: gh.uint32 = 0x0
    duration: gh.float = 0x4
    long_thing: gh.double = 0x8


class Game64(HackStruct):
    selected_index: gh.uint = 0x0
    previous_level: Ptr[Level64] = 0x8
    level: Level64 = 0x10


class Powers64(HackStruct):
    power_0: gh.uint = 0x0
    power_1: gh.uint = 0x4
    power_2: gh.uint = 0x8
    power_3: gh.uint = 0xC
    power_4: gh.uint = 0x10


class App64(HackStruct):
    address = 'app'

    # Grouped
    powers: Powers64 = 0x0
    # Separate
    power_0: gh.uint = 0x0
    power_1: gh.uint = 0x4
    power_2: gh.uint = 0x8
    power_3: gh.uint = 0xC
    power_4: gh.uint = 0x10

    game: Game64 = 0x18
    v_ptr: Ptr[gh.uint] = 0x38
    game_ptr: Ptr[Game64] = 0x40


# endregion


Types._definitions = [i for i in HackStructMeta._to_define if not i._info.is_custom_type]
Types._custom = [i for i in HackStructMeta._to_define if i._info.is_custom_type]
HackStructMeta._to_define.clear()
