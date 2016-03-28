from __future__ import unicode_literals

from datetime import date

from django import forms
from django.contrib.admin import BooleanFieldListFilter, SimpleListFilter
from django.contrib.admin.options import (
    HORIZONTAL, VERTICAL, ModelAdmin, TabularInline,
)
from django.contrib.admin.sites import AdminSite
from django.contrib.admin.widgets import AdminDateWidget, AdminRadioSelect
from django.core.checks import Error
from django.forms.models import BaseModelFormSet
from django.forms.widgets import Select
from django.test import SimpleTestCase, TestCase
from django.utils import six

from .models import (
    Band, Concert, ValidationTestInlineModel, ValidationTestModel,
)


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

        self.assertEqual(list(ma.get_form(request).base_fields), ['name', 'bio', 'sign_date'])
        self.assertEqual(list(ma.get_fields(request)), ['name', 'bio', 'sign_date'])
        self.assertEqual(list(ma.get_fields(request, self.band)), ['name', 'bio', 'sign_date'])

    def test_default_fieldsets(self):
        # fieldsets_add and fieldsets_change should return a special data structure that
        # is used in the templates. They should generate the "right thing" whether we
        # have specified a custom form, the fields argument, or nothing at all.
        #
        # Here's the default case. There are no custom form_add/form_change methods,
        # no fields argument, and no fieldsets argument.
        ma = ModelAdmin(Band, self.site)
        self.assertEqual(ma.get_fieldsets(request), [(None, {'fields': ['name', 'bio', 'sign_date']})])

        self.assertEqual(ma.get_fieldsets(request, self.band), [(None, {'fields': ['name', 'bio', 'sign_date']})])

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
        # If we specify the fields argument, fieldsets_add and fieldsets_change should
        # just stick the fields into a formsets structure and return it.
        class BandAdmin(ModelAdmin):
            fields = ['name']

        ma = BandAdmin(Band, self.site)

        self.assertEqual(list(ma.get_fields(request)), ['name'])
        self.assertEqual(list(ma.get_fields(request, self.band)), ['name'])
        self.assertEqual(ma.get_fieldsets(request), [(None, {'fields': ['name']})])
        self.assertEqual(ma.get_fieldsets(request, self.band), [(None, {'fields': ['name']})])

    def test_field_arguments_restricted_on_form(self):
        # If we specify fields or fieldsets, it should exclude fields on the Form class
        # to the fields specified. This may cause errors to be raised in the db layer if
        # required model fields aren't in fields/fieldsets, but that's preferable to
        # ghost errors where you have a field in your Form class that isn't being
        # displayed because you forgot to add it to fields/fieldsets

        # Using `fields`.
        class BandAdmin(ModelAdmin):
            fields = ['name']

        ma = BandAdmin(Band, self.site)
        self.assertEqual(list(ma.get_form(request).base_fields), ['name'])
        self.assertEqual(list(ma.get_form(request, self.band).base_fields), ['name'])

        # Using `fieldsets`.
        class BandAdmin(ModelAdmin):
            fieldsets = [(None, {'fields': ['name']})]

        ma = BandAdmin(Band, self.site)
        self.assertEqual(list(ma.get_form(request).base_fields), ['name'])
        self.assertEqual(list(ma.get_form(request, self.band).base_fields), ['name'])

        # Using `exclude`.
        class BandAdmin(ModelAdmin):
            exclude = ['bio']

        ma = BandAdmin(Band, self.site)
        self.assertEqual(list(ma.get_form(request).base_fields), ['name', 'sign_date'])

        # You can also pass a tuple to `exclude`.
        class BandAdmin(ModelAdmin):
            exclude = ('bio',)

        ma = BandAdmin(Band, self.site)
        self.assertEqual(list(ma.get_form(request).base_fields), ['name', 'sign_date'])

        # Using `fields` and `exclude`.
        class BandAdmin(ModelAdmin):
            fields = ['name', 'bio']
            exclude = ['bio']

        ma = BandAdmin(Band, self.site)
        self.assertEqual(list(ma.get_form(request).base_fields), ['name'])

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
        self.assertEqual(list(ma.get_form(request).base_fields), ['sign_date'])

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
            list(list(ma.get_formsets_with_inlines(request))[0][0]().forms[0].fields),
            ['main_band', 'opening_band', 'id', 'DELETE'])

    def test_custom_formfield_override_readonly(self):
        class AdminBandForm(forms.ModelForm):
            name = forms.CharField()

            class Meta:
                exclude = tuple()
                model = Band

        class BandAdmin(ModelAdmin):
            form = AdminBandForm
            readonly_fields = ['name']

        ma = BandAdmin(Band, self.site)

        # `name` shouldn't appear in base_fields because it's part of
        # readonly_fields.
        self.assertEqual(
            list(ma.get_form(request).base_fields),
            ['bio', 'sign_date']
        )
        # But it should appear in get_fields()/fieldsets() so it can be
        # displayed as read-only.
        self.assertEqual(
            list(ma.get_fields(request)),
            ['bio', 'sign_date', 'name']
        )
        self.assertEqual(
            list(ma.get_fieldsets(request)),
            [(None, {'fields': ['bio', 'sign_date', 'name']})]
        )

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
        self.assertEqual(list(ma.get_form(request).base_fields), ['bio', 'sign_date'])

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
            list(list(ma.get_formsets_with_inlines(request))[0][0]().forms[0].fields),
            ['main_band', 'opening_band', 'day', 'id', 'DELETE']
        )

    def test_custom_form_validation(self):
        # If we specify a form, it should use it allowing custom validation to work
        # properly. This won't, however, break any of the admin widgets or media.

        class AdminBandForm(forms.ModelForm):
            delete = forms.BooleanField()

        class BandAdmin(ModelAdmin):
            form = AdminBandForm

        ma = BandAdmin(Band, self.site)
        self.assertEqual(list(ma.get_form(request).base_fields), ['name', 'bio', 'sign_date', 'delete'])
        self.assertEqual(type(ma.get_form(request).base_fields['sign_date'].widget), AdminDateWidget)

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
        self.assertEqual(list(ma.get_form(request).base_fields), ['name', 'sign_date'])

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
            list(list(ma.get_formsets_with_inlines(request))[0][0]().forms[0].fields),
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

        self.assertHTMLEqual(
            str(form["main_band"]),
            '<div class="related-widget-wrapper">'
            '<select name="main_band" id="id_main_band" required>'
            '<option value="" selected="selected">---------</option>'
            '<option value="%d">The Beatles</option>'
            '<option value="%d">The Doors</option>'
            '</select></div>' % (band2.id, self.band.id)
        )

        class AdminConcertForm(forms.ModelForm):
            def __init__(self, *args, **kwargs):
                super(AdminConcertForm, self).__init__(*args, **kwargs)
                self.fields["main_band"].queryset = Band.objects.filter(name='The Doors')

        class ConcertAdminWithForm(ModelAdmin):
            form = AdminConcertForm

        ma = ConcertAdminWithForm(Concert, self.site)
        form = ma.get_form(request)()

        self.assertHTMLEqual(
            str(form["main_band"]),
            '<div class="related-widget-wrapper">'
            '<select name="main_band" id="id_main_band" required>'
            '<option value="" selected="selected">---------</option>'
            '<option value="%d">The Doors</option>'
            '</select></div>' % self.band.id
        )

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

        Concert.objects.create(main_band=self.band, opening_band=self.band, day=1)
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

        self.assertEqual(type(cmafa.base_fields['main_band'].widget.widget), Select)
        self.assertEqual(
            list(cmafa.base_fields['main_band'].widget.choices),
            [('', '---------'), (self.band.id, 'The Doors')])

        self.assertEqual(type(cmafa.base_fields['opening_band'].widget.widget), Select)
        self.assertEqual(
            list(cmafa.base_fields['opening_band'].widget.choices),
            [('', '---------'), (self.band.id, 'The Doors')]
        )
        self.assertEqual(type(cmafa.base_fields['day'].widget), Select)
        self.assertEqual(
            list(cmafa.base_fields['day'].widget.choices),
            [('', '---------'), (1, 'Fri'), (2, 'Sat')]
        )
        self.assertEqual(type(cmafa.base_fields['transport'].widget), Select)
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

        self.assertEqual(type(cmafa.base_fields['main_band'].widget.widget), AdminRadioSelect)
        self.assertEqual(cmafa.base_fields['main_band'].widget.attrs, {'class': 'radiolist inline'})
        self.assertEqual(
            list(cmafa.base_fields['main_band'].widget.choices),
            [(self.band.id, 'The Doors')]
        )

        self.assertEqual(type(cmafa.base_fields['opening_band'].widget.widget), AdminRadioSelect)
        self.assertEqual(cmafa.base_fields['opening_band'].widget.attrs, {'class': 'radiolist'})
        self.assertEqual(
            list(cmafa.base_fields['opening_band'].widget.choices),
            [('', 'None'), (self.band.id, 'The Doors')]
        )
        self.assertEqual(type(cmafa.base_fields['day'].widget), AdminRadioSelect)
        self.assertEqual(cmafa.base_fields['day'].widget.attrs, {'class': 'radiolist'})
        self.assertEqual(list(cmafa.base_fields['day'].widget.choices), [(1, 'Fri'), (2, 'Sat')])

        self.assertEqual(type(cmafa.base_fields['transport'].widget), AdminRadioSelect)
        self.assertEqual(cmafa.base_fields['transport'].widget.attrs, {'class': 'radiolist inline'})
        self.assertEqual(
            list(cmafa.base_fields['transport'].widget.choices),
            [('', 'None'), (1, 'Plane'), (2, 'Train'), (3, 'Bus')]
        )

        class AdminConcertForm(forms.ModelForm):
            class Meta:
                model = Concert
                exclude = ('transport',)

        class ConcertAdmin(ModelAdmin):
            form = AdminConcertForm

        ma = ConcertAdmin(Concert, self.site)
        self.assertEqual(list(ma.get_form(request).base_fields), ['main_band', 'opening_band', 'day'])

        class AdminConcertForm(forms.ModelForm):
            extra = forms.CharField()

            class Meta:
                model = Concert
                fields = ['extra', 'transport']

        class ConcertAdmin(ModelAdmin):
            form = AdminConcertForm

        ma = ConcertAdmin(Concert, self.site)
        self.assertEqual(list(ma.get_form(request).base_fields), ['extra', 'transport'])

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
            list(list(ma.get_formsets_with_inlines(request))[0][0]().forms[0].fields),
            ['extra', 'transport', 'id', 'DELETE', 'main_band']
        )


