from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .struct_parser import tuples_to_classes, classes_to_string, DefaultPythonCodeGenerator, Class as StructClass

__all__ = ['ReClassNet']

# TODO: ReClassNet all types

#region ReClassNet

class ReClassNet:

    @dataclass
    class Class(object):
        name: str
        size: int = 0
        fields: Dict[str, 'Class'] = field(default_factory=dict)
        offsets: Dict[str, List[int]] = field(default_factory=dict)
        comments: Dict[str, str] = field(default_factory=dict)


    def load_project_file(path: str) -> List[Class]:
        """
        Load a ReClass.Net project file (.rcnet) from the given path into a list of ReClassNet Class definitions
        """
        import zipfile
        from xml.dom import minidom
        
        classes = []
        archive = zipfile.ZipFile(path, 'r')
        with archive.open(C.DataFileName) as data_xml:    
            mydoc = minidom.parse(data_xml)
            platform, version = Parse.platform_version(mydoc)
            custom_data = Parse.custom_data(mydoc)
            type_mapping = Parse.type_mapping(mydoc)
            enums = Parse.enums(mydoc)
            classes.extend(Parse.classes(mydoc, type_mapping, platform))
        
        return classes

    def convert_structs(classes: List[Class]) -> [StructClass]:
        """
        Convert the given list of ReClassNet Class definitions into a list of pygamehack Class definitions
        """
        tuples = []
        name_to_class = {}
        for class_def in classes:
            name_to_class[class_def.name] = class_def
            tuples.extend((f'{class_def.name}.{k}', v if len(v) > 1 else v[0]) for k, v in class_def.offsets.items())
        
        struct_classes = tuples_to_classes(tuples)
        for c in struct_classes:
            for name, f in c.fields.items():
                # TODO: ReClassNet Comments
                f.annotation_src = f'{generator.library_name}.{name_to_class[f.cls.name].name}'

        return struct_classes

    def generate_struct_src(classes: List[Class], generator: Optional['AbstractCodeGenerator'] = None) -> str:
        """
        Generate source code for the given list of ReClassNet Class definitions using the provided generator, or the default ReClassNetPythonCodeGenerator
        """
        generator = generator or ReClassNetPythonCodeGenerator()

        assert hasattr(generator, 'library_name'), \
            'Code generator must define the property "library_name" in order to correctly prefix imported type names'

        return classes_to_string(ReClassNet.generate_structs(classes), generator=generator)

#endregion

#region ReClassNet Implementation

#region Constants

class C:
    DataFileName = 'Data.xml'
    FileVersion = 0x00010001
    FileVersionCriticalMask = 0xFFFF0000
    
    class Elem:
        RootElement = "reclass"
        CustomData = "custom_data"
        TypeMapping = "type_mapping"
        Enums = "enums"
        Enum = "enum"
        Classes = "classes"
        Class = "class"
        Node = "node"
        Method = "method"
        Item = "item"
    
    class Attr:
        Version = "version"
        Platform = "type"
        Uuid = "uuid"
        Name = "name"
        Comment = "comment"
        Hidden = "hidden"
        Address = "address"
        Type = "type"
        Reference = "reference"
        Count = "count"
        Bits = "bits"
        Length = "length"
        Size = "size"
        Signature = "signature"
        Flags = "flags"
        Value = "value"

#endregion

#region Parse

