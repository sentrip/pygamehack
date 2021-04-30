import contextlib
import importlib
import pathlib
import os
from typing import List, Tuple, Union

from .code import Code
from .struct_parser import *

__all__ = ['StructFile']


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

    def update_code(self, code_definitions: List[Tuple[str, Code]]):
        self._impl.update_code(code_definitions)

    def update_offsets(self, offsets: List[Tuple[str, Union[int, List[int]]]]):
        self._impl.update_offsets(offsets)


#endregion

#region StructFileImpl

class StructFileImpl(object):

    ADDRESS_ROOT_NAME = 'Addresses'
    CODE_ROOT_NAME = 'Code'

    def __init__(self, path):
        self.path = pathlib.Path(path)
        self.module = None
        self.src = ''
        self.all_classes = []
        self.code = []
        self.classes = []
        self.addresses = None
        self.code_dirty = False
        self.addresses_dirty = False
        self.addresses_updated = True
        self.classes_dirty = False
        self.classes_require_update = False
        self.sorted_addresses = []

    def load(self):
        self.load_file()
        self.load_classes()
        self.load_module()
        self.sort_addresses()

    def load_file(self):
        with open(str(self.path)) as f:
            self.src = f.read()
    
    def load_classes(self):
        self.all_classes = string_to_classes(self.src)
        self.addresses = None
        self.code.clear()
        self.classes.clear()
        for c in self.all_classes:
            root_name = c.root().name
            if root_name == StructFileImpl.CODE_ROOT_NAME:
                self.code.append(c)
            elif root_name == StructFileImpl.ADDRESS_ROOT_NAME:
                self.addresses = c
            else:
                self.classes.append(c)

    def load_module(self):
        if self.module:
            importlib.reload(self.module)
        else:
            with StructFileImpl.working_directory(self.path.cwd()):
                self.module = importlib.import_module(self.path.stem)
        
    def flush(self):
        do_write = self.addresses_dirty or self.classes_dirty or self.code_dirty
        
        if self.addresses and self.addresses_dirty:
            self.addresses_dirty = False
            self.src = replace_class_fields_in_string([self.addresses], self.src)

        if self.classes_dirty:
            self.classes_dirty = False
            self.src = replace_class_fields_in_string(self.classes, self.src)
        
        if self.code_dirty:
            self.code_dirty = False
            self.src = replace_class_fields_in_string(self.code, self.src)

        if do_write:
            StructFileImpl.safe_write(str(self.path), self.src)
            importlib.reload(self.module)

    def generate_code(self, code_definitions):
        existing_names = set(v.name for v in self.code)
        tuples = [p for p in StructFileImpl.to_tuples(code_definitions)
                  if p[0].replace(StructFileImpl.CODE_ROOT_NAME + '.', '') not in existing_names]
        generated = tuples_to_classes(tuples)
        self.code.extend(generated)
        gen = PythonAOBCodeGenerator()
        generated_src = classes_to_string(generated, gen)
        self.src += '\n'
        self.src += generated_src
        return existing_names

    def replace_code(self, code_definitions):
        replacer = PythonAOBCodeReplacer()
        tuples = list(StructFileImpl.to_tuples(code_definitions))
        replace_class_fields(tuples_to_classes(tuples), self.code, replacer=replacer)
        self.code_dirty = True
    
    def update_code(self, code_definitions):
        existing_names = self.generate_code(code_definitions)
        updated_defs = [t for t in code_definitions if t[0] in existing_names]
        if updated_defs:
            self.replace_code(updated_defs)

    def update_offsets(self, offsets):
        replace_class_fields(tuples_to_classes(offsets), self.classes)
        self.classes_dirty = True
    
    def add_address(self, name, data):
        raise NotImplementedError("add_address")
        if isinstance(data, int):
            pass
        elif isinstance(data[1], int):
            pass
        else:
            pass
        self.addresses_updated = True

    def remove_address(self, name):
        for i, address in self.sorted_addresses:
            if address[0] == name:
                self.sorted_addresses.pop(i)
                self.addresses_updated = True
                return
        raise KeyError('Unknown address: %s' % name)

    def sort_addresses(self):
        if not self.addresses or not self.addresses_updated:
            return

        self.sorted_addresses.clear()
        manual_addresses = []
        static_addresses = []
        dynamic_addresses = []
        dynamic_address_names = set()
        
        # Split addresses by type
        for name, field in self.addresses.fields.items():
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

        self.sorted_addresses.extend(manual_addresses)
        self.sorted_addresses.extend(static_addresses)
        self.sorted_addresses.extend(sorted_dynamic_addresses)
        self.addresses_updated = False

    def update_addresses(self):
        if self.addresses_updated:
            self.sort_addresses()
        tuples = [(StructFileImpl.ADDRESS_ROOT_NAME + '.' + v[0], (v[1], v[2]))]
        classes = tuples_to_classes(tuples)
        replace_class_fields(classes, [self.addresses])
        self.addresses_dirty = True

    @staticmethod
    def to_tuples(definitions):
        for name, code in definitions:
            yield (StructFileImpl.CODE_ROOT_NAME + '.' + name, code)

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


#region PythonAOBCodeGenerator/PythonAOBCodeReplacer

class PythonAOBCodeGenerator(DefaultPythonCodeGenerator):
    
    def write_field(self, field: 'Field'):
        super().write_field(field)
        self.write_line()

    def field_to_string(self, field: 'Field') -> str:
        inline_values = []
        for k in PythonAOBCodeGenerator._inline_keys:
            data = getattr(field.data, k)
            if k == 'begin' or k == 'size':
                data = f'0x{data:08X}'
            elif k == 'offset':
                data = f'0x{data:X}'
            inline_values.append(f"'{k}': {data}")

        dict_indent = ('    ' * field.indent) + (' ' * (PythonAOBCodeGenerator.min_field_name_length + len('= {')))
        
        code_indent = dict_indent + (' ' * len(PythonAOBCodeGenerator._code_prefix))

        code_def = ('\n' + code_indent).join(
            f"'{v}'" for v in PythonAOBCodeGenerator._code_lines(field.data.code, code_indent))

        full_code_def = f"{{{', '.join(inline_values)},\n{dict_indent}'code': {code_def}}}"

        fmt = '{:%ds}= {}' % self.min_field_name_length

        return fmt.format(field.name, full_code_def)
    
    @staticmethod
    def _code_lines(code: str, indent: str):
        remaining_line_size = PythonAOBCodeGenerator.max_line_length - len(indent)
        max_code_size_bytes = int(remaining_line_size / 3) - 1
        for i in range(0, len(code), max_code_size_bytes * 3):
            yield code[i: i + max_code_size_bytes * 3]

    _code_prefix = "'code': "
    _inline_keys = ['offset', 'offset_size', 'begin', 'size']
    _keys_with_hex_value = {'begin', 'size'}


class PythonAOBCodeReplacer(DefaultPythonCodeReplacer):
    
    def replace(self, src: 'Field', dst: 'Field'):
        super().replace(src, dst)
    
    def regenerate(self, field: 'Field', previous_lines: [str]) -> str:
        return super().regenerate(field, previous_lines)

#endregion