class CheckTestCase(SimpleTestCase):

    def assertIsInvalid(self, model_admin, model, msg, id=None, hint=None, invalid_obj=None):
        invalid_obj = invalid_obj or model_admin
        admin_obj = model_admin(model, AdminSite())
        errors = admin_obj.check()
        expected = [
            Error(
                msg,
                hint=hint,
                obj=invalid_obj,
                id=id,
            )
        ]
        self.assertEqual(errors, expected)

    def assertIsInvalidRegexp(self, model_admin, model, msg, id=None, hint=None, invalid_obj=None):
        """
        Same as assertIsInvalid but treats the given msg as a regexp.
        """
        invalid_obj = invalid_obj or model_admin
        admin_obj = model_admin(model, AdminSite())
        errors = admin_obj.check()
        self.assertEqual(len(errors), 1)
        error = errors[0]
        self.assertEqual(error.hint, hint)
        self.assertEqual(error.obj, invalid_obj)
        self.assertEqual(error.id, id)
        six.assertRegex(self, error.msg, msg)

    def assertIsValid(self, model_admin, model):
        admin_obj = model_admin(model, AdminSite())
        errors = admin_obj.check()
        expected = []
        self.assertEqual(errors, expected)


class RawIdCheckTests(CheckTestCase):

    def test_not_iterable(self):
        class ValidationTestModelAdmin(ModelAdmin):
            raw_id_fields = 10

        self.assertIsInvalid(
            ValidationTestModelAdmin, ValidationTestModel,
            "The value of 'raw_id_fields' must be a list or tuple.",
            'admin.E001')

    def test_missing_field(self):
        class ValidationTestModelAdmin(ModelAdmin):
            raw_id_fields = ('non_existent_field',)

        self.assertIsInvalid(
            ValidationTestModelAdmin, ValidationTestModel,
            ("The value of 'raw_id_fields[0]' refers to 'non_existent_field', "
             "which is not an attribute of 'modeladmin.ValidationTestModel'."),
            'admin.E002')

    def test_invalid_field_type(self):
        class ValidationTestModelAdmin(ModelAdmin):
            raw_id_fields = ('name',)

        self.assertIsInvalid(
            ValidationTestModelAdmin, ValidationTestModel,
            "The value of 'raw_id_fields[0]' must be a foreign key or a many-to-many field.",
            'admin.E003')

    def test_valid_case(self):
        class ValidationTestModelAdmin(ModelAdmin):
            raw_id_fields = ('users',)

        self.assertIsValid(ValidationTestModelAdmin, ValidationTestModel)


