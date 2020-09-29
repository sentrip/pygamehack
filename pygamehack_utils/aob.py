import re
from struct import unpack
from binascii import hexlify, unhexlify
from threading import Thread
from queue import Queue, Empty
from typing import Any, Optional, Union

import pygamehack as gh
import logging

from .debugger import GDB
from .debug_view import DebuggableVariable
from .hackstruct import HackStruct
from .instruction import extract_searchable_raw_code
from .type_helpers import is_hackstruct_type


__all__ = [
    'aob_scan', 'aob_string_to_raw_code', 'raw_code_to_aob_string',
    'AOBFinder', 'AOBScanner'
]

log = logging.getLogger('pygamehack')

_offset_fmt = {1: 'B', 2: 'H', 4: 'L', 8: 'LL'}

_PERIOD_HEX = '2E'


# region AOB scan

def aob_scan(
        hack: gh.Hack,
        aob_string: str,
        offset: int = 0,
        offset_size: int = 4,
        begin: Union[int, str] = 0x00000000,
        size: Optional[int] = None,
        n_results: int = 1
) -> (int, int):
    """

    """
    raw_code = aob_string_to_raw_code(aob_string)
    begin, size = _get_scan_begin_size(hack, begin, size)

    # First scan in preferred region
    results = hack.scan_bytes(raw_code, begin, size, n_results)

    # Otherwise scan entire memory
    if not results:
        log.info(f'Region 0x{begin:X} - 0x{begin+size:X} does not contain {aob_string}')
        log.info(f'Scanning full memory range ({hack.max_ptr})...')
        results = hack.scan_bytes(raw_code, 0, hack.max_ptr, n_results)

    if not results:
        raise RuntimeError(f'Did not find any results for AOB[{aob_string}]')

    data = hack.read_bytes(results[0], len(raw_code))
    offset_bytes = data[offset:offset + offset_size]
    found_offset = unpack(_offset_fmt[offset_size], offset_bytes)[0]

    log.info(f'Offset 0x{found_offset:X} accessed by 0x{results[0]:X} with code: {aob_string}')

    return results[0], found_offset


def aob_string_to_raw_code(aob_string: str) -> bytes:
    return unhexlify(aob_string.replace(' ', '').replace('??', _PERIOD_HEX))


def raw_code_to_aob_string(raw_code: bytes) -> str:
    raw_aob_string = hexlify(raw_code).decode('utf8').upper().replace(_PERIOD_HEX, '??')
    return re.sub('[0-9A-Z?]{2}', lambda m: m.group(0) + ' ', raw_aob_string)[:-1]


def _get_scan_begin_size(hack, begin, size):
    if isinstance(begin, str):
        modules = hack.get_modules()
        # TODO: Check for invalid module name
        begin = modules[begin].begin
        size = size or modules[begin].size

    return begin, min(size or hack.max_ptr, hack.max_ptr - begin)


# endregion


