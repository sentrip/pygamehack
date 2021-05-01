from cpygamehack import *
from .struct import Struct
from .struct_meta import TypeWrapper, StructType
from .variable import Variable, ConstVariable, ListVariable, DictVariable
from .types import String as str, CString as c_str

__all__ = [
    # cpygamehack
    'Address',
    'Buffer',
    'Hack',
    'Process',
    'Instruction',
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
    'str', 'c_str'
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


def _strlen(self, address: int, max_size: int = 1000):
    """
    Get the length of a string located at the given address
    """
    return self.find(0, address, max_size)

Hack.strlen = _strlen


def _read_dynamic_string(self, address: int, max_size: int = 1000):
    """
    Read a dynamic string from the given address
    """
    return self.read_string(address, self.strlen(address, max_size))

Hack.read_dynamic_string = _read_dynamic_string


def _read_dynamic_string_ptr(self, address: int, max_size: int = 1000):
    """
    Read a dynamic string from the given address
    """
    data_address = self.read_ptr(address)
    return self.read_string(data_address, self.strlen(data_address, max_size))

Hack.read_dynamic_string_ptr = _read_dynamic_string_ptr

#endregion