class FieldsetsCheckTests(CheckTestCase):

    def test_valid_case(self):
        class ValidationTestModelAdmin(ModelAdmin):
            fieldsets = (("General", {'fields': ('name',)}),)

        self.assertIsValid(ValidationTestModelAdmin, ValidationTestModel)

    def test_not_iterable(self):

        class ValidationTestModelAdmin(ModelAdmin):
            fieldsets = 10

        self.assertIsInvalid(
            ValidationTestModelAdmin, ValidationTestModel,
            "The value of 'fieldsets' must be a list or tuple.",
            'admin.E007')

    def test_non_iterable_item(self):
        class ValidationTestModelAdmin(ModelAdmin):
            fieldsets = ({},)

        self.assertIsInvalid(
            ValidationTestModelAdmin, ValidationTestModel,
            "The value of 'fieldsets[0]' must be a list or tuple.",
            'admin.E008')

    def test_item_not_a_pair(self):
        class ValidationTestModelAdmin(ModelAdmin):
            fieldsets = ((),)

        self.assertIsInvalid(
            ValidationTestModelAdmin, ValidationTestModel,
            "The value of 'fieldsets[0]' must be of length 2.",
            'admin.E009')

    def test_second_element_of_item_not_a_dict(self):
        class ValidationTestModelAdmin(ModelAdmin):
            fieldsets = (("General", ()),)

        self.assertIsInvalid(
            ValidationTestModelAdmin, ValidationTestModel,
            "The value of 'fieldsets[0][1]' must be a dictionary.",
            'admin.E010')

    def test_missing_fields_key(self):
        class ValidationTestModelAdmin(ModelAdmin):
            fieldsets = (("General", {}),)

        self.assertIsInvalid(
            ValidationTestModelAdmin, ValidationTestModel,
            "The value of 'fieldsets[0][1]' must contain the key 'fields'.",
            'admin.E011')

        class ValidationTestModelAdmin(ModelAdmin):
            fieldsets = (("General", {'fields': ('name',)}),)

        self.assertIsValid(ValidationTestModelAdmin, ValidationTestModel)

    def test_specified_both_fields_and_fieldsets(self):
        class ValidationTestModelAdmin(ModelAdmin):
            fieldsets = (("General", {'fields': ('name',)}),)
            fields = ['name']

        self.assertIsInvalid(
            ValidationTestModelAdmin, ValidationTestModel,
            "Both 'fieldsets' and 'fields' are specified.",
            'admin.E005')

    def test_duplicate_fields(self):
        class ValidationTestModelAdmin(ModelAdmin):
            fieldsets = [(None, {'fields': ['name', 'name']})]

        self.assertIsInvalid(
            ValidationTestModelAdmin, ValidationTestModel,
            "There are duplicate field(s) in 'fieldsets[0][1]'.",
            'admin.E012')

    def test_fieldsets_with_custom_form_validation(self):
        class BandAdmin(ModelAdmin):
            fieldsets = (
                ('Band', {
                    'fields': ('name',)
                }),
            )

        self.assertIsValid(BandAdmin, Band)


class FieldsCheckTests(CheckTestCase):

    def test_duplicate_fields_in_fields(self):
        class ValidationTestModelAdmin(ModelAdmin):
            fields = ['name', 'name']

        self.assertIsInvalid(
            ValidationTestModelAdmin, ValidationTestModel,
            "The value of 'fields' contains duplicate field(s).",
            'admin.E006')

    def test_inline(self):
        class ValidationTestInline(TabularInline):
            model = ValidationTestInlineModel
            fields = 10

        class ValidationTestModelAdmin(ModelAdmin):
            inlines = [ValidationTestInline]

        self.assertIsInvalid(
            ValidationTestModelAdmin, ValidationTestModel,
            "The value of 'fields' must be a list or tuple.",
            'admin.E004',
            invalid_obj=ValidationTestInline)


class FormCheckTests(CheckTestCase):

    def test_invalid_type(self):
        class FakeForm(object):
            pass

        class ValidationTestModelAdmin(ModelAdmin):
            form = FakeForm

        self.assertIsInvalid(
            ValidationTestModelAdmin, ValidationTestModel,
            "The value of 'form' must inherit from 'BaseModelForm'.",
            'admin.E016')

    def test_fieldsets_with_custom_form_validation(self):

        class BandAdmin(ModelAdmin):
            fieldsets = (
                ('Band', {
                    'fields': ('name',)
                }),
            )

        self.assertIsValid(BandAdmin, Band)

    def test_valid_case(self):
        class AdminBandForm(forms.ModelForm):
            delete = forms.BooleanField()

        class BandAdmin(ModelAdmin):
            form = AdminBandForm

            fieldsets = (
                ('Band', {
                    'fields': ('name', 'bio', 'sign_date', 'delete')
                }),
            )

        self.assertIsValid(BandAdmin, Band)


