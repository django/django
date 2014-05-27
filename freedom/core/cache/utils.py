from __future__ import unicode_literals

import hashlib
from freedom.utils.encoding import force_bytes
from freedom.utils.http import urlquote

TEMPLATE_FRAGMENT_KEY_TEMPLATE = 'template.cache.%s.%s'


def make_template_fragment_key(fragment_name, vary_on=None):
    if vary_on is None:
        vary_on = ()
    key = ':'.join(urlquote(var) for var in vary_on)
    args = hashlib.md5(force_bytes(key))
    return TEMPLATE_FRAGMENT_KEY_TEMPLATE % (fragment_name, args.hexdigest())
