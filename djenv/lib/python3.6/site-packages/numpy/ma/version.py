"""Version number

"""
from __future__ import division, absolute_import, print_function

version = '1.00'
release = False

if not release:
    from . import core
    from . import extras
    revision = [core.__revision__.split(':')[-1][:-1].strip(),
                extras.__revision__.split(':')[-1][:-1].strip(),]
    version += '.dev%04i' % max([int(rev) for rev in revision])
