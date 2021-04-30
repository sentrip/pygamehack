from distutils.core import setup, Extension

sources = [
    'src/external/libdasm.c',
    
    'src/Address.cpp',
    'src/Buffer.cpp',
    'src/Hack.cpp',
    'src/Instruction.cpp',
    'src/Process.cpp',
    'src/Variable.cpp',
    'src/pygamehack.cpp',
]

sfc_module = Extension(
    'cpygamehack', 
    sources=sources,
    include_dirs=['venv/lib/site-packages/pybind11/include'],
    library_dirs=[],
    libraries=[],
    language='c++',
    extra_compile_args=['/std:c++17'],
    extra_link_args=[],
)

setup(
    name='pygamehack',
    version='1.0',
    description='Python game hacking interface',
    ext_modules=[sfc_module],
    packages=[
        'pygamehack', 'pygamehack.gdb', 'pygamehack.types',
        'pygamehack_gui', 'pygamehack_gui.core'
    ],
    requires=[]
)
