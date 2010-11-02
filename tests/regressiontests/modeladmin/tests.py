from datetime import date
import unittest

from django import forms
from django.conf import settings
from django.contrib.admin.options import ModelAdmin, TabularInline, \
    HORIZONTAL, VERTICAL
from django.contrib.admin.sites import AdminSite
from django.contrib.admin.validation import validate
from django.contrib.admin.widgets import AdminDateWidget, AdminRadioSelect
from django.core.exceptions import ImproperlyConfigured
from django.forms.models import BaseModelFormSet
from django.forms.widgets import Select
from django.test import TestCase

from models import Band, Concert, ValidationTestModel, \
    ValidationTestInlineModel


# None of the following tests really depend on the content of the request,
# so we'll just pass in None.
request = None


class ModelAdminTests(TestCase):

    def setUp(self):
        self.band = Band.objects.create(
            name='The Doors',
            bio='',
            sign_date=date(1965, 1, 1),
        )
        self.site = AdminSite()

    # form/fields/fieldsets interaction ##############################

    def test_default_fields(self):
        ma = ModelAdmin(Band, self.site)

        self.assertEquals(ma.get_form(request).base_fields.keys(),
            ['name', 'bio', 'sign_date'])

    def test_default_fieldsets(self):
        # fieldsets_add and fieldsets_change should return a special data structure that
        # is used in the templates. They should generate the "right thing" whether we
        # have specified a custom form, the fields argument, or nothing at all.
        #
        # Here's the default case. There are no custom form_add/form_change methods,
        # no fields argument, and no fieldsets argument.
        ma = ModelAdmin(Band, self.site)
        self.assertEqual(ma.get_fieldsets(request),
            [(None, {'fields': ['name', 'bio', 'sign_date']})])

        self.assertEqual(ma.get_fieldsets(request, self.band),
            [(None, {'fields': ['name', 'bio', 'sign_date']})])

    def test_field_arguments(self):
        # If we specify the fields argument, fieldsets_add and fielsets_change should
        # just stick the fields into a formsets structure and return it.
        class BandAdmin(ModelAdmin):
             fields = ['name']

        ma = BandAdmin(Band, self.site)

        self.assertEqual( ma.get_fieldsets(request),
            [(None, {'fields': ['name']})])

        self.assertEqual(ma.get_fieldsets(request, self.band),
            [(None, {'fields': ['name']})])

    def test_field_arguments_restricted_on_form(self):
        # If we specify fields or fieldsets, it should exclude fields on the Form class
        # to the fields specified. This may cause errors to be raised in the db layer if
        # required model fields arent in fields/fieldsets, but that's preferable to
        # ghost errors where you have a field in your Form class that isn't being
        # displayed because you forgot to add it to fields/fieldsets

        # Using `fields`.
        class BandAdmin(ModelAdmin):
            fields = ['name']

        ma = BandAdmin(Band, self.site)
        self.assertEqual(ma.get_form(request).base_fields.keys(), ['name'])
        self.assertEqual(ma.get_form(request, self.band).base_fields.keys(),
            ['name'])

        # Using `fieldsets`.
        class BandAdmin(ModelAdmin):
            fieldsets = [(None, {'fields': ['name']})]

        ma = BandAdmin(Band, self.site)
        self.assertEqual(ma.get_form(request).base_fields.keys(), ['name'])
        self.assertEqual(ma.get_form(request, self.band).base_fields.keys(),
            ['name'])

        # Using `exclude`.
        class BandAdmin(ModelAdmin):
            exclude = ['bio']

        ma = BandAdmin(Band, self.site)
        self.assertEqual(ma.get_form(request).base_fields.keys(),
            ['name', 'sign_date'])

        # You can also pass a tuple to `exclude`.
        class BandAdmin(ModelAdmin):
            exclude = ('bio',)

        ma = BandAdmin(Band, self.site)
        self.assertEqual(ma.get_form(request).base_fields.keys(),
            ['name', 'sign_date'])

        # Using `fields` and `exclude`.
        class BandAdmin(ModelAdmin):
            fields = ['name', 'bio']
            exclude = ['bio']

        ma = BandAdmin(Band, self.site)
        self.assertEqual(ma.get_form(request).base_fields.keys(),
            ['name'])

    def test_custom_form_validation(self):
        # If we specify a form, it should use it allowing custom validation to work
        # properly. This won't, however, break any of the admin widgets or media.

        class AdminBandForm(forms.ModelForm):
            delete = forms.BooleanField()

            class Meta:
                model = Band

        class BandAdmin(ModelAdmin):
            form = AdminBandForm

        ma = BandAdmin(Band, self.site)
        self.assertEqual(ma.get_form(request).base_fields.keys(),
            ['name', 'bio', 'sign_date', 'delete'])

        self.assertEqual(
            type(ma.get_form(request).base_fields['sign_date'].widget),
            AdminDateWidget)

    def test_queryset_override(self):
        # If we need to override the queryset of a ModelChoiceField in our custom form
        # make sure that RelatedFieldWidgetWrapper doesn't mess that up.

        band2 = Band(name='The Beatles', bio='', sign_date=date(1962, 1, 1))
        band2.save()

        class ConcertAdmin(ModelAdmin):
            pass
        ma = ConcertAdmin(Concert, self.site)
        form = ma.get_form(request)()

        self.assertEqual(str(form["main_band"]),
            '<select name="main_band" id="id_main_band">\n'
            '<option value="" selected="selected">---------</option>\n'
            '<option value="%d">The Doors</option>\n'
            '<option value="%d">The Beatles</option>\n'
            '</select>' % (self.band.id, band2.id))

        class AdminConcertForm(forms.ModelForm):
            class Meta:
                model = Concert

            def __init__(self, *args, **kwargs):
                super(AdminConcertForm, self).__init__(*args, **kwargs)
                self.fields["main_band"].queryset = Band.objects.filter(name='The Doors')

        class ConcertAdmin(ModelAdmin):
            form = AdminConcertForm

        ma = ConcertAdmin(Concert, self.site)
        form = ma.get_form(request)()

        self.assertEqual(str(form["main_band"]),
            '<select name="main_band" id="id_main_band">\n'
            '<option value="" selected="selected">---------</option>\n'
            '<option value="%d">The Doors</option>\n'
            '</select>' % self.band.id)

    # radio_fields behavior ###########################################

    def test_default_foreign_key_widget(self):
        # First, without any radio_fields specified, the widgets for ForeignKey
        # and fields with choices specified ought to be a basic Select widget.
        # ForeignKey widgets in the admin are wrapped with RelatedFieldWidgetWrapper so
        # they need to be handled properly when type checking. For Select fields, all of
        # the choices lists have a first entry of dashes.

        cma = ModelAdmin(Concert, self.site)
        cmafa = cma.get_form(request)

        self.assertEqual(type(cmafa.base_fields['main_band'].widget.widget),
            Select)
        self.assertEqual(
            list(cmafa.base_fields['main_band'].widget.choices),
            [(u'', u'---------'), (self.band.id, u'The Doors')])

        self.assertEqual(
            type(cmafa.base_fields['opening_band'].widget.widget), Select)
        self.assertEqual(
            list(cmafa.base_fields['opening_band'].widget.choices),
            [(u'', u'---------'), (self.band.id, u'The Doors')])

        self.assertEqual(type(cmafa.base_fields['day'].widget), Select)
        self.assertEqual(list(cmafa.base_fields['day'].widget.choices),
            [('', '---------'), (1, 'Fri'), (2, 'Sat')])

        self.assertEqual(type(cmafa.base_fields['transport'].widget),
            Select)
        self.assertEqual(
            list(cmafa.base_fields['transport'].widget.choices),
            [('', '---------'), (1, 'Plane'), (2, 'Train'), (3, 'Bus')])

    def test_foreign_key_as_radio_field(self):
        # Now specify all the fields as radio_fields.  Widgets should now be
        # RadioSelect, and the choices list should have a first entry of 'None' if
        # blank=True for the model field.  Finally, the widget should have the
        # 'radiolist' attr, and 'inline' as well if the field is specified HORIZONTAL.

        class ConcertAdmin(ModelAdmin):
            radio_fields = {
                'main_band': HORIZONTAL,
                'opening_band': VERTICAL,
                'day': VERTICAL,
                'transport': HORIZONTAL,
            }

        cma = ConcertAdmin(Concert, self.site)
        cmafa = cma.get_form(request)

        self.assertEqual(type(cmafa.base_fields['main_band'].widget.widget),
            AdminRadioSelect)
        self.assertEqual(cmafa.base_fields['main_band'].widget.attrs,
            {'class': 'radiolist inline'})
        self.assertEqual(list(cmafa.base_fields['main_band'].widget.choices),
            [(self.band.id, u'The Doors')])

        self.assertEqual(
            type(cmafa.base_fields['opening_band'].widget.widget),
            AdminRadioSelect)
        self.assertEqual(cmafa.base_fields['opening_band'].widget.attrs,
            {'class': 'radiolist'})
        self.assertEqual(
            list(cmafa.base_fields['opening_band'].widget.choices),
            [(u'', u'None'), (self.band.id, u'The Doors')])

        self.assertEqual(type(cmafa.base_fields['day'].widget),
            AdminRadioSelect)
        self.assertEqual(cmafa.base_fields['day'].widget.attrs,
            {'class': 'radiolist'})
        self.assertEqual(list(cmafa.base_fields['day'].widget.choices),
            [(1, 'Fri'), (2, 'Sat')])

        self.assertEqual(type(cmafa.base_fields['transport'].widget),
            AdminRadioSelect)
        self.assertEqual(cmafa.base_fields['transport'].widget.attrs,
            {'class': 'radiolist inline'})
        self.assertEqual(list(cmafa.base_fields['transport'].widget.choices),
            [('', u'None'), (1, 'Plane'), (2, 'Train'), (3, 'Bus')])

        class AdminConcertForm(forms.ModelForm):
            class Meta:
                model = Concert
                exclude = ('transport',)

        class ConcertAdmin(ModelAdmin):
            form = AdminConcertForm

        ma = ConcertAdmin(Concert, self.site)
        self.assertEqual(ma.get_form(request).base_fields.keys(),
            ['main_band', 'opening_band', 'day'])

        class AdminConcertForm(forms.ModelForm):
            extra = forms.CharField()

            class Meta:
                model = Concert
                fields = ['extra', 'transport']

        class ConcertAdmin(ModelAdmin):
            form = AdminConcertForm

        ma = ConcertAdmin(Concert, self.site)
        self.assertEqual(ma.get_form(request).base_fields.keys(),
            ['extra', 'transport'])

        class ConcertInline(TabularInline):
            form = AdminConcertForm
            model = Concert
            fk_name = 'main_band'
            can_delete = True

        class BandAdmin(ModelAdmin):
            inlines = [
                ConcertInline
            ]

        ma = BandAdmin(Band, self.site)
        self.assertEqual(
            list(ma.get_formsets(request))[0]().forms[0].fields.keys(),
            ['extra', 'transport', 'id', 'DELETE', 'main_band'])


