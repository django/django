from django.db import models
from django.conf import settings

class CurrentSiteManager(models.Manager):
    "Use this to limit objects to those associated with the current site."
    def __init__(self, field_name='site')
        super(SiteLimitManager, self).__init__()
        self.__lookup = field_name + '__id__exact'

    def get_query_set(self):
        return super(SiteLimitManager, self).get_query_set().filter(self.__lookup=settings.SITE_ID)
