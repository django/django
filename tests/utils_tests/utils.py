import platform


def on_macos_with_hfs():
    """
    MacOS 10.13 (High Sierra) and lower can use HFS+ as a filesystem.
    HFS+ has a time resolution of only one second which can be too low for
    some of the tests.
    """
    macos_version = platform.mac_ver()[0]
    if macos_version != '':
        parsed_macos_version = tuple(int(x) for x in macos_version.split('.'))
        return parsed_macos_version < (10, 14)
    return False
