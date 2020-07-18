
import os
import re

# These need to be listed in .gitattributes too
unix_files = {'.py', '.md', '.yml', '.rst', '.ini'}

def check_file(filename):
    return os.path.splitext(filename)[1] in unix_files

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

def test_version_numbers():
    """Version numbers in different places must be consistent."""
    with open('setup.py') as infile:
        setup_pattern = r"^\s*version='([^']*)',?$"
        setup = re.search(setup_pattern, infile.read(), re.MULTILINE).group(1)
    with open('docn/conf.py') as infile:
        docn_pattern = "^release = '([^']*)'$"
        docn = re.search(docn_pattern, infile.read(), re.MULTILINE).group(1)
    assert docn == setup
