from django.core.exceptions import ImproperlyConfigured

class MissingStorageModule(ImproperlyConfigured):
    pass

class MissingStorageClass(ImproperlyConfigured):
    pass

class NoFileStorageConfigured(ImproperlyConfigured):
    pass