class FilterVerticalCheckTests(CheckTestCase):

    def test_not_iterable(self):
        class ValidationTestModelAdmin(ModelAdmin):
            filter_vertical = 10

        self.assertIsInvalid(
            ValidationTestModelAdmin, ValidationTestModel,
            "The value of 'filter_vertical' must be a list or tuple.",
            'admin.E017')

    def test_missing_field(self):
        class ValidationTestModelAdmin(ModelAdmin):
            filter_vertical = ('non_existent_field',)

        self.assertIsInvalid(
            ValidationTestModelAdmin, ValidationTestModel,
            ("The value of 'filter_vertical[0]' refers to 'non_existent_field', "
             "which is not an attribute of 'modeladmin.ValidationTestModel'."),
            'admin.E019')

    def test_invalid_field_type(self):
        class ValidationTestModelAdmin(ModelAdmin):
            filter_vertical = ('name',)

        self.assertIsInvalid(
            ValidationTestModelAdmin, ValidationTestModel,
            "The value of 'filter_vertical[0]' must be a many-to-many field.",
            'admin.E020')

    def test_valid_case(self):
        class ValidationTestModelAdmin(ModelAdmin):
            filter_vertical = ("users",)

        self.assertIsValid(ValidationTestModelAdmin, ValidationTestModel)


class FilterHorizontalCheckTests(CheckTestCase):

    def test_not_iterable(self):
        class ValidationTestModelAdmin(ModelAdmin):
            filter_horizontal = 10

        self.assertIsInvalid(
            ValidationTestModelAdmin, ValidationTestModel,
            "The value of 'filter_horizontal' must be a list or tuple.",
            'admin.E018')

    def test_missing_field(self):
        class ValidationTestModelAdmin(ModelAdmin):
            filter_horizontal = ('non_existent_field',)

        self.assertIsInvalid(
            ValidationTestModelAdmin, ValidationTestModel,
            ("The value of 'filter_horizontal[0]' refers to 'non_existent_field', "
             "which is not an attribute of 'modeladmin.ValidationTestModel'."),
            'admin.E019')

    def test_invalid_field_type(self):
        class ValidationTestModelAdmin(ModelAdmin):
            filter_horizontal = ('name',)

        self.assertIsInvalid(
            ValidationTestModelAdmin, ValidationTestModel,
            "The value of 'filter_horizontal[0]' must be a many-to-many field.",
            'admin.E020')

    def test_valid_case(self):
        class ValidationTestModelAdmin(ModelAdmin):
            filter_horizontal = ("users",)

        self.assertIsValid(ValidationTestModelAdmin, ValidationTestModel)


class RadioFieldsCheckTests(CheckTestCase):

    def test_not_dictionary(self):

        class ValidationTestModelAdmin(ModelAdmin):
            radio_fields = ()

        self.assertIsInvalid(
            ValidationTestModelAdmin, ValidationTestModel,
            "The value of 'radio_fields' must be a dictionary.",
            'admin.E021')

    def test_missing_field(self):
        class ValidationTestModelAdmin(ModelAdmin):
            radio_fields = {'non_existent_field': VERTICAL}

        self.assertIsInvalid(
            ValidationTestModelAdmin, ValidationTestModel,
            ("The value of 'radio_fields' refers to 'non_existent_field', "
             "which is not an attribute of 'modeladmin.ValidationTestModel'."),
            'admin.E022')

    def test_invalid_field_type(self):
        class ValidationTestModelAdmin(ModelAdmin):
            radio_fields = {'name': VERTICAL}

        self.assertIsInvalid(
            ValidationTestModelAdmin, ValidationTestModel,
            ("The value of 'radio_fields' refers to 'name', which is not an instance "
             "of ForeignKey, and does not have a 'choices' definition."),
            'admin.E023')

    def test_invalid_value(self):
        class ValidationTestModelAdmin(ModelAdmin):
            radio_fields = {"state": None}

        self.assertIsInvalid(
            ValidationTestModelAdmin, ValidationTestModel,
            "The value of 'radio_fields[\"state\"]' must be either admin.HORIZONTAL or admin.VERTICAL.",
            'admin.E024')

    def test_valid_case(self):
        class ValidationTestModelAdmin(ModelAdmin):
            radio_fields = {"state": VERTICAL}

        self.assertIsValid(ValidationTestModelAdmin, ValidationTestModel)


class PrepopulatedFieldsCheckTests(CheckTestCase):

    def test_not_dictionary(self):

        class ValidationTestModelAdmin(ModelAdmin):
            prepopulated_fields = ()

        self.assertIsInvalid(
            ValidationTestModelAdmin, ValidationTestModel,
            "The value of 'prepopulated_fields' must be a dictionary.",
            'admin.E026')

    def test_missing_field(self):
        class ValidationTestModelAdmin(ModelAdmin):
            prepopulated_fields = {'non_existent_field': ("slug",)}

        self.assertIsInvalid(
            ValidationTestModelAdmin, ValidationTestModel,
            ("The value of 'prepopulated_fields' refers to 'non_existent_field', "
             "which is not an attribute of 'modeladmin.ValidationTestModel'."),
            'admin.E027')

    def test_missing_field_again(self):
        class ValidationTestModelAdmin(ModelAdmin):
            prepopulated_fields = {"slug": ('non_existent_field',)}

        self.assertIsInvalid(
            ValidationTestModelAdmin, ValidationTestModel,
            ("The value of 'prepopulated_fields[\"slug\"][0]' refers to 'non_existent_field', "
             "which is not an attribute of 'modeladmin.ValidationTestModel'."),
            'admin.E030')

    def test_invalid_field_type(self):
        class ValidationTestModelAdmin(ModelAdmin):
            prepopulated_fields = {"users": ('name',)}

        self.assertIsInvalid(
            ValidationTestModelAdmin, ValidationTestModel,
            ("The value of 'prepopulated_fields' refers to 'users', which must not be "
             "a DateTimeField, a foreign key, or a many-to-many field."),
            'admin.E028')

    def test_valid_case(self):
        class ValidationTestModelAdmin(ModelAdmin):
            prepopulated_fields = {"slug": ('name',)}

        self.assertIsValid(ValidationTestModelAdmin, ValidationTestModel)


