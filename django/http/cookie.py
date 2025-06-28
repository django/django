from http import cookies

# For backwards compatibility in Django 2.1.
SimpleCookie = cookies.SimpleCookie

# Add support for the Partitioned cookie attribute (CHIPS - Cookies Having
# Independent Partitioned State). This is needed for Chrome's third-party
# cookie handling in iframes.
# https://developers.google.com/privacy-sandbox/3pcd/chips
# Only patch if Python version doesn't have native support for it.
# Python 3.14+ has native support for partitioned cookies.
if "partitioned" not in cookies.Morsel._flags:
    cookies.Morsel._flags.add("partitioned")
    cookies.Morsel._reserved.setdefault("partitioned", "Partitioned")


def parse_cookie(cookie):
    """
    Return a dictionary parsed from a `Cookie:` header string.
    """
    cookiedict = {}
    for chunk in cookie.split(";"):
        if "=" in chunk:
            key, val = chunk.split("=", 1)
        else:
            # Assume an empty name per
            # https://bugzilla.mozilla.org/show_bug.cgi?id=169091
            key, val = "", chunk
        key, val = key.strip(), val.strip()
        if key or val:
            # unquote using Python's algorithm.
            cookiedict[key] = cookies._unquote(val)
    return cookiedict