class ValidationTests(unittest.TestCase):
    def assertRaisesErrorWithMessage(self, error, message, callable, *args, **kwargs):
        self.assertRaises(error, callable, *args, **kwargs)
        try:
            callable(*args, **kwargs)
        except error, e:
            self.assertEqual(message, str(e))

    def test_validation_only_runs_in_debug(self):
        # Ensure validation only runs when DEBUG = True
        try:
            settings.DEBUG = True

            class ValidationTestModelAdmin(ModelAdmin):
                raw_id_fields = 10

            site = AdminSite()

            self.assertRaisesErrorWithMessage(
                ImproperlyConfigured,
                "'ValidationTestModelAdmin.raw_id_fields' must be a list or tuple.",
                site.register,
                ValidationTestModel,
                ValidationTestModelAdmin,
            )
        finally:
            settings.DEBUG = False

        site = AdminSite()
        site.register(ValidationTestModel, ValidationTestModelAdmin)

    def test_raw_id_fields_validation(self):

        class ValidationTestModelAdmin(ModelAdmin):
            raw_id_fields = 10

        self.assertRaisesErrorWithMessage(
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.raw_id_fields' must be a list or tuple.",
            validate,
            ValidationTestModelAdmin,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            raw_id_fields = ('non_existent_field',)

        self.assertRaisesErrorWithMessage(
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.raw_id_fields' refers to field 'non_existent_field' that is missing from model 'ValidationTestModel'.",
            validate,
            ValidationTestModelAdmin,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            raw_id_fields = ('name',)

        self.assertRaisesErrorWithMessage(
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.raw_id_fields[0]', 'name' must be either a ForeignKey or ManyToManyField.",
            validate,
            ValidationTestModelAdmin,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            raw_id_fields = ('users',)

        validate(ValidationTestModelAdmin, ValidationTestModel)

    def test_fieldsets_validation(self):

        class ValidationTestModelAdmin(ModelAdmin):
            fieldsets = 10

        self.assertRaisesErrorWithMessage(
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.fieldsets' must be a list or tuple.",
            validate,
            ValidationTestModelAdmin,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            fieldsets = ({},)

        self.assertRaisesErrorWithMessage(
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.fieldsets[0]' must be a list or tuple.",
            validate,
            ValidationTestModelAdmin,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            fieldsets = ((),)

        self.assertRaisesErrorWithMessage(
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.fieldsets[0]' does not have exactly two elements.",
            validate,
            ValidationTestModelAdmin,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            fieldsets = (("General", ()),)

        self.assertRaisesErrorWithMessage(
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.fieldsets[0][1]' must be a dictionary.",
            validate,
            ValidationTestModelAdmin,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            fieldsets = (("General", {}),)

        self.assertRaisesErrorWithMessage(
            ImproperlyConfigured,
            "'fields' key is required in ValidationTestModelAdmin.fieldsets[0][1] field options dict.",
            validate,
            ValidationTestModelAdmin,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            fieldsets = (("General", {"fields": ("non_existent_field",)}),)

        self.assertRaisesErrorWithMessage(
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.fieldsets[0][1]['fields']' refers to field 'non_existent_field' that is missing from the form.",
            validate,
            ValidationTestModelAdmin,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            fieldsets = (("General", {"fields": ("name",)}),)

        validate(ValidationTestModelAdmin, ValidationTestModel)

        class ValidationTestModelAdmin(ModelAdmin):
            fieldsets = (("General", {"fields": ("name",)}),)
            fields = ["name",]

        self.assertRaisesErrorWithMessage(
            ImproperlyConfigured,
            "Both fieldsets and fields are specified in ValidationTestModelAdmin.",
            validate,
            ValidationTestModelAdmin,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            fieldsets = [(None, {'fields': ['name', 'name']})]

        self.assertRaisesErrorWithMessage(
            ImproperlyConfigured,
            "There are duplicate field(s) in ValidationTestModelAdmin.fieldsets",
            validate,
            ValidationTestModelAdmin,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            fields = ["name", "name"]

        self.assertRaisesErrorWithMessage(
            ImproperlyConfigured,
            "There are duplicate field(s) in ValidationTestModelAdmin.fields",
            validate,
            ValidationTestModelAdmin,
            ValidationTestModel,
        )

    def test_form_validation(self):

        class FakeForm(object):
            pass

        class ValidationTestModelAdmin(ModelAdmin):
            form = FakeForm

        self.assertRaisesErrorWithMessage(
            ImproperlyConfigured,
            "ValidationTestModelAdmin.form does not inherit from BaseModelForm.",
            validate,
            ValidationTestModelAdmin,
            ValidationTestModel,
        )

    def test_fieldsets_with_custom_form_validation(self):

        class BandAdmin(ModelAdmin):

            fieldsets = (
                ('Band', {
                    'fields': ('non_existent_field',)
                }),
            )

        self.assertRaisesErrorWithMessage(
            ImproperlyConfigured,
            "'BandAdmin.fieldsets[0][1]['fields']' refers to field 'non_existent_field' that is missing from the form.",
            validate,
            BandAdmin,
            Band,
        )

        class BandAdmin(ModelAdmin):
            fieldsets = (
                ('Band', {
                    'fields': ('name',)
                }),
            )

        validate(BandAdmin, Band)

        class AdminBandForm(forms.ModelForm):
            class Meta:
                model = Band

        class BandAdmin(ModelAdmin):
            form = AdminBandForm

            fieldsets = (
                ('Band', {
                    'fields': ('non_existent_field',)
                }),
            )

        self.assertRaisesErrorWithMessage(
            ImproperlyConfigured,
            "'BandAdmin.fieldsets[0][1]['fields']' refers to field 'non_existent_field' that is missing from the form.",
            validate,
            BandAdmin,
            Band,
        )

        class AdminBandForm(forms.ModelForm):
            delete = forms.BooleanField()

            class Meta:
                model = Band

        class BandAdmin(ModelAdmin):
            form = AdminBandForm

            fieldsets = (
                ('Band', {
                    'fields': ('name', 'bio', 'sign_date', 'delete')
                }),
            )

        validate(BandAdmin, Band)

    def test_filter_vertical_validation(self):

        class ValidationTestModelAdmin(ModelAdmin):
            filter_vertical = 10

        self.assertRaisesErrorWithMessage(
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.filter_vertical' must be a list or tuple.",
            validate,
            ValidationTestModelAdmin,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            filter_vertical = ("non_existent_field",)

        self.assertRaisesErrorWithMessage(
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.filter_vertical' refers to field 'non_existent_field' that is missing from model 'ValidationTestModel'.",
            validate,
            ValidationTestModelAdmin,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            filter_vertical = ("name",)

        self.assertRaisesErrorWithMessage(
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.filter_vertical[0]' must be a ManyToManyField.",
            validate,
            ValidationTestModelAdmin,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            filter_vertical = ("users",)

        validate(ValidationTestModelAdmin, ValidationTestModel)

    def test_filter_horizontal_validation(self):

        class ValidationTestModelAdmin(ModelAdmin):
            filter_horizontal = 10

        self.assertRaisesErrorWithMessage(
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.filter_horizontal' must be a list or tuple.",
            validate,
            ValidationTestModelAdmin,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            filter_horizontal = ("non_existent_field",)

        self.assertRaisesErrorWithMessage(
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.filter_horizontal' refers to field 'non_existent_field' that is missing from model 'ValidationTestModel'.",
            validate,
            ValidationTestModelAdmin,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            filter_horizontal = ("name",)

        self.assertRaisesErrorWithMessage(
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.filter_horizontal[0]' must be a ManyToManyField.",
            validate,
            ValidationTestModelAdmin,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            filter_horizontal = ("users",)

        validate(ValidationTestModelAdmin, ValidationTestModel)

    def test_radio_fields_validation(self):

        class ValidationTestModelAdmin(ModelAdmin):
            radio_fields = ()

        self.assertRaisesErrorWithMessage(
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.radio_fields' must be a dictionary.",
            validate,
            ValidationTestModelAdmin,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            radio_fields = {"non_existent_field": None}

        self.assertRaisesErrorWithMessage(
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.radio_fields' refers to field 'non_existent_field' that is missing from model 'ValidationTestModel'.",
            validate,
            ValidationTestModelAdmin,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            radio_fields = {"name": None}

        self.assertRaisesErrorWithMessage(
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.radio_fields['name']' is neither an instance of ForeignKey nor does have choices set.",
            validate,
            ValidationTestModelAdmin,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            radio_fields = {"state": None}

        self.assertRaisesErrorWithMessage(
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.radio_fields['state']' is neither admin.HORIZONTAL nor admin.VERTICAL.",
            validate,
            ValidationTestModelAdmin,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            radio_fields = {"state": VERTICAL}

        validate(ValidationTestModelAdmin, ValidationTestModel)

    def test_prepopulated_fields_validation(self):

        class ValidationTestModelAdmin(ModelAdmin):
            prepopulated_fields = ()

        self.assertRaisesErrorWithMessage(
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.prepopulated_fields' must be a dictionary.",
            validate,
            ValidationTestModelAdmin,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            prepopulated_fields = {"non_existent_field": None}

        self.assertRaisesErrorWithMessage(
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.prepopulated_fields' refers to field 'non_existent_field' that is missing from model 'ValidationTestModel'.",
            validate,
            ValidationTestModelAdmin,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            prepopulated_fields = {"slug": ("non_existent_field",)}

        self.assertRaisesErrorWithMessage(
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.prepopulated_fields['slug'][0]' refers to field 'non_existent_field' that is missing from model 'ValidationTestModel'.",
            validate,
            ValidationTestModelAdmin,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            prepopulated_fields = {"users": ("name",)}

        self.assertRaisesErrorWithMessage(
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.prepopulated_fields['users']' is either a DateTimeField, ForeignKey or ManyToManyField. This isn't allowed.",
            validate,
            ValidationTestModelAdmin,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            prepopulated_fields = {"slug": ("name",)}

        validate(ValidationTestModelAdmin, ValidationTestModel)

    def test_list_display_validation(self):

        class ValidationTestModelAdmin(ModelAdmin):
            list_display = 10

        self.assertRaisesErrorWithMessage(
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.list_display' must be a list or tuple.",
            validate,
            ValidationTestModelAdmin,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            list_display = ('non_existent_field',)

        self.assertRaisesErrorWithMessage(
            ImproperlyConfigured,
            "ValidationTestModelAdmin.list_display[0], 'non_existent_field' is not a callable or an attribute of 'ValidationTestModelAdmin' or found in the model 'ValidationTestModel'.",
            validate,
            ValidationTestModelAdmin,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            list_display = ('users',)

        self.assertRaisesErrorWithMessage(
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.list_display[0]', 'users' is a ManyToManyField which is not supported.",
            validate,
            ValidationTestModelAdmin,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            list_display = ('name',)

        validate(ValidationTestModelAdmin, ValidationTestModel)

    def test_list_display_links_validation(self):

        class ValidationTestModelAdmin(ModelAdmin):
            list_display_links = 10

        self.assertRaisesErrorWithMessage(
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.list_display_links' must be a list or tuple.",
            validate,
            ValidationTestModelAdmin,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            list_display_links = ('non_existent_field',)

        self.assertRaisesErrorWithMessage(
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.list_display_links[0]' refers to 'non_existent_field' that is neither a field, method or property of model 'ValidationTestModel'.",
            validate,
            ValidationTestModelAdmin,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            list_display_links = ('name',)

        self.assertRaisesErrorWithMessage(
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.list_display_links[0]'refers to 'name' which is not defined in 'list_display'.",
            validate,
            ValidationTestModelAdmin,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            list_display = ('name',)
            list_display_links = ('name',)

        validate(ValidationTestModelAdmin, ValidationTestModel)

    def test_list_filter_validation(self):

        class ValidationTestModelAdmin(ModelAdmin):
            list_filter = 10

        self.assertRaisesErrorWithMessage(
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.list_filter' must be a list or tuple.",
            validate,
            ValidationTestModelAdmin,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            list_filter = ('non_existent_field',)

        self.assertRaisesErrorWithMessage(
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.list_filter[0]' refers to field 'non_existent_field' that is missing from model 'ValidationTestModel'.",
            validate,
            ValidationTestModelAdmin,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            list_filter = ('is_active',)

        validate(ValidationTestModelAdmin, ValidationTestModel)

    def test_list_per_page_validation(self):

        class ValidationTestModelAdmin(ModelAdmin):
            list_per_page = 'hello'

        self.assertRaisesErrorWithMessage(
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.list_per_page' should be a integer.",
            validate,
            ValidationTestModelAdmin,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            list_per_page = 100

        validate(ValidationTestModelAdmin, ValidationTestModel)

    def test_search_fields_validation(self):

        class ValidationTestModelAdmin(ModelAdmin):
            search_fields = 10

        self.assertRaisesErrorWithMessage(
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.search_fields' must be a list or tuple.",
            validate,
            ValidationTestModelAdmin,
            ValidationTestModel,
        )

    def test_date_hierarchy_validation(self):

        class ValidationTestModelAdmin(ModelAdmin):
            date_hierarchy = 'non_existent_field'

        self.assertRaisesErrorWithMessage(
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.date_hierarchy' refers to field 'non_existent_field' that is missing from model 'ValidationTestModel'.",
            validate,
            ValidationTestModelAdmin,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            date_hierarchy = 'name'

        self.assertRaisesErrorWithMessage(
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.date_hierarchy is neither an instance of DateField nor DateTimeField.",
            validate,
            ValidationTestModelAdmin,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            date_hierarchy = 'pub_date'

        validate(ValidationTestModelAdmin, ValidationTestModel)

    def test_ordering_validation(self):

        class ValidationTestModelAdmin(ModelAdmin):
            ordering = 10

        self.assertRaisesErrorWithMessage(
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.ordering' must be a list or tuple.",
            validate,
            ValidationTestModelAdmin,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            ordering = ('non_existent_field',)

        self.assertRaisesErrorWithMessage(
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.ordering[0]' refers to field 'non_existent_field' that is missing from model 'ValidationTestModel'.",
            validate,
            ValidationTestModelAdmin,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            ordering = ('?', 'name')

        self.assertRaisesErrorWithMessage(
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.ordering' has the random ordering marker '?', but contains other fields as well. Please either remove '?' or the other fields.",
            validate,
            ValidationTestModelAdmin,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            ordering = ('?',)

        validate(ValidationTestModelAdmin, ValidationTestModel)

        class ValidationTestModelAdmin(ModelAdmin):
            ordering = ('band__name',)

        validate(ValidationTestModelAdmin, ValidationTestModel)

        class ValidationTestModelAdmin(ModelAdmin):
            ordering = ('name',)

        validate(ValidationTestModelAdmin, ValidationTestModel)

    def test_list_select_related_validation(self):

        class ValidationTestModelAdmin(ModelAdmin):
            list_select_related = 1

        self.assertRaisesErrorWithMessage(
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.list_select_related' should be a boolean.",
            validate,
            ValidationTestModelAdmin,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            list_select_related = False

        validate(ValidationTestModelAdmin, ValidationTestModel)

    def test_save_as_validation(self):

        class ValidationTestModelAdmin(ModelAdmin):
            save_as = 1

        self.assertRaisesErrorWithMessage(
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.save_as' should be a boolean.",
            validate,
            ValidationTestModelAdmin,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            save_as = True

        validate(ValidationTestModelAdmin, ValidationTestModel)

    def test_save_on_top_validation(self):

        class ValidationTestModelAdmin(ModelAdmin):
            save_on_top = 1

        self.assertRaisesErrorWithMessage(
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.save_on_top' should be a boolean.",
            validate,
            ValidationTestModelAdmin,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            save_on_top = True

        validate(ValidationTestModelAdmin, ValidationTestModel)

    def test_inlines_validation(self):

        class ValidationTestModelAdmin(ModelAdmin):
            inlines = 10

        self.assertRaisesErrorWithMessage(
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.inlines' must be a list or tuple.",
            validate,
            ValidationTestModelAdmin,
            ValidationTestModel,
        )

        class ValidationTestInline(object):
            pass

        class ValidationTestModelAdmin(ModelAdmin):
            inlines = [ValidationTestInline]

        self.assertRaisesErrorWithMessage(
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.inlines[0]' does not inherit from BaseModelAdmin.",
            validate,
            ValidationTestModelAdmin,
            ValidationTestModel,
        )

        class ValidationTestInline(TabularInline):
            pass

        class ValidationTestModelAdmin(ModelAdmin):
            inlines = [ValidationTestInline]

        self.assertRaisesErrorWithMessage(
            ImproperlyConfigured,
            "'model' is a required attribute of 'ValidationTestModelAdmin.inlines[0]'.",
            validate,
            ValidationTestModelAdmin,
            ValidationTestModel,
        )

        class SomethingBad(object):
            pass

        class ValidationTestInline(TabularInline):
            model = SomethingBad

        class ValidationTestModelAdmin(ModelAdmin):
            inlines = [ValidationTestInline]

        self.assertRaisesErrorWithMessage(
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.inlines[0].model' does not inherit from models.Model.",
            validate,
            ValidationTestModelAdmin,
            ValidationTestModel,
        )

        class ValidationTestInline(TabularInline):
            model = ValidationTestInlineModel

        class ValidationTestModelAdmin(ModelAdmin):
            inlines = [ValidationTestInline]

        validate(ValidationTestModelAdmin, ValidationTestModel)

    def test_fields_validation(self):

        class ValidationTestInline(TabularInline):
            model = ValidationTestInlineModel
            fields = 10

        class ValidationTestModelAdmin(ModelAdmin):
            inlines = [ValidationTestInline]

        self.assertRaisesErrorWithMessage(
            ImproperlyConfigured,
            "'ValidationTestInline.fields' must be a list or tuple.",
            validate,
            ValidationTestModelAdmin,
            ValidationTestModel,
        )

        class ValidationTestInline(TabularInline):
            model = ValidationTestInlineModel
            fields = ("non_existent_field",)

        class ValidationTestModelAdmin(ModelAdmin):
            inlines = [ValidationTestInline]

        self.assertRaisesErrorWithMessage(
            ImproperlyConfigured,
            "'ValidationTestInline.fields' refers to field 'non_existent_field' that is missing from the form.",
            validate,
            ValidationTestModelAdmin,
            ValidationTestModel,
        )

    def test_fk_name_validation(self):

        class ValidationTestInline(TabularInline):
            model = ValidationTestInlineModel
            fk_name = "non_existent_field"

        class ValidationTestModelAdmin(ModelAdmin):
            inlines = [ValidationTestInline]

        self.assertRaisesErrorWithMessage(
            ImproperlyConfigured,
            "'ValidationTestInline.fk_name' refers to field 'non_existent_field' that is missing from model 'ValidationTestInlineModel'.",
            validate,
            ValidationTestModelAdmin,
            ValidationTestModel,
        )

        class ValidationTestInline(TabularInline):
            model = ValidationTestInlineModel
            fk_name = "parent"

        class ValidationTestModelAdmin(ModelAdmin):
            inlines = [ValidationTestInline]

        validate(ValidationTestModelAdmin, ValidationTestModel)

    def test_extra_validation(self):

        class ValidationTestInline(TabularInline):
            model = ValidationTestInlineModel
            extra = "hello"

        class ValidationTestModelAdmin(ModelAdmin):
            inlines = [ValidationTestInline]

        self.assertRaisesErrorWithMessage(
            ImproperlyConfigured,
            "'ValidationTestInline.extra' should be a integer.",
            validate,
            ValidationTestModelAdmin,
            ValidationTestModel,
        )

        class ValidationTestInline(TabularInline):
            model = ValidationTestInlineModel
            extra = 2

        class ValidationTestModelAdmin(ModelAdmin):
            inlines = [ValidationTestInline]

        validate(ValidationTestModelAdmin, ValidationTestModel)

    def test_max_num_validation(self):

        class ValidationTestInline(TabularInline):
            model = ValidationTestInlineModel
            max_num = "hello"

        class ValidationTestModelAdmin(ModelAdmin):
            inlines = [ValidationTestInline]

        self.assertRaisesErrorWithMessage(
            ImproperlyConfigured,
            "'ValidationTestInline.max_num' should be an integer or None (default).",
            validate,
            ValidationTestModelAdmin,
            ValidationTestModel,
        )

        class ValidationTestInline(TabularInline):
            model = ValidationTestInlineModel
            max_num = 2

        class ValidationTestModelAdmin(ModelAdmin):
            inlines = [ValidationTestInline]

        validate(ValidationTestModelAdmin, ValidationTestModel)

    def test_formset_validation(self):

        class FakeFormSet(object):
            pass

        class ValidationTestInline(TabularInline):
            model = ValidationTestInlineModel
            formset = FakeFormSet

        class ValidationTestModelAdmin(ModelAdmin):
            inlines = [ValidationTestInline]

        self.assertRaisesErrorWithMessage(
            ImproperlyConfigured,
            "'ValidationTestInline.formset' does not inherit from BaseModelFormSet.",
            validate,
            ValidationTestModelAdmin,
            ValidationTestModel,
        )

        class RealModelFormSet(BaseModelFormSet):
            pass

        class ValidationTestInline(TabularInline):
            model = ValidationTestInlineModel
            formset = RealModelFormSet

        class ValidationTestModelAdmin(ModelAdmin):
            inlines = [ValidationTestInline]

        validate(ValidationTestModelAdmin, ValidationTestModel)
