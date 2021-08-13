import pytest
import pygamehack as gh
from pygamehack.code import Code


@pytest.fixture
def code(arch):
    if arch == 32:
        return Code(offset=12, offset_size=4, begin='TestProgram-32.exe', size=0,
                    code='00 00 A1 ?? ?? ?? ?? 40 83 E0 ?? A3 ?? ?? ?? ?? E9 ?? ?? ?? ?? 5? ?8 ?? ?? ?? ?? 52')
    else:
        return Code(offset=12, offset_size=4, begin='TestProgram-64.exe', size=0,
                    code='05 ?? ?? ?? ?? FF C0 83 E0 ?? 89 05 ?? ?? ?? ?? E9 ?? ?? ?? ?? 8B C8 E8 ?? ?? ?? ?? 90')


@pytest.mark.skip
def test_code_scanner(hack, app, code):
    entry = gh.Process.entry_point('tests\\test_program\\' + app.program_name)
    print(entry)

    hack.attach(app.pid)
    r = code.scan_in_process(hack)
    static_offset = r.offset - hack.process.get_base_address(app.program_name)
    print(hack.read_u32(r.offset))
    print(hex(app.addr.marker), hex(r.address), hex(r.offset), hex(static_offset))
