import re
import struct
from binascii import hexlify, unhexlify
from collections import namedtuple, deque
from dataclasses import dataclass
from typing import Callable, Dict, List, Tuple, Optional, Union

from pygamehack.c import Address, Instruction, InstructionDecoder, Hack, MemoryScan, Process
from .gdb import GDB, Watch
from .struct import Struct

__all__ = ['Code', 'CodeFindConfig', 'CodeFindTarget', 'CodeFinder', 'CodeScanResult', 'CodeScanner']

__doc__ = """
When defining structs, you must hard code the offsets of each struct.
If the binary you are reversing changes, these offsets might also change.
To aid the process of updating these offsets, the 'CodeFinder' allows you to 
use a debugger (GDB) to watch for reads/writes in the properties of your struct objects
in the target process' memory, and using the addresses of the instructions that read/write
your structs you can extract a searchable code string that contain the found instructions.
These searchable code strings can be fed into the 'CodeScanner' to produce updated offsets.
These updated offsets can then be used to update your structs, or both the searchable code info
and the offsets can be used with a 'StructFile' to update an already-defined struct file.
"""

# TODO: Find code for every single offset in an offset path, not just the final address

#region Code

CodeScanResult = namedtuple('CodeScanResult', ['address', 'offset'])


@dataclass
class Code(object):
    # The offset being scanned for
    offset: int
    # Size of the offset being scanned for in bytes
    offset_size: int
    # If the code can be found in a dynamic lib, stores the name of the dynamic lib
    # Otherwise it stores the starting offset for the scan
    begin: Union[int, str]
    # The size of the scan
    size: int
    # The code to scan for
    code: str

    def scan_in_process(self, hack: Hack) -> CodeScanResult:
        """
        Scan for this piece of code in the target process.
        returns tuple(address, offset)
        """
        return _code_scan_in_process(hack, self)

    @staticmethod
    def bytes_to_string(raw_code: bytes) -> str:
        """Convert a raw code byte string into a readable spaced hex string"""
        return _code_bytes_to_string(raw_code)

    @staticmethod
    def string_to_bytes(code: str) -> bytes:
        """Convert a readable spaced hex string into a raw code byte string"""
        return _code_string_to_bytes(code)


#endregion

#region CodeFinder

@dataclass(unsafe_hash=True)
class CodeFindConfig:
    read: bool = False
    write: bool = True
    c_type: str = ''


@dataclass(unsafe_hash=True)
class CodeFindTarget:
    target: Union[Address, Struct]
    config: CodeFindConfig = CodeFindConfig()
    watch_trigger: Optional[Callable[[Hack, Address], None]] = None
    children: Optional[Dict[str, 'CodeFindTarget']] = None


class CodeFinder(object):
    """
    Debugs the target process to observe reads/writes that can produce searchable code strings 
    that help automate the finding/updating of the offset path of the addresses observed
    """
    def __init__(self):
        self._to_find = []
    
    def add_target(self, name: str, target: CodeFindTarget):
        self._to_find.append((name, target))
        if Struct.is_struct(target.target):
            for child_name, child in Struct.iter_variables(target.target):
                if child_name in target.children:
                    self.add_target(name, target.children[name])

    def find(self, hack: Hack) -> List[Tuple[str, Code]]:
        results = _code_find_in_process(hack, self._to_find)
        self._to_find.clear()
        return results


#endregion

#region CodeScanner

class CodeScanner(object):
    """
    Scans the target process memory for the given searchable code strings
    """
    def __init__(self):
        self._to_scan = []

    def add_code(self, name: str, code: Code):
        self._to_scan.append((name, code))
    
    def scan(self, hack: Hack) -> List[Tuple[str, CodeScanResult]]:
        results = []
        for name, code in self._to_scan:
            results.append((name, code.scan_in_process(hack)))
        self._to_scan.clear()
        return results


#endregion

#region Code Find Implementation

WATCH_TRIGGER_MAX_RETRIES = 5
INSTRUCTION_READ_DISTANCE = 16


def _code_find_in_process(hack, to_find):
    if not hack.process.attached:
        raise RuntimeError('You must first attach the hack to a process before using the CodeFinder')
    
    modules = hack.process.modules
    # TODO: Proper gdb path
    gdb = GDB('C:\\MinGW\\bin\\gdb.exe')
    target_queue = deque()
    results = []
    target_to_address = {}
    watch_to_target = {}
    triggered_target_results = {}
    retry_count = {}

    def on_watch_trigger(watch, previous, current, data):
        result = _code_on_watch_trigger('', watch, data, hack, modules, gdb, results)
        triggered_target_results[watch_to_target[watch]] = result
    
    # Queue targets for watch trigger execution
    for _, target in to_find:
        target_queue.append(target)

    # Create watches for targets
    gdb.attach(hack.process.pid)
    for name, target in to_find:
        address = target.target.address if Struct.is_struct(target.target) else target.target
        target_to_address[target] = address
        watch = Watch(
            name=name, 
            address=address.value,
            callback=on_watch_trigger,
            read=target.config.read, 
            write=target.config.write,
            c_type=target.config.c_type
        )
        watch_to_target[watch] = target
        gdb.add_watch(watch)
    
    # Execute watch triggers while there are targets without results
    while target_queue:
        target = target_queue.popleft()
        
        # TODO: Timeout/failure?
        with gdb.continue_wait():
            target.watch_trigger(hack, target_to_address[target])

        if target not in triggered_target_results and retry_count.get(target, 0) < WATCH_TRIGGER_MAX_RETRIES:
            retry_count[target] = retry_count.get(target, 0) + 1
            target_queue.append(target)

    gdb.detach()
    
    # Check which targets did not not successfully find code
    for target, retries in retry_count.items():
        if retries >= WATCH_TRIGGER_MAX_RETRIES:
            raise RuntimeError(f'Max retries reached for target {target}')

    return results