class ListDisplayTests(CheckTestCase):

    def test_not_iterable(self):

        class ValidationTestModelAdmin(ModelAdmin):
            list_display = 10

        self.assertIsInvalid(
            ValidationTestModelAdmin, ValidationTestModel,
            "The value of 'list_display' must be a list or tuple.",
            'admin.E107')

    def test_missing_field(self):
        class ValidationTestModelAdmin(ModelAdmin):
            list_display = ('non_existent_field',)

        self.assertIsInvalid(
            ValidationTestModelAdmin, ValidationTestModel,
            ("The value of 'list_display[0]' refers to 'non_existent_field', which is not a callable, an attribute "
             "of 'ValidationTestModelAdmin', or an attribute or method on 'modeladmin.ValidationTestModel'."),
            'admin.E108')

    def test_invalid_field_type(self):
        class ValidationTestModelAdmin(ModelAdmin):
            list_display = ('users',)

        self.assertIsInvalid(
            ValidationTestModelAdmin, ValidationTestModel,
            "The value of 'list_display[0]' must not be a many-to-many field.",
            'admin.E109')

    def test_valid_case(self):
        def a_callable(obj):
            pass

        class ValidationTestModelAdmin(ModelAdmin):
            def a_method(self, obj):
                pass
            list_display = ('name', 'decade_published_in', 'a_method', a_callable)

        self.assertIsValid(ValidationTestModelAdmin, ValidationTestModel)


class ListDisplayLinksCheckTests(CheckTestCase):

    def test_not_iterable(self):
        class ValidationTestModelAdmin(ModelAdmin):
            list_display_links = 10

        self.assertIsInvalid(
            ValidationTestModelAdmin, ValidationTestModel,
            "The value of 'list_display_links' must be a list, a tuple, or None.",
            'admin.E110')

    def test_missing_field(self):
        class ValidationTestModelAdmin(ModelAdmin):
            list_display_links = ('non_existent_field',)

        self.assertIsInvalid(
            ValidationTestModelAdmin, ValidationTestModel, (
                "The value of 'list_display_links[0]' refers to "
                "'non_existent_field', which is not defined in 'list_display'."
            ), 'admin.E111'
        )

    def test_missing_in_list_display(self):
        class ValidationTestModelAdmin(ModelAdmin):
            list_display_links = ('name',)

        self.assertIsInvalid(
            ValidationTestModelAdmin, ValidationTestModel,
            "The value of 'list_display_links[0]' refers to 'name', which is not defined in 'list_display'.",
            'admin.E111')

    def test_valid_case(self):
        def a_callable(obj):
            pass

        class ValidationTestModelAdmin(ModelAdmin):
            def a_method(self, obj):
                pass
            list_display = ('name', 'decade_published_in', 'a_method', a_callable)
            list_display_links = ('name', 'decade_published_in', 'a_method', a_callable)

        self.assertIsValid(ValidationTestModelAdmin, ValidationTestModel)

    def test_None_is_valid_case(self):
        class ValidationTestModelAdmin(ModelAdmin):
            list_display_links = None

        self.assertIsValid(ValidationTestModelAdmin, ValidationTestModel)


class ListFilterTests(CheckTestCase):

    def test_list_filter_validation(self):
        class ValidationTestModelAdmin(ModelAdmin):
            list_filter = 10

        self.assertIsInvalid(
            ValidationTestModelAdmin, ValidationTestModel,
            "The value of 'list_filter' must be a list or tuple.",
            'admin.E112')

    def test_missing_field(self):
        class ValidationTestModelAdmin(ModelAdmin):
            list_filter = ('non_existent_field',)

        self.assertIsInvalid(
            ValidationTestModelAdmin, ValidationTestModel,
            "The value of 'list_filter[0]' refers to 'non_existent_field', which does not refer to a Field.",
            'admin.E116')

    def test_not_filter(self):
        class RandomClass(object):
            pass

        class ValidationTestModelAdmin(ModelAdmin):
            list_filter = (RandomClass,)

        self.assertIsInvalid(
            ValidationTestModelAdmin, ValidationTestModel,
            "The value of 'list_filter[0]' must inherit from 'ListFilter'.",
            'admin.E113')

    def test_not_filter_again(self):
        class RandomClass(object):
            pass

        class ValidationTestModelAdmin(ModelAdmin):
            list_filter = (('is_active', RandomClass),)

        self.assertIsInvalid(
            ValidationTestModelAdmin, ValidationTestModel,
            "The value of 'list_filter[0][1]' must inherit from 'FieldListFilter'.",
            'admin.E115')

    def test_not_filter_again_again(self):
        class AwesomeFilter(SimpleListFilter):
            def get_title(self):
                return 'awesomeness'

            def get_choices(self, request):
                return (('bit', 'A bit awesome'), ('very', 'Very awesome'), )

            def get_queryset(self, cl, qs):
                return qs

        class ValidationTestModelAdmin(ModelAdmin):
            list_filter = (('is_active', AwesomeFilter),)

        self.assertIsInvalid(
            ValidationTestModelAdmin, ValidationTestModel,
            "The value of 'list_filter[0][1]' must inherit from 'FieldListFilter'.",
            'admin.E115')

    def test_not_associated_with_field_name(self):
        class ValidationTestModelAdmin(ModelAdmin):
            list_filter = (BooleanFieldListFilter,)

        self.assertIsInvalid(
            ValidationTestModelAdmin, ValidationTestModel,
            "The value of 'list_filter[0]' must not inherit from 'FieldListFilter'.",
            'admin.E114')

    def test_valid_case(self):
        class AwesomeFilter(SimpleListFilter):
            def get_title(self):
                return 'awesomeness'

            def get_choices(self, request):
                return (('bit', 'A bit awesome'), ('very', 'Very awesome'), )

            def get_queryset(self, cl, qs):
                return qs

        class ValidationTestModelAdmin(ModelAdmin):
            list_filter = ('is_active', AwesomeFilter, ('is_active', BooleanFieldListFilter), 'no')

        self.assertIsValid(ValidationTestModelAdmin, ValidationTestModel)


