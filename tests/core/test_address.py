import pygamehack as gh


def test_address_manual(hack, app):
    addr = gh.Address(hack, app.addr.marker)
    
    assert addr.type == gh.Address.Type.Manual
    assert addr.loaded
    assert addr.value == app.addr.marker
    assert not addr.valid

    hack.attach(app.program_name)

    assert addr.valid


def test_address_static(hack, app):
    addr = gh.Address(hack, app.program_name, app.addr.entry_offset)
    
    assert addr.type == gh.Address.Type.Static
    assert not addr.loaded
    assert addr.value == 0
    assert not addr.valid

    hack.attach(app.program_name)
    loaded_addr = addr.load()

    assert loaded_addr == app.addr.marker
    assert addr.value == app.addr.marker
    assert addr.loaded
    assert addr.valid


def test_address_dynamic(hack, app):
    static_addr = gh.Address(hack, app.program_name, app.addr.entry_offset + (app.addr.ptr_types.marker - app.addr.marker))
    addr = gh.Address(static_addr, [0])
    
    assert addr.type == gh.Address.Type.Dynamic
    assert not addr.loaded
    assert addr.value == 0
    assert not addr.valid

    hack.attach(app.program_name)
    static_addr.load()
    loaded_addr = addr.load()

    assert loaded_addr == app.addr.marker
    assert addr.value == app.addr.marker
    assert addr.loaded
    assert addr.valid


def test_address_dynamic_add_first_offset_to_parent(hack, app):
    static_addr = gh.Address(hack, app.program_name, app.addr.entry_offset)
    addr = gh.Address(static_addr, [app.addr.ptr_types.marker - app.addr.marker, 0], True)
    
    assert addr.type == gh.Address.Type.Dynamic
    assert not addr.loaded
    assert addr.value == 0
    assert not addr.valid

    hack.attach(app.program_name)
    static_addr.load()
    loaded_addr = addr.load()

    assert loaded_addr == app.addr.marker
    assert addr.value == app.addr.marker
    assert addr.loaded
    assert addr.valid
