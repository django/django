VERSION = (1, 0, 'alpha 2')

def get_version():
    "Returns the version as a human-format string."
    v = '.'.join([str(i) for i in VERSION[:-1]])
    if VERSION[-1]:
        from django.utils.version import get_svn_revision
        v = '%s-%s-%s' % (v, VERSION[-1], get_svn_revision())
    return v
