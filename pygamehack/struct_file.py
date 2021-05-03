import contextlib
import importlib
import pathlib
import os
from typing import List, Tuple, Union

from pygamehack.c import Address
from .code import Code
from .struct_parser import *

__all__ = [
    'StructFile',
    'PythonAddressSourceGenerator', 'PythonStructSourceGenerator', 'PythonCodeSourceGenerator'
]


#region StructFile

class StructFile(object):
    """
    Class that is used to read/modify/update pygamehack Addresses, Structs and Code defined in a file
    """
    def __init__(self, path: str):
        self._impl = StructFileImpl(path)

    def load(self):
        self._impl.load()

    def flush(self):
        self._impl.flush()

    def add_address(self, name: str, data: Union[int, Tuple[str, int], Tuple[Address, List[int]]]):
        self._impl.add_address(name, data)

    def remove_address(self, name: str):
        self._impl.remove_address(name)

    def update_code(self, code_definitions: List[Tuple[str, Code]]):
        self._impl.update_code(code_definitions)

    def update_offsets(self, offsets: List[Tuple[str, Union[int, List[int]]]]):
        self._impl.update_offsets(offsets)


#endregion

#region StructFileImpl

ADDRESS_ROOT_NAME = 'Address'
CODE_ROOT_NAME = 'Code'
INVALID_LINENO = 1000000000000


class FilePart(object):
    def __init__(self, generator):
        self.dirty = False
        self.classes = []
        self.linenos = [INVALID_LINENO, 0]
        self.generator = generator

    @property
    def has_valid_lines(self):
        return self.linenos[0] != INVALID_LINENO

    def reset_linenos(self):
        self.linenos = [INVALID_LINENO, 0]

    def append_lines(self, lines, new_lines):
        # Update line numbers
        self.linenos[0] = len(lines)
        self.linenos[1] = self.linenos[0] + len(new_lines)
        # Add lines to end
        lines.extend(new_lines)

    def replace_lines(self, lines, new_lines, line_offset):
        # Replace lines
        offset_lineno, offset_end_lineno = self.linenos[0] + line_offset, self.linenos[1] + line_offset
        updated_lines = lines[:offset_lineno] + new_lines + lines[offset_end_lineno:]
        lines.clear()
        lines.extend(updated_lines)
        # Update line offset
        old_size = self.linenos[1] - self.linenos[0]
        new_size = len(new_lines)
        extra_line_offset = (new_size - old_size)
        # Update line numbers
        self.linenos[0] = offset_lineno
        self.linenos[1] = offset_lineno + new_size
        return extra_line_offset


