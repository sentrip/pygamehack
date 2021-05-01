import pytest
import pygamehack as gh
from pygamehack.code import Code


@pytest.fixture
def code(arch):
    if arch == 32:
        return Code(offset=11, offset_size=4, begin='TestProgram-32.exe', size=0,
                    code='?? A1 0C A0 DE 00 ?? 83 ?? ?? ?? ?? A0 ?? ?? ?? ?? FD ')
    else:
        return Code(offset=11, offset_size=4, begin='TestProgram-64.exe', size=0,
                    code='5A 6D 00 00 FF ?? 83 E0 ?? ?? ?? ?? 6D ?? ?? ?? ?? FE ')


@pytest.mark.skip
def test_code_scanner(hack, app, code):
    entry = gh.Process.entry_point('tests\\' + app.program_name)
    print(entry)

    hack.attach(app.pid)
    r = code.scan_in_process(hack)
    print(r.address, r.offset, r.offset - entry)
