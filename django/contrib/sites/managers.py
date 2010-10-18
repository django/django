from django.conf import settings
from django.db import models
from django.db.models.fields import FieldDoesNotExist

class CurrentSiteManager(models.Manager):
    "Use this to limit objects to those associated with the current site."
    def __init__(self, field_name=None):
        super(CurrentSiteManager, self).__init__()
        self.__field_name = field_name
        self.__is_validated = False
        
    def _validate_field_name(self):
        field_names = self.model._meta.get_all_field_names()
        
        # If a custom name is provided, make sure the field exists on the model
        if self.__field_name is not None and self.__field_name not in field_names:
            raise ValueError("%s couldn't find a field named %s in %s." % \
                (self.__class__.__name__, self.__field_name, self.model._meta.object_name))
        
        # Otherwise, see if there is a field called either 'site' or 'sites'
        else:
            for potential_name in ['site', 'sites']:
                if potential_name in field_names:
                    self.__field_name = potential_name
                    self.__is_validated = True
                    break
        
        # Now do a type check on the field (FK or M2M only)
        try:
            field = self.model._meta.get_field(self.__field_name)
            if not isinstance(field, (models.ForeignKey, models.ManyToManyField)):
                raise TypeError("%s must be a ForeignKey or ManyToManyField." %self.__field_name)
        except FieldDoesNotExist:
            raise ValueError("%s couldn't find a field named %s in %s." % \
                    (self.__class__.__name__, self.__field_name, self.model._meta.object_name))
        self.__is_validated = True
    
    def get_query_set(self):
        if not self.__is_validated:
            self._validate_field_name()
        return super(CurrentSiteManager, self).get_query_set().filter(**{self.__field_name + '__id__exact': settings.SITE_ID})
