import pytest
import pygamehack as gh


@pytest.fixture
def raw_code():
    return bytes(bytearray([
        0x48, 0x8B, 0x05, 0x39, 0x00, 0x13, 0x00,  # mov rax, qword ptr ds:[<SomeModule.SomeData>]
        0x50,                                      # push rax
        0xFF, 0x15, 0xF2, 0x10, 0x00, 0x00,        # call qword ptr ds:[<SomeModule.SomeFunction>]
        0x85, 0xC0,                                # test eax, eax
        0x0F, 0x84, 0x00, 0x00, 0x00, 0x00,        # jz 0x007FFFFFFF400016
        0xE9, 0xE5, 0x0F, 0x00, 0x00               # jmp <SomeModule.EntryPoint>
    ]))


@pytest.fixture
def raw_code_info():
    return [
        # (0, 'mov rax, qword ptr ds:[<SomeModule.SomeData>]'),
        (0, 'mov rax, [rip+0x130039]'),
        (7, 'push rax'),
        # (8, 'call qword ptr ds:[<SomeModule.SomeFunction>]'),
        (8, 'call [rip+0x10F2]'),
        (14, 'test eax, eax'),
        (16, 'jz +0x06'),
        (22, 'jmp +0xFEA'),
    ]


def test_instruction_iter(raw_code, raw_code_info):
    decoder = gh.InstructionDecoder(gh.Instruction.Mode.Long64, gh.Instruction.AddressWidth.W64)
    decoder.set_format(gh.Instruction.Format.Intel)
    for (exp_offset, exp_str), (offset, ins) in zip(raw_code_info, decoder.iter(raw_code)):
        assert offset == exp_offset
        assert decoder.format(ins) == exp_str


def test_instruction_extract_searchable_code(raw_code):
    expected_searchable = b'H\x8b\x05....P\xff\x15....\x85\xc0\x0f\x84....\xe9....'
    decoder = gh.InstructionDecoder(gh.Instruction.Mode.Long64, gh.Instruction.AddressWidth.W64)
    searchable, offset, size = decoder.extract_searchable_bytes(raw_code, 8)
    assert searchable == expected_searchable
    assert offset == 10
    assert size == 4


# def test_instruction_iter(raw_code, raw_code_info):
    # raw = b'Rj\x00Q\xff\xd0\x83\xc4\x10\xc7C\x14\x01\x00\x00\x00\xc7CH\x00\x00\x00\x00\x8bC@\x8bS\x08\x8b\x00\xc3'
    #
    # expected = [
    #     (0, 'push %edx'),
    #     (1, 'pushb $0x0'),
    #     (3, 'push %ecx'),
    #     (4, 'call %eax'),
    #     (6, 'add $0x10,%esp'),
    #     (9, 'movl $0x1,0x14(%ebx)'),
    #     (16, 'movl $0x0,0x48(%ebx)'),
    #     (23, 'mov 0x40(%ebx),%eax'),
    #     (26, 'mov 0x8(%ebx),%edx'),
    #     (29, 'mov (%eax),%eax'),
    #     (31, 'ret ')
    # ]
    #
    # raw += raw
    # expected += [(i[0] + 32, i[1]) for i in expected]
    # last_offset = 0
    #
    # for (exp_offset, exp_str), (offset, ins) in zip(expected, gh.Instruction.iter(raw, True)):
    #     assert offset == exp_offset
    #     assert ins.to_string() == exp_str
    #     last_offset = offset
    #
    # assert last_offset == 31
    #
    # for (exp_offset, exp_str), (offset, ins) in zip(expected, gh.Instruction.iter(raw, False)):
    #     assert offset == exp_offset
    #     assert ins.to_string() == exp_str
    #     last_offset = offset
    #
    # assert last_offset == 63
    

# def test_instruction_extract_searchable_code(raw_code):
    # raw = b'Rj\x00Q\xff\xd0\x83\xc4\x10\xc7C\x14\x01\x00\x00\x00\xc7CH\x00\x00\x00\x00\x8bC@\x8bS\x08\x8b\x00\xc3'
    # searchable, offset, size = gh.Instruction.extract_searchable_bytes(raw, 16)
    # assert searchable == b'Rj.Q\xff\xd0\x83\xc4.\xc7C.....\xc7C.....\x8bC.\x8bS.\x8b\x00\xc3'
    # assert offset == 11
    # assert size == 1
    # assert searchable[offset:offset + size] == (b'.' * size)

    # raw = bytes(bytearray([
    #     0x51, 0x8D, 0x45, 0xFF, 0x50, 0xFF, 0x75, 0x0C, 0xFF, 0x75,
    #     0x08, 0xFF, 0x15, 0xA0, 0xA5, 0x48, 0x76, 0x85, 0xC0, 0x0F,
    #     0x88, 0xFC, 0xDA, 0x02, 0x00
    # ]))
