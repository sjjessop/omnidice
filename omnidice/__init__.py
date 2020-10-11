
from os.path import basename
from sys import argv, modules
import typing

__version__ = '1.2.0'

# Patch for Sphinx only. The module that originally needs this is omnidice.drv,
# but of course once the patch is applied it sticks, even if only imported
# indirectly. Rather than allowing any confusion as to which imports activate
# this patch and which don't, put it here so that anything activates it.
#
# Belt and braces check, whether or not we're in Sphinx.
using_sphinx = basename(argv[0]) == 'sphinx-build' and 'sphinx' in modules
if using_sphinx:  # pragma: no cover
    # Hack to suppress type alias expansion in auto-generated docs.
    #
    # https://github.com/sphinx-doc/sphinx/issues/6518
    _original = typing.get_type_hints

    def hacked_hints(obj, globalns=None, localns=None, *args, **kwargs):
        if localns is None:
            localns = {}
        # Suppress expansion of these type aliases, whenever used as strings in
        # annotations or with "from __future__ import annotations".
        localns['Probability'] = typing.ForwardRef('Probability')
        localns['DictData'] = typing.ForwardRef('DictData')
        return _original(obj, globalns, localns, *args, **kwargs)

    typing.get_type_hints = hacked_hints
