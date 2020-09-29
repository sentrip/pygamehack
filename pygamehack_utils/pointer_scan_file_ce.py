import math
import pathlib
import struct
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
from typing import Optional, Tuple, Union
try:
    import pygamehack as gh
except ImportError:
    # We only need this for type hints
    class gh:
        Hack = None


DEFAULT_MAX_LEVEL = 7  # This is the default in Cheat Engine


@dataclass
class StaticAddress:
    name: str
    offset: int
    count: int

    module_id: int
    flags: int

    def __eq__(self, other):
        return self.offset == other.offset and self.name == other.name

    def __hash__(self):
        return hash(self.name) + hash(self.offset)


@dataclass
class DynamicAddress:
    address: StaticAddress
    offsets: [int]

    module_index: int


@dataclass
class PointerScanModule:
    module_id : int    # 0x00, size=2
    flags     : int    # 0x02, size=4
    size      : int    # 0x06, size=4
    name      : str    # 0x0A, size=1 * (size + 2)
    # TOTAL = 10 + 1 * (size + 2)

    @classmethod
    def load(cls, data: bytes) -> ['PointerScanModule']:
        modules = []
        current = 0
        to_read = len(data)

        while current + 12 < to_read:
            module_id = struct.unpack('H', data[current:current + 2])[0]
            flags, size = struct.unpack('LL', data[current + 2:current + 2 + 8])
            name = struct.unpack(f'<{size}s', data[current + 10:current + 10 + size])[0]

            module = PointerScanModule(module_id, flags, size, name.decode('utf8'))
            modules.append(module)

            size_bytes = 2 + (2 * 4) + (size + 2)
            current += size_bytes

        return modules


@dataclass
class PointerScanResult:
    module_index : int    # 0x00, size=4
    offset       : int    # 0x04, size=4
    # pad        : int    # 0x08, size=4
    n_offsets    : int    # 0x0C, size=4
    offsets      : [int]  # 0x10, size=4 * n_offsets
    # TOTAL = 16 + 4 * n_offsets

    @classmethod
    def load(cls, data: bytes, max_level: int = 7) -> ['PointerScanResult']:

        results = []
        current = 0
        to_read = len(data)

        size_bits = 32 + 32 + 32 + 32 + (32 * max_level)
        size_bytes = int(math.ceil(size_bits / 8))

        while current < to_read:
            offsets_begin = current + 16
            module_index, offset, _, n_offsets = struct.unpack('LLLL', data[current:offsets_begin])

            offsets_end = offsets_begin + (n_offsets * 4)
            offsets = struct.unpack('L' * n_offsets, data[offsets_begin:offsets_end])

            results.append(PointerScanResult(module_index, offset, n_offsets, list(reversed(offsets))))
            current += size_bytes

        return results


