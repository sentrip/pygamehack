import ast
import io
import tokenize

from abc import ABC, abstractmethod
from typing import Any, Optional, Iterable


#region Conversions

def string_to_classes(
        src: str
) -> ['Class']:
    """
    Convert a string into a list of Class definitions
    """
    module = ast.parse(src)

    classes, seen = [], set()

    for node in module.body:
        if isinstance(node, ast.ClassDef):
            _parse_class(node, src, classes=classes)

    _assign_comments(_get_comments(src), classes)

    return classes


def classes_to_string(
        classes: ['Class'],
        generator: Optional['AbstractCodeGenerator'] = None,
        skip_fields: Optional[Iterable] = None
) -> str:
    """
    Convert a list of Class definitions into a string (the source code required to use these classes)
    """
    generator = generator or DefaultPythonCodeGenerator()
    skipped = set(v for v in (skip_fields or []))

    generator.write_file_begin()

    _apply_to_roots(classes, lambda c: _generate_class(c, generator, skipped))

    generator.write_file_end()

    return generator.generated_code()


def replace_class_fields(
        src_classes: ['Class'],
        dst_classes: ['Class'],
        replacer: 'AbstractCodeReplacer' = None,
        skip_fields: Optional[Iterable] = None
):
    """
    Replace the fields of all classes in 'dst_classes' that exist in the corresponding class in 'src_classes'
    using the given replacer to replace the fields
    """
    replacer = replacer or DefaultPythonCodeReplacer()
    skipped = set(v for v in (skip_fields or []))
    _apply_to_roots(dst_classes, lambda c: _replace_class(c, src_classes, replacer, skipped))


def replace_class_fields_in_string(
        classes: ['Class'],
        target_src: str,
        replacer: 'AbstractCodeReplacer' = None,
        skip_fields: Optional[Iterable] = None
) -> str:
    """
    Replace the source code of fields defined in 'target_src' with the generated code of fields in 'classes'
    """
    replacer = replacer or DefaultPythonCodeReplacer()
    skipped = set(v for v in (skip_fields or []))

    target_lines = target_src.splitlines()
    _apply_to_roots(classes, lambda c: _replace_class_code(c, target_lines, replacer, skipped))
    return '\n'.join(target_lines)


def classes_to_tuples(
        classes: ['Class']
) -> [(str, Any)]:
    """
    Convert a list of Class definitions into a list of tuples of the fields
    Each tuple contains the full path of each field in each Class definition and the data for that field
    NOTE: Lots of information contained in Classes/Fields is stripped when converting to tuples (like line-numbers)
    """
    tuples = []
    _apply_to_roots(classes, lambda c: _generate_tuples(c, tuples))
    return tuples


def tuples_to_classes(
        tuples: [(str, Any)]
) -> ['Class']:
    """
    Convert a list of tuples into a list of Class definitions

    NOTE: The classes created with this function DO NOT CONTAIN line-definition information
    The output of this function should be used in combination with replacement of previously defined classes
    The intention of this function is NOT to generate new class definitions from tuples, but to update existing ones
    """
    classes = []
    for name, data in tuples:
        _parse_tuple(name, data, classes)
    return classes

#endregion


#region Generator/Replacer Interface

class AbstractCodeManipulator(ABC):

    max_line_length = 120
    min_field_name_length = 30
    min_annotation_length = 50
    min_data_length = 30


class AbstractCodeReplacer(AbstractCodeManipulator):

    @abstractmethod
    def replace(self, src: 'Field', dst: 'Field'):
        raise NotImplementedError

    @abstractmethod
    def regenerate(self, field: 'Field', previous_lines: [str]) -> str:
        raise NotImplementedError


