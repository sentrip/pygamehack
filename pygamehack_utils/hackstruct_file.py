
import contextlib
import importlib
import os
import pathlib
from typing import Callable, List, Tuple

from .aob import AOBFinder
from .parser import *
from .parser import Class
from .type_helpers import is_hackstruct_type, unwrap_type


@contextlib.contextmanager
def working_directory(path):
    """Changes working directory and returns to previous on exit."""
    prev_cwd = str(pathlib.Path.cwd())
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev_cwd)


class HackStructFile(object):

    class Struct:
        def __init__(self, struct, aob):
            self.struct = struct
            self.aob = aob

    def __init__(self, hackstruct_path: str):
        self.hackstruct_path = pathlib.Path(hackstruct_path)
        self.hackstruct_file = self.hackstruct_path.parts[-1]
        self.hackstruct_src = ''
        self.module = None
        self.add_addresses = lambda h: None
        self.structs = {}
        self.aob = {}
        self.root_structs = []

    def address_path_to_aob_path(self, path: str) -> str:
        parts = path.split('/')
        cls = [c for c in self.root_structs if c.address == parts[0]][0]

        offset_path = 'AOB'

        for part in parts[1:]:
            variable_type = unwrap_type(cls.__annotations__[part])
            offset_path += f'.{variable_type.__name__ if is_hackstruct_type(variable_type) else part}'
            cls = variable_type

        return offset_path

    def load(self):
        with working_directory(str(self.hackstruct_path.cwd())):
            self.module = importlib.import_module(self.hackstruct_file.replace('.py', ''))

            with open(self.hackstruct_file) as f:
                self.hackstruct_src = f.read()
                classes = string_to_classes(self.hackstruct_src)

        self.add_addresses = self.module.add_addresses
        self.structs = {}
        self.root_structs = []
        self.aob = {c.name: c for c in classes if c.root().name == 'AOB'}

        for cls in classes:
            if not cls.name == cls.root().name:
                continue

            loaded_struct = HackStructFile.Struct(getattr(self.module, cls.name, None), self.aob.get(cls.name, None))

            self.structs[cls.name] = loaded_struct

            if loaded_struct.struct:
                address = getattr(loaded_struct.struct, 'address', None)
                if address and isinstance(address, str):
                    self.root_structs.append(loaded_struct.struct)

    # Modify

    def generate_aob(
            self,
            find: Callable[[], List[Any]],
            reload_when_complete: bool = True
    ) -> List[Any]:
        results = find()

        replacer = AOBPythonCodeReplacer()
        original_classes = list(self.aob.values())
        tuples = [(self.address_path_to_aob_path(r['name']), r) for r in results]
        replace_class_fields(tuples_to_classes(tuples), original_classes, replacer=replacer)
        new_code = replace_class_fields_in_string(original_classes, self.hackstruct_src, replacer=replacer)

        print(new_code)

        with working_directory(str(self.hackstruct_path.cwd())):
            # HackStructFile._safe_write(self.hackstruct_file, new_code)
            pass

        # if reload_when_complete:
        #     self.load()

        return results

    def update_offsets(
            self,
            scan : Callable[[List[Class]], List[Tuple[str, Any]]],
            reload_when_complete: bool = True
    ) -> List[Tuple[str, Any]]:
        """
        Read an offsets file to perform an aob scan, and write the updated offsets into that file and improve scan ranges
        REQUIRES AOB SCANNER (the process you want to scan must be running)
        REQUIRES DEFINED OFFSETS AND AOB
        """

        classes = string_to_classes(self.hackstruct_src)
        aob_classes = [c for c in classes if c.root().name == 'AOB']

        results = scan(aob_classes)

        # Update offsets
        # TODO: HANDLE DUPLICATE SCANS

        replacer = DefaultPythonCodeReplacer()
        new_classes = tuples_to_classes([(name.replace('AOB.', ''), offset) for name, offset, _ in results])
        new_offsets_src, _ = HackStructFile._updated_src(
            (self.hackstruct_src, [c for c in classes if c.name != 'AOB']),
            new_classes,
            '',
            skip_fields=HackStructFile._hackstruct_skip_fields,
            replacer=replacer
        )

        # Improve scan ranges
        new_aob_classes = tuples_to_classes([(name, begin) for name, _, begin in results])
        new_src, _ = HackStructFile._updated_src(
            new_offsets_src,
            new_aob_classes,
            'AOB',
            replacer=AOBPythonCodeReplacer(line_offset=replacer.line_offset)
        )

        print(new_src)

        with working_directory(str(self.hackstruct_path.cwd())):
            # HackStructFile._safe_write(self.hackstruct_file, new_code)
            pass

        # if reload_when_complete:
        #     self.load()

        return results

    # Implementation

    _hackstruct_skip_fields = {'address', 'debug_config', 'debug_address', 'debug_address_to_watch', 'debug_string'}

    @staticmethod
    def _safe_write(file_name, data, old_file_suffix='_old', temp_file_name='temp_file_name.py'):
        # write to temp and swap files
        old_file_name = file_name.replace('.py', f'{old_file_suffix}.py')
        try:
            # if the file exists then safe write must be used
            if os.path.exists(file_name):
                with open(temp_file_name, 'w') as f:
                    f.write(data)
                os.rename(file_name, old_file_name)
                os.rename(temp_file_name, file_name)
            # if the file does not exist write directly
            else:
                with open(file_name, 'w') as f:
                    f.write(data)

        except Exception as e:
            raise e

        # delete temp/renamed old file
        finally:
            if os.path.exists(temp_file_name):
                os.remove(temp_file_name)
            if os.path.exists(old_file_name):
                os.remove(old_file_name)

    @staticmethod
    def _updated_src(src, new_classes, root_name, skip_fields=None, replacer=None):
        skip_fields = skip_fields or []
        src, classes = (src, string_to_classes(src)) if isinstance(src, str) else src
        existing_classes = [cls for cls in classes if cls.root().name == (root_name or cls.name)]
        replace_class_fields(new_classes, existing_classes, skip_fields=skip_fields, replacer=replacer)
        return replace_class_fields_in_string(existing_classes, src, skip_fields=skip_fields,
                                              replacer=replacer), classes


