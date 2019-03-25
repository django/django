# -*- coding: utf-8 -*-
"""
markupsafe._compat
~~~~~~~~~~~~~~~~~~

:copyright: © 2010 by the Pallets team.
:license: BSD, see LICENSE for more details.
"""
import sys

PY2 = sys.version_info[0] == 2

if not PY2:
    text_type = str
    string_types = (str,)
    unichr = chr
    int_types = (int,)

    def iteritems(x):
        return iter(x.items())

    from collections.abc import Mapping

else:
    text_type = unicode
    string_types = (str, unicode)
    unichr = unichr
    int_types = (int, long)

    def iteritems(x):
        return x.iteritems()

    from collections import Mapping
