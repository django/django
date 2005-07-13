from django.conf.settings import INSTALLED_APPS

for a in INSTALLED_APPS:
    try:
        __path__.extend(__import__(a + '.templatetags', '', '', ['']).__path__)
    except ImportError:
        pass
