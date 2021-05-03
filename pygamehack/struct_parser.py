import ast
import io
import tokenize
from abc import ABC, abstractmethod
from typing import Any, Callable, Iterable, List, Optional, Tuple

__all__ = [
    'classes_to_string', 'string_to_classes',
    'classes_to_tuples', 'tuples_to_classes', 'update_classes',
    'Class', 'Field', 'Comment',
    'AbstractSourceGenerator', 'PythonSourceGenerator'
]


#region Public API

def string_to_classes(
        src: str,
        convert_data: Optional[Callable[[Any], Any]] = None
) -> ['Class']:
    """
    Convert a string into a list of Class definitions
    """
    classes = []
    convert_data = convert_data or (lambda x: x)

    module = ast.parse(src)
    for node in module.body:
        if isinstance(node, ast.ClassDef):
            classes.append(_parse_class_node(node, src, convert_data))

    _update_class_definitions_with_comments(classes, src)

    return classes


def classes_to_string(
        classes: ['Class'],
        generator: Optional['AbstractSourceGenerator'] = None,
        skip_fields: Optional[Iterable] = None
) -> str:
    """
    Convert a list of Class definitions into a string (the source code required to use these classes)
    """
    generator = generator or PythonSourceGenerator()
    skipped = set(v for v in (skip_fields or []))

    generator.write_file_begin()

    for c in [cls for cls in classes if cls.name == cls.root().name]:
        _generate_class_src(c, generator, skipped)

    generator.write_file_end()

    return generator.generated_code()


def classes_to_tuples(
        classes: List['Class']
) -> List[Tuple[str, Any]]:
    """
    Convert a list of Class definitions into a list of tuples of the fields
    Each tuple contains the full path of each field in each Class definition and the data for that field
    NOTE: Lots of information contained in Classes/Fields is stripped when converting to tuples (like line-numbers)
    """
    tuples = []
    for c in [cls for cls in classes if cls.name == cls.root().name]:
        tuples.extend(_generate_tuples(c))
    return tuples


def tuples_to_classes(
        tuples: List[Tuple[str, Any]]
) -> List['Class']:
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


def update_classes(
        src_classes: List['Class'],
        dst_classes: List['Class'],
        skip_fields: Optional[Iterable] = None
):
    """
    Replace the fields of all classes in 'dst_classes' that exist in the corresponding class in 'src_classes'.
    Fields in 'src_classes' that do not exist in 'dst_classes' will be added.
    """
    skipped = set(v for v in (skip_fields or []))
    for c in dst_classes:
        _replace_class_fields(c, src_classes, skipped)


#endregion

#region Class/Field

class Class(object):

    name: str
    lineno: int
    end_lineno: int
    fields: {str: 'Field'}
    parent: Optional['Class']
    children: List['Class']
    comments: List['Comment']
    docstring: Optional[str]

    def __init__(self, name: str, lineno: int, end_lineno: int):
        self.name = name
        self.lineno = lineno
        self.end_lineno = end_lineno
        self.fields = {}
        self.parent = None
        self.children = []
        self.comments = []
        self.docstring = None

    def __repr__(self):
        return f'Class({self.name}, parent={self.parent})'

    def root(self) -> Optional['Class']:
        root_class = self
        while root_class.parent is not None:
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

#region SourceGenerator Interface

class SourceGeneratorBase(object):
    def __init__(self, write_int_as_hex=True):
        self.indent = 0
        self.write_int_as_hex = write_int_as_hex
        self._data = io.StringIO()

    def generated_code(self) -> str:
        return self._data.getvalue()

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
        elif isinstance(field.data, list) or isinstance(field.data, tuple):
            return '[' + ', '.join(f'0x{v:X}' for v in field.data) + ']'
        else:
            return str(field.data)


class AbstractSourceGenerator(SourceGeneratorBase, ABC):

    max_line_length = 120
    min_field_name_length = 30
    min_annotation_length = 50
    min_data_length = 30

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

    @classmethod
    def generate_class(cls, klass: 'Class', *args, indent=0, **kwargs) -> str:
        generator = cls(*args, **kwargs)
        generator.indent = indent
        _generate_class_src(klass, generator, [])
        return generator.generated_code()

    @classmethod
    def generate_field(cls, field: 'Field', *args, **kwargs) -> str:
        generator = cls(*args, **kwargs)
        generator.indent = field.indent
        generator.write_indent()
        generator.write_field(field)
        return generator.generated_code()


class PythonSourceGenerator(AbstractSourceGenerator):

    def __init__(self, *, write_int_as_hex: bool = True, base_class: Optional[str] = None):
        super().__init__(write_int_as_hex=write_int_as_hex)
        self.base_class = base_class

    def write_file_begin(self):
        pass

    def write_file_end(self):
        pass

    def write_class_begin(self, cls: 'Class'):
        if self.base_class:
            self.write(f'class {cls.name}({self.base_class}):')
        else:
            self.write(f'class {cls.name}:')

        if cls.docstring:
            self.write_line()
            self.indent += 1
            self.write_indent()
            self.indent -= 1
            self.write(f'"""{cls.docstring}"""')

    def write_class_end(self, cls: 'Class'):
        self.write_line()
        self.write_line()

    def write_empty_class(self, cls: 'Class'):
        self.write_indent()
        self.write('pass')

    def write_field(self, field: 'Field'):
        for comment in field.comments:
            if comment.lineno < field.lineno:
                self.write(comment.comment)
                self.write_line()
                self.write_indent()

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

