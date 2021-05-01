
# TODO: Test follow
# TODO: Test iter processes
# TODO: Test iter regions
# TODO: Test kill
# TODO: Test created at
# TODO: Test entry_point

def test_process_protect(hack, app):
    hack.attach(app.pid)
    with hack.process.protect(app.addr.marker, 4):
        assert hack.read_u32(app.addr.marker) == app.marker_value
