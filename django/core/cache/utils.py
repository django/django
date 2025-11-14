from hashlib import md5

from django.utils.regex_helper import _lazy_re_compile

TEMPLATE_FRAGMENT_KEY_TEMPLATE = "template.cache.%s.%s"

server_separator_re = _lazy_re_compile("[;,]")


def make_template_fragment_key(fragment_name, vary_on=None):
    hasher = md5(usedforsecurity=False)
    if vary_on is not None:
        for arg in vary_on:
            hasher.update(str(arg).encode())
            hasher.update(b":")
    return TEMPLATE_FRAGMENT_KEY_TEMPLATE % (fragment_name, hasher.hexdigest())
