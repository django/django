from freedom.core.exceptions import ImproperlyConfigured


class MissingStorage(ImproperlyConfigured):
    pass


class NoFileStorageConfigured(ImproperlyConfigured):
    pass
