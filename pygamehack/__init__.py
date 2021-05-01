from cpygamehack import *
from .struct import Struct
from .struct_meta import TypeWrapper, StructType
from .variable import Variable, ConstVariable, ListVariable, DictVariable
from .types import String as str, CString as c_str, Array as arr, CArray as c_arr

__all__ = [
    # cpygamehack
    'Address',
    'Buffer',
    'Hack',
    'Process',
    'Instruction',
    'MemoryScan',
    'i8', 'i16', 'i32', 'i64',
    'u8', 'u16', 'u32', 'u64',
    'bool', 'float', 'double',
    'ptr', 'buf', 'p_buf',
    'int', 'uint', 'usize',
    # pygamehack
    'Struct', 'TypeWrapper', 'StructType',
    'Variable', 'ConstVariable', 
    'ListVariable', 'DictVariable', 
    # pygamehack types
    'str', 'c_str', 'arr', 'c_arr'
]


#region Extensions

def _all_processes():
    """
    Iterator that lists the running processes on the system
    """
    processes = []
    Process.iter(lambda info: processes.append(info))
    for info in processes:
        yield info

Process.all = _all_processes

#endregion
