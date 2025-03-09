#!/usr/bin/env python
#
# Copyright (C) 2009-2020 the sqlparse authors and contributors
# <see AUTHORS file>
#
# This module is part of python-sqlparse and is released under
# the BSD License: https://opensource.org/licenses/BSD-3-Clause

"""Entrypoint module for `python -m sqlparse`.

Why does this file exist, and why __main__? For more info, read:
- https://www.python.org/dev/peps/pep-0338/
- https://docs.python.org/2/using/cmdline.html#cmdoption-m
- https://docs.python.org/3/using/cmdline.html#cmdoption-m
"""

import sys

from sqlparse.cli import main

if __name__ == "__main__":
    sys.exit(main())