class AOBFinder(object):
    # TODO: Config

    DISABLED = 0
    WRITE = 1
    READ = 2
    DEFAULT_READ_DISTANCE = 16

    def __init__(self, hack: Union[str, gh.Hack], read_distance: int = DEFAULT_READ_DISTANCE):
        self.hack = gh.Hack(hack) if isinstance(hack, str) else hack
        self.read_distance = read_distance
        self.targets = []
        self.results = []
        self._modules = {}
        self._watches = {}

        GDB.kill_process()
        self.dbg = GDB()

        # Allow HackStructs to be created as targets
        if not self.hack.is_attached:
            self.hack.attach()

    def add_target(self, struct: Any, config: Union[bool, dict] = True):
        # struct: HackStruct
        if is_hackstruct_type(struct):
            self._add_hackstruct_target(struct, config)
        # struct: pygamehack.Address
        elif isinstance(struct, gh.Address):
            self.targets.append((struct.name, struct, config))
        else:
            raise RuntimeError('Invalid args - only HackStruct or pygamehack.Address is allowed')

    def find_all(self) -> [dict]:
        if not self._modules:
            self._modules = self.hack.get_modules()

        self.dbg.attach(self.hack.process_id)
        self.hack.load_addresses()

        for name, address, write in self.targets:
            self._watches[name] = self.dbg.watch_address(name, address.address, self._on_update, write=write)

        self.dbg.watch_for_changes()

        self.dbg.exit()

        results = [i for i in self.results]
        self.results.clear()
        return results

    @staticmethod
    def begin_mask(lhs, rhs):
        mask = 0
        for i in range(0, 64):
            mask |= (lhs & (0x1 << i)) & (rhs & (0x1 << i))
        return mask

    @staticmethod
    def size_mask(v):
        mask = 0
        for i in range(0, 64):
            m = (0x1 << i)
            if m < v:
                mask |= (~v & m)
        return mask

    @staticmethod
    def estimated_begin_mask(begin, max_ptr, significant_hex_chars=3):
        return begin & (max_ptr & ~(max_ptr >> (significant_hex_chars * 4)))

    def _add_hackstruct_target(self, struct, config):
        for name, v in HackStruct.iter_variables(struct):
            if not is_hackstruct_type(v) or isinstance(v, DebuggableVariable):
                property_path = v.__class__.__name__ if name is None else f'{v.__class__.__name__}.{name}'
                if isinstance(config, dict):
                    c = config.get(property_path, AOBFinder.WRITE)
                    if c != AOBFinder.DISABLED:
                        self.targets.append((property_path, v.debug_address_to_watch(), c == AOBFinder.WRITE))
                else:
                    self.targets.append((property_path, v.debug_address_to_watch(), config))

    def _get_begin_and_size(self, instruction_address):
        # If the code can be found in a dll, then use the name of the dll
        for name, (begin, size) in self._modules.items():
            if begin <= instruction_address < begin + size:
                return name, None
        # Otherwise chop off top bits as an estimate
        begin = AOBFinder.estimated_begin_mask(instruction_address, self.hack.max_ptr, significant_hex_chars=3)
        return begin, AOBFinder.size_mask(begin)

    def _on_update(self, name, result):
        if name not in self._watches:
            return

        # TODO: Detect useless accesses (e.g. no offset)

        del self._watches[name]
        self.dbg.remove_watch(result['wpt']['number'])
        instruction_address = int(result['frame']['addr'], base=16)

        # TODO: Smarter code selection (e.g. function boundary analysis)
        raw_code = self.hack.read_bytes(instruction_address - self.read_distance, self.read_distance * 2)

        begin, size = self._get_begin_and_size(instruction_address)

        raw_code, offset, offset_size = extract_searchable_raw_code(raw_code, instruction_end_offset=self.read_distance)

        log.debug(f'{name} accessed with code at 0x{instruction_address:X}')

        self.results.append({
            'name': name,
            'aob_string': raw_code_to_aob_string(raw_code),
            'offset': offset,
            'offset_size': offset_size,
            'begin': begin,
            'size': size
        })


class AOBScanner(object):

    def __init__(self, process_name: str):
        self.process_name = process_name
        self.input_queue = Queue()
        self.output_queue = Queue()
        self._seen_searches = {}

    def add_aob(
            self,
            name: str = '',
            aob_string: str = '',
            offset: int = 0,
            offset_size: int = 4,
            begin: Union[int, str] = 0x00000000,
            size: Optional[int] = None,
            **_  # this is so you can pass arbitrary kwargs without errors
    ):
        """

        """
        search = (offset, offset_size, aob_string)

        if search in self._seen_searches:
            self._log_duplicate(name, search)
        else:
            self._seen_searches[search] = name
            self.input_queue.put((name, aob_string, offset, offset_size, begin, size))

    def scan(self, *, n_threads=4) -> [(str, int)]:
        """

        """
        n_threads = min(self.input_queue.qsize(), n_threads)
        workers = []

        for i in range(n_threads):
            worker = Thread(target=_scan_until_no_input, args=(self.process_name, self.input_queue, self.output_queue))
            worker.start()
            workers.append(worker)

        for worker in workers:
            worker.join()

        results = []

        while not self.output_queue.empty():
            results.append(self.output_queue.get())

        return results

    def _log_duplicate(self, name, search):
        offset, offset_size, aob_string = search
        log.warning(f"Skipping duplicate - {name}")
        msg = '\nThe duplicates are:\n'
        for n in [self._seen_searches[search], name]:
            msg += '\t' + f'{n:40} - offset = {offset:2}, offset_size = {offset_size:2}, aob = {aob_string}\n'
        log.debug(msg)


def _scan_until_no_input(process_name, input_queue, output_queue):
    hack = gh.Hack(process_name)
    hack.attach()

    while not input_queue.empty():
        try:
            name, *rest = input_queue.get(timeout=0.01)
        except (TimeoutError, Empty):
            continue
        instruction_address, offset = aob_scan(hack, *rest, n_results=1)
        output_queue.put((name, offset, instruction_address))
