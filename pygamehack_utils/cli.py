import argparse

import pygamehack as gh
from .aob import AOBScanner, AOBFinder
from .parser import classes_to_tuples
from .hackstruct_file import HackStructFile
from .pointer_scan_file_ce import PointerScanFile, DEFAULT_MAX_LEVEL
from pygamehack_gui.pycheatengine import gui_main

"""
========================================= HACK DEVELOPMENT/REVERSE ENGINEERING =========================================
Steps:
    REVERSING: 
    1. Find static and dynamic addresses with Cheat Engine (or similar)
    2. Reverse engineer structs with ReClass.NET
    3. Use pygamehack plugin to generate hackstruct file OR manually create/add to hackstruct file
    
    OFFSETS:
    4. Use 'generate_aob_classes' and offsets file to generate/add to the aob class in hackstruct file
    
    UPDATE:
    5. Use 'update_offsets_in_file' and offsets file to update offsets in hackstruct file
 

To ensure your hack lasts long as possible:

When starting a new hack or adding to an existing hack:
    Do steps 1-3 as needed
    Do steps 4-5

When the game updates:
    Do step 5


NOTE: The more time spent on the config for 'generate_aob_class', the more efficient the search/debug sessions.

Steps 1-3 - manual (step 3 can be automated with the pygamehack plugin)
Step  4   - manual (minimal, you have to change values in the process which can be quick with the gui or right config)
Step  5   - automatic (the target process must be running and the scan may take long but it should be fast)
 
 
 
========================================================================================================================
=========================================== CHEAT ENGINE POINTER SCAN FILES ============================================
Steps:
 
 
 
========================================================================================================================
"""


def get_args(parser_name=None):
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    parsers = {}

    for name in ['gui', 'generate', 'update']:
        p = subparsers.add_parser(name)
        parsers[name] = p
        p.add_argument('process_name', nargs=1, type=str)
        p.add_argument('hackstruct_file', nargs=1, type=str)

    parsers['update'].add_argument('--threads', type=int, default=4)

    clean = subparsers.add_parser('clean')
    clean.add_argument('path', type=str)
    clean.add_argument('target_path', type=str)
    clean.add_argument('-l', '--max-level', type=int, default=DEFAULT_MAX_LEVEL)

    rescan = subparsers.add_parser('rescan')
    rescan.add_argument('process_name', nargs=1, type=str)
    rescan.add_argument('pointer_scan_file_name', nargs=1, type=str)
    rescan.add_argument('-v', '--value', default=None)
    rescan.add_argument('-t', '--value-type', type=str, default='uint32')
    rescan.add_argument('-l', '--max-level', type=int, default=DEFAULT_MAX_LEVEL)

    return parser.parse_args() if parser_name is None else parsers[parser_name].parse_args()


def gui(command='gui'):
    """
    Run the PyCheatEngine gui
    If process and hackstruct file are provided then it will attach to process and load hackstruct file
    """
    args = get_args(command)
    gui_main(process_name=args.process_name, hackstruct_file_name=args.hackstruct_file)


def generate_aob_classes(command='generate'):
    """
    Read an offsets file and hackstruct file to generate an AOB class that is written to the offsets file
    REQUIRES AOB FINDER/DEBUGGER (you have to manually make the target values change so the debugger can detect changes)
    REQUIRES DEFINED OFFSETS
    """
    args = get_args(command)
    process_name, hackstruct_file_name = args.process_name, args.hackstruct_file
    # TODO: Take config from command line
    config = {}

    hackstruct_file = HackStructFile(hackstruct_file_name)
    hackstruct_file.load()

    def find():
        from brawl_structs import Game
        hack = gh.Hack(process_name)
        finder = AOBFinder(hack)
        finder.add_target(Game(hack))
        return finder.find_all()

    hackstruct_file.generate_aob(find, reload_when_complete=False)


def update_offsets_in_file(command='update'):
    """
    Read an offsets file to perform an aob scan, and write the updated offsets into that file and improve scan ranges
    REQUIRES AOB SCANNER (the process you want to scan must be running)
    REQUIRES DEFINED OFFSETS AND AOB
    """
    args = get_args(command)
    process_name, hackstruct_file_name = args.process_name, args.hackstruct_file
    n_threads = args.threads

    hackstruct_file = HackStructFile(hackstruct_file_name)
    hackstruct_file.load()

    def scan(aob_classes):
        scanner = AOBScanner(process_name)

        for name, data in classes_to_tuples(aob_classes):
            scanner.add_aob(name=name, aob_string=data['aob'], **data)

        return scanner.scan(n_threads=n_threads)

    hackstruct_file.update_offsets(scan, reload_when_complete=False)