class AbstractCodeGenerator(AbstractCodeManipulator):

    def __init__(self, write_int_as_hex=True):
        self.indent = 0
        self.write_int_as_hex = write_int_as_hex
        self._data = io.StringIO()

    def generated_code(self) -> str:
        return self._data.getvalue()

    @abstractmethod
    def write_file_begin(self):
        raise NotImplementedError

    @abstractmethod
    def write_file_end(self):
        raise NotImplementedError

    @abstractmethod
    def write_class_begin(self, cls: 'Class'):
        raise NotImplementedError

    @abstractmethod
    def write_class_end(self, cls: 'Class'):
        raise NotImplementedError
    
    @abstractmethod
    def write_empty_class(self, cls: 'Class'):
        raise NotImplementedError

    @abstractmethod
    def write_field(self, field: 'Field'):
        raise NotImplementedError

    def write(self, value: str):
        self._data.write(value)

    def write_indent(self):
        self.write('    ' * self.indent)

    def write_line(self, line: Optional[str] = None):
        if line:
            self.write_indent()
            self.write(line)
        self.write('\n')

    def field_data_to_string(self, field: 'Field') -> str:
        if self.write_int_as_hex and isinstance(field.data, int):
            return f'0x{field.data:X}'
        else:
            return '[' + ', '.join(f'0x{v:X}' for v in field.data) + ']'

    @classmethod
    def generate_class(cls, klass: 'Class', *args, indent=0, **kwargs) -> str:
        generator = cls(*args, **kwargs)
        generator.indent = indent
        _generate_class(klass, generator, [])
        return generator.generated_code()

    @classmethod
    def generate_field(cls, field: 'Field', *args, **kwargs) -> str:
        generator = cls(*args, **kwargs)
        generator.indent = field.indent
        generator.write_indent()
        generator.write_field(field)
        return generator.generated_code()

#endregion


#region Class/Field

class Class(object):

    name: str
    lineno: int
    end_lineno: int
    fields: {str: 'Field'}
    parent: Optional['Class']
    children: ['Class']
    comments: ['Comment']

    def __init__(self, name: str, lineno: int, end_lineno: int):
        self.name = name
        self.lineno = lineno
        self.end_lineno = end_lineno
        self.fields = {}
        self.parent = None
        self.children = []
        self.comments = []

    def __repr__(self):
        return f'Class({self.name}, parent={self.parent})'

    def root(self) -> Optional['Class']:
        root_class = self
        while root_class.parent:
            root_class = root_class.parent
        return root_class

    def full_path(self) -> str:
        path = self.name
        parent = self.parent
        while parent:
            path = f'{parent.name}.{path}'
            parent = parent.parent
        return path

    def source(self, lines: [str], offset: int = 0) -> str:
        return lines[self.lineno - 1 + offset: self.end_lineno + offset]


class Comment(object):
    comment: str
    lineno: int
    column: int
    column_end: int

    def __init__(self, comment: str, lineno: int, column: int, column_end: int):
        self.comment = comment
        self.lineno = lineno
        self.column = column
        self.column_end = column_end

    def __repr__(self):
        return f"Comment('{self.comment}', line={self.lineno})"


class Field(object):

    name: str
    data: Optional[Any]
    comments: [Comment]
    lineno: int
    end_lineno: int
    indent: int
    annotation_src: Optional[str]

    def __init__(self, cls: Class, name: str, lineno: int, end_lineno: int, indent: int, data: Optional[Any] = None):
        self.cls = cls
        self.name = name
        self.data = data
        self.comments = []
        self.lineno = lineno
        self.end_lineno = end_lineno
        self.indent = indent
        self.annotation_src = None

    def __repr__(self):
        return f'Field({self.name}, class={self.cls.name})'

    @property
    def indent_str(self) -> str:
        return '    ' * self.indent

    @property
    def line_count(self) -> int:
        return self.end_lineno - self.lineno + 1

    def source(self, lines: [str], offset: int = 0) -> str:
        return lines[self.lineno - 1 + offset: self.end_lineno + offset]

    def update_source(self, lines: [str], data: str, offset: int = 0):
        lines[self.lineno - 1 + offset: self.end_lineno + offset] = data

#endregion


#region Conversions Implementation

def _apply_to_roots(classes, func):
    roots = [cls for cls in classes if cls.name == cls.root().name]
    for cls in roots:
        func(cls)


def _create_lines(previous_lines, max_length):
    lines = []
    for i, line in enumerate(previous_lines):
        if i < max_length:
            lines.append(line)
        else:
            lines[-1] += '\n%s' % line
    return lines


def _get_class_with_same_path(path_parts, classes):
    for c in classes:
        c_path_parts = c.full_path().split('.')
        if path_parts == c_path_parts:
            return c
    return None


