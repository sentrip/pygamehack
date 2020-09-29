import pytest
import pygamehack as gh


# region Read

def test_read_static_variable(hack, program, static_addresses):

    marker_a = hack.add_static_address(*static_addresses['marker'])
    marker_v = gh.uint(marker_a)

    assert marker_a.address == 0

    assert marker_v.read() == 0
    assert hack.read_uint32(marker_a.address) == 0

    hack.attach()
    assert marker_a.address != 0

    assert marker_v.read() == 1234567898
    assert hack.read_uint32(marker_a.address) == 1234567898


def test_read_dynamic_variable(hack, program, static_addresses, dynamic_addresses):

    app_a = hack.add_static_address(*static_addresses['app'])
    app_a.previous_holds_ptr = False  # Since 'App' is a static object, this is necessary unless defined as a buffer
    power_1_a = hack.add_dynamic_address(*dynamic_addresses['power_1'])
    power_1_v = gh.uint(power_1_a)

    assert power_1_a.name == 'power_1'
    assert power_1_a.address == 0

    hack.attach()
    assert power_1_a.address == 0

    assert power_1_v.read() == 0
    assert hack.read_uint32(power_1_a.address) == 0

    hack.load_addresses()
    assert power_1_a.address != 0

    assert power_1_v.read() == 2
    assert hack.read_uint32(power_1_a.address) == 2


def test_read_hackstruct_type(hack, program, static_addresses, dynamic_addresses, types):
    types.define()

    app_a = hack.add_static_address(*static_addresses['app'])
    app_a.previous_holds_ptr = False  # Since 'App' is a static object, this is necessary unless defined as a buffer
    powers_a = hack.add_dynamic_address(*dynamic_addresses['powers'])
    powers_a.previous_holds_ptr = False  # Since 'Powers' is an instance, this is necessary unless defined as a buffer
    game_a = hack.add_dynamic_address(*dynamic_addresses['game'])
    level_a = hack.add_dynamic_address(*dynamic_addresses['level'])

    hack.attach()

    powers = types.Powers(powers_a)
    level = types.Level(level_a)

    assert powers.power_1 == 0
    assert powers.address.address == 0

    assert level.id == 0
    assert level.address.address == 0

    hack.load_addresses()

    assert powers.address.address != 0
    assert powers.power_0 == 1

    assert level.address.address != 0
    assert level.id == 500


def test_read_hackstruct_type_nested(hack, program, static_addresses, types):
    types.define()

    app_a = hack.add_static_address(*static_addresses['app'])
    app_a.previous_holds_ptr = False  # Since 'App' is a static object, this is necessary unless defined as a buffer

    hack.attach()

    app = types.App(hack)

    hack.load_addresses()

    assert app.power_0 == 1
    assert app.powers.power_0 == 1

    assert app.v_ptr == 12

    assert app.game.selected_index == 4
    assert app.game.level.id == 321
    assert app.game.level.duration == 0.5
    assert app.game.level.long_thing == 25.0

    assert app.game.previous_level.id == 520
    assert app.game.previous_level.duration == 0.5
    assert app.game.previous_level.long_thing == 50.0

    assert app.game_ptr.selected_index == 4
    assert app.game_ptr.level.id == 321
    assert app.game_ptr.level.duration == 0.5
    assert app.game_ptr.level.long_thing == 25.0

    assert app.game_ptr.previous_level.id == 500
    assert app.game_ptr.previous_level.duration == 0.0
    assert app.game_ptr.previous_level.long_thing == 0.0


def test_read_hackstruct_buffer_type(hack, program, static_addresses, dynamic_addresses, types):
    types.define()

    app_a = hack.add_static_address(*static_addresses['app'])
    powers_a = hack.add_dynamic_address(*dynamic_addresses['powers'])
    game_a = hack.add_dynamic_address(*dynamic_addresses['game'])
    level_a = hack.add_dynamic_address(*dynamic_addresses['level'])

    hack.attach()

    powers = types.Powers(powers_a, buffer=True)
    level  = types.Level(level_a, buffer=True)

    level_a.previous_holds_ptr = True

    assert powers.power_0 == 0
    assert powers.address.address == 0

    assert level.id == 0
    assert level.address.address == 0

    hack.load_addresses()
    powers.buffer.read()
    level.buffer.read()

    assert powers.address.address != 0
    assert powers.power_0 == 1

    # Should this work...?
    # assert level.address.address != 0
    # assert level.id == 500