def pointer_scan_file_ce_clean(command='clean'):
    """

    """
    args = get_args(command)
    PointerScanFile.clean(args.path, args.target_path, max_level=args.max_level)


def pointer_scan_file_ce_rescan(command='rescan'):
    """

    """
    args = get_args(command)
    hack = gh.Hack(args.process_name)
    value_and_type = (args.value, args.value_type) if args.value is not None else None
    PointerScanFile.rescan_update(hack, args.pointer_scan_file_name,
                                  value_and_type=value_and_type, max_level=args.max_level)


# def _safe_write(file_name, data, old_file_suffix='_old', temp_file_name='temp_file_name.py'):
#     # write to temp and swap files
#     old_file_name = file_name.replace('.py', f'{old_file_suffix}.py')
#     try:
#         # if the file exists then safe write must be used
#         if os.path.exists(file_name):
#             with open(temp_file_name, 'w') as f:
#                 f.write(data)
#             os.rename(file_name, old_file_name)
#             os.rename(temp_file_name, file_name)
#         # if the file does not exist write directly
#         else:
#             with open(file_name, 'w') as f:
#                 f.write(data)
#
#     except Exception as e:
#         raise e
#
#     # delete temp/renamed old file
#     finally:
#         if os.path.exists(temp_file_name):
#             os.remove(temp_file_name)
#         if os.path.exists(old_file_name):
#             os.remove(old_file_name)
#
#
# def _updated_src(src, new_classes, root_name, skip_fields=None, replacer=None):
#     skip_fields = skip_fields or []
#     src, classes = (src, string_to_classes(src)) if isinstance(src, str) else src
#     existing_classes = [cls for cls in classes if cls.root().name == root_name]
#     replace_class_fields(new_classes, existing_classes, skip_fields=skip_fields, replacer=replacer)
#     return replace_class_fields_in_string(existing_classes, src, skip_fields=skip_fields, replacer=replacer), classes
# def generate_offsets_file():
#     """
#     Read a hackstruct file to generate Offsets class that contains all offsets of defined structs
#     Also replaces properties in the hackstruct file that have defined offsets in the offsets file
#     NOTE: If the offsets file exists, the properties with defined offsets in the offsets file are used instead
#     """
#     offsets_file_name, hackstruct_file_name = sys.argv[1:3]
#
#     with open(hackstruct_file_name) as f:
#         hackstruct_src = f.read()
#
#     hackstruct_classes = string_to_classes(hackstruct_src)
#
#     tuples = [('Offsets.' + v[0], *v[1:]) for v in classes_to_tuples(hackstruct_classes)]
#     offset_classes_from_hackstructs = tuples_to_classes(tuples)
#
#     if not os.path.exists(offsets_file_name):
#         offset_classes = offset_classes_from_hackstructs
#         new_src = classes_to_string(offset_classes_from_hackstructs, skip_fields=['address'])
#     else:
#         with open(offsets_file_name) as f:
#             offsets_src = f.read()
#
#         new_src, offset_classes = _updated_src(offsets_src, offset_classes_from_hackstructs, 'Offsets', ['address'])
#
#     print(new_src)
#
#     # _safe_write(offsets_file_name, new_src)
#
#     replacer = HackStructOffsetReplacer(offset_classes)
#     new_src = replace_class_fields_in_string(hackstruct_classes, hackstruct_src, replacer=replacer)
#
#     print(new_src)
#
#     # _safe_write(hackstruct_file_name, new_src)
#
#     """
#     classes = _get_sorted_hackstructs(hackstruct_file_name)
#
#     offsets_file_exists = os.path.exists(offsets_file_name)
#     offsets_class = _import_class('Offsets', offsets_file_name) if offsets_file_exists else DefaultOffsets
#
#     properties = _get_offset_properties_from_hackstructs(offsets_class, classes)
#
#     generated_code = PythonOffsetClassGenerator().generate(list(properties))
#
#     if not offsets_file_exists:
#         new_offsets_code = generated_code
#     else:
#         with open(offsets_file_name, 'r') as f:
#             lines = f.read().splitlines()
#
#         new_offsets_code = _replace_offsets_aob(lines, generated_code, aob=False)
#
#     _safe_write(offsets_file_name, new_offsets_code)
#     """
#
#
# def update_hackstruct_file():
#     """
#     Read an offsets file to replace properties in a hackstruct file that have defined offsets in the offsets file
#     REQUIRES DEFINED OFFSETS
#     """
#     offsets_file_name, hackstruct_file_name = sys.argv[1:3]
#
#     with open(offsets_file_name) as f:
#         offsets_src = f.read()
#
#     with open(hackstruct_file_name) as f:
#         hackstruct_src = f.read()
#
#     hackstruct_classes = string_to_classes(hackstruct_src)
#     offset_classes = [cls for cls in string_to_classes(offsets_src) if cls.root().name == 'Offsets']
#     replacer = HackStructOffsetReplacer(offset_classes)
#     new_src = replace_class_fields_in_string(hackstruct_classes, hackstruct_src, replacer=replacer)
#
#     print(new_src)
#
#     # _safe_write(hackstruct_file_name, new_src)
#     """
#     offsets_class = _import_class('Offsets', offsets_file_name)
#
#     new_code = _replace_hackstruct_offsets_with_offset_class_properties(offsets_class, hackstruct_file_name)
#
#     _safe_write(hackstruct_file_name, new_code)
#     """

