from http import cookies

# For backwards compatibility in Django 2.1.
SimpleCookie = cookies.SimpleCookie


def parse_cookie(cookie):
    """
    Return a dictionary parsed from a `Cookie:` header string.
    """
    cookiedict = {}
    # Parse Cookie header similar to multiple Set-Cookie headers, using algorithm from RFC6265 section 5.2.
    # "The algorithm below is more permissive... use this algorithm so as to interoperate"
    for set_cookie_string in cookie.split(';'):
        # 1. The name-value-pair string consists of the characters up to, but not including, the first %x3B (";")
        name_value_pair = set_cookie_string  # We're already splitting on semicolon above.
        # 2. If the name-value-pair string lacks a %x3D ("=") character, ignore the set-cookie-string entirely.
        if '=' not in name_value_pair:
            continue
        # 3. The (possibly empty) name string consists of the characters up
        #    to, but not including, the first %x3D ("=") character, and the
        #    (possibly empty) value string consists of the characters after
        #    the first %x3D ("=") character.
        name, value = name_value_pair.split('=', 1)
        # 4. Remove any leading or trailing WSP characters from the name
        #    string and the value string.
        # RFC5234 Appendix B.1 says WSP means SP or HTAB
        name, value = name.strip(' \t'), value.strip(' \t')
        # 5. If the name string is empty, ignore the set-cookie-string
        #    entirely.
        if not name:
            continue
        # 6. The cookie-name is the name string, and the cookie-value is the
        #    value string.

        # The RFC allows for multiple cookies with the same name.
        # Most implementations use the first value, so match that.
        if name in cookiedict:
            continue
        # For backward-compatibility, unquote value using Python's algorithm.
        cookiedict[name] = cookies._unquote(value)
    return cookiedict