def test_read_hackstruct_buffer_type_nested(hack, program, static_addresses, types):
    types.define()

    hack.add_static_address(*static_addresses['app'])

    hack.attach()

    app = types.App(hack, buffer=True, propagate=True)

    hack.load_addresses()
    app.buffer.read()
    app.game.buffer.read()
    app.powers.buffer.read()
    app.game_ptr.buffer.read()
    app.game.level.buffer.read()
    app.game.previous_level.buffer.read()
    app.game_ptr.level.buffer.read()
    app.game_ptr.previous_level.buffer.read()

    assert app.power_0 == 1
    assert app.powers.power_0 == 1

    assert app.v_ptr == 12

    assert app.game.selected_index == 4
    assert app.game.level.id == 321
    assert app.game.level.duration == 0.5
    assert app.game.level.long_thing == 25.0

    assert app.game.previous_level.id == 520
    assert app.game.previous_level.duration == 0.5
    assert app.game.previous_level.long_thing == 50.0

    assert app.game_ptr.selected_index == 4
    assert app.game_ptr.level.id == 321
    assert app.game_ptr.level.duration == 0.5
    assert app.game_ptr.level.long_thing == 25.0

    assert app.game_ptr.previous_level.id == 500
    assert app.game_ptr.previous_level.duration == 0.0
    assert app.game_ptr.previous_level.long_thing == 0.0

# endregion


# region Write

def test_write_static_variable(hack, program, static_addresses, set_cleanup):
    marker_a = hack.add_static_address(*static_addresses['marker'])
    marker_v = gh.uint(marker_a)

    def cleanup():
        nonlocal marker_v
        marker_v.write(1234567898)  # reset state for other tests
    set_cleanup(cleanup)

    hack.attach()

    assert marker_v.read() == 1234567898

    marker_v.write(10)

    assert marker_v.read() == 10

    hack.write_uint32(marker_a.address, 15)

    assert hack.read_uint32(marker_a.address) == 15


def test_write_dynamic_variable(hack, program, static_addresses, dynamic_addresses, set_cleanup):

    app_a = hack.add_static_address(*static_addresses['app'])
    app_a.previous_holds_ptr = False  # Since 'App' is a static object, this is necessary unless defined as a buffer
    power_1_a = hack.add_dynamic_address(*dynamic_addresses['power_1'])
    power_1_v = gh.uint(power_1_a)

    def cleanup():
        nonlocal power_1_v
        power_1_v.write(2)  # reset state for other tests
    set_cleanup(cleanup)

    hack.attach()

    hack.load_addresses()

    assert power_1_v.read() == 2

    power_1_v.write(10)

    assert power_1_v.read() == 10

    hack.write_uint32(power_1_a.address, 15)

    assert hack.read_uint32(power_1_a.address) == 15


def test_write_hackstruct_type(hack, program, static_addresses, dynamic_addresses, types, set_cleanup):
    types.define()

    app_a = hack.add_static_address(*static_addresses['app'])
    app_a.previous_holds_ptr = False  # Since 'App' is a static object, this is necessary unless defined as a buffer
    game_a = hack.add_dynamic_address(*dynamic_addresses['game'])
    level_a = hack.add_dynamic_address(*dynamic_addresses['level'])

    hack.attach()

    level = types.Level(level_a)

    def cleanup():
        nonlocal level
        level.id = 500  # reset state for other tests
    set_cleanup(cleanup)

    hack.load_addresses()

    assert level.id == 500

    level.id = 15
    assert level.id == 15


# TODO: test_write_hackstruct_type_nested_with_hackstruct_types

# TODO: test_write_hackstruct_type_nested_with_hackstruct_buffer_types