def _get_raw_value(value):
    if isinstance(value, ast.Constant):
        return value.value
    elif isinstance(value, ast.List):
        return [_get_raw_value(v) for v in value.values]
    elif isinstance(value, ast.Dict):
        return {_get_raw_value(k): _get_raw_value(v) for k, v in zip(value.keys, value.values)}
    elif isinstance(value, ast.Set):
        return {_get_raw_value(v) for v in value.values}
    elif isinstance(value, ast.Attribute):
        path = value.attr
        value = value.value
        while not isinstance(value, ast.Name):
            path = f'{value.attr}.{path}'
            value = value.value
        return f'{value.id}.{path}'

    raise RuntimeError('Unrecognized value: ', value)


def _parse_class(class_node, src, indent=0, classes=None):
    classes = classes if classes is not None else []

    cls = Class(class_node.name, class_node.lineno, class_node.end_lineno)

    for node in class_node.body:

        if isinstance(node, ast.Assign):
            name = node.targets[0].id
            cls.fields[name] = Field(cls, name, node.lineno, node.end_lineno, indent + 1, _get_raw_value(node.value))

        elif isinstance(node, ast.AnnAssign):
            field = Field(cls, node.target.id, node.lineno, node.end_lineno, indent + 1, _get_raw_value(node.value))
            field.annotation_src = ast.get_source_segment(src, node.annotation)
            cls.fields[field.name] = field

        elif isinstance(node, ast.ClassDef):
            sub_classes = _parse_class(node, src, indent=indent + 1)
            for c in sub_classes:
                c.parent = cls
            cls.children.extend(sub_classes)
            classes.extend(sub_classes)

    classes.append(cls)

    return classes


def _parse_tuple(name, data, classes):
    parts = name.split('.')
    class_name, field_name = parts[-2:]
    parent_names = parts[:-2]

    if parent_names:
        for i in range(len(parent_names)):
            parent = _get_class_with_same_path(parent_names[:i+1], classes)
            if not parent:
                parent = Class(parent_names[i], 0, 0)
                classes.append(parent)

    cls = _get_class_with_same_path(parts[:-1], classes)
    parent = _get_class_with_same_path(parent_names, classes) if len(parts) > 2 else None

    if not cls:
        cls = Class(class_name, 0, 0)
        classes.append(cls)

    if parent:
        cls.parent = parent
        for c in parent.children:
            if c.name == cls.name:
                break
        else:
            parent.children.append(cls)

    cls.fields[field_name] = Field(cls, field_name, 0, 0, len(parts) - 1, data)


def _generate_class(cls, generator, skipped):
    has_fields = len(cls.fields) > 0

    generator.write_indent()
    generator.write_class_begin(cls)
    generator.indent += 1
    generator.write_line()

    for field_name in sorted(cls.fields):

        if field_name in skipped:
            continue

        generator.write_indent()
        generator.write_field(cls.fields[field_name])
        generator.write_line()

    if cls.children:
        if has_fields:
            generator.write_line()

        for child in sorted(cls.children, key=lambda ch: ch.name):
            _generate_class(child, generator, skipped)
    
    elif not has_fields:
        generator.write_empty_class(cls)

    generator.indent -= 1
    generator.write_class_end(cls)
    generator.write_line()


def _generate_tuples(cls, tuples):
    name_path = cls.full_path()

    for name, field in cls.fields.items():
        tuples.append((f'{name_path}.{name}', field.data))

    for child in cls.children:
        _generate_tuples(child, tuples)


def _replace_class(cls, src_classes, replacer, skipped):
    src_class = _get_class_with_same_path(cls.full_path().split('.'), src_classes)
    all_fields = sorted(list(set(list(cls.fields) + list(src_class.fields if src_class else []))))

    for field_name in all_fields:

        if field_name in skipped:
            continue

        # Both have field
        if field_name in cls.fields and src_class and field_name in src_class.fields:
            replacer.replace(src_class.fields[field_name], cls.fields[field_name])

        # Missing in cls
        elif field_name not in cls.fields:
            cls.fields[field_name] = src_class.fields[field_name]

    for child in sorted(cls.children, key=lambda ch: ch.name):
        _replace_class(child, src_classes, replacer, skipped)


def _replace_class_code(cls, target_lines, replacer, skipped):
    previous_field = cls

    for field_name in sorted(cls.fields):

        if field_name in skipped:
            continue

        field = cls.fields[field_name]

        if field.lineno == 0:
            field_lines = DefaultPythonCodeGenerator.generate_field(field).splitlines()
            field_lines = target_lines[previous_field.lineno - 1: previous_field.end_lineno] + field_lines
            field.lineno, field.end_lineno = previous_field.lineno, previous_field.end_lineno
            replacer.line_offset += field.line_count
        else:
            field_lines = replacer.regenerate(field, field.source(target_lines, offset=replacer.line_offset)).splitlines()

        field.update_source(target_lines, _create_lines(field_lines, field.line_count),
                            offset=max(0, replacer.line_offset - field.line_count))
        previous_field = field

    for child in sorted(cls.children, key=lambda ch: ch.name):
        _replace_class_code(child, target_lines, replacer, skipped)


