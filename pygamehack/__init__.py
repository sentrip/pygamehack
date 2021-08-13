from pygamehack.c import *
from .struct import Struct
from .reclassnet import ReClassNet
from .struct_file import StructFile
from .struct_meta import TypeWrapper, StructType
from .variable import Variable, ConstVariable, ListVariable, DictVariable
from .code import Code, CodeFindConfig, CodeFindTarget, CodeFinder, CodeScanResult, CodeScanner

__all__ = [
    # pygamehack.c
    'Address', 'Buffer', 'Hack',
    'Process', 'ProcessInfo', 'MemoryScan',
    'Instruction', 'InstructionDecoder',
    'CheatEnginePointerScanSettings',
    # pygamhack.c variable types
    'i8', 'i16', 'i32', 'i64',
    'u8', 'u16', 'u32', 'u64',
    'bool', 'float', 'double',
    'ptr', 'int', 'uint', 'usize',
    'buf', 'str', 'c_str', 'arr', 'c_arr',
    # pygamehack
    'Struct', 'StructType', 'TypeWrapper',
    'Variable', 'ConstVariable',
    'ListVariable', 'DictVariable',
    # pygamehack extras
    'Code', 'StructFile', 'ReClassNet',
    'CodeFinder', 'CodeFindConfig', 'CodeFindTarget',
    'CodeScanner', 'CodeScanResult',
]


#region Extensions

# Process.all() iterator that can be used in generator expressions
def _all_processes():
    """
    Iterator that lists the running processes on the system
    """
    processes = []
    Process.iter(lambda info: processes.append(info))
    for info in processes:
        yield info

Process.all = _all_processes


# Array __class_getitem__ return StructType instead of tuple
_old_arr_getitem = arr.__class_getitem__


def _convert_arr_getitem(typ):
    t = _old_arr_getitem(typ)
    return StructType(t[1], StructType.LAZY_SIZE, t[2], container_type=t[0])


arr.__class_getitem__ = _convert_arr_getitem

#endregion