def test_write_hackstruct_type_nested_with_basic_types(hack, program, static_addresses, types, set_cleanup):
    types.define()

    app_a = hack.add_static_address(*static_addresses['app'])
    app_a.previous_holds_ptr = False  # Since 'App' is a static object, this is necessary unless defined as a buffer

    hack.attach()

    app = types.App(hack)

    def cleanup():
        nonlocal app
        app.power_0 = 1  # reset state for other tests

        app.v_ptr = 12

        app.game.selected_index = 4
        app.game.level.id = 321
        app.game.level.duration = 0.5
        app.game.level.long_thing = 25.0

        app.game.previous_level.id = 520
        app.game.previous_level.duration = 0.5
        app.game.previous_level.long_thing = 50.0

        app.game_ptr.selected_index = 4
        app.game_ptr.level.id = 321
        app.game_ptr.level.duration = 0.5
        app.game_ptr.level.long_thing = 25.0

        app.game_ptr.previous_level.id = 500
        app.game_ptr.previous_level.duration = 0.0
        app.game_ptr.previous_level.long_thing = 0.0
    set_cleanup(cleanup)

    hack.load_addresses()

    app.power_0 = 2
    assert app.power_0 == 2
    assert app.powers.power_0 == 2

    app.v_ptr = 24
    assert app.v_ptr == 24

    app.game.selected_index = 8
    app.game.level.id = 3211
    app.game.level.duration = 5.5
    app.game.level.long_thing = 28.0
    assert app.game.selected_index == 8
    assert app.game.level.id == 3211
    assert app.game.level.duration == 5.5
    assert app.game.level.long_thing == 28.0

    app.game.previous_level.id = 5200
    app.game.previous_level.duration = 0.75
    app.game.previous_level.long_thing = 50.05
    assert app.game.previous_level.id == 5200
    assert app.game.previous_level.duration == 0.75
    assert app.game.previous_level.long_thing == 50.05

    app.game_ptr.selected_index = 10
    app.game_ptr.level.id = 3215
    app.game_ptr.level.duration = 12.5
    app.game_ptr.level.long_thing = 22.0
    assert app.game_ptr.selected_index == 10
    assert app.game_ptr.level.id == 3215
    assert app.game_ptr.level.duration == 12.5
    assert app.game_ptr.level.long_thing == 22.0

    app.game_ptr.previous_level.id = 5000
    app.game_ptr.previous_level.duration = 10.0
    app.game_ptr.previous_level.long_thing = 110.0
    assert app.game_ptr.previous_level.id == 5000
    assert app.game_ptr.previous_level.duration == 10.0
    assert app.game_ptr.previous_level.long_thing == 110.0


def test_write_hackstruct_buffer_type(hack, program, static_addresses, dynamic_addresses, types, set_cleanup):
    types.define()

    app_a = hack.add_static_address(*static_addresses['app'])
    app_a.previous_holds_ptr = False  # Since 'App' is a static object, this is necessary unless defined as a buffer
    powers_a = hack.add_dynamic_address(*dynamic_addresses['powers'])
    game_a = hack.add_dynamic_address(*dynamic_addresses['game'])
    level_a = hack.add_dynamic_address(*dynamic_addresses['level'])

    hack.attach()

    powers = types.Powers(powers_a, buffer=True)
    level = types.Level(level_a, buffer=True)

    level_a.previous_holds_ptr = True

    def cleanup():
        nonlocal powers, level
        powers.power_0 = 1  # reset state for other tests
        powers.buffer.write_contents()
        # level.id = 500
        # level.buffer.write_contents()

    set_cleanup(cleanup)

    hack.load_addresses()
    powers.buffer.read()
    level.buffer.read()
    assert powers.power_0 == 1

    powers.power_0 = 10
    powers.buffer.write_contents()

    powers.buffer.read()
    assert powers.power_0 == 10

    # should this work...?
    # assert level.id == 500

    # level.id = 15
    # level.buffer.write_contents()
    # level.buffer.read()

    # assert level.id == 15


