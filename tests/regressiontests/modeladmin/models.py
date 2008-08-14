# coding: utf-8
from datetime import date

from django.db import models
from django.contrib.auth.models import User

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

class ValidationTestModel(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField()
    users = models.ManyToManyField(User)
    state = models.CharField(max_length=2, choices=(("CO", "Colorado"), ("WA", "Washington")))
    is_active = models.BooleanField()
    pub_date = models.DateTimeField()
    band = models.ForeignKey(Band)

class ValidationTestInlineModel(models.Model):
    parent = models.ForeignKey(ValidationTestModel)

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

>>> from django import forms
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

If we need to override the queryset of a ModelChoiceField in our custom form
make sure that RelatedFieldWidgetWrapper doesn't mess that up.

>>> band2 = Band(name='The Beetles', bio='', sign_date=date(1962, 1, 1))
>>> band2.save()

>>> class AdminConcertForm(forms.ModelForm):
...     class Meta:
...         model = Concert
...
...     def __init__(self, *args, **kwargs):
...         super(AdminConcertForm, self).__init__(*args, **kwargs)
...         self.fields["main_band"].queryset = Band.objects.filter(name='The Doors')

>>> class ConcertAdmin(ModelAdmin):
...     form = AdminConcertForm

>>> ma = ConcertAdmin(Concert, site)
>>> form = ma.get_form(request)()
>>> print form["main_band"]
<select name="main_band" id="id_main_band">
<option value="" selected="selected">---------</option>
<option value="1">The Doors</option>
</select>

>>> band2.delete()

# radio_fields behavior ################################################

First, without any radio_fields specified, the widgets for ForeignKey
and fields with choices specified ought to be a basic Select widget.
ForeignKey widgets in the admin are wrapped with RelatedFieldWidgetWrapper so
they need to be handled properly when type checking. For Select fields, all of
the choices lists have a first entry of dashes.

>>> cma = ModelAdmin(Concert, site)
>>> cmafa = cma.get_form(request)

>>> type(cmafa.base_fields['main_band'].widget.widget)
<class 'django.forms.widgets.Select'>
>>> list(cmafa.base_fields['main_band'].widget.choices)
[(u'', u'---------'), (1, u'The Doors')]

>>> type(cmafa.base_fields['opening_band'].widget.widget)
<class 'django.forms.widgets.Select'>
>>> list(cmafa.base_fields['opening_band'].widget.choices)
[(u'', u'---------'), (1, u'The Doors')]

>>> type(cmafa.base_fields['day'].widget)
<class 'django.forms.widgets.Select'>
>>> list(cmafa.base_fields['day'].widget.choices)
[('', '---------'), (1, 'Fri'), (2, 'Sat')]

>>> type(cmafa.base_fields['transport'].widget)
<class 'django.forms.widgets.Select'>
>>> list(cmafa.base_fields['transport'].widget.choices)
[('', '---------'), (1, 'Plane'), (2, 'Train'), (3, 'Bus')]

Now specify all the fields as radio_fields.  Widgets should now be
RadioSelect, and the choices list should have a first entry of 'None' if
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

>>> type(cmafa.base_fields['main_band'].widget.widget)
<class 'django.contrib.admin.widgets.AdminRadioSelect'>
>>> cmafa.base_fields['main_band'].widget.attrs
{'class': 'radiolist inline'}
>>> list(cmafa.base_fields['main_band'].widget.choices)
[(1, u'The Doors')]

>>> type(cmafa.base_fields['opening_band'].widget.widget)
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

# ModelAdmin Option Validation ################################################

>>> from django.contrib.admin.validation import validate
>>> from django.conf import settings

# Ensure validation only runs when DEBUG = True

>>> settings.DEBUG = True

>>> class ValidationTestModelAdmin(ModelAdmin):
...     raw_id_fields = 10
>>> site = AdminSite()
>>> site.register(ValidationTestModel, ValidationTestModelAdmin)
Traceback (most recent call last):
...
ImproperlyConfigured: `ValidationTestModelAdmin.raw_id_fields` must be a list or tuple.

>>> settings.DEBUG = False

>>> class ValidationTestModelAdmin(ModelAdmin):
...     raw_id_fields = 10
>>> site = AdminSite()
>>> site.register(ValidationTestModel, ValidationTestModelAdmin)

# raw_id_fields

>>> class ValidationTestModelAdmin(ModelAdmin):
...     raw_id_fields = 10
>>> validate(ValidationTestModelAdmin, ValidationTestModel)
Traceback (most recent call last):
...
ImproperlyConfigured: `ValidationTestModelAdmin.raw_id_fields` must be a list or tuple.

>>> class ValidationTestModelAdmin(ModelAdmin):
...     raw_id_fields = ('non_existent_field',)
>>> validate(ValidationTestModelAdmin, ValidationTestModel)
Traceback (most recent call last):
...
ImproperlyConfigured: `ValidationTestModelAdmin.raw_id_fields` refers to field `non_existent_field` that is missing from model `ValidationTestModel`.

>>> class ValidationTestModelAdmin(ModelAdmin):
...     raw_id_fields = ('name',)
>>> validate(ValidationTestModelAdmin, ValidationTestModel)
Traceback (most recent call last):
...
ImproperlyConfigured: `ValidationTestModelAdmin.raw_id_fields[0]`, `name` must be either a ForeignKey or ManyToManyField.

>>> class ValidationTestModelAdmin(ModelAdmin):
...     raw_id_fields = ('users',)
>>> validate(ValidationTestModelAdmin, ValidationTestModel)

# fieldsets

>>> class ValidationTestModelAdmin(ModelAdmin):
...     fieldsets = 10
>>> validate(ValidationTestModelAdmin, ValidationTestModel)
Traceback (most recent call last):
...
ImproperlyConfigured: `ValidationTestModelAdmin.fieldsets` must be a list or tuple.

>>> class ValidationTestModelAdmin(ModelAdmin):
...     fieldsets = ({},)
>>> validate(ValidationTestModelAdmin, ValidationTestModel)
Traceback (most recent call last):
...
ImproperlyConfigured: `ValidationTestModelAdmin.fieldsets[0]` must be a list or tuple.

>>> class ValidationTestModelAdmin(ModelAdmin):
...     fieldsets = ((),)
>>> validate(ValidationTestModelAdmin, ValidationTestModel)
Traceback (most recent call last):
...
ImproperlyConfigured: `ValidationTestModelAdmin.fieldsets[0]` does not have exactly two elements.

>>> class ValidationTestModelAdmin(ModelAdmin):
...     fieldsets = (("General", ()),)
>>> validate(ValidationTestModelAdmin, ValidationTestModel)
Traceback (most recent call last):
...
ImproperlyConfigured: `ValidationTestModelAdmin.fieldsets[0][1]` must be a dictionary.

>>> class ValidationTestModelAdmin(ModelAdmin):
...     fieldsets = (("General", {}),)
>>> validate(ValidationTestModelAdmin, ValidationTestModel)
Traceback (most recent call last):
...
ImproperlyConfigured: `fields` key is required in ValidationTestModelAdmin.fieldsets[0][1] field options dict.

>>> class ValidationTestModelAdmin(ModelAdmin):
...     fieldsets = (("General", {"fields": ("non_existent_field",)}),)
>>> validate(ValidationTestModelAdmin, ValidationTestModel)
Traceback (most recent call last):
...
ImproperlyConfigured: `ValidationTestModelAdmin.fieldsets[0][1]['fields']` refers to field `non_existent_field` that is missing from the form.

>>> class ValidationTestModelAdmin(ModelAdmin):
...     fieldsets = (("General", {"fields": ("name",)}),)
>>> validate(ValidationTestModelAdmin, ValidationTestModel)

>>> class ValidationTestModelAdmin(ModelAdmin):
...     fieldsets = (("General", {"fields": ("name",)}),)
...     fields = ["name",]
>>> validate(ValidationTestModelAdmin, ValidationTestModel)
Traceback (most recent call last):
...
ImproperlyConfigured: Both fieldsets and fields are specified in ValidationTestModelAdmin.

>>> class ValidationTestModelAdmin(ModelAdmin): 
...     fieldsets = [(None, {'fields': ['name', 'name']})] 
>>> validate(ValidationTestModelAdmin, ValidationTestModel) 
Traceback (most recent call last): 
... 
ImproperlyConfigured: There are duplicate field(s) in ValidationTestModelAdmin.fieldsets

>>> class ValidationTestModelAdmin(ModelAdmin):
...     fields = ["name", "name"]
>>> validate(ValidationTestModelAdmin, ValidationTestModel)
Traceback (most recent call last):
...
ImproperlyConfigured: There are duplicate field(s) in ValidationTestModelAdmin.fields

# form

>>> class FakeForm(object):
...     pass
>>> class ValidationTestModelAdmin(ModelAdmin):
...     form = FakeForm
>>> validate(ValidationTestModelAdmin, ValidationTestModel)
Traceback (most recent call last):
...
ImproperlyConfigured: ValidationTestModelAdmin.form does not inherit from BaseModelForm.

# fielsets with custom form

>>> class BandAdmin(ModelAdmin):
...     fieldsets = (
...         ('Band', {
...             'fields': ('non_existent_field',)
...         }),
...     )
>>> validate(BandAdmin, Band)
Traceback (most recent call last):
...
ImproperlyConfigured: `BandAdmin.fieldsets[0][1]['fields']` refers to field `non_existent_field` that is missing from the form.

>>> class BandAdmin(ModelAdmin):
...     fieldsets = (
...         ('Band', {
...             'fields': ('name',)
...         }),
...     )
>>> validate(BandAdmin, Band)

>>> class AdminBandForm(forms.ModelForm):
...     class Meta:
...         model = Band
>>> class BandAdmin(ModelAdmin):
...     form = AdminBandForm
...
...     fieldsets = (
...         ('Band', {
...             'fields': ('non_existent_field',)
...         }),
...     )
>>> validate(BandAdmin, Band)
Traceback (most recent call last):
...
ImproperlyConfigured: `BandAdmin.fieldsets[0][1]['fields']` refers to field `non_existent_field` that is missing from the form.

>>> class AdminBandForm(forms.ModelForm):
...     delete = forms.BooleanField()
...
...     class Meta:
...         model = Band
>>> class BandAdmin(ModelAdmin):
...     form = AdminBandForm
...
...     fieldsets = (
...         ('Band', {
...             'fields': ('name', 'bio', 'sign_date', 'delete')
...         }),
...     )
>>> validate(BandAdmin, Band)

# filter_vertical

>>> class ValidationTestModelAdmin(ModelAdmin):
...     filter_vertical = 10
>>> validate(ValidationTestModelAdmin, ValidationTestModel)
Traceback (most recent call last):
...
ImproperlyConfigured: `ValidationTestModelAdmin.filter_vertical` must be a list or tuple.

>>> class ValidationTestModelAdmin(ModelAdmin):
...     filter_vertical = ("non_existent_field",)
>>> validate(ValidationTestModelAdmin, ValidationTestModel)
Traceback (most recent call last):
...
ImproperlyConfigured: `ValidationTestModelAdmin.filter_vertical` refers to field `non_existent_field` that is missing from model `ValidationTestModel`.

>>> class ValidationTestModelAdmin(ModelAdmin):
...     filter_vertical = ("name",)
>>> validate(ValidationTestModelAdmin, ValidationTestModel)
Traceback (most recent call last):
...
ImproperlyConfigured: `ValidationTestModelAdmin.filter_vertical[0]` must be a ManyToManyField.

>>> class ValidationTestModelAdmin(ModelAdmin):
...     filter_vertical = ("users",)
>>> validate(ValidationTestModelAdmin, ValidationTestModel)

# filter_horizontal

>>> class ValidationTestModelAdmin(ModelAdmin):
...     filter_horizontal = 10
>>> validate(ValidationTestModelAdmin, ValidationTestModel)
Traceback (most recent call last):
...
ImproperlyConfigured: `ValidationTestModelAdmin.filter_horizontal` must be a list or tuple.

>>> class ValidationTestModelAdmin(ModelAdmin):
...     filter_horizontal = ("non_existent_field",)
>>> validate(ValidationTestModelAdmin, ValidationTestModel)
Traceback (most recent call last):
...
ImproperlyConfigured: `ValidationTestModelAdmin.filter_horizontal` refers to field `non_existent_field` that is missing from model `ValidationTestModel`.

>>> class ValidationTestModelAdmin(ModelAdmin):
...     filter_horizontal = ("name",)
>>> validate(ValidationTestModelAdmin, ValidationTestModel)
Traceback (most recent call last):
...
ImproperlyConfigured: `ValidationTestModelAdmin.filter_horizontal[0]` must be a ManyToManyField.

>>> class ValidationTestModelAdmin(ModelAdmin):
...     filter_horizontal = ("users",)
>>> validate(ValidationTestModelAdmin, ValidationTestModel)

# radio_fields

>>> class ValidationTestModelAdmin(ModelAdmin):
...     radio_fields = ()
>>> validate(ValidationTestModelAdmin, ValidationTestModel)
Traceback (most recent call last):
...
ImproperlyConfigured: `ValidationTestModelAdmin.radio_fields` must be a dictionary.

>>> class ValidationTestModelAdmin(ModelAdmin):
...     radio_fields = {"non_existent_field": None}
>>> validate(ValidationTestModelAdmin, ValidationTestModel)
Traceback (most recent call last):
...
ImproperlyConfigured: `ValidationTestModelAdmin.radio_fields` refers to field `non_existent_field` that is missing from model `ValidationTestModel`.

>>> class ValidationTestModelAdmin(ModelAdmin):
...     radio_fields = {"name": None}
>>> validate(ValidationTestModelAdmin, ValidationTestModel)
Traceback (most recent call last):
...
ImproperlyConfigured: `ValidationTestModelAdmin.radio_fields['name']` is neither an instance of ForeignKey nor does have choices set.

>>> class ValidationTestModelAdmin(ModelAdmin):
...     radio_fields = {"state": None}
>>> validate(ValidationTestModelAdmin, ValidationTestModel)
Traceback (most recent call last):
...
ImproperlyConfigured: `ValidationTestModelAdmin.radio_fields['state']` is neither admin.HORIZONTAL nor admin.VERTICAL.

>>> class ValidationTestModelAdmin(ModelAdmin):
...     radio_fields = {"state": VERTICAL}
>>> validate(ValidationTestModelAdmin, ValidationTestModel)

# prepopulated_fields

>>> class ValidationTestModelAdmin(ModelAdmin):
...     prepopulated_fields = ()
>>> validate(ValidationTestModelAdmin, ValidationTestModel)
Traceback (most recent call last):
...
ImproperlyConfigured: `ValidationTestModelAdmin.prepopulated_fields` must be a dictionary.

>>> class ValidationTestModelAdmin(ModelAdmin):
...     prepopulated_fields = {"non_existent_field": None}
>>> validate(ValidationTestModelAdmin, ValidationTestModel)
Traceback (most recent call last):
...
ImproperlyConfigured: `ValidationTestModelAdmin.prepopulated_fields` refers to field `non_existent_field` that is missing from model `ValidationTestModel`.

>>> class ValidationTestModelAdmin(ModelAdmin):
...     prepopulated_fields = {"slug": ("non_existent_field",)}
>>> validate(ValidationTestModelAdmin, ValidationTestModel)
Traceback (most recent call last):
...
ImproperlyConfigured: `ValidationTestModelAdmin.prepopulated_fields['non_existent_field'][0]` refers to field `non_existent_field` that is missing from model `ValidationTestModel`.

>>> class ValidationTestModelAdmin(ModelAdmin):
...     prepopulated_fields = {"users": ("name",)}
>>> validate(ValidationTestModelAdmin, ValidationTestModel)
Traceback (most recent call last):
...
ImproperlyConfigured: `ValidationTestModelAdmin.prepopulated_fields['users']` is either a DateTimeField, ForeignKey or ManyToManyField. This isn't allowed.

>>> class ValidationTestModelAdmin(ModelAdmin):
...     prepopulated_fields = {"slug": ("name",)}
>>> validate(ValidationTestModelAdmin, ValidationTestModel)

# list_display

>>> class ValidationTestModelAdmin(ModelAdmin):
...     list_display = 10
>>> validate(ValidationTestModelAdmin, ValidationTestModel)
Traceback (most recent call last):
...
ImproperlyConfigured: `ValidationTestModelAdmin.list_display` must be a list or tuple.

>>> class ValidationTestModelAdmin(ModelAdmin):
...     list_display = ('non_existent_field',)
>>> validate(ValidationTestModelAdmin, ValidationTestModel)
Traceback (most recent call last):
...
ImproperlyConfigured: ValidationTestModelAdmin.list_display[0], 'non_existent_field' is not a callable or an attribute of 'ValidationTestModelAdmin' or found in the model 'ValidationTestModel'.


>>> class ValidationTestModelAdmin(ModelAdmin):
...     list_display = ('users',)
>>> validate(ValidationTestModelAdmin, ValidationTestModel)
Traceback (most recent call last):
...
ImproperlyConfigured: `ValidationTestModelAdmin.list_display[0]`, `users` is a ManyToManyField which is not supported.

>>> class ValidationTestModelAdmin(ModelAdmin):
...     list_display = ('name',)
>>> validate(ValidationTestModelAdmin, ValidationTestModel)

# list_display_links

>>> class ValidationTestModelAdmin(ModelAdmin):
...     list_display_links = 10
>>> validate(ValidationTestModelAdmin, ValidationTestModel)
Traceback (most recent call last):
...
ImproperlyConfigured: `ValidationTestModelAdmin.list_display_links` must be a list or tuple.

>>> class ValidationTestModelAdmin(ModelAdmin):
...     list_display_links = ('non_existent_field',)
>>> validate(ValidationTestModelAdmin, ValidationTestModel)
Traceback (most recent call last):
...
ImproperlyConfigured: `ValidationTestModelAdmin.list_display_links[0]` refers to `non_existent_field` that is neither a field, method or property of model `ValidationTestModel`.

>>> class ValidationTestModelAdmin(ModelAdmin):
...     list_display_links = ('name',)
>>> validate(ValidationTestModelAdmin, ValidationTestModel)
Traceback (most recent call last):
...
ImproperlyConfigured: `ValidationTestModelAdmin.list_display_links[0]`refers to `name` which is not defined in `list_display`.

>>> class ValidationTestModelAdmin(ModelAdmin):
...     list_display = ('name',)
...     list_display_links = ('name',)
>>> validate(ValidationTestModelAdmin, ValidationTestModel)

# list_filter

>>> class ValidationTestModelAdmin(ModelAdmin):
...     list_filter = 10
>>> validate(ValidationTestModelAdmin, ValidationTestModel)
Traceback (most recent call last):
...
ImproperlyConfigured: `ValidationTestModelAdmin.list_filter` must be a list or tuple.

>>> class ValidationTestModelAdmin(ModelAdmin):
...     list_filter = ('non_existent_field',)
>>> validate(ValidationTestModelAdmin, ValidationTestModel)
Traceback (most recent call last):
...
ImproperlyConfigured: `ValidationTestModelAdmin.list_filter[0]` refers to field `non_existent_field` that is missing from model `ValidationTestModel`.

>>> class ValidationTestModelAdmin(ModelAdmin):
...     list_filter = ('is_active',)
>>> validate(ValidationTestModelAdmin, ValidationTestModel)

# list_per_page

>>> class ValidationTestModelAdmin(ModelAdmin):
...     list_per_page = 'hello'
>>> validate(ValidationTestModelAdmin, ValidationTestModel)
Traceback (most recent call last):
...
ImproperlyConfigured: `ValidationTestModelAdmin.list_per_page` should be a integer.

>>> class ValidationTestModelAdmin(ModelAdmin):
...     list_per_page = 100
>>> validate(ValidationTestModelAdmin, ValidationTestModel)

# search_fields

>>> class ValidationTestModelAdmin(ModelAdmin):
...     search_fields = 10
>>> validate(ValidationTestModelAdmin, ValidationTestModel)
Traceback (most recent call last):
...
ImproperlyConfigured: `ValidationTestModelAdmin.search_fields` must be a list or tuple.

# date_hierarchy

>>> class ValidationTestModelAdmin(ModelAdmin):
...     date_hierarchy = 'non_existent_field'
>>> validate(ValidationTestModelAdmin, ValidationTestModel)
Traceback (most recent call last):
...
ImproperlyConfigured: `ValidationTestModelAdmin.date_hierarchy` refers to field `non_existent_field` that is missing from model `ValidationTestModel`.

>>> class ValidationTestModelAdmin(ModelAdmin):
...     date_hierarchy = 'name'
>>> validate(ValidationTestModelAdmin, ValidationTestModel)
Traceback (most recent call last):
...
ImproperlyConfigured: `ValidationTestModelAdmin.date_hierarchy is neither an instance of DateField nor DateTimeField.

>>> class ValidationTestModelAdmin(ModelAdmin):
...     date_hierarchy = 'pub_date'
>>> validate(ValidationTestModelAdmin, ValidationTestModel)

# ordering

>>> class ValidationTestModelAdmin(ModelAdmin):
...     ordering = 10
>>> validate(ValidationTestModelAdmin, ValidationTestModel)
Traceback (most recent call last):
...
ImproperlyConfigured: `ValidationTestModelAdmin.ordering` must be a list or tuple.

>>> class ValidationTestModelAdmin(ModelAdmin):
...     ordering = ('non_existent_field',)
>>> validate(ValidationTestModelAdmin, ValidationTestModel)
Traceback (most recent call last):
...
ImproperlyConfigured: `ValidationTestModelAdmin.ordering[0]` refers to field `non_existent_field` that is missing from model `ValidationTestModel`.

>>> class ValidationTestModelAdmin(ModelAdmin):
...     ordering = ('?', 'name')
>>> validate(ValidationTestModelAdmin, ValidationTestModel)
Traceback (most recent call last):
...
ImproperlyConfigured: `ValidationTestModelAdmin.ordering` has the random ordering marker `?`, but contains other fields as well. Please either remove `?` or the other fields.

>>> class ValidationTestModelAdmin(ModelAdmin):
...     ordering = ('?',)
>>> validate(ValidationTestModelAdmin, ValidationTestModel)

>>> class ValidationTestModelAdmin(ModelAdmin):
...     ordering = ('band__name',)
>>> validate(ValidationTestModelAdmin, ValidationTestModel)

>>> class ValidationTestModelAdmin(ModelAdmin):
...     ordering = ('name',)
>>> validate(ValidationTestModelAdmin, ValidationTestModel)

# list_select_related

>>> class ValidationTestModelAdmin(ModelAdmin):
...     list_select_related = 1
>>> validate(ValidationTestModelAdmin, ValidationTestModel)
Traceback (most recent call last):
...
ImproperlyConfigured: `ValidationTestModelAdmin.list_select_related` should be a boolean.

>>> class ValidationTestModelAdmin(ModelAdmin):
...     list_select_related = False
>>> validate(ValidationTestModelAdmin, ValidationTestModel)

# save_as

>>> class ValidationTestModelAdmin(ModelAdmin):
...     save_as = 1
>>> validate(ValidationTestModelAdmin, ValidationTestModel)
Traceback (most recent call last):
...
ImproperlyConfigured: `ValidationTestModelAdmin.save_as` should be a boolean.

>>> class ValidationTestModelAdmin(ModelAdmin):
...     save_as = True
>>> validate(ValidationTestModelAdmin, ValidationTestModel)

# save_on_top

>>> class ValidationTestModelAdmin(ModelAdmin):
...     save_on_top = 1
>>> validate(ValidationTestModelAdmin, ValidationTestModel)
Traceback (most recent call last):
...
ImproperlyConfigured: `ValidationTestModelAdmin.save_on_top` should be a boolean.

>>> class ValidationTestModelAdmin(ModelAdmin):
...     save_on_top = True
>>> validate(ValidationTestModelAdmin, ValidationTestModel)

# inlines

>>> from django.contrib.admin.options import TabularInline

>>> class ValidationTestModelAdmin(ModelAdmin):
...     inlines = 10
>>> validate(ValidationTestModelAdmin, ValidationTestModel)
Traceback (most recent call last):
...
ImproperlyConfigured: `ValidationTestModelAdmin.inlines` must be a list or tuple.

>>> class ValidationTestInline(object):
...     pass
>>> class ValidationTestModelAdmin(ModelAdmin):
...     inlines = [ValidationTestInline]
>>> validate(ValidationTestModelAdmin, ValidationTestModel)
Traceback (most recent call last):
...
ImproperlyConfigured: `ValidationTestModelAdmin.inlines[0]` does not inherit from BaseModelAdmin.

>>> class ValidationTestInline(TabularInline):
...     pass
>>> class ValidationTestModelAdmin(ModelAdmin):
...     inlines = [ValidationTestInline]
>>> validate(ValidationTestModelAdmin, ValidationTestModel)
Traceback (most recent call last):
...
ImproperlyConfigured: `model` is a required attribute of `ValidationTestModelAdmin.inlines[0]`.

>>> class SomethingBad(object):
...     pass
>>> class ValidationTestInline(TabularInline):
...     model = SomethingBad
>>> class ValidationTestModelAdmin(ModelAdmin):
...     inlines = [ValidationTestInline]
>>> validate(ValidationTestModelAdmin, ValidationTestModel)
Traceback (most recent call last):
...
ImproperlyConfigured: `ValidationTestModelAdmin.inlines[0].model` does not inherit from models.Model.

>>> class ValidationTestInline(TabularInline):
...     model = ValidationTestInlineModel
>>> class ValidationTestModelAdmin(ModelAdmin):
...     inlines = [ValidationTestInline]
>>> validate(ValidationTestModelAdmin, ValidationTestModel)

# fields

>>> class ValidationTestInline(TabularInline):
...     model = ValidationTestInlineModel
...     fields = 10
>>> class ValidationTestModelAdmin(ModelAdmin):
...     inlines = [ValidationTestInline]
>>> validate(ValidationTestModelAdmin, ValidationTestModel)
Traceback (most recent call last):
...
ImproperlyConfigured: `ValidationTestInline.fields` must be a list or tuple.

>>> class ValidationTestInline(TabularInline):
...     model = ValidationTestInlineModel
...     fields = ("non_existent_field",)
>>> class ValidationTestModelAdmin(ModelAdmin):
...     inlines = [ValidationTestInline]
>>> validate(ValidationTestModelAdmin, ValidationTestModel)
Traceback (most recent call last):
...
ImproperlyConfigured: `ValidationTestInline.fields` refers to field `non_existent_field` that is missing from the form.

# fk_name

>>> class ValidationTestInline(TabularInline):
...     model = ValidationTestInlineModel
...     fk_name = "non_existent_field"
>>> class ValidationTestModelAdmin(ModelAdmin):
...     inlines = [ValidationTestInline]
>>> validate(ValidationTestModelAdmin, ValidationTestModel)
Traceback (most recent call last):
...
ImproperlyConfigured: `ValidationTestInline.fk_name` refers to field `non_existent_field` that is missing from model `ValidationTestInlineModel`.

>>> class ValidationTestInline(TabularInline):
...     model = ValidationTestInlineModel
...     fk_name = "parent"
>>> class ValidationTestModelAdmin(ModelAdmin):
...     inlines = [ValidationTestInline]
>>> validate(ValidationTestModelAdmin, ValidationTestModel)

# extra

>>> class ValidationTestInline(TabularInline):
...     model = ValidationTestInlineModel
...     extra = "hello"
>>> class ValidationTestModelAdmin(ModelAdmin):
...     inlines = [ValidationTestInline]
>>> validate(ValidationTestModelAdmin, ValidationTestModel)
Traceback (most recent call last):
...
ImproperlyConfigured: `ValidationTestInline.extra` should be a integer.

>>> class ValidationTestInline(TabularInline):
...     model = ValidationTestInlineModel
...     extra = 2
>>> class ValidationTestModelAdmin(ModelAdmin):
...     inlines = [ValidationTestInline]
>>> validate(ValidationTestModelAdmin, ValidationTestModel)

# max_num

>>> class ValidationTestInline(TabularInline):
...     model = ValidationTestInlineModel
...     max_num = "hello"
>>> class ValidationTestModelAdmin(ModelAdmin):
...     inlines = [ValidationTestInline]
>>> validate(ValidationTestModelAdmin, ValidationTestModel)
Traceback (most recent call last):
...
ImproperlyConfigured: `ValidationTestInline.max_num` should be a integer.

>>> class ValidationTestInline(TabularInline):
...     model = ValidationTestInlineModel
...     max_num = 2
>>> class ValidationTestModelAdmin(ModelAdmin):
...     inlines = [ValidationTestInline]
>>> validate(ValidationTestModelAdmin, ValidationTestModel)

# formset

>>> from django.forms.models import BaseModelFormSet

>>> class FakeFormSet(object):
...     pass
>>> class ValidationTestInline(TabularInline):
...     model = ValidationTestInlineModel
...     formset = FakeFormSet
>>> class ValidationTestModelAdmin(ModelAdmin):
...     inlines = [ValidationTestInline]
>>> validate(ValidationTestModelAdmin, ValidationTestModel)
Traceback (most recent call last):
...
ImproperlyConfigured: `ValidationTestInline.formset` does not inherit from BaseModelFormSet.

>>> class RealModelFormSet(BaseModelFormSet):
...     pass
>>> class ValidationTestInline(TabularInline):
...     model = ValidationTestInlineModel
...     formset = RealModelFormSet
>>> class ValidationTestModelAdmin(ModelAdmin):
...     inlines = [ValidationTestInline]
>>> validate(ValidationTestModelAdmin, ValidationTestModel)

"""
}
