from __future__ import annotations


def get_short_path_name(long_name):
    """Gets the short path name of a given long path - http://stackoverflow.com/a/23598461/200291."""
    import ctypes  # noqa: PLC0415
    from ctypes import wintypes  # noqa: PLC0415

    GetShortPathNameW = ctypes.windll.kernel32.GetShortPathNameW  # noqa: N806
    GetShortPathNameW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
    GetShortPathNameW.restype = wintypes.DWORD
    output_buf_size = 0
    while True:
        output_buf = ctypes.create_unicode_buffer(output_buf_size)
        needed = GetShortPathNameW(long_name, output_buf, output_buf_size)
        if output_buf_size >= needed:
            return output_buf.value
        output_buf_size = needed


__all__ = [
    "get_short_path_name",
]
