import os, sys


def compile_test_programs(config, directory):
    os.system(f'mkdir {directory}')
    os.chdir(directory)
    os.system(f'cmake -A {config} ..')
    os.system('cmake --build . --target ALL --config Release')
    os.chdir('../')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        exit(0)

    if sys.argv[1] == 'c':
        os.chdir('tests')

        compile_test_programs('x64', 'build')
        compile_test_programs('x86', 'build-32')
    
    elif sys.argv[1] == 'i':
        os.system('python setup.py install')

    elif sys.argv[1] == 'g':
        os.system('python setup.py install')
        os.system('python pygamehack_gui/main.py')
    
    elif sys.argv[1] == 't':
        os.system('python setup.py install')
        os.system('pytest -s ' + ' '.join(sys.argv[2:] if len(sys.argv) > 2 else []))