# region AOB Code Generation

class AOBPythonCodeGenerator(DefaultPythonCodeGenerator):

    _aob_prefix = "'aob': "
    _inline_keys = ['offset', 'offset_size', 'begin', 'size']
    _keys_with_hex_value = {'begin', 'size'}

    def write_field(self, field: 'Field'):
        super().write_field(field)
        self.write_line()

    def field_to_string(self, field: 'Field') -> str:
        inline_keys = ', '.join(f"'{k}': {f'0x{field.data[k]:08X}' if (k == 'begin' or k == 'size') else field.data[k]}"
                                for k in AOBPythonCodeGenerator._inline_keys)

        dict_indent = ('    ' * field.indent) + (' ' * (AOBPythonCodeGenerator.min_field_name_length + len('= {')))
        aob_indent = dict_indent + (' ' * len(AOBPythonCodeGenerator._aob_prefix))

        aob_def = ('\n' + aob_indent).join(
            f"'{v}'" for v in AOBPythonCodeGenerator._aob_lines(field.data['aob'], aob_indent))

        return f"{{{inline_keys},\n{dict_indent}'aob': {aob_def}}}"

    @staticmethod
    def _aob_lines(aob: str, indent: str):
        remaining_line_size = AOBPythonCodeGenerator.max_line_length - len(indent)
        max_aob_size_bytes = int(remaining_line_size / 3) - 1
        for i in range(0, len(aob), max_aob_size_bytes * 3):
            yield aob[i: i + max_aob_size_bytes * 3]


class AOBPythonCodeReplacer(DefaultPythonCodeReplacer):

    def replace(self, current: 'Field', target: 'Field'):
        current_begin = current.data if isinstance(current.data, int) else current.data['begin']
        target.data['begin'] = AOBFinder.begin_mask(target.data['begin'], current_begin)
        target.data['size'] = AOBFinder.size_mask(target.data['begin'])

    def regenerate(self, field: 'Field', previous_lines: [str]) -> str:
        return AOBPythonCodeGenerator.generate_field(field)


# endregion
