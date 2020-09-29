from distutils.core import setup, Extension

sources = [
    'libdasm.c',
    'Proc.cpp',
    'Hack.cpp',
    'pygamehack.cpp',
]

sfc_module = Extension(
    'pygamehack', 
    sources=sources,
    include_dirs=['pybind11/include'],
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
    packages=['pygamehack_utils', 'pygamehack_extensions'],
    requires=['pygdbmi', 'psutil'],
    entry_points={
        'console_scripts': [
            'pyce-aob=pygamehack_utils.cli:gui',
            'generate-aob=pygamehack_utils.cli:generate_aob_classes',
            'update-offsets=pygamehack_utils.cli:update_offsets_in_file',
        ],
    }
)
