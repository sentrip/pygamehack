import os, sys


def compile_test_programs(config, directory):
    os.system(f'mkdir {directory}')
    os.chdir(directory)
    os.system(f'cmake -A {config if config == "x64" else "Win32"} ..')
    os.system('cmake --build . --target TestProgram --config Release')
    os.chdir('../')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        exit(0)

    if sys.argv[1] == 'c':
        os.chdir('tests/test_program')

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

    elif sys.argv[1] == 'cloc':
        os.system('cloc src/ pygamehack/ pygamehack_gui/ %s --exclude-dir external --exclude-lang=XML,CMake' % ' '.join(sys.argv[2:]))

    elif sys.argv[1] == 'cov':
        os.system('coverage run --source "pygamehack" -m pytest')
        os.system('coverage html')
        import webbrowser
        webbrowser.open(os.getcwd() + '/htmlcov/index.html')
