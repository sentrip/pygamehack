import pytest
from pygamehack.reclassnet import ReClassNet

# TODO: Test ReClassNet


@pytest.mark.skip
def test_load_reclass_file():
    reclass_classes = ReClassNet.load_project_file('tests/utils/CheatEnginePointerScans/test.rcnet')
    # classes = ReClassNet.convert_structs(reclass_classes)
    src = ReClassNet.generate_struct_src(reclass_classes)
    print(src)