class PointerScanFile:

    # CheatEngine

    @staticmethod
    def load(path_str: str, max_level: int = DEFAULT_MAX_LEVEL) -> (bytes, [StaticAddress], [DynamicAddress]):
        """

        """
        path = pathlib.Path(path_str)

        data = path.read_bytes()
        modules = PointerScanModule.load(data)

        static_addresses = {}
        dynamic_addresses = []

        results = _get_results_from_path_threaded(path, max_level)

        for result in results:
            module = modules[result.module_index]
            static = StaticAddress(module.name, result.offset, 0, module.module_id, module.flags)

            existing = static_addresses.get(static, None)
            if existing is None:
                existing = static
                static_addresses[static] = static

            existing.count += 1
            dynamic_addresses.append(DynamicAddress(existing, result.offsets, result.module_index))

        return data, list(static_addresses.values()), dynamic_addresses

    @staticmethod
    def save(path_str: str, original_ptr_file: bytes, addresses: [DynamicAddress], max_level: int = DEFAULT_MAX_LEVEL):
        """

        """
        path = pathlib.Path(path_str)

        with open(str(path), 'wb') as f:
            f.write(original_ptr_file)

        with open(str(path) + '.results.1', 'wb') as f:
            for address in addresses:
                f.write(struct.pack('LLLL', address.module_index, address.address.offset, 0, len(address.offsets)))
                full_offsets = list(reversed(address.offsets)) + [0] * (max_level - len(address.offsets))
                f.write(struct.pack('L' * max_level, *full_offsets))

    @staticmethod
    def clean(path_str: str, target_path_str: str, max_level: int = DEFAULT_MAX_LEVEL):
        """

        """
        path = pathlib.Path(path_str)
        original, _, dynamic = PointerScanFile.load(str(path), max_level=max_level)
        target_path = pathlib.Path(target_path_str)
        if target_path.is_dir():
            target_path = target_path + path.name
        PointerScanFile.save(target_path, original, dynamic)

    # pygamehack

    @staticmethod
    def load_into_hack(
            hack: gh.Hack,
            path_str: str,
            name: str,
            skip_last_n_offsets: int = 0,
            max_level: int = DEFAULT_MAX_LEVEL
    ):
        _, static, dynamic = PointerScanFile.load(path_str, max_level=max_level)

        static_addresses = {}

        for i, address in enumerate(static):
            static_addresses[address] = hack.add_static_address(f'{name}_{i}_static', address.name, address.offset)

        if not dynamic:
            return

        offsets = dynamic[0].offsets[:len(dynamic[0].offsets) - skip_last_n_offsets]
        original = hack.add_dynamic_address(f'{name}', static_addresses[dynamic[0].address], offsets)

        for address in dynamic[1:]:
            offsets = address.offsets[:len(address.offsets) - skip_last_n_offsets]
            original.add_backup(static_addresses[address.address], offsets)

    @staticmethod
    def rescan(
            hack: gh.Hack,
            static: [StaticAddress],
            dynamic: [DynamicAddress],
            value_and_type: Optional[Tuple[Union[int, float], str]] = None
    ) -> [DynamicAddress]:
        """

        """
        read_method = None if value_and_type is None else 'read_' + value_and_type[1]

        static_addresses = {}
        modules = hack.get_modules()

        for address in static:
            static_addresses[address] = modules[address.name][0] + address.offset

        valid = []
        for address in dynamic:
            addr = hack.manual_address(static_addresses[address.address])
            addr.add_offsets(address.offsets)
            addr.load()
            if addr.is_valid():

                if read_method is not None:
                    value = getattr(hack, read_method)(addr.address)
                    if value != value_and_type[0]:
                        continue

                valid.append(address)

        return valid

    @staticmethod
    def rescan_update(
            hack: gh.Hack,
            path_str: str,
            value_and_type: Optional[Tuple[Union[int, float], str]] = None,
            max_level: int = DEFAULT_MAX_LEVEL
    ):
        original, static, dynamic = PointerScanFile.load(path_str, max_level=max_level)
        valid = PointerScanFile.rescan(hack, static, dynamic, value_and_type=value_and_type)
        PointerScanFile.save(path_str, original, valid, max_level=max_level)


def _get_results_from_path_threaded(path, max_level, n_threads=20):
    def put_result(q, pt):
        rs = PointerScanResult.load(pt.read_bytes(), max_level)
        for r in rs:
            q.put(r)

    queue = Queue()
    with ThreadPoolExecutor(max_workers=n_threads) as pool:
        futures = []
        prefix = path.name + '.results'
        for p in path.parent.iterdir():
            if p.name.startswith(prefix):
                futures.append(pool.submit(put_result, queue, p))

        for f in futures:
            f.result()

    results = []
    while not queue.empty():
        results.append(queue.get_nowait())
    return results


if __name__ == '__main__':
    pth = 'C:\\Users\\djord\\Desktop\\Projects\\BrawlhallaCheat\\Scans\\Scans\\'
    PointerScanFile.clean(pth + 'MainMenuUpdated.PTR', pth + 'MainMenuTest.PTR', max_level=7)
