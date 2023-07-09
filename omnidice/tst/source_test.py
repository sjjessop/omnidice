
import os
import re

# These need to be listed in .gitattributes too
unix_files = {'.py', '.md', '.yml', '.rst', '.ini'}

def check_file(filename: str) -> bool:
    return os.path.splitext(filename)[1] in unix_files

def check_dir(dirname: str) -> bool:
    if dirname.startswith('.'):
        return False
    if dirname.endswith('.egg-info'):
        return False
    return dirname != 'htmlcov'

def test_linebreaks() -> None:
    for path, dirs, files in os.walk('.'):
        for filename in filter(check_file, files):
            fullname = os.path.join(path, filename)
            with open(fullname, 'rb') as infile:
                assert b'\r\n' not in infile.read(), f'{fullname} contains Windows linebreaks'
        dirs[:] = filter(check_dir, dirs)

def search_file(pattern: str, filename: str) -> str:
    with open(filename) as infile:
        result = re.search(pattern, infile.read(), re.MULTILINE)
        assert result is not None
        return result.group(1)

def test_version_numbers() -> None:
    """Version numbers in different places must be consistent."""
    setup = search_file(r"^\s*version='([^']*)',?$", 'setup.py')
    init = search_file("^__version__ = '([^']*)'$", 'omnidice/__init__.py')
    assert init == setup
    docn = search_file("^release = '([^']*)'$", 'docn/conf.py')
    assert docn == setup
