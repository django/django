from __future__ import annotations

import sys
import traceback
from tempfile import NamedTemporaryFile
from typing import TYPE_CHECKING

from sphinx.errors import SphinxParallelError
from sphinx.util.console import strip_colors

if TYPE_CHECKING:
    from sphinx.application import Sphinx


def save_traceback(app: Sphinx | None, exc: BaseException) -> str:
    """Save the given exception's traceback in a temporary file."""
    import platform

    import docutils
    import jinja2
    import pygments

    import sphinx

    if isinstance(exc, SphinxParallelError):
        exc_format = '(Error in parallel process)\n' + exc.traceback
    else:
        exc_format = traceback.format_exc()

    if app is None:
        last_msgs = exts_list = ''
    else:
        extensions = app.extensions.values()
        last_msgs = '\n'.join(f'#   {strip_colors(s).strip()}' for s in app.messagelog)
        exts_list = '\n'.join(f'#   {ext.name} ({ext.version})' for ext in extensions
                              if ext.version != 'builtin')

    with NamedTemporaryFile('w', suffix='.log', prefix='sphinx-err-', delete=False) as f:
        f.write(f"""\
# Platform:         {sys.platform}; ({platform.platform()})
# Sphinx version:   {sphinx.__display_version__}
# Python version:   {platform.python_version()} ({platform.python_implementation()})
# Docutils version: {docutils.__version__}
# Jinja2 version:   {jinja2.__version__}
# Pygments version: {pygments.__version__}

# Last messages:
{last_msgs}

# Loaded extensions:
{exts_list}

# Traceback:
{exc_format}
""")
    return f.name


def format_exception_cut_frames(x: int = 1) -> str:
    """Format an exception with traceback, but only the last x frames."""
    typ, val, tb = sys.exc_info()
    # res = ['Traceback (most recent call last):\n']
    res: list[str] = []
    tbres = traceback.format_tb(tb)
    res += tbres[-x:]
    res += traceback.format_exception_only(typ, val)
    return ''.join(res)
