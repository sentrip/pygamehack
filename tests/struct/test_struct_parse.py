import os
import pytest
from shutil import copyfile
from pygamehack.code import Code
from pygamehack.struct_parser import string_to_classes, classes_to_string
from pygamehack.struct_file import StructFile

# TODO: Test struct parsing
# TODO: Test struct file

# def test_struct_parse():
#     src = """
    
# class A:
#     a: int = 5
        

#     """

#     print(classes_to_string(string_to_classes(src)))


@pytest.fixture
def temp_struct_file():
    temp_name = 'tests/struct/program_structs_temp.py'
    copyfile('tests/struct/program_structs.py', temp_name)
    yield temp_name
    os.remove(temp_name)


def test_struct_file(temp_struct_file):
    sf = StructFile(temp_struct_file)
    sf.load()
    
    sf.update_offsets([('IntTypes.num_i8', 10)])

    sf.update_code([
        ('IntTypes.num_i8', Code(code='00 AA BB', offset=10, offset_size=4, begin=100, size=10))
    ])
    
    sf.flush()
    
    # print(sf._impl.classes)
    # print(sf._impl.code)
    # print(sf._impl.src)
