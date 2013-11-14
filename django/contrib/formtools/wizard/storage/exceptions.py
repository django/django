from django.core.exceptions import ImproperlyConfigured


class MissingStorage(ImproperlyConfigured):
    pass


class NoFileStorageConfigured(ImproperlyConfigured):
    pass
