VERSION = (1, 4, 0, 'alpha', 1)

def get_version():
    version = '%s.%s' % (VERSION[0], VERSION[1])
    if VERSION[2]:
        version = '%s.%s' % (version, VERSION[2])
    if VERSION[3:] == ('alpha', 0):
        version = '%s pre-alpha' % version
    else:
        if VERSION[3] != 'final':
            version = '%s %s %s' % (version, VERSION[3], VERSION[4])
    from django.utils.version import get_svn_revision
    svn_rev = get_svn_revision()
    if svn_rev != u'SVN-unknown':
        version = "%s %s" % (version, svn_rev)
    return version

def get_distutils_version():
    # Distutils expects a version number formatted as major.minor[.patch][sub]
    parts = 5
    if VERSION[3] == 'final':
        parts = 3
        if VERSION[2] == 0:
            parts = 2
    version = VERSION[:parts]
    version = [str(x)[0] for x in version]      # ['1', '4', '0', 'a', '1']
    if parts > 2:
        version[2:] = [''.join(version[2:])]    # ['1', '4', '0a1']
    version = '.'.join(version)                 # '1.4.0a1'
    return version
