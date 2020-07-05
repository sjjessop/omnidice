
import os

def check_file(filename):
    return os.path.splitext(filename)[1] == '.py'

def check_dir(dirname):
    if dirname.startswith('.'):
        return False
    if dirname.endswith('.egg-info'):
        return False
    if dirname == 'htmlcov':
        return False
    return True

def test_linebreaks():
    for path, dirs, files in os.walk('.'):
        for filename in filter(check_file, files):
            fullname = os.path.join(path, filename)
            with open(fullname, 'rb') as infile:
                assert b'\r\n' not in infile.read(), f'{fullname} contains Windows linebreaks'
        dirs[:] = filter(check_dir, dirs)