#region Implementation

class Flag(object):
    def __init__(self, value: bool = False):
        self.value = value

    def __bool__(self):
        return self.value

    def on(self):
        self.value = True

    def off(self):
        self.value = False


def _generate_class_src(cls, generator, skipped, wrote_end_flag=None):
    wrote_end_flag = wrote_end_flag if wrote_end_flag is not None else Flag()
    has_fields = len(cls.fields) > 0

    wrote_end_flag.off()
    generator.write_indent()
    generator.write_class_begin(cls)
    generator.indent += 1
    generator.write_line()

    for field_name in cls.fields:

        if field_name in skipped:
            continue

        generator.write_indent()
        generator.write_field(cls.fields[field_name])
        generator.write_line()
        wrote_end_flag.on()

    if cls.children:
        wrote_end_flag.off()

        if has_fields:
            generator.write_line()

        for child in sorted(cls.children, key=lambda ch: ch.name):
            _generate_class_src(child, generator, skipped, wrote_end_flag)

    elif not has_fields:
        generator.write_empty_class(cls)

    generator.indent -= 1
    generator.write_class_end(cls)
    if not wrote_end_flag:
        generator.write_line()
    wrote_end_flag.on()


def _parse_class_node(class_node, src, convert_data, indent=0):
    cls = Class(class_node.name, class_node.lineno, class_node.end_lineno)
    for i, node in enumerate(class_node.body):
        # Docstring
        if i == 0 and isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            cls.docstring = node.value.value

        elif isinstance(node, ast.Assign):
            name = node.targets[0].id
            data = convert_data(_get_raw_value(node.value))
            cls.fields[name] = Field(cls, name, node.lineno, node.end_lineno, indent + 1, data)

        elif isinstance(node, ast.AnnAssign):
            data = convert_data(_get_raw_value(node.value))
            field = Field(cls, node.target.id, node.lineno, node.end_lineno, indent + 1, data)
            field.annotation_src = ast.get_source_segment(src, node.annotation)
            cls.fields[field.name] = field

        elif isinstance(node, ast.ClassDef):
            child = _parse_class_node(node, src, convert_data, indent=indent + 1)
            child.parent = cls
            cls.children.append(child)

    return cls


def _replace_class_fields(cls, src_classes, skipped):
    src_class = _get_class_with_same_path(cls.full_path().split('.'), src_classes)
    all_fields = sorted(list(set(list(cls.fields) + list(src_class.fields if src_class else []))))

    for field_name in all_fields:

        if field_name in skipped:
            continue

        # Both have field
        if field_name in cls.fields and src_class and field_name in src_class.fields:
            cls.fields[field_name].data = src_class.fields[field_name].data

        # Missing in cls
        elif field_name not in cls.fields:
            cls.fields[field_name] = src_class.fields[field_name]

    for child in sorted(cls.children, key=lambda ch: ch.name):
        _replace_class_fields(child, src_classes, skipped)


def _generate_tuples(cls):
    tuples = []
    name_path = cls.full_path()

    for name, field in cls.fields.items():
        tuples.append((f'{name_path}.{name}', field.data))

    for child in cls.children:
        tuples.extend(_generate_tuples(child))

    return tuples


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


def _get_class_with_same_path(path_parts, classes):
    for c in classes:
        c_path_parts = c.full_path().split('.')
        if path_parts == c_path_parts:
            return c
    return None


def _get_comments_inline_and_prefix(field):
    inline_comment_src = ''
    for i, comment in enumerate(field.comments):
        if comment.lineno == field.lineno:
            inline_comment_src = '  ' + comment.comment
            break
    else:
        i = -1

    return inline_comment_src, [field.comments[idx] for idx in range(len(field.comments)) if idx != i]


def _get_all_comments_from_src(src):
    comments = []
    g = tokenize.tokenize(io.BytesIO(src.encode('utf-8')).readline)
    for token, value, begin, end, _ in g:
        if token == tokenize.COMMENT:
            comments.append(Comment(value, begin[0], begin[1], end[1]))
    return comments


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


def _update_consume_comments(cls, comments):
    while comments and comments[0].lineno <= cls.lineno:
        cls.comments.append(comments[0])
        comments.pop(0)

    # TODO: Handle inline comments for multi-line fields
    for field in sorted(list(cls.fields.values()), key=lambda f: f.lineno):
        while comments and comments[0].lineno <= field.lineno:
            field.comments.append(comments[0])
            comments.pop(0)

    for child in sorted(cls.children, key=lambda c: c.lineno):
        _update_consume_comments(child, comments)


def _update_class_definitions_with_comments(classes, src):
    comments = _get_all_comments_from_src(src)
    for cls in sorted(classes, key=lambda c: c.lineno):
        _update_consume_comments(cls, comments)

#endregion
