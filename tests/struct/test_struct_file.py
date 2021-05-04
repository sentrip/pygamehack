import os
import pytest
from shutil import copyfile
from pygamehack.code import Code
from pygamehack.struct_file import StructFile

# TODO: Test struct file


@pytest.fixture
def temp_struct_file():
    temp_name = 'tests/struct/program_structs_temp.py'
    copyfile('tests/struct/program_structs.py', temp_name)
    yield temp_name
    os.remove(temp_name)


# @pytest.mark.skip
def test_struct_file(temp_struct_file):
    sf = StructFile(temp_struct_file)
    sf.load()

    sf.update_offsets([('IntTypes.num_i8', 20)])

    sf.update_code([
        ('IntTypes.num_i8', Code(code='QQ AA BB', offset=10, offset_size=4, begin=100, size=10))
    ])

    sf._impl.add_address('test', 10)

    sf.flush()
    # print(sf._impl.src)
    # print("#" * 150)
    sf.update_code([
        ('IntTypes.num_u8', Code(code='00 AA BB', offset=10, offset_size=4, begin=100, size=10))
    ])

    # sf._impl.add_address('test2', 20)

    sf.flush()
    # print(sf._impl.src)

    # print("#" * 150)
    sf.update_code([
        ('IntTypes.num_u8', Code(code='GG AA BB', offset=10, offset_size=4, begin=100, size=10))
    ])

    sf.flush()
    # print(sf._impl.src)