class ListPerPageCheckTests(CheckTestCase):

    def test_not_integer(self):
        class ValidationTestModelAdmin(ModelAdmin):
            list_per_page = 'hello'

        self.assertIsInvalid(
            ValidationTestModelAdmin, ValidationTestModel,
            "The value of 'list_per_page' must be an integer.",
            'admin.E118')

    def test_valid_case(self):
        class ValidationTestModelAdmin(ModelAdmin):
            list_per_page = 100

        self.assertIsValid(ValidationTestModelAdmin, ValidationTestModel)


class ListMaxShowAllCheckTests(CheckTestCase):

    def test_not_integer(self):
        class ValidationTestModelAdmin(ModelAdmin):
            list_max_show_all = 'hello'

        self.assertIsInvalid(
            ValidationTestModelAdmin, ValidationTestModel,
            "The value of 'list_max_show_all' must be an integer.",
            'admin.E119')

    def test_valid_case(self):
        class ValidationTestModelAdmin(ModelAdmin):
            list_max_show_all = 200

        self.assertIsValid(ValidationTestModelAdmin, ValidationTestModel)


class SearchFieldsCheckTests(CheckTestCase):

    def test_not_iterable(self):

        class ValidationTestModelAdmin(ModelAdmin):
            search_fields = 10

        self.assertIsInvalid(
            ValidationTestModelAdmin, ValidationTestModel,
            "The value of 'search_fields' must be a list or tuple.",
            'admin.E126')


class DateHierarchyCheckTests(CheckTestCase):

    def test_missing_field(self):

        class ValidationTestModelAdmin(ModelAdmin):
            date_hierarchy = 'non_existent_field'

        self.assertIsInvalid(
            ValidationTestModelAdmin, ValidationTestModel,
            ("The value of 'date_hierarchy' refers to 'non_existent_field', which "
             "is not an attribute of 'modeladmin.ValidationTestModel'."),
            'admin.E127')

    def test_invalid_field_type(self):
        class ValidationTestModelAdmin(ModelAdmin):
            date_hierarchy = 'name'

        self.assertIsInvalid(
            ValidationTestModelAdmin, ValidationTestModel,
            "The value of 'date_hierarchy' must be a DateField or DateTimeField.",
            'admin.E128')

    def test_valid_case(self):
        class ValidationTestModelAdmin(ModelAdmin):
            date_hierarchy = 'pub_date'

        self.assertIsValid(ValidationTestModelAdmin, ValidationTestModel)


class OrderingCheckTests(CheckTestCase):

    def test_not_iterable(self):
        class ValidationTestModelAdmin(ModelAdmin):
            ordering = 10

        self.assertIsInvalid(
            ValidationTestModelAdmin, ValidationTestModel,
            "The value of 'ordering' must be a list or tuple.",
            'admin.E031'
        )

        class ValidationTestModelAdmin(ModelAdmin):
            ordering = ('non_existent_field',)

        self.assertIsInvalid(
            ValidationTestModelAdmin, ValidationTestModel,
            "The value of 'ordering[0]' refers to 'non_existent_field', "
            "which is not an attribute of 'modeladmin.ValidationTestModel'.",
            'admin.E033'
        )

    def test_random_marker_not_alone(self):
        class ValidationTestModelAdmin(ModelAdmin):
            ordering = ('?', 'name')

        self.assertIsInvalid(
            ValidationTestModelAdmin, ValidationTestModel,
            "The value of 'ordering' has the random ordering marker '?', but contains "
            "other fields as well.",
            'admin.E032',
            hint='Either remove the "?", or remove the other fields.'
        )

    def test_valid_random_marker_case(self):
        class ValidationTestModelAdmin(ModelAdmin):
            ordering = ('?',)

        self.assertIsValid(ValidationTestModelAdmin, ValidationTestModel)

    def test_valid_complex_case(self):
        class ValidationTestModelAdmin(ModelAdmin):
            ordering = ('band__name',)

        self.assertIsValid(ValidationTestModelAdmin, ValidationTestModel)

    def test_valid_case(self):
        class ValidationTestModelAdmin(ModelAdmin):
            ordering = ('name',)

        self.assertIsValid(ValidationTestModelAdmin, ValidationTestModel)


class ListSelectRelatedCheckTests(CheckTestCase):

    def test_invalid_type(self):
        class ValidationTestModelAdmin(ModelAdmin):
            list_select_related = 1

        self.assertIsInvalid(
            ValidationTestModelAdmin, ValidationTestModel,
            "The value of 'list_select_related' must be a boolean, tuple or list.",
            'admin.E117')

    def test_valid_case(self):
        class ValidationTestModelAdmin(ModelAdmin):
            list_select_related = False

        self.assertIsValid(ValidationTestModelAdmin, ValidationTestModel)


class SaveAsCheckTests(CheckTestCase):

    def test_not_boolean(self):
        class ValidationTestModelAdmin(ModelAdmin):
            save_as = 1

        self.assertIsInvalid(
            ValidationTestModelAdmin, ValidationTestModel,
            "The value of 'save_as' must be a boolean.",
            'admin.E101')

    def test_valid_case(self):
        class ValidationTestModelAdmin(ModelAdmin):
            save_as = True

        self.assertIsValid(ValidationTestModelAdmin, ValidationTestModel)


