def aix_platform(osname, version, release):
    try:
        import _aix_support

        return _aix_support.aix_platform()
    except ImportError:
        pass
    return f"{osname}-{version}.{release}"
