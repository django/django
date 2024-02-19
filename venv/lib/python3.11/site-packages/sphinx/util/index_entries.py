from __future__ import annotations


def split_index_msg(entry_type: str, value: str) -> list[str]:
    # new entry types must be listed in util/nodes.py!
    if entry_type == 'single':
        try:
            return _split_into(2, 'single', value)
        except ValueError:
            return _split_into(1, 'single', value)
    if entry_type == 'pair':
        return _split_into(2, 'pair', value)
    if entry_type == 'triple':
        return _split_into(3, 'triple', value)
    if entry_type in {'see', 'seealso'}:
        return _split_into(2, 'see', value)
    msg = f'invalid {entry_type} index entry {value!r}'
    raise ValueError(msg)


def _split_into(n: int, type: str, value: str) -> list[str]:
    """Split an index entry into a given number of parts at semicolons."""
    parts = [x.strip() for x in value.split(';', n - 1)]
    if len(list(filter(None, parts))) < n:
        msg = f'invalid {type} index entry {value!r}'
        raise ValueError(msg)
    return parts
