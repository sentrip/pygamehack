import os
import pytest
import pygamehack as gh


# TODO: Test CheatEnginePointerScanFile multiple configurations


@pytest.fixture
def pointer_scan_file_read():
    return "tests/utils/CheatEnginePointerScans/TestProgram-64.PTR"

@pytest.fixture
def pointer_scan_file_read_uncompressed():
    return "tests/utils/CheatEnginePointerScans/TestProgramNonCompressed-64.PTR"

@pytest.fixture
def get_pointer_scan_file_write_name_and_remove():
    def get(base):
        path = f"tests/utils/CheatEnginePointerScans/{base}-64.PTR"
        yield path
        os.remove(path)
        for f in os.listdir(path.replace(f'{base}-64.PTR', '')):
            if f.startswith(base):
                os.remove('tests/utils/CheatEnginePointerScans/' + f)
    return get

@pytest.fixture
def pointer_scan_file_write(get_pointer_scan_file_write_name_and_remove):
    yield from get_pointer_scan_file_write_name_and_remove('TestProgramWrite')

@pytest.fixture
def pointer_scan_file_write_uncompressed(get_pointer_scan_file_write_name_and_remove):
    yield from get_pointer_scan_file_write_name_and_remove('TestProgramWriteUnCompressed')

@pytest.fixture
def pointer_scan_file_offsets():
    return [
        0xB050,
        0xB820,
        0xB828,
        0xB830,
        0xB838,
        0xB840,
        0xB848,
        0xB850,
        0xB858
    ]

@pytest.fixture
def pointer_scan_file_offsets_uncompressed():
    return [
        0xB058,
        0xB050,
        0xB820,
        0xB828,
        0xB830,
        0xB838,
        0xB840,
        0xB848,
        0xB850,
        0xB858,
        0xB870,
        0xB888,
        0xB8A0,
        0xB8B8
    ]
    

def test_hack_cheat_engine_load_pointer_scan_file_compressed(pointer_scan_file_read, pointer_scan_file_offsets):
    hack = gh.Hack()

    addresses, settings = hack.cheat_engine_load_pointer_scan_file(pointer_scan_file_read, True)
    for i, a in enumerate(addresses):
        assert a.type == gh.Address.Type.Static
        assert a.module_name == 'TestProgram-64.exe'
        assert a.module_offset == pointer_scan_file_offsets[i]
    
    assert settings.max_level == 7
    assert settings.max_offset == 4095
    assert settings.is_compressed == True
    assert settings.is_aligned == True
    assert settings.ends_with_offsets == []


def test_hack_cheat_engine_save_pointer_scan_file_compressed(pointer_scan_file_write, pointer_scan_file_offsets):
    hack = gh.Hack()

    addresses = []
    for offset in pointer_scan_file_offsets:
        addresses.append(gh.Address(hack, 'TestProgram-64.exe', offset))

    settings = gh.CheatEnginePointerScanSettings()
    hack.cheat_engine_save_pointer_scan_file(pointer_scan_file_write, addresses, settings, True)


def test_hack_cheat_engine_load_pointer_scan_file_uncompressed(pointer_scan_file_read_uncompressed, pointer_scan_file_offsets_uncompressed):
    hack = gh.Hack()

    addresses, settings = hack.cheat_engine_load_pointer_scan_file(pointer_scan_file_read_uncompressed, True)
    for i, a in enumerate(addresses):
        assert a.type == gh.Address.Type.Static
        assert a.module_name == 'TestProgram-64.exe'
        assert a.module_offset == pointer_scan_file_offsets_uncompressed[i]

    assert settings.max_level == 3
    assert settings.max_offset == ((1 << 32) - 1) # UINT32_MAX
    assert settings.is_compressed == False
    assert settings.is_aligned == False
    assert settings.ends_with_offsets == []


def test_hack_cheat_engine_save_pointer_scan_file_uncompressed(pointer_scan_file_write_uncompressed, pointer_scan_file_offsets_uncompressed):
    hack = gh.Hack()

    addresses = []
    for offset in pointer_scan_file_offsets_uncompressed:
        addresses.append(gh.Address(hack, 'TestProgram-64.exe', offset))

    settings = gh.CheatEnginePointerScanSettings()
    hack.cheat_engine_save_pointer_scan_file(pointer_scan_file_write_uncompressed, addresses, settings, True)
