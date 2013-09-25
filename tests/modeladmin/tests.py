from __future__ import absolute_import, unicode_literals

from datetime import date

from django import forms
from django.conf import settings
from django.contrib.admin.options import (ModelAdmin, TabularInline,
     HORIZONTAL, VERTICAL)
from django.contrib.admin.sites import AdminSite
from django.contrib.admin.widgets import AdminDateWidget, AdminRadioSelect
from django.contrib.admin import (SimpleListFilter,
     BooleanFieldListFilter)
from django.core.exceptions import ImproperlyConfigured
from django.forms.models import BaseModelFormSet
from django.forms.widgets import Select
from django.test import TestCase
from django.test.utils import str_prefix
from django.utils import unittest, six

from .models import Band, Concert, ValidationTestModel, ValidationTestInlineModel


class MockRequest(object):
    pass


class MockSuperUser(object):
    def has_perm(self, perm):
        return True

request = MockRequest()
request.user = MockSuperUser()


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

        self.assertEqual(list(ma.get_form(request).base_fields),
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

    def test_get_fieldsets(self):
        # Test that get_fieldsets is called when figuring out form fields.
        # Refs #18681.

        class BandAdmin(ModelAdmin):
            def get_fieldsets(self, request, obj=None):
                return [(None, {'fields': ['name', 'bio']})]

        ma = BandAdmin(Band, self.site)
        form = ma.get_form(None)
        self.assertEqual(form._meta.fields, ['name', 'bio'])

        class InlineBandAdmin(TabularInline):
            model = Concert
            fk_name = 'main_band'
            can_delete = False

            def get_fieldsets(self, request, obj=None):
                return [(None, {'fields': ['day', 'transport']})]

        ma = InlineBandAdmin(Band, self.site)
        form = ma.get_formset(None).form
        self.assertEqual(form._meta.fields, ['day', 'transport'])

    def test_lookup_allowed_allows_nonexistent_lookup(self):
        """
        Ensure that a lookup_allowed allows a parameter
        whose field lookup doesn't exist.
        Refs #21129.
        """
        class BandAdmin(ModelAdmin):
            fields = ['name']

        ma = BandAdmin(Band, self.site)
        self.assertTrue(ma.lookup_allowed('name__nonexistent', 'test_value'))

    def test_field_arguments(self):
        # If we specify the fields argument, fieldsets_add and fielsets_change should
        # just stick the fields into a formsets structure and return it.
        class BandAdmin(ModelAdmin):
            fields = ['name']

        ma = BandAdmin(Band, self.site)

        self.assertEqual(ma.get_fieldsets(request),
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
        self.assertEqual(list(ma.get_form(request).base_fields), ['name'])
        self.assertEqual(list(ma.get_form(request, self.band).base_fields),
            ['name'])

        # Using `fieldsets`.
        class BandAdmin(ModelAdmin):
            fieldsets = [(None, {'fields': ['name']})]

        ma = BandAdmin(Band, self.site)
        self.assertEqual(list(ma.get_form(request).base_fields), ['name'])
        self.assertEqual(list(ma.get_form(request, self.band).base_fields),
            ['name'])

        # Using `exclude`.
        class BandAdmin(ModelAdmin):
            exclude = ['bio']

        ma = BandAdmin(Band, self.site)
        self.assertEqual(list(ma.get_form(request).base_fields),
            ['name', 'sign_date'])

        # You can also pass a tuple to `exclude`.
        class BandAdmin(ModelAdmin):
            exclude = ('bio',)

        ma = BandAdmin(Band, self.site)
        self.assertEqual(list(ma.get_form(request).base_fields),
            ['name', 'sign_date'])

        # Using `fields` and `exclude`.
        class BandAdmin(ModelAdmin):
            fields = ['name', 'bio']
            exclude = ['bio']

        ma = BandAdmin(Band, self.site)
        self.assertEqual(list(ma.get_form(request).base_fields),
            ['name'])

    def test_custom_form_meta_exclude_with_readonly(self):
        """
        Ensure that the custom ModelForm's `Meta.exclude` is respected when
        used in conjunction with `ModelAdmin.readonly_fields` and when no
        `ModelAdmin.exclude` is defined.
        Refs #14496.
        """
        # First, with `ModelAdmin` -----------------------

        class AdminBandForm(forms.ModelForm):

            class Meta:
                model = Band
                exclude = ['bio']

        class BandAdmin(ModelAdmin):
            readonly_fields = ['name']
            form = AdminBandForm

        ma = BandAdmin(Band, self.site)
        self.assertEqual(list(ma.get_form(request).base_fields),
            ['sign_date'])

        # Then, with `InlineModelAdmin`  -----------------

        class AdminConcertForm(forms.ModelForm):

            class Meta:
                model = Concert
                exclude = ['day']

        class ConcertInline(TabularInline):
            readonly_fields = ['transport']
            form = AdminConcertForm
            fk_name = 'main_band'
            model = Concert

        class BandAdmin(ModelAdmin):
            inlines = [
                ConcertInline
            ]

        ma = BandAdmin(Band, self.site)
        self.assertEqual(
            list(list(ma.get_formsets(request))[0]().forms[0].fields),
            ['main_band', 'opening_band', 'id', 'DELETE'])

    def test_custom_form_meta_exclude(self):
        """
        Ensure that the custom ModelForm's `Meta.exclude` is overridden if
        `ModelAdmin.exclude` or `InlineModelAdmin.exclude` are defined.
        Refs #14496.
        """
        # First, with `ModelAdmin` -----------------------

        class AdminBandForm(forms.ModelForm):

            class Meta:
                model = Band
                exclude = ['bio']

        class BandAdmin(ModelAdmin):
            exclude = ['name']
            form = AdminBandForm

        ma = BandAdmin(Band, self.site)
        self.assertEqual(list(ma.get_form(request).base_fields),
            ['bio', 'sign_date'])

        # Then, with `InlineModelAdmin`  -----------------

        class AdminConcertForm(forms.ModelForm):

            class Meta:
                model = Concert
                exclude = ['day']

        class ConcertInline(TabularInline):
            exclude = ['transport']
            form = AdminConcertForm
            fk_name = 'main_band'
            model = Concert

        class BandAdmin(ModelAdmin):
            inlines = [
                ConcertInline
            ]

        ma = BandAdmin(Band, self.site)
        self.assertEqual(
            list(list(ma.get_formsets(request))[0]().forms[0].fields),
            ['main_band', 'opening_band', 'day', 'id', 'DELETE'])

    def test_custom_form_validation(self):
        # If we specify a form, it should use it allowing custom validation to work
        # properly. This won't, however, break any of the admin widgets or media.

        class AdminBandForm(forms.ModelForm):
            delete = forms.BooleanField()

        class BandAdmin(ModelAdmin):
            form = AdminBandForm

        ma = BandAdmin(Band, self.site)
        self.assertEqual(list(ma.get_form(request).base_fields),
            ['name', 'bio', 'sign_date', 'delete'])

        self.assertEqual(
            type(ma.get_form(request).base_fields['sign_date'].widget),
            AdminDateWidget)

    def test_form_exclude_kwarg_override(self):
        """
        Ensure that the `exclude` kwarg passed to `ModelAdmin.get_form()`
        overrides all other declarations. Refs #8999.
        """

        class AdminBandForm(forms.ModelForm):

            class Meta:
                model = Band
                exclude = ['name']

        class BandAdmin(ModelAdmin):
            exclude = ['sign_date']
            form = AdminBandForm

            def get_form(self, request, obj=None, **kwargs):
                kwargs['exclude'] = ['bio']
                return super(BandAdmin, self).get_form(request, obj, **kwargs)

        ma = BandAdmin(Band, self.site)
        self.assertEqual(list(ma.get_form(request).base_fields),
            ['name', 'sign_date'])

    def test_formset_exclude_kwarg_override(self):
        """
        Ensure that the `exclude` kwarg passed to `InlineModelAdmin.get_formset()`
        overrides all other declarations. Refs #8999.
        """

        class AdminConcertForm(forms.ModelForm):

            class Meta:
                model = Concert
                exclude = ['day']

        class ConcertInline(TabularInline):
            exclude = ['transport']
            form = AdminConcertForm
            fk_name = 'main_band'
            model = Concert

            def get_formset(self, request, obj=None, **kwargs):
                kwargs['exclude'] = ['opening_band']
                return super(ConcertInline, self).get_formset(request, obj, **kwargs)

        class BandAdmin(ModelAdmin):
            inlines = [
                ConcertInline
            ]

        ma = BandAdmin(Band, self.site)
        self.assertEqual(
            list(list(ma.get_formsets(request))[0]().forms[0].fields),
            ['main_band', 'day', 'transport', 'id', 'DELETE'])

    def test_queryset_override(self):
        # If we need to override the queryset of a ModelChoiceField in our custom form
        # make sure that RelatedFieldWidgetWrapper doesn't mess that up.

        band2 = Band(name='The Beatles', bio='', sign_date=date(1962, 1, 1))
        band2.save()

        class ConcertAdmin(ModelAdmin):
            pass
        ma = ConcertAdmin(Concert, self.site)
        form = ma.get_form(request)()

        self.assertHTMLEqual(str(form["main_band"]),
            '<select name="main_band" id="id_main_band">\n'
            '<option value="" selected="selected">---------</option>\n'
            '<option value="%d">The Beatles</option>\n'
            '<option value="%d">The Doors</option>\n'
            '</select>' % (band2.id, self.band.id))

        class AdminConcertForm(forms.ModelForm):
            pass

            def __init__(self, *args, **kwargs):
                super(AdminConcertForm, self).__init__(*args, **kwargs)
                self.fields["main_band"].queryset = Band.objects.filter(name='The Doors')

        class ConcertAdmin(ModelAdmin):
            form = AdminConcertForm

        ma = ConcertAdmin(Concert, self.site)
        form = ma.get_form(request)()

        self.assertHTMLEqual(str(form["main_band"]),
            '<select name="main_band" id="id_main_band">\n'
            '<option value="" selected="selected">---------</option>\n'
            '<option value="%d">The Doors</option>\n'
            '</select>' % self.band.id)

    def test_regression_for_ticket_15820(self):
        """
        Ensure that `obj` is passed from `InlineModelAdmin.get_fieldsets()` to
        `InlineModelAdmin.get_formset()`.
        """
        class CustomConcertForm(forms.ModelForm):

            class Meta:
                model = Concert
                fields = ['day']

        class ConcertInline(TabularInline):
            model = Concert
            fk_name = 'main_band'

            def get_formset(self, request, obj=None, **kwargs):
                if obj:
                    kwargs['form'] = CustomConcertForm
                return super(ConcertInline, self).get_formset(request, obj, **kwargs)

        class BandAdmin(ModelAdmin):
            inlines = [
                ConcertInline
            ]

        concert = Concert.objects.create(main_band=self.band, opening_band=self.band, day=1)
        ma = BandAdmin(Band, self.site)
        inline_instances = ma.get_inline_instances(request)
        fieldsets = list(inline_instances[0].get_fieldsets(request))
        self.assertEqual(fieldsets[0][1]['fields'], ['main_band', 'opening_band', 'day', 'transport'])
        fieldsets = list(inline_instances[0].get_fieldsets(request, inline_instances[0].model))
        self.assertEqual(fieldsets[0][1]['fields'], ['day'])

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
            [('', '---------'), (self.band.id, 'The Doors')])

        self.assertEqual(
            type(cmafa.base_fields['opening_band'].widget.widget), Select)
        self.assertEqual(
            list(cmafa.base_fields['opening_band'].widget.choices),
            [('', '---------'), (self.band.id, 'The Doors')])

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
            [(self.band.id, 'The Doors')])

        self.assertEqual(
            type(cmafa.base_fields['opening_band'].widget.widget),
            AdminRadioSelect)
        self.assertEqual(cmafa.base_fields['opening_band'].widget.attrs,
            {'class': 'radiolist'})
        self.assertEqual(
            list(cmafa.base_fields['opening_band'].widget.choices),
            [('', 'None'), (self.band.id, 'The Doors')])

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
            [('', 'None'), (1, 'Plane'), (2, 'Train'), (3, 'Bus')])

        class AdminConcertForm(forms.ModelForm):
            class Meta:
                model = Concert
                exclude = ('transport',)

        class ConcertAdmin(ModelAdmin):
            form = AdminConcertForm

        ma = ConcertAdmin(Concert, self.site)
        self.assertEqual(list(ma.get_form(request).base_fields),
            ['main_band', 'opening_band', 'day'])

        class AdminConcertForm(forms.ModelForm):
            extra = forms.CharField()

            class Meta:
                model = Concert
                fields = ['extra', 'transport']

        class ConcertAdmin(ModelAdmin):
            form = AdminConcertForm

        ma = ConcertAdmin(Concert, self.site)
        self.assertEqual(list(ma.get_form(request).base_fields),
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
            list(list(ma.get_formsets(request))[0]().forms[0].fields),
            ['extra', 'transport', 'id', 'DELETE', 'main_band'])


