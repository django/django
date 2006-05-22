from django.conf import settings
from django.db import models
from django.db.models.fields import FieldDoesNotExist

class CurrentSiteManager(models.Manager):
    "Use this to limit objects to those associated with the current site."
    def __init__(self, field_name='site'):
        super(CurrentSiteManager, self).__init__()
        self.__field_name = field_name

    def contribute_to_class(self, *args, **kwargs):
        # This method is overridden purely to check for errors in
        # self.field_name. We can't do this in __init__() because of
        # how Managers are implemented -- self.model isn't available
        # until after contribute_to_class() is called.
        super(CurrentSiteManager, self).contribute_to_class(*args, **kwargs)
        try:
            self.model._meta.get_field(self.__field_name)
        except FieldDoesNotExist:
            raise ValueError, "%s couldn't find a field named %s in %s." % \
                (self.__class__.__name__, self.__field_name, self.model._meta.object_name)
        self.__lookup = self.__field_name + '__id__exact'
        del self.__field_name

    def get_query_set(self):
        return super(SiteLimitManager, self).get_query_set().filter(**{self.__lookup: settings.SITE_ID})
