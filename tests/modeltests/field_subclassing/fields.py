from django.core.exceptions import FieldError
from django.db import models
from django.utils import simplejson as json
from django.utils.encoding import force_unicode


class Small(object):
    """
    A simple class to show that non-trivial Python objects can be used as
    attributes.
    """
    def __init__(self, first, second):
        self.first, self.second = first, second

    def __unicode__(self):
        return u'%s%s' % (force_unicode(self.first), force_unicode(self.second))

    def __str__(self):
        return unicode(self).encode('utf-8')

class SmallField(models.Field):
    """
    Turns the "Small" class into a Django field. Because of the similarities
    with normal character fields and the fact that Small.__unicode__ does
    something sensible, we don't need to implement a lot here.
    """
    __metaclass__ = models.SubfieldBase

    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 2
        super(SmallField, self).__init__(*args, **kwargs)

    def get_internal_type(self):
        return 'CharField'

    def to_python(self, value):
        if isinstance(value, Small):
            return value
        return Small(value[0], value[1])

    def get_db_prep_save(self, value):
        return unicode(value)

    def get_prep_lookup(self, lookup_type, value):
        if lookup_type == 'exact':
            return force_unicode(value)
        if lookup_type == 'in':
            return [force_unicode(v) for v in value]
        if lookup_type == 'isnull':
            return []
        raise TypeError('Invalid lookup type: %r' % lookup_type)


class JSONField(models.TextField):
    __metaclass__ = models.SubfieldBase
    
    description = ("JSONField automatically serializes and desializes values to "
        "and from JSON.")
    
    def to_python(self, value):
        if not value:
            return None
        
        if isinstance(value, basestring):
            value = json.loads(value)
        return value
    
    def get_db_prep_save(self, value):
        if value is None:
            return None
        return json.dumps(value)
