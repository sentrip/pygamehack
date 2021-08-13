import pygamehack as gh


def test_address_manual(app):
    hack = gh.Hack()

    for a in app.addr.roots:
        addr = gh.Address(hack, a)
        assert addr.type == gh.Address.Type.Manual
        assert addr.loaded
        assert addr.value == a
        assert not addr.valid

        hack.attach(app.pid)

        assert addr.valid

        hack.detach()


def test_address_static(app):
    hack = gh.Hack()
    addr = gh.Address(hack, app.program_name, app.offsets.static)

    assert not addr.loaded
    assert not addr.valid
    assert addr.type == gh.Address.Type.Static
    assert addr.value == 0

    hack.attach(app.pid)
    loaded_addr = addr.load()

    assert addr.loaded
    assert addr.valid
    assert loaded_addr == app.addr.roots[0]
    assert addr.value == app.addr.roots[0]

    hack.detach()


def test_address_dynamic_add_first_offset_to_parent(app):
    hack = gh.Hack()

    for addr in app.addr.roots:
        manual_addr = gh.Address(hack, addr)
        addr = gh.Address(manual_addr, [app.offsets.Basic.ptr], True)

        assert not addr.loaded
        assert not addr.valid
        assert addr.type == gh.Address.Type.Dynamic
        assert addr.value == 0

        hack.attach(app.pid)
        loaded_addr = addr.load()

        assert addr.loaded
        assert addr.valid
        assert loaded_addr == manual_addr.value + app.offsets.Basic.ptr
        assert addr.value == manual_addr.value + app.offsets.Basic.ptr

        hack.detach()


"""
def test_address_manual(hack, app):
    addr = gh.Address(hack, app.addr.marker)
    
    assert addr.type == gh.Address.Type.Manual
    assert addr.loaded
    assert addr.value == app.addr.marker
    assert not addr.valid

    hack.attach(app.pid)

    assert addr.valid


def test_address_static(hack, app):
    addr = gh.Address(hack, app.program_name, app.addr.entry_offset)
    
    assert addr.type == gh.Address.Type.Static
    assert not addr.loaded
    assert addr.value == 0
    assert not addr.valid

    hack.attach(app.pid)
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

    hack.attach(app.pid)
    static_addr.load()
    loaded_addr = addr.load()

    assert loaded_addr == app.addr.marker
    assert addr.value == app.addr.marker
    assert addr.loaded
    assert addr.valid
"""