import pytest
import pygamehack as gh


@pytest.mark.skip
def test_instruction_iter():
    raw = b'Rj\x00Q\xff\xd0\x83\xc4\x10\xc7C\x14\x01\x00\x00\x00\xc7CH\x00\x00\x00\x00\x8bC@\x8bS\x08\x8b\x00\xc3'
    
    expected = [
        (0, 'push %edx'),
        (1, 'pushb $0x0'),
        (3, 'push %ecx'),
        (4, 'call %eax'),
        (6, 'add $0x10,%esp'),
        (9, 'movl $0x1,0x14(%ebx)'),
        (16, 'movl $0x0,0x48(%ebx)'),
        (23, 'mov 0x40(%ebx),%eax'),
        (26, 'mov 0x8(%ebx),%edx'),
        (29, 'mov (%eax),%eax'),
        (31, 'ret ')
    ]

    raw += raw
    expected += [(i[0] + 32, i[1]) for i in expected]
    last_offset = 0

    for (exp_offset, exp_str), (offset, ins) in zip(expected, gh.Instruction.iter(raw, True)):
        assert offset == exp_offset
        assert ins.to_string() == exp_str
        last_offset = offset

    assert last_offset == 31
    
    for (exp_offset, exp_str), (offset, ins) in zip(expected, gh.Instruction.iter(raw, False)):
        assert offset == exp_offset
        assert ins.to_string() == exp_str
        last_offset = offset
    
    assert last_offset == 63


def test_instruction_extract_searchable_code():
    raw = b'Rj\x00Q\xff\xd0\x83\xc4\x10\xc7C\x14\x01\x00\x00\x00\xc7CH\x00\x00\x00\x00\x8bC@\x8bS\x08\x8b\x00\xc3'
    
    searchable, offset, size = gh.Instruction.extract_searchable_bytes(raw, 16)
    assert searchable == b'Rj.Q\xff\xd0\x83\xc4.\xc7C.....\xc7C.....\x8bC.\x8bS.\x8b\x00\xc3'
    assert offset == 11
    assert size == 1
    assert searchable[offset:offset + size] == (b'.' * size)