def test_write_hackstruct_buffer_type_nested_with_basic_types(hack, program, static_addresses, types, set_cleanup):
    types.define()

    hack.add_static_address(*static_addresses['app'])

    hack.attach()

    app = types.App(hack, buffer=True, propagate=True)

    def cleanup():
        nonlocal app
        app.power_0 = 1  # reset state for other tests

        app.v_ptr = 12

        app.game.selected_index = 4
        app.game.level.id = 321
        app.game.level.duration = 0.5
        app.game.level.long_thing = 25.0

        app.game.previous_level.id = 520
        app.game.previous_level.duration = 0.5
        app.game.previous_level.long_thing = 50.0

        app.game_ptr.selected_index = 4
        app.game_ptr.level.id = 321
        app.game_ptr.level.duration = 0.5
        app.game_ptr.level.long_thing = 25.0

        app.game_ptr.previous_level.id = 500
        app.game_ptr.previous_level.duration = 0.0
        app.game_ptr.previous_level.long_thing = 0.0

        app.buffer.write_contents()
        app.game.buffer.write_contents()
        app.powers.buffer.write_contents()
        app.game_ptr.buffer.write_contents()
        app.game.level.buffer.write_contents()
        app.game.previous_level.buffer.write_contents()
        app.game_ptr.level.buffer.write_contents()
        app.game_ptr.previous_level.buffer.write_contents()

    set_cleanup(cleanup)

    hack.load_addresses()
    app.buffer.read()
    app.game.buffer.read()
    app.powers.buffer.read()
    app.game_ptr.buffer.read()
    app.game.level.buffer.read()
    app.game.previous_level.buffer.read()
    app.game_ptr.level.buffer.read()
    app.game_ptr.previous_level.buffer.read()

    app.power_0 = 2
    app.v_ptr = 24
    app.buffer.write_contents()
    app.buffer.read()
    app.powers.buffer.read()
    assert app.power_0 == 2
    assert app.powers.power_0 == 2
    assert app.v_ptr == 24

    app.game.selected_index = 8
    app.game.level.id = 3211
    app.game.level.duration = 5.5
    app.game.level.long_thing = 28.0
    app.game.buffer.write_contents()
    app.game.level.buffer.write_contents()
    app.game.buffer.read()
    app.game.level.buffer.read()
    assert app.game.selected_index == 8
    assert app.game.level.id == 3211
    assert app.game.level.duration == 5.5
    assert app.game.level.long_thing == 28.0

    app.game.previous_level.id = 5200
    app.game.previous_level.duration = 0.75
    app.game.previous_level.long_thing = 50.05
    app.game.previous_level.buffer.write_contents()
    app.game.previous_level.buffer.read()
    assert app.game.previous_level.id == 5200
    assert app.game.previous_level.duration == 0.75
    assert app.game.previous_level.long_thing == 50.05

    app.game_ptr.selected_index = 10
    app.game_ptr.level.id = 3215
    app.game_ptr.level.duration = 12.5
    app.game_ptr.level.long_thing = 22.0
    app.game_ptr.buffer.write_contents()
    app.game_ptr.level.buffer.write_contents()
    app.game_ptr.buffer.read()
    app.game_ptr.level.buffer.read()
    assert app.game_ptr.selected_index == 10
    assert app.game_ptr.level.id == 3215
    assert app.game_ptr.level.duration == 12.5
    assert app.game_ptr.level.long_thing == 22.0

    app.game_ptr.previous_level.id = 5000
    app.game_ptr.previous_level.duration = 10.0
    app.game_ptr.previous_level.long_thing = 110.0
    app.game_ptr.previous_level.buffer.write_contents()
    app.game_ptr.previous_level.buffer.read()
    assert app.game_ptr.previous_level.id == 5000
    assert app.game_ptr.previous_level.duration == 10.0
    assert app.game_ptr.previous_level.long_thing == 110.0


# TODO: test_write_hackstruct_buffer_type_nested_with_hackstruct_types

# TODO: test_write_hackstruct_buffer_type_nested_with_hackstruct_buffer_types

# endregion


# region Misc

def test_backup_address(hack, program, static_addresses, dynamic_addresses):

    app_a = hack.add_static_address(*static_addresses['app'])
    app_a.previous_holds_ptr = False  # Since 'App' is a static object, this is necessary unless defined as a buffer

    power_1_a = hack.add_dynamic_address('power_1', 'app', [0x101, 0x11, 0x5DC])
    power_1_a.add_backup(*(dynamic_addresses['power_1'][1:]))

    hack.attach()

    assert hack.read_uint32(power_1_a.address) == 0

    hack.load_addresses()

    assert power_1_a.address != 0

    assert hack.read_uint32(power_1_a.address) == 2

# endregion
