from django.conf import settings
from django.db import models
from django.db.models.fields import FieldDoesNotExist

class CurrentSiteManager(models.Manager):
    "Use this to limit objects to those associated with the current site."
    def __init__(self, field_name='site'):
        super(CurrentSiteManager, self).__init__()
        self.__field_name = field_name
        self.__is_validated = False

    def get_query_set(self):
        if not self.__is_validated:
            try:
                self.model._meta.get_field(self.__field_name)
            except FieldDoesNotExist:
                raise ValueError, "%s couldn't find a field named %s in %s." % \
                    (self.__class__.__name__, self.__field_name, self.model._meta.object_name)
            self.__is_validated = True
        return super(CurrentSiteManager, self).get_query_set().filter(**{self.__field_name + '__id__exact': settings.SITE_ID})
