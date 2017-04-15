import importlib
from distutils.version import StrictVersion


required_versions = {
    "asgi_rabbitmq": "0.4.0",
    "asgi_redis": "1.2.0",
    "asgi_ipc": "1.3.0",
}


def check_all():
    """
    Checks versions of all the possible packages you have installed so that
    we can easily warn people about incompatible versions.

    This is needed as there are some packages (e.g. asgi_redis) that we cannot
    declare dependencies on as they are not _required_. People usually remember
    to upgrade their Channels package so this is where we check.
    """
    for package, version in required_versions.items():
        try:
            module = importlib.import_module(package)
        except ImportError:
            continue
        else:
            if StrictVersion(version) > StrictVersion(module.__version__):
                raise RuntimeError("Your version of %s is too old - it must be at least %s" % (
                    package,
                    version,
                ))
