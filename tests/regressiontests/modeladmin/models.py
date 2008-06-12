# coding: utf-8
from django.db import models
from datetime import date

class Band(models.Model):
    name = models.CharField(max_length=100)
    bio = models.TextField()
    sign_date = models.DateField()
    
    def __unicode__(self):
        return self.name

class Concert(models.Model):
    main_band = models.ForeignKey(Band, related_name='main_concerts')
    opening_band = models.ForeignKey(Band, related_name='opening_concerts',
        blank=True)
    day = models.CharField(max_length=3, choices=((1, 'Fri'), (2, 'Sat')))
    transport = models.CharField(max_length=100, choices=(
        (1, 'Plane'),
        (2, 'Train'),
        (3, 'Bus')
    ), blank=True)


__test__ = {'API_TESTS': """

>>> from django.contrib.admin.options import ModelAdmin, HORIZONTAL, VERTICAL
>>> from django.contrib.admin.sites import AdminSite

None of the following tests really depend on the content of the request, so
we'll just pass in None.

>>> request = None

# the sign_date is not 100 percent accurate ;)
>>> band = Band(name='The Doors', bio='', sign_date=date(1965, 1, 1))
>>> band.save()

Under the covers, the admin system will initialize ModelAdmin with a Model
class and an AdminSite instance, so let's just go ahead and do that manually
for testing.

>>> site = AdminSite()
>>> ma = ModelAdmin(Band, site)

>>> ma.get_form(request).base_fields.keys()
['name', 'bio', 'sign_date']


# form/fields/fieldsets interaction ##########################################

fieldsets_add and fieldsets_change should return a special data structure that
is used in the templates. They should generate the "right thing" whether we
have specified a custom form, the fields arugment, or nothing at all.

Here's the default case. There are no custom form_add/form_change methods,
no fields argument, and no fieldsets argument.

>>> ma = ModelAdmin(Band, site)
>>> ma.get_fieldsets(request)
[(None, {'fields': ['name', 'bio', 'sign_date']})]
>>> ma.get_fieldsets(request, band)
[(None, {'fields': ['name', 'bio', 'sign_date']})]


If we specify the fields argument, fieldsets_add and fielsets_change should
just stick the fields into a formsets structure and return it.

>>> class BandAdmin(ModelAdmin):
...     fields = ['name']

>>> ma = BandAdmin(Band, site)
>>> ma.get_fieldsets(request)
[(None, {'fields': ['name']})]
>>> ma.get_fieldsets(request, band)
[(None, {'fields': ['name']})]




If we specify fields or fieldsets, it should exclude fields on the Form class
to the fields specified. This may cause errors to be raised in the db layer if
required model fields arent in fields/fieldsets, but that's preferable to
ghost errors where you have a field in your Form class that isn't being
displayed because you forgot to add it to fields/fielsets

>>> class BandAdmin(ModelAdmin):
...     fields = ['name']

>>> ma = BandAdmin(Band, site)
>>> ma.get_form(request).base_fields.keys()
['name']
>>> ma.get_form(request, band).base_fields.keys()
['name']

>>> class BandAdmin(ModelAdmin):
...     fieldsets = [(None, {'fields': ['name']})]

>>> ma = BandAdmin(Band, site)
>>> ma.get_form(request).base_fields.keys()
['name']
>>> ma.get_form(request, band).base_fields.keys()
['name']


If we specify a form, it should use it allowing custom validation to work
properly. This won't, however, break any of the admin widgets or media.

>>> from django import newforms as forms
>>> class AdminBandForm(forms.ModelForm):
...     delete = forms.BooleanField()
...     
...     class Meta:
...         model = Band

>>> class BandAdmin(ModelAdmin):
...     form = AdminBandForm

>>> ma = BandAdmin(Band, site)
>>> ma.get_form(request).base_fields.keys()
['name', 'bio', 'sign_date', 'delete']
>>> type(ma.get_form(request).base_fields['sign_date'].widget)
<class 'django.contrib.admin.widgets.AdminDateWidget'>

# radio_fields behavior ################################################

First, without any radio_fields specified, the widgets for ForeignKey
and fields with choices specified ought to be a basic Select widget.
For Select fields, all of the choices lists have a first entry of dashes.

>>> cma = ModelAdmin(Concert, site)
>>> cmafa = cma.get_form(request)

>>> type(cmafa.base_fields['main_band'].widget)
<class 'django.newforms.widgets.Select'>
>>> list(cmafa.base_fields['main_band'].widget.choices)
[(u'', u'---------'), (1, u'The Doors')]

>>> type(cmafa.base_fields['opening_band'].widget)
<class 'django.newforms.widgets.Select'>
>>> list(cmafa.base_fields['opening_band'].widget.choices)
[(u'', u'---------'), (1, u'The Doors')]

>>> type(cmafa.base_fields['day'].widget)
<class 'django.newforms.widgets.Select'>
>>> list(cmafa.base_fields['day'].widget.choices)
[('', '---------'), (1, 'Fri'), (2, 'Sat')]

>>> type(cmafa.base_fields['transport'].widget)
<class 'django.newforms.widgets.Select'>
>>> list(cmafa.base_fields['transport'].widget.choices)
[('', '---------'), (1, 'Plane'), (2, 'Train'), (3, 'Bus')]

Now specify all the fields as radio_fields.  Widgets should now be
RadioSelect, and the choices list should have a first entry of 'None' iff
blank=True for the model field.  Finally, the widget should have the
'radiolist' attr, and 'inline' as well if the field is specified HORIZONTAL.

>>> class ConcertAdmin(ModelAdmin):
...     radio_fields = {
...         'main_band': HORIZONTAL,
...         'opening_band': VERTICAL,
...         'day': VERTICAL,
...         'transport': HORIZONTAL,
...     }

>>> cma = ConcertAdmin(Concert, site)
>>> cmafa = cma.get_form(request)

>>> type(cmafa.base_fields['main_band'].widget)
<class 'django.contrib.admin.widgets.AdminRadioSelect'>
>>> cmafa.base_fields['main_band'].widget.attrs
{'class': 'radiolist inline'}
>>> list(cmafa.base_fields['main_band'].widget.choices)
[(1, u'The Doors')]

>>> type(cmafa.base_fields['opening_band'].widget)
<class 'django.contrib.admin.widgets.AdminRadioSelect'>
>>> cmafa.base_fields['opening_band'].widget.attrs
{'class': 'radiolist'}
>>> list(cmafa.base_fields['opening_band'].widget.choices)
[(u'', u'None'), (1, u'The Doors')]

>>> type(cmafa.base_fields['day'].widget)
<class 'django.contrib.admin.widgets.AdminRadioSelect'>
>>> cmafa.base_fields['day'].widget.attrs
{'class': 'radiolist'}
>>> list(cmafa.base_fields['day'].widget.choices)
[(1, 'Fri'), (2, 'Sat')]

>>> type(cmafa.base_fields['transport'].widget)
<class 'django.contrib.admin.widgets.AdminRadioSelect'>
>>> cmafa.base_fields['transport'].widget.attrs
{'class': 'radiolist inline'}
>>> list(cmafa.base_fields['transport'].widget.choices)
[('', u'None'), (1, 'Plane'), (2, 'Train'), (3, 'Bus')]

>>> band.delete()

"""
}