class StructFileImpl(object):
    def __init__(self, path):
        self.path = pathlib.Path(path)
        self.module = None
        self.src = ''
        self.imported_name = 'gh'
        self.addresses = FilePart(lambda: PythonAddressSourceGenerator())
        self.code = FilePart(lambda: PythonCodeSourceGenerator())
        self.classes = FilePart(lambda: PythonStructSourceGenerator(imported_name=self.imported_name))
        self.parts = [self.classes, self.addresses, self.code]

    def load(self):
        self.load_file()
        self.load_classes()
        self.load_module()

    def load_file(self):
        with open(str(self.path)) as f:
            self.src = f.read()
        self.imported_name = StructFileImpl.detect_imported_name(str(self.path), self.src, 'pygamehack')

    def load_module(self):
        if self.module:
            importlib.reload(self.module)
        else:
            with StructFileImpl.working_directory(self.path.cwd()):
                self.module = importlib.import_module(self.path.stem)

    def load_classes(self):
        all_classes = string_to_classes(self.src)

        for part in self.parts:
            part.reset_linenos()
            part.classes.clear()

        for c in all_classes:
            root_name = c.root().name

            if c.name == CODE_ROOT_NAME:
                self.code.classes = [c]
                self.code.linenos = [c.lineno - 1, c.end_lineno]
            elif c.name == ADDRESS_ROOT_NAME:
                self.addresses.classes = [c]
                self.addresses.linenos = [c.lineno - 1, c.end_lineno]
            elif root_name != ADDRESS_ROOT_NAME and root_name != CODE_ROOT_NAME:
                self.classes.classes.append(c)
                self.classes.linenos = [
                    min(c.lineno - 1, self.classes.linenos[0]),
                    max(c.end_lineno, self.classes.linenos[1])
                ]

    def add_address(self, name, data):
        if not self.addresses.classes:
            self.addresses.classes = [Class(ADDRESS_ROOT_NAME, 0, 0)]

        # TODO: Check data format
        assert name not in self.addresses.classes[0].fields, f"Address already exists with name '{name}'"
        self.addresses.classes[0].fields[name] = Field(self.addresses.classes[0], name, 0, 0, 1, data)
        self.addresses.dirty = True

    def remove_address(self, name):
        if not self.addresses.classes:
            self.addresses.classes = [Class(ADDRESS_ROOT_NAME, 0, 0)]

        assert name in self.addresses.classes[0].fields, f"Address does not exist with name '{name}'"
        del self.addresses.classes[0].fields[name]
        self.addresses.dirty = True

    def update_code(self, code_definitions):
        prefixed = [(f'{CODE_ROOT_NAME}.{n}', d) for n, d in code_definitions]
        classes = tuples_to_classes(prefixed)
        if not self.code.classes:
            self.code.classes = [classes[0].root()]
        update_classes(classes, self.code.classes[0].children)
        self.code.dirty = True

    def update_offsets(self, offsets):
        classes = tuples_to_classes(offsets)
        update_classes(classes, self.classes.classes)
        self.classes.dirty = True

    def flush(self):
        if not (self.addresses.dirty or self.code.dirty or self.classes.dirty):
            return

        if self.addresses.dirty:
            self.sort_addresses()

        self.update_src()

        StructFileImpl.safe_write(str(self.path), self.src)

    def sort_addresses(self):
        if not self.addresses.classes:
            return

        address_root = self.addresses.classes[0]

        manual_addresses = []
        static_addresses = []
        dynamic_addresses = []
        dynamic_address_names = set()

        # Split addresses by type
        for name, field in address_root.fields.items():
            if isinstance(field.data, int):
                manual_addresses.append((name, field.data))
            elif isinstance(field.data[1], int):
                static_addresses.append((name, field.data[0], field.data[1]))
            else:
                dynamic_address_names.add(name)
                dynamic_addresses.append((name, field.data[0], field.data[1]))

        # Sort dynamic addresses by dependency order
        defined_address_names = set()
        sorted_dynamic_addresses = []
        while dynamic_addresses:
            address = next(v for v in dynamic_addresses if v[1] not in dynamic_address_names or v[1] in defined_address_names)
            defined_address_names.add(address[0])
            sorted_dynamic_addresses.append(address)

        sorted_addresses = []
        sorted_addresses.extend(manual_addresses)
        sorted_addresses.extend(static_addresses)
        sorted_addresses.extend(sorted_dynamic_addresses)

        address_root.fields.clear()
        for name, data in sorted_addresses:
            address_root.fields[name] = Field(address_root, name, 0, 0, 1, data)

    def update_src(self):
        lines = self.src.splitlines()

        # Sort parts by order of appearance in the file
        self.parts.sort(key=lambda p: p.linenos[0])

        # For each dirty part, append or replace lines depending on whether it was there before
        line_offset = 0
        for part in self.parts:
            if not part.dirty:
                continue

            new_src = classes_to_string(part.classes, generator=part.generator())
            new_lines = new_src.splitlines()

            if part.has_valid_lines:
                line_offset += part.replace_lines(lines, new_lines, line_offset)
            else:
                part.append_lines(lines, new_lines)

            part.dirty = False

        # Fix class line number definitions
        for part in [self.addresses, self.code]:
            if part.classes:
                c = part.classes[0]
                c.lineno, c.end_lineno = part.linenos
                c.lineno += 1

        # Remove redundant lines at the end
        while len(lines) > 1 and (not lines[-2] or lines[-2] == '\n') and (not lines[-1] or lines[-1] == '\n'):
            lines.pop(-1)

        self.src = '\n'.join(lines)
        self.src += '\n'

    @staticmethod
    def detect_imported_name(path, src, library_name):
        found = False
        index = 0
        while not found and index < len(src):
            index = src.find(library_name, index, -1)
            if index == -1:
                raise RuntimeError(f'Did not find {library_name} import statement in {path}')
            # Skip 'import library_name.<WHATEVER>'
            # Only detect 'import library_name' and 'import library_name as ...'
            after_name = src[index + len(library_name)]
            found = after_name == '\n' or after_name == ' '

        # Extract import statement from src
        line_begin = index - len('import ')
        line_end = src.find('\n', index + len(library_name))
        import_statement = src[line_begin:line_end]

        if 'as' in import_statement:
            return import_statement[import_statement.index('as') + 3:]
        else:
            return library_name

    @staticmethod
    def safe_write(file_name, data, old_file_suffix='_old', temp_file_name='temp_file_name.py'):
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
    @contextlib.contextmanager
    def working_directory(path):
        """Changes working directory and returns to previous on exit."""
        prev_cwd = str(pathlib.Path.cwd())
        os.chdir(path)
        try:
            yield
        finally:
            os.chdir(prev_cwd)


#endregion

#region SourceGenerators

class PythonAddressSourceGenerator(PythonSourceGenerator):
    pass


class PythonStructSourceGenerator(PythonSourceGenerator):
    def __init__(self, imported_name='gh'):
        # imported_name.Struct
        if imported_name:
            struct_base = f'{imported_name}.Struct'
        # Struct is in global namespace
        else:
            struct_base = 'Struct'

        super().__init__(write_int_as_hex=True, base_class=struct_base)


class PythonCodeSourceGenerator(PythonSourceGenerator):
    def write_field(self, field: 'Field'):
        super().write_field(field)
        self.write_line()

    def field_to_string(self, field: 'Field') -> str:
        inline_values = []
        for k in PythonCodeSourceGenerator._inline_keys:
            data = getattr(field.data, k)
            if k == 'begin' or k == 'size':
                data = f'0x{data:08X}'
            elif k == 'offset':
                data = f'0x{data:X}'
            inline_values.append(f"'{k}': {data}")

        dict_indent = ('    ' * field.indent) + (' ' * (PythonCodeSourceGenerator.min_field_name_length + len('= {')))
        
        code_indent = dict_indent + (' ' * len(PythonCodeSourceGenerator._code_prefix))

        code_def = ('\n' + code_indent).join(
            f"'{v}'" for v in PythonCodeSourceGenerator._code_lines(field.data.code, code_indent))

        full_code_def = f"{{{', '.join(inline_values)},\n{dict_indent}'code': {code_def}}}"

        fmt = '{:%ds}= {}' % self.min_field_name_length

        return fmt.format(field.name, full_code_def)
    
    @staticmethod
    def _code_lines(code: str, indent: str):
        remaining_line_size = PythonCodeSourceGenerator.max_line_length - len(indent)
        max_code_size_bytes = int(remaining_line_size / 3) - 1
        for i in range(0, len(code), max_code_size_bytes * 3):
            yield code[i: i + max_code_size_bytes * 3]

    _code_prefix = "'code': "
    _inline_keys = ['offset', 'offset_size', 'begin', 'size']
    _keys_with_hex_value = {'begin', 'size'}


#endregion
