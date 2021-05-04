from setuptools import setup

from pybind11.setup_helpers import Pybind11Extension

__version__ = "0.0.1"

sources = [
    'src/Address.cpp',
    'src/Buffer.cpp',
    'src/Hack.cpp',
    'src/Instruction.cpp',
    'src/Process.cpp',
    'src/Variable.cpp',
    'src/python/pygamehack.cpp',

    'src/external/libdasm.c',
]

setup(
    name='pygamehack',
    version=__version__,
    author="Djordje Pepic",
    author_email="djordje.m.pepic@gmail.com",
    url="https://github.com/sentrip/pygamehack",
    long_description="",
    description='Python game hacking interface',
    packages=[
        'pygamehack', 'pygamehack.gdb',
        'pygamehack_gui', 'pygamehack_gui.core'
    ],
    ext_modules=[Pybind11Extension(
        'pygamehack.c',
        sources,
        cxx_std=17,
        define_macros=[('VERSION_INFO', __version__)]
    )],
    python_requires='>=3.7',
    install_requires=['pybind11>=2.6.2'],
    extras_require={"test": "pytest"},
    zip_safe=False
)