class ValidationTests(unittest.TestCase):
    def test_validation_only_runs_in_debug(self):
        # Ensure validation only runs when DEBUG = True
        try:
            settings.DEBUG = True

            class ValidationTestModelAdmin(ModelAdmin):
                raw_id_fields = 10

            site = AdminSite()

            six.assertRaisesRegex(self,
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

        six.assertRaisesRegex(self,
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.raw_id_fields' must be a list or tuple.",
            ValidationTestModelAdmin.validate,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            raw_id_fields = ('non_existent_field',)

        six.assertRaisesRegex(self,
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.raw_id_fields' refers to field 'non_existent_field' that is missing from model 'modeladmin.ValidationTestModel'.",
            ValidationTestModelAdmin.validate,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            raw_id_fields = ('name',)

        six.assertRaisesRegex(self,
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.raw_id_fields\[0\]', 'name' must be either a ForeignKey or ManyToManyField.",
            ValidationTestModelAdmin.validate,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            raw_id_fields = ('users',)

        ValidationTestModelAdmin.validate(ValidationTestModel)

    def test_fieldsets_validation(self):

        class ValidationTestModelAdmin(ModelAdmin):
            fieldsets = 10

        six.assertRaisesRegex(self,
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.fieldsets' must be a list or tuple.",
            ValidationTestModelAdmin.validate,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            fieldsets = ({},)

        six.assertRaisesRegex(self,
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.fieldsets\[0\]' must be a list or tuple.",
            ValidationTestModelAdmin.validate,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            fieldsets = ((),)

        six.assertRaisesRegex(self,
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.fieldsets\[0\]' does not have exactly two elements.",
            ValidationTestModelAdmin.validate,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            fieldsets = (("General", ()),)

        six.assertRaisesRegex(self,
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.fieldsets\[0\]\[1\]' must be a dictionary.",
            ValidationTestModelAdmin.validate,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            fieldsets = (("General", {}),)

        six.assertRaisesRegex(self,
            ImproperlyConfigured,
            "'fields' key is required in ValidationTestModelAdmin.fieldsets\[0\]\[1\] field options dict.",
            ValidationTestModelAdmin.validate,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            fieldsets = (("General", {"fields": ("name",)}),)

        ValidationTestModelAdmin.validate(ValidationTestModel)

        class ValidationTestModelAdmin(ModelAdmin):
            fieldsets = (("General", {"fields": ("name",)}),)
            fields = ["name",]

        six.assertRaisesRegex(self,
            ImproperlyConfigured,
            "Both fieldsets and fields are specified in ValidationTestModelAdmin.",
            ValidationTestModelAdmin.validate,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            fieldsets = [(None, {'fields': ['name', 'name']})]

        six.assertRaisesRegex(self,
            ImproperlyConfigured,
            "There are duplicate field\(s\) in ValidationTestModelAdmin.fieldsets",
            ValidationTestModelAdmin.validate,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            fields = ["name", "name"]

        six.assertRaisesRegex(self,
            ImproperlyConfigured,
            "There are duplicate field\(s\) in ValidationTestModelAdmin.fields",
            ValidationTestModelAdmin.validate,
            ValidationTestModel,
        )

    def test_form_validation(self):

        class FakeForm(object):
            pass

        class ValidationTestModelAdmin(ModelAdmin):
            form = FakeForm

        six.assertRaisesRegex(self,
            ImproperlyConfigured,
            "ValidationTestModelAdmin.form does not inherit from BaseModelForm.",
            ValidationTestModelAdmin.validate,
            ValidationTestModel,
        )

    def test_fieldsets_with_custom_form_validation(self):

        class BandAdmin(ModelAdmin):
            fieldsets = (
                ('Band', {
                    'fields': ('name',)
                }),
            )

        BandAdmin.validate(Band)

        class AdminBandForm(forms.ModelForm):
            delete = forms.BooleanField()

        class BandAdmin(ModelAdmin):
            form = AdminBandForm

            fieldsets = (
                ('Band', {
                    'fields': ('name', 'bio', 'sign_date', 'delete')
                }),
            )

        BandAdmin.validate(Band)

    def test_filter_vertical_validation(self):

        class ValidationTestModelAdmin(ModelAdmin):
            filter_vertical = 10

        six.assertRaisesRegex(self,
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.filter_vertical' must be a list or tuple.",
            ValidationTestModelAdmin.validate,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            filter_vertical = ("non_existent_field",)

        six.assertRaisesRegex(self,
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.filter_vertical' refers to field 'non_existent_field' that is missing from model 'modeladmin.ValidationTestModel'.",
            ValidationTestModelAdmin.validate,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            filter_vertical = ("name",)

        six.assertRaisesRegex(self,
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.filter_vertical\[0\]' must be a ManyToManyField.",
            ValidationTestModelAdmin.validate,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            filter_vertical = ("users",)

        ValidationTestModelAdmin.validate(ValidationTestModel)

    def test_filter_horizontal_validation(self):

        class ValidationTestModelAdmin(ModelAdmin):
            filter_horizontal = 10

        six.assertRaisesRegex(self,
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.filter_horizontal' must be a list or tuple.",
            ValidationTestModelAdmin.validate,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            filter_horizontal = ("non_existent_field",)

        six.assertRaisesRegex(self,
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.filter_horizontal' refers to field 'non_existent_field' that is missing from model 'modeladmin.ValidationTestModel'.",
            ValidationTestModelAdmin.validate,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            filter_horizontal = ("name",)

        six.assertRaisesRegex(self,
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.filter_horizontal\[0\]' must be a ManyToManyField.",
            ValidationTestModelAdmin.validate,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            filter_horizontal = ("users",)

        ValidationTestModelAdmin.validate(ValidationTestModel)

    def test_radio_fields_validation(self):

        class ValidationTestModelAdmin(ModelAdmin):
            radio_fields = ()

        six.assertRaisesRegex(self,
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.radio_fields' must be a dictionary.",
            ValidationTestModelAdmin.validate,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            radio_fields = {"non_existent_field": None}

        six.assertRaisesRegex(self,
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.radio_fields' refers to field 'non_existent_field' that is missing from model 'modeladmin.ValidationTestModel'.",
            ValidationTestModelAdmin.validate,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            radio_fields = {"name": None}

        six.assertRaisesRegex(self,
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.radio_fields\['name'\]' is neither an instance of ForeignKey nor does have choices set.",
            ValidationTestModelAdmin.validate,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            radio_fields = {"state": None}

        six.assertRaisesRegex(self,
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.radio_fields\['state'\]' is neither admin.HORIZONTAL nor admin.VERTICAL.",
            ValidationTestModelAdmin.validate,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            radio_fields = {"state": VERTICAL}

        ValidationTestModelAdmin.validate(ValidationTestModel)

    def test_prepopulated_fields_validation(self):

        class ValidationTestModelAdmin(ModelAdmin):
            prepopulated_fields = ()

        six.assertRaisesRegex(self,
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.prepopulated_fields' must be a dictionary.",
            ValidationTestModelAdmin.validate,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            prepopulated_fields = {"non_existent_field": None}

        six.assertRaisesRegex(self,
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.prepopulated_fields' refers to field 'non_existent_field' that is missing from model 'modeladmin.ValidationTestModel'.",
            ValidationTestModelAdmin.validate,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            prepopulated_fields = {"slug": ("non_existent_field",)}

        six.assertRaisesRegex(self,
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.prepopulated_fields\['slug'\]\[0\]' refers to field 'non_existent_field' that is missing from model 'modeladmin.ValidationTestModel'.",
            ValidationTestModelAdmin.validate,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            prepopulated_fields = {"users": ("name",)}

        six.assertRaisesRegex(self,
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.prepopulated_fields\['users'\]' is either a DateTimeField, ForeignKey or ManyToManyField. This isn't allowed.",
            ValidationTestModelAdmin.validate,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            prepopulated_fields = {"slug": ("name",)}

        ValidationTestModelAdmin.validate(ValidationTestModel)

    def test_list_display_validation(self):

        class ValidationTestModelAdmin(ModelAdmin):
            list_display = 10

        six.assertRaisesRegex(self,
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.list_display' must be a list or tuple.",
            ValidationTestModelAdmin.validate,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            list_display = ('non_existent_field',)

        six.assertRaisesRegex(self,
            ImproperlyConfigured,
            str_prefix("ValidationTestModelAdmin.list_display\[0\], %(_)s'non_existent_field' is not a callable or an attribute of 'ValidationTestModelAdmin' or found in the model 'ValidationTestModel'."),
            ValidationTestModelAdmin.validate,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            list_display = ('users',)

        six.assertRaisesRegex(self,
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.list_display\[0\]', 'users' is a ManyToManyField which is not supported.",
            ValidationTestModelAdmin.validate,
            ValidationTestModel,
        )

        def a_callable(obj):
            pass

        class ValidationTestModelAdmin(ModelAdmin):
            def a_method(self, obj):
                pass
            list_display = ('name', 'decade_published_in', 'a_method', a_callable)

        ValidationTestModelAdmin.validate(ValidationTestModel)

    def test_list_display_links_validation(self):

        class ValidationTestModelAdmin(ModelAdmin):
            list_display_links = 10

        six.assertRaisesRegex(self,
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.list_display_links' must be a list or tuple.",
            ValidationTestModelAdmin.validate,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            list_display_links = ('non_existent_field',)

        six.assertRaisesRegex(self,
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.list_display_links\[0\]' refers to 'non_existent_field' which is not defined in 'list_display'.",
            ValidationTestModelAdmin.validate,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            list_display_links = ('name',)

        six.assertRaisesRegex(self,
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.list_display_links\[0\]' refers to 'name' which is not defined in 'list_display'.",
            ValidationTestModelAdmin.validate,
            ValidationTestModel,
        )

        def a_callable(obj):
            pass

        class ValidationTestModelAdmin(ModelAdmin):
            def a_method(self, obj):
                pass
            list_display = ('name', 'decade_published_in', 'a_method', a_callable)
            list_display_links = ('name', 'decade_published_in', 'a_method', a_callable)

        ValidationTestModelAdmin.validate(ValidationTestModel)

    def test_list_filter_validation(self):

        class ValidationTestModelAdmin(ModelAdmin):
            list_filter = 10

        six.assertRaisesRegex(self,
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.list_filter' must be a list or tuple.",
            ValidationTestModelAdmin.validate,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            list_filter = ('non_existent_field',)

        six.assertRaisesRegex(self,
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.list_filter\[0\]' refers to 'non_existent_field' which does not refer to a Field.",
            ValidationTestModelAdmin.validate,
            ValidationTestModel,
        )

        class RandomClass(object):
            pass

        class ValidationTestModelAdmin(ModelAdmin):
            list_filter = (RandomClass,)

        six.assertRaisesRegex(self,
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.list_filter\[0\]' is 'RandomClass' which is not a descendant of ListFilter.",
            ValidationTestModelAdmin.validate,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            list_filter = (('is_active', RandomClass),)

        six.assertRaisesRegex(self,
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.list_filter\[0\]\[1\]' is 'RandomClass' which is not of type FieldListFilter.",
            ValidationTestModelAdmin.validate,
            ValidationTestModel,
        )

        class AwesomeFilter(SimpleListFilter):
            def get_title(self):
                return 'awesomeness'
            def get_choices(self, request):
                return (('bit', 'A bit awesome'), ('very', 'Very awesome'), )
            def get_queryset(self, cl, qs):
                return qs

        class ValidationTestModelAdmin(ModelAdmin):
            list_filter = (('is_active', AwesomeFilter),)

        six.assertRaisesRegex(self,
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.list_filter\[0\]\[1\]' is 'AwesomeFilter' which is not of type FieldListFilter.",
            ValidationTestModelAdmin.validate,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            list_filter = (BooleanFieldListFilter,)

        six.assertRaisesRegex(self,
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.list_filter\[0\]' is 'BooleanFieldListFilter' which is of type FieldListFilter but is not associated with a field name.",
            ValidationTestModelAdmin.validate,
            ValidationTestModel,
        )

        # Valid declarations below -----------

        class ValidationTestModelAdmin(ModelAdmin):
            list_filter = ('is_active', AwesomeFilter, ('is_active', BooleanFieldListFilter), 'no')

        ValidationTestModelAdmin.validate(ValidationTestModel)

    def test_list_per_page_validation(self):

        class ValidationTestModelAdmin(ModelAdmin):
            list_per_page = 'hello'

        six.assertRaisesRegex(self,
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.list_per_page' should be a int.",
            ValidationTestModelAdmin.validate,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            list_per_page = 100

        ValidationTestModelAdmin.validate(ValidationTestModel)

    def test_max_show_all_allowed_validation(self):

        class ValidationTestModelAdmin(ModelAdmin):
            list_max_show_all = 'hello'

        six.assertRaisesRegex(self,
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.list_max_show_all' should be a int.",
            ValidationTestModelAdmin.validate,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            list_max_show_all = 200

        ValidationTestModelAdmin.validate(ValidationTestModel)

    def test_search_fields_validation(self):

        class ValidationTestModelAdmin(ModelAdmin):
            search_fields = 10

        six.assertRaisesRegex(self,
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.search_fields' must be a list or tuple.",
            ValidationTestModelAdmin.validate,
            ValidationTestModel,
        )

    def test_date_hierarchy_validation(self):

        class ValidationTestModelAdmin(ModelAdmin):
            date_hierarchy = 'non_existent_field'

        six.assertRaisesRegex(self,
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.date_hierarchy' refers to field 'non_existent_field' that is missing from model 'modeladmin.ValidationTestModel'.",
            ValidationTestModelAdmin.validate,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            date_hierarchy = 'name'

        six.assertRaisesRegex(self,
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.date_hierarchy is neither an instance of DateField nor DateTimeField.",
            ValidationTestModelAdmin.validate,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            date_hierarchy = 'pub_date'

        ValidationTestModelAdmin.validate(ValidationTestModel)

    def test_ordering_validation(self):

        class ValidationTestModelAdmin(ModelAdmin):
            ordering = 10

        six.assertRaisesRegex(self,
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.ordering' must be a list or tuple.",
            ValidationTestModelAdmin.validate,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            ordering = ('non_existent_field',)

        six.assertRaisesRegex(self,
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.ordering\[0\]' refers to field 'non_existent_field' that is missing from model 'modeladmin.ValidationTestModel'.",
            ValidationTestModelAdmin.validate,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            ordering = ('?', 'name')

        six.assertRaisesRegex(self,
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.ordering' has the random ordering marker '\?', but contains other fields as well. Please either remove '\?' or the other fields.",
            ValidationTestModelAdmin.validate,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            ordering = ('?',)

        ValidationTestModelAdmin.validate(ValidationTestModel)

        class ValidationTestModelAdmin(ModelAdmin):
            ordering = ('band__name',)

        ValidationTestModelAdmin.validate(ValidationTestModel)

        class ValidationTestModelAdmin(ModelAdmin):
            ordering = ('name',)

        ValidationTestModelAdmin.validate(ValidationTestModel)

    def test_list_select_related_validation(self):

        class ValidationTestModelAdmin(ModelAdmin):
            list_select_related = 1

        six.assertRaisesRegex(
            self,
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.list_select_related' should be either a "
            "bool, a tuple or a list",
            ValidationTestModelAdmin.validate,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            list_select_related = False

        ValidationTestModelAdmin.validate(ValidationTestModel)

    def test_save_as_validation(self):

        class ValidationTestModelAdmin(ModelAdmin):
            save_as = 1

        six.assertRaisesRegex(self,
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.save_as' should be a bool.",
            ValidationTestModelAdmin.validate,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            save_as = True

        ValidationTestModelAdmin.validate(ValidationTestModel)

    def test_save_on_top_validation(self):

        class ValidationTestModelAdmin(ModelAdmin):
            save_on_top = 1

        six.assertRaisesRegex(self,
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.save_on_top' should be a bool.",
            ValidationTestModelAdmin.validate,
            ValidationTestModel,
        )

        class ValidationTestModelAdmin(ModelAdmin):
            save_on_top = True

        ValidationTestModelAdmin.validate(ValidationTestModel)

    def test_inlines_validation(self):

        class ValidationTestModelAdmin(ModelAdmin):
            inlines = 10

        six.assertRaisesRegex(self,
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.inlines' must be a list or tuple.",
            ValidationTestModelAdmin.validate,
            ValidationTestModel,
        )

        class ValidationTestInline(object):
            pass

        class ValidationTestModelAdmin(ModelAdmin):
            inlines = [ValidationTestInline]

        six.assertRaisesRegex(self,
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.inlines\[0\]' does not inherit from BaseModelAdmin.",
            ValidationTestModelAdmin.validate,
            ValidationTestModel,
        )

        class ValidationTestInline(TabularInline):
            pass

        class ValidationTestModelAdmin(ModelAdmin):
            inlines = [ValidationTestInline]

        six.assertRaisesRegex(self,
            ImproperlyConfigured,
            "'model' is a required attribute of 'ValidationTestModelAdmin.inlines\[0\]'.",
            ValidationTestModelAdmin.validate,
            ValidationTestModel,
        )

        class SomethingBad(object):
            pass

        class ValidationTestInline(TabularInline):
            model = SomethingBad

        class ValidationTestModelAdmin(ModelAdmin):
            inlines = [ValidationTestInline]

        six.assertRaisesRegex(self,
            ImproperlyConfigured,
            "'ValidationTestModelAdmin.inlines\[0\].model' does not inherit from models.Model.",
            ValidationTestModelAdmin.validate,
            ValidationTestModel,
        )

        class ValidationTestInline(TabularInline):
            model = ValidationTestInlineModel

        class ValidationTestModelAdmin(ModelAdmin):
            inlines = [ValidationTestInline]

        ValidationTestModelAdmin.validate(ValidationTestModel)

    def test_fields_validation(self):

        class ValidationTestInline(TabularInline):
            model = ValidationTestInlineModel
            fields = 10

        class ValidationTestModelAdmin(ModelAdmin):
            inlines = [ValidationTestInline]

        six.assertRaisesRegex(self,
            ImproperlyConfigured,
            "'ValidationTestInline.fields' must be a list or tuple.",
            ValidationTestModelAdmin.validate,
            ValidationTestModel,
        )

    def test_fk_name_validation(self):

        class ValidationTestInline(TabularInline):
            model = ValidationTestInlineModel
            fk_name = "non_existent_field"

        class ValidationTestModelAdmin(ModelAdmin):
            inlines = [ValidationTestInline]

        six.assertRaisesRegex(self,
            ImproperlyConfigured,
            "'ValidationTestInline.fk_name' refers to field 'non_existent_field' that is missing from model 'modeladmin.ValidationTestInlineModel'.",
            ValidationTestModelAdmin.validate,
            ValidationTestModel,
        )

        class ValidationTestInline(TabularInline):
            model = ValidationTestInlineModel
            fk_name = "parent"

        class ValidationTestModelAdmin(ModelAdmin):
            inlines = [ValidationTestInline]

        ValidationTestModelAdmin.validate(ValidationTestModel)

    def test_extra_validation(self):

        class ValidationTestInline(TabularInline):
            model = ValidationTestInlineModel
            extra = "hello"

        class ValidationTestModelAdmin(ModelAdmin):
            inlines = [ValidationTestInline]

        six.assertRaisesRegex(self,
            ImproperlyConfigured,
            "'ValidationTestInline.extra' should be a int.",
            ValidationTestModelAdmin.validate,
            ValidationTestModel,
        )

        class ValidationTestInline(TabularInline):
            model = ValidationTestInlineModel
            extra = 2

        class ValidationTestModelAdmin(ModelAdmin):
            inlines = [ValidationTestInline]

        ValidationTestModelAdmin.validate(ValidationTestModel)

    def test_max_num_validation(self):

        class ValidationTestInline(TabularInline):
            model = ValidationTestInlineModel
            max_num = "hello"

        class ValidationTestModelAdmin(ModelAdmin):
            inlines = [ValidationTestInline]

        six.assertRaisesRegex(self,
            ImproperlyConfigured,
            "'ValidationTestInline.max_num' should be a int.",
            ValidationTestModelAdmin.validate,
            ValidationTestModel,
        )

        class ValidationTestInline(TabularInline):
            model = ValidationTestInlineModel
            max_num = 2

        class ValidationTestModelAdmin(ModelAdmin):
            inlines = [ValidationTestInline]

        ValidationTestModelAdmin.validate(ValidationTestModel)

    def test_formset_validation(self):

        class FakeFormSet(object):
            pass

        class ValidationTestInline(TabularInline):
            model = ValidationTestInlineModel
            formset = FakeFormSet

        class ValidationTestModelAdmin(ModelAdmin):
            inlines = [ValidationTestInline]

        six.assertRaisesRegex(self,
            ImproperlyConfigured,
            "'ValidationTestInline.formset' does not inherit from BaseModelFormSet.",
            ValidationTestModelAdmin.validate,
            ValidationTestModel,
        )

        class RealModelFormSet(BaseModelFormSet):
            pass

        class ValidationTestInline(TabularInline):
            model = ValidationTestInlineModel
            formset = RealModelFormSet

        class ValidationTestModelAdmin(ModelAdmin):
            inlines = [ValidationTestInline]

        ValidationTestModelAdmin.validate(ValidationTestModel)
