import re
from typing import Iterator, Optional, Tuple

import pygamehack as gh

__all__ = ['extract_searchable_raw_code', 'Instruction', 'Operand']


def extract_searchable_raw_code(
        raw_code: bytes,
        instruction_end_offset: Optional[int] = None
) -> (bytes, int, int):
    """

    """
    begin, offset, instruction_offset, offset_size = 0, 0, 0, 0

    # Strip or replace regex special characters with .
    code = re.sub(b'\[|\]', b'.', raw_code)

    for offset, instruction in Instruction.iter(raw_code, mode=gh.Instruction.M32, break_on_return=True):

        # Skip empty instructions at the beginning
        if instruction.opcode == 0 and not begin:
            begin = offset + instruction.length

        for op, _, off, size in instruction.dynamic_bytes_offsets_sizes():
            # Replace dynamic bytes with dots
            code = code[:offset + off] + b'.' * size + code[offset + off + size:]

            # Detect offset and offset size
            if op.displacement and offset + instruction.length == instruction_end_offset:
                instruction_offset = offset + off - begin
                offset_size = size

    return code[begin:offset+1], instruction_offset, offset_size


class Instruction(object):

    _properties = [
        'length',
        # 'mode',
        'opcode', 'modrm', 'sib', 'modrm_offset',
        'extindex', 'fpuindex',
        'dispbytes', 'immbytes', 'sectionbytes',
        'op1', 'op2', 'op3',
        'flags', 'eflags_affected', 'eflags_used',
        'iop_written', 'iop_read'
    ]

    def __init__(
            self,
            raw: bytes,
            mode: gh.Instruction.Mode = gh.Instruction.M32,
            fmt: gh.Instruction.Format = gh.Instruction.Format.INTEL
    ):
        self.raw = gh.get_instruction(raw, mode)
        self.code = raw[:self.raw.length]
        self.fmt = fmt
        self.ops = [Operand(self, getattr(self.raw, f'op{i}')) for i in range(1, 4)]

    def __getattribute__(self, item):
        try:
            return super().__getattribute__(item)
        except AttributeError:
            return self.raw.__getattribute__(item)

    def __iter__(self):
        return self.ops.__iter__()

    def __len__(self):
        return self.raw.length

    def __str__(self):
        return _print_thing(self)

    def __repr__(self):
        return gh.get_instruction_string(self.raw, format=self.fmt)

    def dynamic_bytes_offsets_sizes(self) -> Iterator[Tuple['Operand', str, int, int]]:
        for op in self.ops:
            for prop in ['immediate', 'displacement']:
                offset, size = getattr(op, f'{prop}_offset_size')
                if not size:
                    continue
                yield op, prop, offset, size

    @staticmethod
    def iter(
            raw_code: bytes,
            mode: gh.Instruction.Mode = gh.Instruction.M32,
            break_on_return: bool = True
    ) -> Iterator[Tuple[int, 'Instruction']]:
        """
        """
        offset = 0

        while offset < len(raw_code):
            instruction = Instruction(raw_code[offset:], mode)
            yield offset, instruction

            offset += len(instruction)

            instruction_string = str(instruction)
            if break_on_return and instruction_string.startswith('ret '):
                break


class Operand(object):

    _properties = [
        'reg',
        'basereg',
        'indexreg',
        'scale',
        'dispbytes',
        'dispoffset',
        'immbytes',
        'immoffset',
        'sectionbytes',
        'section',
        'displacement',
        'immediate',
        'flags'
    ]

    def __init__(self, instruction: Instruction, raw: gh.Operand):
        self.instruction = instruction
        self.raw = raw

    def __getattribute__(self, item):
        try:
            return super().__getattribute__(item)
        except AttributeError:
            return self.raw.__getattribute__(item)

    def __repr__(self):
        return _print_thing(self)

    @property
    def displacement_offset_size(self) -> (int, int):
        return self.raw.dispoffset, self.raw.dispbytes

    @property
    def immediate_offset_size(self) -> (int, int):
        return self.raw.immoffset, self.raw.immbytes


def _iter_ops(self) -> Iterator[gh.Operand]:
    for op in [self.op1, self.op2, self.op3]:
        yield op


def _print_thing(self):
    props = []
    for p in self.__class__._properties:
        value = getattr(self, p)
        props.append(f'\t{p} = 0x{value:X}' if isinstance(value, int) else f'\t{p} = {value}')
    props_str = ',\n'.join(props)
    return f'{self.__class__.__name__}(\n{props_str})'


gh.Instruction._properties = Instruction._properties
gh.Operand._properties = Operand._properties
gh.Operand.__repr__ = lambda s: _print_thing(s)
gh.Instruction.__repr__ = lambda s: _print_thing(s)
gh.Instruction.iter_ops = _iter_ops