#
# # region Helper classes
#
# class DefaultOffsets:
#     pass
#
#
# class OffsetProperty:
#     def __init__(self, name, offset):
#         self.name = name
#         self.offset = offset
#
#     def __getitem__(self, item):
#         if item > 1:
#             raise IndexError(f'Index out of range {item}, range: (0, 1)')
#         return self.name if item == 0 else self.offset
#
#     def __eq__(self, other):
#         return self.name == other.name
#
#     def __hash__(self):
#         return hash(self.name)
#
#
# class AOBProperty:
#     def __init__(self, data):
#         self.data = data
#
#     def __getitem__(self, item):
#         return self.data[item if item != 'aob_string' else 'aob']
#
#     def __eq__(self, other):
#         return self.data == other.data
#
#     def __hash__(self):
#         return hash(self.data['name'])
#
#
#
# # region Offset/AOB/Hackstruct read
#
# def _get_sorted_hackstructs(file_name):
#     module_dict = _import_class('__dict__', file_name)
#     classes = [v for v in module_dict.values() if not isinstance(v, str) and is_hackstruct_type(v)]
#     classes.sort(key=lambda v: v._info.line_defined)
#     return classes
#
#
# def _import_class(name, file_name):
#     module = importlib.import_module(file_name.replace('.py', ''))
#     return getattr(module, name, None)
#
#
# def _get_offset_properties_from_hackstructs(offsets_class, classes):
#     properties = set()
#
#     # First get properties from offsets
#     properties.update(OffsetProperty(*v) for v in OffsetClass.to_list(offsets_class))
#
#     class_name_and_property = {'.'.join(v.name.split('.')[-2:]): v.name.replace('Offsets.', '') for v in properties}
#
#     # Then fill in missing properties from hackstruct
#     properties.update(OffsetProperty(class_name_and_property.get(f'{cls.__name__}.{k}', f'{cls.__name__}.{k}'), v)
#                       for cls in classes for k, v in cls._info.offsets.items())
#
#     return properties
#
#
# def _get_offset_properties_from_offsets_class(offsets_class, results):
#     properties = {}
#
#     # First get the data from previous definitions
#     properties.update({n: OffsetProperty(n, o) for n, o in OffsetClass.to_list(offsets_class)})
#
#     # Then add new properties from results
#     for name, offset, _ in results:
#         properties[name] = OffsetProperty(name, offset)
#
#     for p in properties.values():
#         p.name = p.name.replace('Offsets.', '')
#
#     return list(properties.values())
#
#
# def _get_aob_properties_from_offsets_classes(aob_class, results):
#     properties = {}
#     # First get the data from previous definitions
#     properties.update({d['name']: AOBProperty(d) for d in AOBClass.to_list(aob_class)})
#
#     # Then update the data with the results
#     for name, offset, instruction_address in results:
#         new_begin = AOBFinder.begin_mask(properties[name].data['begin'], instruction_address)
#         properties[name].data['begin'] = new_begin
#         properties[name].data['size'] = AOBFinder.size_mask(new_begin)
#
#     for p in properties.values():
#         p.data['name'] = p.data['name'].replace('AOB.', '')
#
#     return list(properties.values())
#
#
# # endregion
#
#
# # region HackStruct replace (only replaces updated lines in hackstruct definition
#
# def _iter_hackstructs_and_properties(lines, classes):
#     for i, cls in enumerate(classes):
#         begin = cls._info.line_defined
#         next_definition = classes[i + 1]._info.line_defined if (i < len(classes) - 1) else len(lines)
#
#         for line_i, line in enumerate(lines[begin: next_definition]):
#             equals_position = line.find('=')
#             before_equals = line[:equals_position].strip()
#
#             if (
#                 equals_position == -1
#                 or before_equals == 'address'
#                 or before_equals.endswith('metaclass')
#                 or before_equals.startswith('#')
#             ):
#                 continue
#
#             yield cls, begin + line_i, line
#
#
# def _replace_hackstruct_offsets_with_offset_class_properties(offsets_class, hackstruct_file_name):
#     offsets = {v[0]: v[1] for v in OffsetClass.to_list(offsets_class)}
#     class_name_and_property = {'.'.join(k.split('.')[-2:]): k for k in offsets}
#     class_names_with_corresponding_offsets = {k.split('.')[-2] for k in class_name_and_property}
#
#     with open(hackstruct_file_name, 'r') as f:
#         lines = f.read().splitlines()
#
#     for cls, line_no, line in _iter_hackstructs_and_properties(lines, _get_sorted_hackstructs(hackstruct_file_name)):
#         if cls.__name__ in class_names_with_corresponding_offsets:
#             lines[line_no] = _replace_hackstruct_property(line, cls, class_name_and_property)
#
#     return '\n'.join(lines) + '\n'
#
#
# def _replace_hackstruct_property(line, cls, class_name_and_property,
#                                  max_property_name_length=30, max_type_name_length=50):
#     colon = line.find(':')
#     equals = line.find('=')
#     property_name = line[:colon].strip()
#     type_name = line[colon + 1:equals].strip()
#
#     property_fmt = ('{:%ds}' % max_property_name_length).format(property_name)
#     type_fmt = ('{:%ds}' % max_type_name_length).format(type_name)
#
#     property_path = f'{cls.__name__}.{property_name}'
#
#     if property_path in class_name_and_property:
#         n_spaces = line.find(property_name)
#         return f"{' ' * n_spaces}{property_fmt}: {type_fmt} = {class_name_and_property[property_path]}  # noqa"
#     else:
#         return line
#
# # endregion
#
#
# # region Offsets/AOB replace (replaces entire Offsets/AOB definition)
#
# def _iter_offsets_aob(lines, aob=False, offset_class_is_first_line=False):
#     found_aob_begin, found_offsets_begin = False, False
#
#     current_class = None
#     for line_no, line in enumerate(lines):
#         stripped = line.strip()
#         found_aob_begin = found_aob_begin or stripped.startswith('class AOB')
#         found_offsets_begin = found_offsets_begin or stripped.startswith('class Offsets')
#
#         if not line or not stripped or not line.startswith(' '):
#             continue
#         elif aob and not found_aob_begin:
#             continue
#         elif not aob and not found_offsets_begin:
#             continue
#         elif not aob and found_aob_begin and found_offsets_begin:
#             break
#         elif stripped.startswith('class '):
#             current_class = line[line.find('class ') + 6: min(line.find('('), line.find(':'))]
#             if offset_class_is_first_line:
#                 offset_class_is_first_line = False
#                 yield current_class, line_no, line
#         else:
#             yield current_class, line_no, line
#
#
# def _replace_offsets_aob(lines, generated_code, aob=False):
#     output = io.StringIO()
#
#     begin_line, end_line = None, 0
#     for class_name, line_no, line in _iter_offsets_aob(lines, aob=aob, offset_class_is_first_line=True):
#         begin_line = line_no if begin_line is None else begin_line
#         end_line = line_no
#
#     # detect comments
#     for i, line in enumerate(lines[begin_line+1:end_line]):
#         if line.strip().startswith('#'):
#             raise RuntimeError(f'Comment detected on line {begin_line + i + 1} - please remove before updating file')
#
#     for line in lines[1:begin_line-2]:
#         output.write(line)
#         output.write('\n')
#
#     output.write('\n')
#     output.write(generated_code)
#
#     for line in lines[end_line+1:]:
#         if line:
#             output.write(line)
#             output.write('\n')
#
#     return output.getvalue()
#
# # endregion

# endregion
