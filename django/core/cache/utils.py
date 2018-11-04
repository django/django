import hashlib
from urllib.parse import quote

TEMPLATE_FRAGMENT_KEY_TEMPLATE = 'template.cache.%s.%s'


def make_template_fragment_key(fragment_name, vary_on=None):
    if vary_on is None:
        vary_on = ()
    key = ':'.join(quote(str(var)) for var in vary_on)
    
    # Try to generate an MD5 hash but fall up to SHA256 if in FIPS mode
    try:
        args = hashlib.md5(key.encode())
    except ValueError as exc:
        if 'disabled for fips' not in exc.message:
            raise
        args = hashlib.sha256(key.encode())

    return TEMPLATE_FRAGMENT_KEY_TEMPLATE % (fragment_name, args.hexdigest())
