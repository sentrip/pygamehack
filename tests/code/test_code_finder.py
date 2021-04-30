import pytest
import pygamehack as gh
from pygamehack.code import CodeFinder, CodeFindTarget

@pytest.mark.skip
def test_code_finder(hack, app, set_cleanup):
    def cleanup():
        hack.write_u32(app.addr.marker + 0x8, 0)
        hack.write_u32(app.addr.marker + 0xC, 0)
    set_cleanup(cleanup)

    class TestProgram(gh.Struct):
        marker: gh.uint = 0x0
        flag: gh.uint = 0x8
        update: gh.uint = 0xC

    gh.Struct.define_types(app.arch)

    hack.attach(app.program_name)

    t = TestProgram(gh.Address(hack, app.addr.marker))
    getattr(t, 'update')

    finder = CodeFinder()
    finder.add_target('update', CodeFindTarget(t.variables['update'].address,
                                               watch_trigger=lambda h, a: h.write_u32(a.value - 4, 1)))
    results = finder.find(hack)

    for name, code in results:
        print(name, code)
