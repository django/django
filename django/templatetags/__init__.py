from django.conf import settings

for a in settings.INSTALLED_APPS:
    try:
        __path__.extend(__import__(a + '.templatetags', '', '', ['']).__path__)
    except ImportError:
        pass
