# from __future__ import unicode_literals

from django.db import models
# from django.utils.translation import ugettext_lazy as _
# from django.contrib.postgres.fields import ArrayField


class PositionField(models.Field):
    def __init__(self, *args, **kwargs):
        super(PositionField, self).__init__(*args, **kwargs)

    def db_type(self, connection):
        # Type is defined as char(25)
        return 'char(25)'

    def to_python(self, value):     
        #The input value is received and split into list, For example:- mapspot = 10,20  will be converted to [10,20]
        result = value.split(',')        
        return result        

    def get_db_prep_value(self, value, connection, prepared=False):            
        # The list created above is converted into a string before saving into the database.
        # When the unique check index is executed the string is used rather than the list value as expected.
        result = ','.join([str(each) for each in value])        
        return result    

    def from_db_value(self, value, expression, connection, context):
        if value is None:
            return value        
        return value        


class Map(models.Model):
    name = models.CharField(max_length=128)


class MapSpot(models.Model):
    map = models.ForeignKey('polls.Map')    
    position = PositionField()

    class Meta:
        unique_together = (('map', 'position'))







# data = {
#             'book_set-TOTAL_FORMS': '3',  # the number of forms rendered
#             'book_set-INITIAL_FORMS': '0',  # the number of forms with initial data
#             'book_set-MAX_NUM_FORMS': '',  # the max number of forms
#             'book_set-0-title': 'Les Fleurs du Mal',
#             'book_set-1-title': '',
#             'book_set-2-title': '',
#         }        

# data = {
#             'mapspot_set-TOTAL_FORMS': '3',  # the number of forms rendered
#             'mapspot_set-INITIAL_FORMS': '0',  # the number of forms with initial data
#             'mapspot_set-MAX_NUM_FORMS': '',  # the max number of forms
#             'mapspot_set-0-position': '10,20',
#             'mapspot_set-1-position': '10,20',
#             'mapspot_set-2-position': '30,40',
#         }        

# from django.forms.models import *
# MapSpotFormSet = inlineformset_factory(Map, MapSpot, can_delete=False, extra=3, fields="__all__")
# map=Map.objects.create(name='Rockville')        
# formset=MapSpotFormSet(data,instance=map)


# db_type(self, connection)
# – Defines'database'data'type,'based'on'connec$on'(e.g.'
# Postgres,'MySQL,'etc.)'
# • to_python(self, value)
# – Mapper'from'database'data'type'to'Python'data'type'
# – Use'to'put'it'in'most'convenient'Python'type,'not'display'
# type'(e.g.'HTML)'
# • get_prep_value(self, value)
# – Python'representa$on'=>'Postgres'representa$on'
# • get_prep_db_value(self, value,
# connection, prepared=False)
# – get_prep_value,'but'database'specific'

