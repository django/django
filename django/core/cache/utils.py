from hashlib import md5

TEMPLATE_FRAGMENT_KEY_TEMPLATE = "template.cache.%s.%s"


def make_template_fragment_key(fragment_name, vary_on=None):
    hasher = md5(usedforsecurity=False)
    if vary_on is not None:
        for arg in vary_on:
            data = str(arg).encode()
            # Use the netstring delimiter (with trailing comma).
            hasher.update(b"%d:%s," % (len(data), data))
    return TEMPLATE_FRAGMENT_KEY_TEMPLATE % (fragment_name, hasher.hexdigest())