def _code_on_watch_trigger(name, watch, data, hack, modules, gdb, results):
    # TODO: Detect useless accesses (e.g. no offset)
    # TODO: Smarter code selection (e.g. function boundary analysis)
    # Remove the watch as we have successfully triggered
    gdb.remove_watch(watch)
    # Get address of instruction which caused the watch to trigger
    instruction_address = int(data['frame']['addr'], base=16)
    # Read memory surrounding the address of this instruction
    raw_code = hack.read_bytes(instruction_address - INSTRUCTION_READ_DISTANCE, INSTRUCTION_READ_DISTANCE * 2)
    # Try calculate best memory range in which to find the code for speeding up future scans
    begin, size = _code_get_best_begin_and_size_for_scans(hack, modules, instruction_address)
    # Extract searchable bytes from the raw code near the instruction address
    decoder = InstructionDecoder(hack.process.arch)
    for (o, i) in decoder.iter(raw_code):
        print(o, decoder.format(i))

    searchable_code, offset, offset_size = decoder.extract_searchable_bytes(raw_code, INSTRUCTION_READ_DISTANCE - 1)
    # Add code result when everything has been calculated
    results.append((name, Code(
        offset=offset,
        offset_size=offset_size,
        begin=begin,
        size=size,
        code=Code.bytes_to_string(searchable_code)
    )))


def _code_get_best_begin_and_size_for_scans(hack, modules, instruction_address):
    # If the code can be found in a dynamic library, then use the name of the dynamic library
    for name, (begin, size) in modules.items():
        if begin <= instruction_address < begin + size:
            return name, 0

    # Otherwise chop off top bits as an estimate
    begin = _code_mask_estimated_begin(instruction_address, hack.process.max_ptr, significant_hex_chars=3)
    return begin, _code_mask_estimated_size(begin)


def _code_mask_estimated_begin(begin, max_ptr, significant_hex_chars=3):
    return begin & (max_ptr & ~(max_ptr >> (significant_hex_chars * 4)))


def _code_mask_estimated_size(begin):
    mask = 0
    for i in range(0, 64):
        m = (0x1 << i)
        if m < begin:
            mask |= (~begin & m)
    return mask

#endregion

#region Code Scan Implementation

_CHAR_PERIOD_IN_HEX = '2E'
_CHAR_PERIOD_REPLACEMENT = '??'
_OFFSET_PACK_FORMAT = {1: 'B', 2: 'H', 4: 'L', 8: 'LL'}


def _code_scan_in_process(hack, code):
    if not hack.process.attached:
        raise RuntimeError('You must first attach the hack to a process before using the CodeScanner')

    raw_code = Code.string_to_bytes(code.code)
    begin, size = _code_scan_get_begin_size(hack, code)

    # First scan preferred region
    # results = hack.scan(raw_code, begin, size, 1, True, False)
    results = hack.scan(MemoryScan.str(raw_code, begin, size, max_results=1, regex=True, threaded=False))

    # Otherwise scan entire memory range
    if not results:
        # TODO: scan only target process memory instead of whole thing?
        # results = hack.scan(raw_code, 0, hack.process.max_ptr, 1, True)
        results = hack.scan(MemoryScan.str(raw_code, 0, hack.process.max_ptr, max_results=1, regex=True, threaded=False))

        if not results:
            raise RuntimeError(f'Did not find any results for Code[{code.code}]')

    # Extract offset from loaded code in memory
    address = results[0]
    data = hack.read_bytes(address, len(raw_code))

    decoder = InstructionDecoder(hack.process.arch)
    print(data)
    for offset, inst in decoder.iter(data):
        print(offset, decoder.format(inst))

    offset = _code_unpack_offset(data, code.offset, code.offset_size)
    return CodeScanResult(address, offset)


def _code_bytes_to_string(raw_code: bytes) -> str:
    raw_code_string = hexlify(raw_code).decode('utf8').upper()
    raw_code_string = raw_code_string.replace(_CHAR_PERIOD_IN_HEX, _CHAR_PERIOD_REPLACEMENT)
    return re.sub('[0-9A-Z?]{2} ?', lambda m: m.group(0) + ' ', raw_code_string)[:-1]


def _code_scan_get_begin_size(hack, code) -> (int, int):
    begin, size = code.begin, code.size
    if isinstance(begin, str):
        modules = hack.process.modules
        # TODO: Check for invalid module name
        begin, s = modules[code.begin]
        size = code.size or s

    size = min(size or hack.process.max_ptr, hack.process.max_ptr - begin)
    return begin, size


def _code_string_to_bytes(code: str) -> bytes:
    return unhexlify(code.replace(' ', '').replace(_CHAR_PERIOD_REPLACEMENT, _CHAR_PERIOD_IN_HEX))


def _code_unpack_offset(data, offset, offset_size):
    offset_bytes = data[offset:offset + offset_size]
    return struct.unpack(_OFFSET_PACK_FORMAT[offset_size], offset_bytes)[0]

#endregion
