def to_string(s, encoding: str = "utf-8"):
    if isinstance(s, str):
        return s
    elif isinstance(s, bytes):
        return s.decode(encoding, "ignore")
    else:
        return s  # Not a string we care about
