VERSION = (0, 97, 'newforms-admin')

def get_version():
    "Returns the version as a human-format string."
    v = '.'.join([str(i) for i in VERSION[:-1]])
    if VERSION[-1]:
        v += '-' + VERSION[-1]
    return v