class SaveOnTopCheckTests(CheckTestCase):

    def test_not_boolean(self):
        class ValidationTestModelAdmin(ModelAdmin):
            save_on_top = 1

        self.assertIsInvalid(
            ValidationTestModelAdmin, ValidationTestModel,
            "The value of 'save_on_top' must be a boolean.",
            'admin.E102')

    def test_valid_case(self):
        class ValidationTestModelAdmin(ModelAdmin):
            save_on_top = True

        self.assertIsValid(ValidationTestModelAdmin, ValidationTestModel)


class InlinesCheckTests(CheckTestCase):

    def test_not_iterable(self):
        class ValidationTestModelAdmin(ModelAdmin):
            inlines = 10

        self.assertIsInvalid(
            ValidationTestModelAdmin, ValidationTestModel,
            "The value of 'inlines' must be a list or tuple.",
            'admin.E103')

    def test_not_model_admin(self):
        class ValidationTestInline(object):
            pass

        class ValidationTestModelAdmin(ModelAdmin):
            inlines = [ValidationTestInline]

        self.assertIsInvalidRegexp(
            ValidationTestModelAdmin, ValidationTestModel,
            r"'.*\.ValidationTestInline' must inherit from 'BaseModelAdmin'\.",
            'admin.E104')

    def test_missing_model_field(self):
        class ValidationTestInline(TabularInline):
            pass

        class ValidationTestModelAdmin(ModelAdmin):
            inlines = [ValidationTestInline]

        self.assertIsInvalidRegexp(
            ValidationTestModelAdmin, ValidationTestModel,
            r"'.*\.ValidationTestInline' must have a 'model' attribute\.",
            'admin.E105')

    def test_invalid_model_type(self):
        """ Test if `model` attribute on inline model admin is a models.Model.
        """

        class SomethingBad(object):
            pass

        class ValidationTestInline(TabularInline):
            model = SomethingBad

        class ValidationTestModelAdmin(ModelAdmin):
            inlines = [ValidationTestInline]

        self.assertIsInvalidRegexp(
            ValidationTestModelAdmin, ValidationTestModel,
            r"The value of '.*\.ValidationTestInline.model' must be a Model\.",
            'admin.E106')

    def test_valid_case(self):
        class ValidationTestInline(TabularInline):
            model = ValidationTestInlineModel

        class ValidationTestModelAdmin(ModelAdmin):
            inlines = [ValidationTestInline]

        self.assertIsValid(ValidationTestModelAdmin, ValidationTestModel)


class FkNameCheckTests(CheckTestCase):

    def test_missing_field(self):
        class ValidationTestInline(TabularInline):
            model = ValidationTestInlineModel
            fk_name = 'non_existent_field'

        class ValidationTestModelAdmin(ModelAdmin):
            inlines = [ValidationTestInline]

        self.assertIsInvalid(
            ValidationTestModelAdmin, ValidationTestModel,
            "'modeladmin.ValidationTestInlineModel' has no field named 'non_existent_field'.",
            'admin.E202',
            invalid_obj=ValidationTestInline)

    def test_valid_case(self):
        class ValidationTestInline(TabularInline):
            model = ValidationTestInlineModel
            fk_name = "parent"

        class ValidationTestModelAdmin(ModelAdmin):
            inlines = [ValidationTestInline]

        self.assertIsValid(ValidationTestModelAdmin, ValidationTestModel)


class ExtraCheckTests(CheckTestCase):

    def test_not_integer(self):
        class ValidationTestInline(TabularInline):
            model = ValidationTestInlineModel
            extra = "hello"

        class ValidationTestModelAdmin(ModelAdmin):
            inlines = [ValidationTestInline]

        self.assertIsInvalid(
            ValidationTestModelAdmin, ValidationTestModel,
            "The value of 'extra' must be an integer.",
            'admin.E203',
            invalid_obj=ValidationTestInline)

    def test_valid_case(self):
        class ValidationTestInline(TabularInline):
            model = ValidationTestInlineModel
            extra = 2

        class ValidationTestModelAdmin(ModelAdmin):
            inlines = [ValidationTestInline]

        self.assertIsValid(ValidationTestModelAdmin, ValidationTestModel)


class MaxNumCheckTests(CheckTestCase):

    def test_not_integer(self):
        class ValidationTestInline(TabularInline):
            model = ValidationTestInlineModel
            max_num = "hello"

        class ValidationTestModelAdmin(ModelAdmin):
            inlines = [ValidationTestInline]

        self.assertIsInvalid(
            ValidationTestModelAdmin, ValidationTestModel,
            "The value of 'max_num' must be an integer.",
            'admin.E204',
            invalid_obj=ValidationTestInline)

    def test_valid_case(self):
        class ValidationTestInline(TabularInline):
            model = ValidationTestInlineModel
            max_num = 2

        class ValidationTestModelAdmin(ModelAdmin):
            inlines = [ValidationTestInline]

        self.assertIsValid(ValidationTestModelAdmin, ValidationTestModel)


class MinNumCheckTests(CheckTestCase):

    def test_not_integer(self):
        class ValidationTestInline(TabularInline):
            model = ValidationTestInlineModel
            min_num = "hello"

        class ValidationTestModelAdmin(ModelAdmin):
            inlines = [ValidationTestInline]

        self.assertIsInvalid(
            ValidationTestModelAdmin, ValidationTestModel,
            "The value of 'min_num' must be an integer.",
            'admin.E205',
            invalid_obj=ValidationTestInline)

    def test_valid_case(self):
        class ValidationTestInline(TabularInline):
            model = ValidationTestInlineModel
            min_num = 2

        class ValidationTestModelAdmin(ModelAdmin):
            inlines = [ValidationTestInline]

        self.assertIsValid(ValidationTestModelAdmin, ValidationTestModel)