def _assign_comments(comments, classes):
    if not comments:
        return

    classes_and_fields = _get_class_and_field_for_each_line(classes)

    for comment in comments:
        if comment.lineno >= len(classes_and_fields):
            continue

        cls, field = classes_and_fields[comment.lineno - 1]
        if field:
            field.comments.append(comment)
        elif cls:
            cls.comments.append(comment)


def _get_class_and_field_for_each_line(classes):
    max_line = max(0, *(c.end_lineno for c in classes))
    classes_and_fields = [(None, None) for _ in range(max_line)]

    sorted_classes = sorted(classes, key=lambda c: c.lineno)

    previous_class = None

    for i, cls in enumerate(sorted_classes):
        class_begin = (cls.lineno - 1) if not previous_class else previous_class.end_lineno
        for lineno in range(class_begin, cls.end_lineno):
            classes_and_fields[lineno] = (cls, sorted_classes[i + 1] if i < len(sorted_classes) - 1 else None)

        previous_field = None
        sorted_fields = sorted(cls.fields.values(), key=lambda f: f.lineno)

        for field in sorted_fields:
            begin = cls.lineno if not previous_field else previous_field.end_lineno
            for lineno in range(begin, field.end_lineno):
                classes_and_fields[lineno] = (cls, field)

            previous_field = field

    return classes_and_fields


def _get_comments(s):
    comments = []
    g = tokenize.tokenize(io.BytesIO(s.encode('utf-8')).readline)
    for token, value, begin, end, _ in g:
        if token == tokenize.COMMENT:
            comments.append(Comment(value, begin[0], begin[1], end[1]))
    return comments


def _get_comments_inline_and_prefix(field):
    inline_comment_src = ''
    for i, comment in enumerate(field.comments):
        if comment.lineno == field.lineno:
            inline_comment_src = '  ' + comment.comment
            break
    else:
        i = -1

    return inline_comment_src, [field.comments[idx] for idx in range(len(field.comments)) if idx != i]

#endregion


#region Python Generator

class DefaultPythonCodeGenerator(AbstractCodeGenerator):

    def write_file_begin(self):
        pass

    def write_file_end(self):
        pass

    def write_class_begin(self, cls: 'Class'):
        self.write(f'class {cls.name}:')

    def write_class_end(self, cls: 'Class'):
        pass

    def write_empty_class(self, cls: 'Class'):
        self.write_indent()
        self.write('pass')

    def write_field(self, field: 'Field'):
        # TODO: Write pre-comments
        self.write(self.field_to_string(field))

    def field_to_string(self, field: 'Field') -> str:
        inline_comment_src, _ = _get_comments_inline_and_prefix(field)

        if field.annotation_src:
            fmt = '{:%ds}: {:%ds}= {:%ds}{}' % (self.min_field_name_length, self.min_annotation_length, self.min_data_length)
            args = field.name, field.annotation_src, self.field_data_to_string(field), inline_comment_src
        else:
            fmt = '{:%ds}= {:%ds}{}' % (self.min_field_name_length, self.min_data_length)
            args = field.name, self.field_data_to_string(field), inline_comment_src
        
        return fmt.format(*args)

#endregion


#region Python Replacer

class DefaultPythonCodeReplacer(AbstractCodeReplacer):

    def __init__(self, line_offset=0, write_int_as_hex=True):
        self.line_offset = line_offset
        self.write_int_as_hex = write_int_as_hex

    def replace(self, src: 'Field', dst: 'Field'):
        dst.data = src.data
        if dst.lineno:
            dst.end_lineno = dst.lineno + len(self.field_to_string(dst).splitlines()) - 1 + self.line_offset

    def regenerate(self, field: 'Field', previous_lines: [str]) -> str:
        return field.indent_str + self.field_to_string(field)

    def field_to_string(self, field: 'Field') -> str:
        return DefaultPythonCodeGenerator(write_int_as_hex=self.write_int_as_hex).field_to_string(field)

#endregion
 