class Parse:

    #region Basic

    # Platform/Version
    @staticmethod
    def platform_version(doc):
        platform = doc.documentElement.attributes[C.Attr.Platform].value
        
        version = int(doc.documentElement.attributes[C.Attr.Version].value)
        if ((version & C.FileVersionCriticalMask) > (C.FileVersion & C.FileVersionCriticalMask)):
            raise RuntimeError(f'The file version is unsupported.')
        
        return platform, version

    # Custom Data
    @staticmethod
    def custom_data(doc):
        # TODO: Parse ReClassNet custom data
        custom_data = doc.documentElement.getElementsByTagName(C.Elem.CustomData)
        if custom_data:
            pass
        return None
    
    # Type Mapping
    @staticmethod
    def type_mapping(doc):
        import xml.dom
        type_mapping = {}
        type_mapping_elem = doc.documentElement.getElementsByTagName(C.Elem.TypeMapping)
        if type_mapping_elem and type_mapping_elem.length > 0:
            for node in type_mapping_elem.item(0).childNodes:
                if node.nodeType == xml.dom.Node.ELEMENT_NODE:
                    type_mapping[node.nodeName] = node.childNodes[0].nodeValue
        return type_mapping

    # Enums
    @staticmethod
    def enums(doc):
        enums = []
        enums_elem = doc.documentElement.getElementsByTagName(C.Elem.Enums)
        if enums_elem and enums_elem.length > 0:
            for node in enums_elem.item(0).childNodes:
                name = node.attributes.get(C.Attr.Name) or ''
                use_flags = node.attributes.get(C.Attr.Flags) or False
                size = node.attributes.get(C.Attr.Size, 4) # TODO: Default enum size
                values = {}
                if node.length > 0:
                    for item in node.item(0).childNodes:
                        item_name = node.attributes.get(C.Attr.Name) or ''
                        value = node.attributes.get(C.Attr.Value) or 0
                        values[item_name] = value
                enums.append((name, use_flags, size, values))
        return enums

    #endregion
    
    #region Classes

    @staticmethod
    def classes(doc, types, platform):
        classes = []
        Parse.classes_without_size_and_offsets(doc, types, classes)
        Parse.class_sizes_and_offsets(classes, platform)
        return classes

    @staticmethod
    def classes_without_size_and_offsets(doc, types, classes):
        classes_elem = doc.documentElement.getElementsByTagName(C.Elem.Classes)
        element_class = []
        seen_classes = {}

        # Parse classes
        if classes_elem and classes_elem.length > 0:          
            for node in classes_elem.item(0).childNodes:
                if node.attributes:
                    uuid = node.attributes.get(C.Attr.Uuid, None)
                    if uuid is not None and node.attributes and uuid.value not in seen_classes:
                        name = node.attributes.get(C.Attr.Name, None)
                        if name is not None and node.childNodes and not Parse.in_type_mapping(name.value, types):
                            class_def = ReClassNet.Class(name.value)
                            classes.append(class_def)
                            seen_classes[uuid.value] = class_def
                            element_class.append((node, class_def))

        
        # Parse properties for each class recursively
        for node, class_def in element_class:
            for child in node.childNodes:
                if child.attributes:
                    Parse.create_class_property_from_node(class_def, child, types, seen_classes, node)

    @staticmethod
    def class_sizes_and_offsets(classes, platform):
        from .struct_meta import _sort_by_dependency

        # Sort classes in reverse dependency order
        dependencies = {}
        for class_def in classes:
            dependencies[class_def.name] = []
            for child_def in class_def.fields.values():
                if isinstance(child_def, ReClassNet.Class):        
                    dependencies[class_def.name].append(child_def.name)
        _sort_by_dependency(classes, dependencies, lambda t: t.name)
        
        # Calculate class sizes now that all the classes have been sorted
        calculated = {}
        def calculate_size_offsets(class_def, calculated):
            if class_def.name in calculated:
                return class_def.size
            
            calculated[class_def.name] = True
            offset = 0
            for name, child_def in class_def.fields.items():
                class_def.offsets[name][0] = offset
                property_size = 0
                
                if isinstance(child_def, ReClassNet.Class):
                    property_size = calculate_size_offsets(child_def, calculated)
                    class_def.size = max(offset + property_size, class_def.size)
                else:
                    pygamehack_type = Parse.pygamehack_type(child_def)
                    class_def.fields[name] = ReClassNet.Class(pygamehack_type.__name__)
                    if pygamehack_type.__name__ != 'ptr':
                        property_size = pygamehack_type.size
                        class_def.fields[name].size = property_size
                
                if len(class_def.offsets[name]) == 1:
                    offset += property_size
                else:
                    offset += 4 if platform == 'x86' else 8
            
            class_def.size = max(offset, class_def.size)
            return class_def.size

        for class_def in classes:
            calculate_size_offsets(class_def, calculated)

    @staticmethod
    def create_class_property_from_node(class_def, node, types, seen_classes, parent=None, comes_from_pointer=False):
        uuid = node.attributes.get(C.Attr.Reference, None)
        node_type = node.attributes.get(C.Attr.Type, None)
        name = (parent if comes_from_pointer else node).attributes.get(C.Attr.Name, None)
        name = name.value if name is not None else ''
        comment = (parent if comes_from_pointer else node).attributes.get(C.Attr.Comment, None)
        class_def.comments[name] = comment.value if comment is not None else ''

        # Existing class
        if uuid is not None and uuid.value in seen_classes:
            field_def = seen_classes[uuid.value]
            class_def.fields[name] = field_def
            class_def.offsets[name] = [0] if not comes_from_pointer else [0, 0]
        
        # Basic Type
        elif node_type is not None and Parse.in_type_mapping(node_type.value, types):
            class_def.fields[name] = node_type.value
            class_def.offsets[name] = [0]
        
        # Pointer to existing class
        elif node_type.value == 'PointerNode':
            for n in node.childNodes:
                if n.attributes:
                    Parse.create_class_property_from_node(class_def, n, types, seen_classes, node, True)
                    break
        
        # Undefined Class that comes from pointer
        else:
            assert node_type.value == 'ClassInstanceNode', 'We should only be parsing undefined classes here'
            assert comes_from_pointer, 'Inline instance definiton of undefined class is not allowed'
            class_def.fields[name] = 'ptr'
            class_def.offsets[name] = [0, 0]

    @staticmethod
    def in_type_mapping(name, types):
        if 'Type' + name.replace('Node', '') in types:
            return True

    @staticmethod
    def pygamehack_type(reclass_type_name):
        import pygamehack as gh

        name = reclass_type_name.replace('Node', '') \
            .replace('UInt', 'u') \
            .replace('Int', 'i') \
            .lower()
        
        if hasattr(gh, name):
            return getattr(gh, name)
        else:
            raise RuntimeError("Unknown type name", reclass_type_name)

    #endregion

#endregion

#endregion

#region ReClassNet Python Code Generator

class ReClassNetPythonCodeGenerator(DefaultPythonCodeGenerator):
    library_name = 'gh'

    def write_file_begin(self):
        self.write_line(f'import pygamehack as {self.library_name}\n')

#endregion
