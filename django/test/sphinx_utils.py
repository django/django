import inspect
import sys
from os.path import abspath, dirname, join, relpath, sep


def github_linkcode_resolve(domain, info):
    """
    Resolves link to view source code.
    """
    if domain != "py":
        return None

    if not info.get("module", None):
        return None

    modname = info["module"]
    fullname = info["fullname"]
    submod = sys.modules.get(modname)

    obj = submod
    for part in fullname.split("."):
        try:
            obj = getattr(obj, part)
            str(obj)
        except Exception:
            return None

    # Handle use of @cached_property.
    if hasattr(obj, "real_func"):
        obj = getattr(obj, "real_func")

    try:
        fn = inspect.getsourcefile(obj)
    except Exception:
        fn = None

    if not fn:
        try:
            fn = inspect.getsourcefile(sys.modules[obj.__module__])
        except Exception:
            fn = None

    if not fn:
        return None

    try:
        source, lineno = inspect.getsourcelines(obj)
    except Exception:
        lineno = None

    if lineno:
        linespec = "#L%d" % lineno
    else:
        linespec = ""

    startdir = abspath(join(dirname(__file__), "../../"))
    fn = relpath(fn, start=startdir).replace(sep, "/")

    return "https://github.com/django/django/blob/main/%s%s" % (fn, linespec)