class FormsetCheckTests(CheckTestCase):

    def test_invalid_type(self):
        class FakeFormSet(object):
            pass

        class ValidationTestInline(TabularInline):
            model = ValidationTestInlineModel
            formset = FakeFormSet

        class ValidationTestModelAdmin(ModelAdmin):
            inlines = [ValidationTestInline]

        self.assertIsInvalid(
            ValidationTestModelAdmin, ValidationTestModel,
            "The value of 'formset' must inherit from 'BaseModelFormSet'.",
            'admin.E206',
            invalid_obj=ValidationTestInline)

    def test_valid_case(self):
        class RealModelFormSet(BaseModelFormSet):
            pass

        class ValidationTestInline(TabularInline):
            model = ValidationTestInlineModel
            formset = RealModelFormSet

        class ValidationTestModelAdmin(ModelAdmin):
            inlines = [ValidationTestInline]

        self.assertIsValid(ValidationTestModelAdmin, ValidationTestModel)


class ListDisplayEditableTests(CheckTestCase):
    def test_list_display_links_is_none(self):
        """
        list_display and list_editable can contain the same values
        when list_display_links is None
        """
        class ProductAdmin(ModelAdmin):
            list_display = ['name', 'slug', 'pub_date']
            list_editable = list_display
            list_display_links = None
        self.assertIsValid(ProductAdmin, ValidationTestModel)

    def test_list_display_first_item_same_as_list_editable_first_item(self):
        """
        The first item in list_display can be the same as the first in
        list_editable.
        """
        class ProductAdmin(ModelAdmin):
            list_display = ['name', 'slug', 'pub_date']
            list_editable = ['name', 'slug']
            list_display_links = ['pub_date']
        self.assertIsValid(ProductAdmin, ValidationTestModel)

    def test_list_display_first_item_in_list_editable(self):
        """
        The first item in list_display can be in list_editable as long as
        list_display_links is defined.
        """
        class ProductAdmin(ModelAdmin):
            list_display = ['name', 'slug', 'pub_date']
            list_editable = ['slug', 'name']
            list_display_links = ['pub_date']
        self.assertIsValid(ProductAdmin, ValidationTestModel)

    def test_list_display_first_item_same_as_list_editable_no_list_display_links(self):
        """
        The first item in list_display cannot be the same as the first item
        in list_editable if list_display_links is not defined.
        """
        class ProductAdmin(ModelAdmin):
            list_display = ['name']
            list_editable = ['name']
        self.assertIsInvalid(
            ProductAdmin, ValidationTestModel,
            "The value of 'list_editable[0]' refers to the first field "
            "in 'list_display' ('name'), which cannot be used unless "
            "'list_display_links' is set.",
            id='admin.E124',
        )

    def test_list_display_first_item_in_list_editable_no_list_display_links(self):
        """
        The first item in list_display cannot be in list_editable if
        list_display_links isn't defined.
        """
        class ProductAdmin(ModelAdmin):
            list_display = ['name', 'slug', 'pub_date']
            list_editable = ['slug', 'name']
        self.assertIsInvalid(
            ProductAdmin, ValidationTestModel,
            "The value of 'list_editable[1]' refers to the first field "
            "in 'list_display' ('name'), which cannot be used unless "
            "'list_display_links' is set.",
            id='admin.E124',
        )


class ModelAdminPermissionTests(SimpleTestCase):

    class MockUser(object):
        def has_module_perms(self, app_label):
            if app_label == "modeladmin":
                return True
            return False

    class MockAddUser(MockUser):
        def has_perm(self, perm):
            if perm == "modeladmin.add_band":
                return True
            return False

    class MockChangeUser(MockUser):
        def has_perm(self, perm):
            if perm == "modeladmin.change_band":
                return True
            return False

    class MockDeleteUser(MockUser):
        def has_perm(self, perm):
            if perm == "modeladmin.delete_band":
                return True
            return False

    def test_has_add_permission(self):
        """
        Ensure that has_add_permission returns True for users who can add
        objects and False for users who can't.
        """
        ma = ModelAdmin(Band, AdminSite())
        request = MockRequest()
        request.user = self.MockAddUser()
        self.assertTrue(ma.has_add_permission(request))
        request.user = self.MockChangeUser()
        self.assertFalse(ma.has_add_permission(request))
        request.user = self.MockDeleteUser()
        self.assertFalse(ma.has_add_permission(request))

    def test_has_change_permission(self):
        """
        Ensure that has_change_permission returns True for users who can edit
        objects and False for users who can't.
        """
        ma = ModelAdmin(Band, AdminSite())
        request = MockRequest()
        request.user = self.MockAddUser()
        self.assertFalse(ma.has_change_permission(request))
        request.user = self.MockChangeUser()
        self.assertTrue(ma.has_change_permission(request))
        request.user = self.MockDeleteUser()
        self.assertFalse(ma.has_change_permission(request))

    def test_has_delete_permission(self):
        """
        Ensure that has_delete_permission returns True for users who can delete
        objects and False for users who can't.
        """
        ma = ModelAdmin(Band, AdminSite())
        request = MockRequest()
        request.user = self.MockAddUser()
        self.assertFalse(ma.has_delete_permission(request))
        request.user = self.MockChangeUser()
        self.assertFalse(ma.has_delete_permission(request))
        request.user = self.MockDeleteUser()
        self.assertTrue(ma.has_delete_permission(request))

    def test_has_module_permission(self):
        """
        Ensure that has_module_permission returns True for users who have any
        permission for the module and False for users who don't.
        """
        ma = ModelAdmin(Band, AdminSite())
        request = MockRequest()
        request.user = self.MockAddUser()
        self.assertTrue(ma.has_module_permission(request))
        request.user = self.MockChangeUser()
        self.assertTrue(ma.has_module_permission(request))
        request.user = self.MockDeleteUser()
        self.assertTrue(ma.has_module_permission(request))

        original_app_label = ma.opts.app_label
        ma.opts.app_label = 'anotherapp'
        try:
            request.user = self.MockAddUser()
            self.assertFalse(ma.has_module_permission(request))
            request.user = self.MockChangeUser()
            self.assertFalse(ma.has_module_permission(request))
            request.user = self.MockDeleteUser()
            self.assertFalse(ma.has_module_permission(request))
        finally:
            ma.opts.app_label = original_app_label
