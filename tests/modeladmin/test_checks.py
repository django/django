from django import forms
from django.contrib.admin import BooleanFieldListFilter, SimpleListFilter
from django.contrib.admin.options import VERTICAL, ModelAdmin, TabularInline
from django.contrib.admin.sites import AdminSite
from django.core.checks import Error
from django.forms.models import BaseModelFormSet
from django.test import SimpleTestCase

from .models import Band, ValidationTestInlineModel, ValidationTestModel


class CheckTestCase(SimpleTestCase):

    def assertIsInvalid(self, model_admin, model, msg, id=None, hint=None, invalid_obj=None):
        invalid_obj = invalid_obj or model_admin
        admin_obj = model_admin(model, AdminSite())
        self.assertEqual(admin_obj.check(), [Error(msg, hint=hint, obj=invalid_obj, id=id)])

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
        self.assertRegex(error.msg, msg)

    def assertIsValid(self, model_admin, model):
        admin_obj = model_admin(model, AdminSite())
        self.assertEqual(admin_obj.check(), [])


class RawIdCheckTests(CheckTestCase):

    def test_not_iterable(self):
        class TestModelAdmin(ModelAdmin):
            raw_id_fields = 10

        self.assertIsInvalid(
            TestModelAdmin, ValidationTestModel,
            "The value of 'raw_id_fields' must be a list or tuple.",
            'admin.E001'
        )

    def test_missing_field(self):
        class TestModelAdmin(ModelAdmin):
            raw_id_fields = ('non_existent_field',)

        self.assertIsInvalid(
            TestModelAdmin, ValidationTestModel,
            "The value of 'raw_id_fields[0]' refers to 'non_existent_field', "
            "which is not an attribute of 'modeladmin.ValidationTestModel'.",
            'admin.E002'
        )

    def test_invalid_field_type(self):
        class TestModelAdmin(ModelAdmin):
            raw_id_fields = ('name',)

        self.assertIsInvalid(
            TestModelAdmin, ValidationTestModel,
            "The value of 'raw_id_fields[0]' must be a foreign key or a "
            "many-to-many field.",
            'admin.E003'
        )

    def test_valid_case(self):
        class TestModelAdmin(ModelAdmin):
            raw_id_fields = ('users',)

        self.assertIsValid(TestModelAdmin, ValidationTestModel)


class FieldsetsCheckTests(CheckTestCase):

    def test_valid_case(self):
        class TestModelAdmin(ModelAdmin):
            fieldsets = (('General', {'fields': ('name',)}),)

        self.assertIsValid(TestModelAdmin, ValidationTestModel)

    def test_not_iterable(self):
        class TestModelAdmin(ModelAdmin):
            fieldsets = 10

        self.assertIsInvalid(
            TestModelAdmin, ValidationTestModel,
            "The value of 'fieldsets' must be a list or tuple.",
            'admin.E007'
        )

    def test_non_iterable_item(self):
        class TestModelAdmin(ModelAdmin):
            fieldsets = ({},)

        self.assertIsInvalid(
            TestModelAdmin, ValidationTestModel,
            "The value of 'fieldsets[0]' must be a list or tuple.",
            'admin.E008'
        )

    def test_item_not_a_pair(self):
        class TestModelAdmin(ModelAdmin):
            fieldsets = ((),)

        self.assertIsInvalid(
            TestModelAdmin, ValidationTestModel,
            "The value of 'fieldsets[0]' must be of length 2.",
            'admin.E009'
        )

    def test_second_element_of_item_not_a_dict(self):
        class TestModelAdmin(ModelAdmin):
            fieldsets = (('General', ()),)

        self.assertIsInvalid(
            TestModelAdmin, ValidationTestModel,
            "The value of 'fieldsets[0][1]' must be a dictionary.",
            'admin.E010'
        )

    def test_missing_fields_key(self):
        class TestModelAdmin(ModelAdmin):
            fieldsets = (('General', {}),)

        self.assertIsInvalid(
            TestModelAdmin, ValidationTestModel,
            "The value of 'fieldsets[0][1]' must contain the key 'fields'.",
            'admin.E011'
        )

        class TestModelAdmin(ModelAdmin):
            fieldsets = (('General', {'fields': ('name',)}),)

        self.assertIsValid(TestModelAdmin, ValidationTestModel)

    def test_specified_both_fields_and_fieldsets(self):
        class TestModelAdmin(ModelAdmin):
            fieldsets = (('General', {'fields': ('name',)}),)
            fields = ['name']

        self.assertIsInvalid(
            TestModelAdmin, ValidationTestModel,
            "Both 'fieldsets' and 'fields' are specified.",
            'admin.E005'
        )

    def test_duplicate_fields(self):
        class TestModelAdmin(ModelAdmin):
            fieldsets = [(None, {'fields': ['name', 'name']})]

        self.assertIsInvalid(
            TestModelAdmin, ValidationTestModel,
            "There are duplicate field(s) in 'fieldsets[0][1]'.",
            'admin.E012'
        )

    def test_fieldsets_with_custom_form_validation(self):
        class BandAdmin(ModelAdmin):
            fieldsets = (('Band', {'fields': ('name',)}),)

        self.assertIsValid(BandAdmin, Band)


class FieldsCheckTests(CheckTestCase):

    def test_duplicate_fields_in_fields(self):
        class TestModelAdmin(ModelAdmin):
            fields = ['name', 'name']

        self.assertIsInvalid(
            TestModelAdmin, ValidationTestModel,
            "The value of 'fields' contains duplicate field(s).",
            'admin.E006'
        )

    def test_inline(self):
        class ValidationTestInline(TabularInline):
            model = ValidationTestInlineModel
            fields = 10

        class TestModelAdmin(ModelAdmin):
            inlines = [ValidationTestInline]

        self.assertIsInvalid(
            TestModelAdmin, ValidationTestModel,
            "The value of 'fields' must be a list or tuple.",
            'admin.E004',
            invalid_obj=ValidationTestInline
        )


class FormCheckTests(CheckTestCase):

    def test_invalid_type(self):
        class FakeForm:
            pass

        class TestModelAdmin(ModelAdmin):
            form = FakeForm

        self.assertIsInvalid(
            TestModelAdmin, ValidationTestModel,
            "The value of 'form' must inherit from 'BaseModelForm'.",
            'admin.E016'
        )

    def test_fieldsets_with_custom_form_validation(self):

        class BandAdmin(ModelAdmin):
            fieldsets = (('Band', {'fields': ('name',)}),)

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
        class TestModelAdmin(ModelAdmin):
            filter_vertical = 10

        self.assertIsInvalid(
            TestModelAdmin, ValidationTestModel,
            "The value of 'filter_vertical' must be a list or tuple.",
            'admin.E017'
        )

    def test_missing_field(self):
        class TestModelAdmin(ModelAdmin):
            filter_vertical = ('non_existent_field',)

        self.assertIsInvalid(
            TestModelAdmin, ValidationTestModel,
            "The value of 'filter_vertical[0]' refers to 'non_existent_field', "
            "which is not an attribute of 'modeladmin.ValidationTestModel'.",
            'admin.E019'
        )

    def test_invalid_field_type(self):
        class TestModelAdmin(ModelAdmin):
            filter_vertical = ('name',)

        self.assertIsInvalid(
            TestModelAdmin, ValidationTestModel,
            "The value of 'filter_vertical[0]' must be a many-to-many field.",
            'admin.E020'
        )

    def test_valid_case(self):
        class TestModelAdmin(ModelAdmin):
            filter_vertical = ('users',)

        self.assertIsValid(TestModelAdmin, ValidationTestModel)


class FilterHorizontalCheckTests(CheckTestCase):

    def test_not_iterable(self):
        class TestModelAdmin(ModelAdmin):
            filter_horizontal = 10

        self.assertIsInvalid(
            TestModelAdmin, ValidationTestModel,
            "The value of 'filter_horizontal' must be a list or tuple.",
            'admin.E018'
        )

    def test_missing_field(self):
        class TestModelAdmin(ModelAdmin):
            filter_horizontal = ('non_existent_field',)

        self.assertIsInvalid(
            TestModelAdmin, ValidationTestModel,
            "The value of 'filter_horizontal[0]' refers to 'non_existent_field', "
            "which is not an attribute of 'modeladmin.ValidationTestModel'.",
            'admin.E019'
        )

    def test_invalid_field_type(self):
        class TestModelAdmin(ModelAdmin):
            filter_horizontal = ('name',)

        self.assertIsInvalid(
            TestModelAdmin, ValidationTestModel,
            "The value of 'filter_horizontal[0]' must be a many-to-many field.",
            'admin.E020'
        )

    def test_valid_case(self):
        class TestModelAdmin(ModelAdmin):
            filter_horizontal = ('users',)

        self.assertIsValid(TestModelAdmin, ValidationTestModel)


class RadioFieldsCheckTests(CheckTestCase):

    def test_not_dictionary(self):

        class TestModelAdmin(ModelAdmin):
            radio_fields = ()

        self.assertIsInvalid(
            TestModelAdmin, ValidationTestModel,
            "The value of 'radio_fields' must be a dictionary.",
            'admin.E021'
        )

    def test_missing_field(self):
        class TestModelAdmin(ModelAdmin):
            radio_fields = {'non_existent_field': VERTICAL}

        self.assertIsInvalid(
            TestModelAdmin, ValidationTestModel,
            "The value of 'radio_fields' refers to 'non_existent_field', "
            "which is not an attribute of 'modeladmin.ValidationTestModel'.",
            'admin.E022'
        )

    def test_invalid_field_type(self):
        class TestModelAdmin(ModelAdmin):
            radio_fields = {'name': VERTICAL}

        self.assertIsInvalid(
            TestModelAdmin, ValidationTestModel,
            "The value of 'radio_fields' refers to 'name', which is not an instance "
            "of ForeignKey, and does not have a 'choices' definition.",
            'admin.E023'
        )

    def test_invalid_value(self):
        class TestModelAdmin(ModelAdmin):
            radio_fields = {'state': None}

        self.assertIsInvalid(
            TestModelAdmin, ValidationTestModel,
            "The value of 'radio_fields[\"state\"]' must be either admin.HORIZONTAL or admin.VERTICAL.",
            'admin.E024'
        )

    def test_valid_case(self):
        class TestModelAdmin(ModelAdmin):
            radio_fields = {'state': VERTICAL}

        self.assertIsValid(TestModelAdmin, ValidationTestModel)


class PrepopulatedFieldsCheckTests(CheckTestCase):

    def test_not_list_or_tuple(self):
        class TestModelAdmin(ModelAdmin):
            prepopulated_fields = {'slug': 'test'}

        self.assertIsInvalid(
            TestModelAdmin, ValidationTestModel,
            'The value of \'prepopulated_fields["slug"]\' must be a list '
            'or tuple.',
            'admin.E029'
        )

    def test_not_dictionary(self):
        class TestModelAdmin(ModelAdmin):
            prepopulated_fields = ()

        self.assertIsInvalid(
            TestModelAdmin, ValidationTestModel,
            "The value of 'prepopulated_fields' must be a dictionary.",
            'admin.E026'
        )

    def test_missing_field(self):
        class TestModelAdmin(ModelAdmin):
            prepopulated_fields = {'non_existent_field': ('slug',)}

        self.assertIsInvalid(
            TestModelAdmin, ValidationTestModel,
            "The value of 'prepopulated_fields' refers to 'non_existent_field', "
            "which is not an attribute of 'modeladmin.ValidationTestModel'.",
            'admin.E027'
        )

    def test_missing_field_again(self):
        class TestModelAdmin(ModelAdmin):
            prepopulated_fields = {'slug': ('non_existent_field',)}

        self.assertIsInvalid(
            TestModelAdmin, ValidationTestModel,
            "The value of 'prepopulated_fields[\"slug\"][0]' refers to 'non_existent_field', "
            "which is not an attribute of 'modeladmin.ValidationTestModel'.",
            'admin.E030'
        )

    def test_invalid_field_type(self):
        class TestModelAdmin(ModelAdmin):
            prepopulated_fields = {'users': ('name',)}

        self.assertIsInvalid(
            TestModelAdmin, ValidationTestModel,
            "The value of 'prepopulated_fields' refers to 'users', which must not be "
            "a DateTimeField, a ForeignKey, a OneToOneField, or a ManyToManyField.",
            'admin.E028'
        )

    def test_valid_case(self):
        class TestModelAdmin(ModelAdmin):
            prepopulated_fields = {'slug': ('name',)}

        self.assertIsValid(TestModelAdmin, ValidationTestModel)

    def test_one_to_one_field(self):
        class TestModelAdmin(ModelAdmin):
            prepopulated_fields = {'best_friend': ('name',)}

        self.assertIsInvalid(
            TestModelAdmin, ValidationTestModel,
            "The value of 'prepopulated_fields' refers to 'best_friend', which must not be "
            "a DateTimeField, a ForeignKey, a OneToOneField, or a ManyToManyField.",
            'admin.E028'
        )


class ListDisplayTests(CheckTestCase):

    def test_not_iterable(self):
        class TestModelAdmin(ModelAdmin):
            list_display = 10

        self.assertIsInvalid(
            TestModelAdmin, ValidationTestModel,
            "The value of 'list_display' must be a list or tuple.",
            'admin.E107'
        )

    def test_missing_field(self):
        class TestModelAdmin(ModelAdmin):
            list_display = ('non_existent_field',)

        self.assertIsInvalid(
            TestModelAdmin, ValidationTestModel,
            "The value of 'list_display[0]' refers to 'non_existent_field', "
            "which is not a callable, an attribute of 'TestModelAdmin', "
            "or an attribute or method on 'modeladmin.ValidationTestModel'.",
            'admin.E108'
        )

    def test_invalid_field_type(self):
        class TestModelAdmin(ModelAdmin):
            list_display = ('users',)

        self.assertIsInvalid(
            TestModelAdmin, ValidationTestModel,
            "The value of 'list_display[0]' must not be a ManyToManyField.",
            'admin.E109'
        )

    def test_valid_case(self):
        def a_callable(obj):
            pass

        class TestModelAdmin(ModelAdmin):
            def a_method(self, obj):
                pass
            list_display = ('name', 'decade_published_in', 'a_method', a_callable)

        self.assertIsValid(TestModelAdmin, ValidationTestModel)


class ListDisplayLinksCheckTests(CheckTestCase):

    def test_not_iterable(self):
        class TestModelAdmin(ModelAdmin):
            list_display_links = 10

        self.assertIsInvalid(
            TestModelAdmin, ValidationTestModel,
            "The value of 'list_display_links' must be a list, a tuple, or None.",
            'admin.E110'
        )

    def test_missing_field(self):
        class TestModelAdmin(ModelAdmin):
            list_display_links = ('non_existent_field',)

        self.assertIsInvalid(
            TestModelAdmin, ValidationTestModel, (
                "The value of 'list_display_links[0]' refers to "
                "'non_existent_field', which is not defined in 'list_display'."
            ), 'admin.E111'
        )

    def test_missing_in_list_display(self):
        class TestModelAdmin(ModelAdmin):
            list_display_links = ('name',)

        self.assertIsInvalid(
            TestModelAdmin, ValidationTestModel,
            "The value of 'list_display_links[0]' refers to 'name', which is not defined in 'list_display'.",
            'admin.E111'
        )

    def test_valid_case(self):
        def a_callable(obj):
            pass

        class TestModelAdmin(ModelAdmin):
            def a_method(self, obj):
                pass
            list_display = ('name', 'decade_published_in', 'a_method', a_callable)
            list_display_links = ('name', 'decade_published_in', 'a_method', a_callable)

        self.assertIsValid(TestModelAdmin, ValidationTestModel)

    def test_None_is_valid_case(self):
        class TestModelAdmin(ModelAdmin):
            list_display_links = None

        self.assertIsValid(TestModelAdmin, ValidationTestModel)

    def test_list_display_links_check_skipped_if_get_list_display_overridden(self):
        """
        list_display_links check is skipped if get_list_display() is overridden.
        """
        class TestModelAdmin(ModelAdmin):
            list_display_links = ['name', 'subtitle']

            def get_list_display(self, request):
                pass

        self.assertIsValid(TestModelAdmin, ValidationTestModel)

    def test_list_display_link_checked_for_list_tuple_if_get_list_display_overridden(self):
        """
        list_display_links is checked for list/tuple/None even if
        get_list_display() is overridden.
        """
        class TestModelAdmin(ModelAdmin):
            list_display_links = 'non-list/tuple'

            def get_list_display(self, request):
                pass

        self.assertIsInvalid(
            TestModelAdmin, ValidationTestModel,
            "The value of 'list_display_links' must be a list, a tuple, or None.",
            'admin.E110'
        )


class ListFilterTests(CheckTestCase):

    def test_list_filter_validation(self):
        class TestModelAdmin(ModelAdmin):
            list_filter = 10

        self.assertIsInvalid(
            TestModelAdmin, ValidationTestModel,
            "The value of 'list_filter' must be a list or tuple.",
            'admin.E112'
        )

    def test_missing_field(self):
        class TestModelAdmin(ModelAdmin):
            list_filter = ('non_existent_field',)

        self.assertIsInvalid(
            TestModelAdmin, ValidationTestModel,
            "The value of 'list_filter[0]' refers to 'non_existent_field', "
            "which does not refer to a Field.",
            'admin.E116'
        )

    def test_not_filter(self):
        class RandomClass:
            pass

        class TestModelAdmin(ModelAdmin):
            list_filter = (RandomClass,)

        self.assertIsInvalid(
            TestModelAdmin, ValidationTestModel,
            "The value of 'list_filter[0]' must inherit from 'ListFilter'.",
            'admin.E113')

    def test_not_filter_again(self):
        class RandomClass:
            pass

        class TestModelAdmin(ModelAdmin):
            list_filter = (('is_active', RandomClass),)

        self.assertIsInvalid(
            TestModelAdmin, ValidationTestModel,
            "The value of 'list_filter[0][1]' must inherit from 'FieldListFilter'.",
            'admin.E115'
        )

    def test_not_filter_again_again(self):
        class AwesomeFilter(SimpleListFilter):
            def get_title(self):
                return 'awesomeness'

            def get_choices(self, request):
                return (('bit', 'A bit awesome'), ('very', 'Very awesome'), )

            def get_queryset(self, cl, qs):
                return qs

        class TestModelAdmin(ModelAdmin):
            list_filter = (('is_active', AwesomeFilter),)

        self.assertIsInvalid(
            TestModelAdmin, ValidationTestModel,
            "The value of 'list_filter[0][1]' must inherit from 'FieldListFilter'.",
            'admin.E115'
        )

    def test_not_associated_with_field_name(self):
        class TestModelAdmin(ModelAdmin):
            list_filter = (BooleanFieldListFilter,)

        self.assertIsInvalid(
            TestModelAdmin, ValidationTestModel,
            "The value of 'list_filter[0]' must not inherit from 'FieldListFilter'.",
            'admin.E114'
        )

    def test_valid_case(self):
        class AwesomeFilter(SimpleListFilter):
            def get_title(self):
                return 'awesomeness'

            def get_choices(self, request):
                return (('bit', 'A bit awesome'), ('very', 'Very awesome'), )

            def get_queryset(self, cl, qs):
                return qs

        class TestModelAdmin(ModelAdmin):
            list_filter = ('is_active', AwesomeFilter, ('is_active', BooleanFieldListFilter), 'no')

        self.assertIsValid(TestModelAdmin, ValidationTestModel)


class ListPerPageCheckTests(CheckTestCase):

    def test_not_integer(self):
        class TestModelAdmin(ModelAdmin):
            list_per_page = 'hello'

        self.assertIsInvalid(
            TestModelAdmin, ValidationTestModel,
            "The value of 'list_per_page' must be an integer.",
            'admin.E118'
        )

    def test_valid_case(self):
        class TestModelAdmin(ModelAdmin):
            list_per_page = 100

        self.assertIsValid(TestModelAdmin, ValidationTestModel)


class ListMaxShowAllCheckTests(CheckTestCase):

    def test_not_integer(self):
        class TestModelAdmin(ModelAdmin):
            list_max_show_all = 'hello'

        self.assertIsInvalid(
            TestModelAdmin, ValidationTestModel,
            "The value of 'list_max_show_all' must be an integer.",
            'admin.E119'
        )

    def test_valid_case(self):
        class TestModelAdmin(ModelAdmin):
            list_max_show_all = 200

        self.assertIsValid(TestModelAdmin, ValidationTestModel)


class SearchFieldsCheckTests(CheckTestCase):

    def test_not_iterable(self):
        class TestModelAdmin(ModelAdmin):
            search_fields = 10

        self.assertIsInvalid(
            TestModelAdmin, ValidationTestModel,
            "The value of 'search_fields' must be a list or tuple.",
            'admin.E126'
        )


class DateHierarchyCheckTests(CheckTestCase):

    def test_missing_field(self):
        class TestModelAdmin(ModelAdmin):
            date_hierarchy = 'non_existent_field'

        self.assertIsInvalid(
            TestModelAdmin, ValidationTestModel,
            "The value of 'date_hierarchy' refers to 'non_existent_field', "
            "which does not refer to a Field.",
            'admin.E127'
        )

    def test_invalid_field_type(self):
        class TestModelAdmin(ModelAdmin):
            date_hierarchy = 'name'

        self.assertIsInvalid(
            TestModelAdmin, ValidationTestModel,
            "The value of 'date_hierarchy' must be a DateField or DateTimeField.",
            'admin.E128'
        )

    def test_valid_case(self):
        class TestModelAdmin(ModelAdmin):
            date_hierarchy = 'pub_date'

        self.assertIsValid(TestModelAdmin, ValidationTestModel)

    def test_related_valid_case(self):
        class TestModelAdmin(ModelAdmin):
            date_hierarchy = 'band__sign_date'

        self.assertIsValid(TestModelAdmin, ValidationTestModel)

    def test_related_invalid_field_type(self):
        class TestModelAdmin(ModelAdmin):
            date_hierarchy = 'band__name'

        self.assertIsInvalid(
            TestModelAdmin, ValidationTestModel,
            "The value of 'date_hierarchy' must be a DateField or DateTimeField.",
            'admin.E128'
        )


class OrderingCheckTests(CheckTestCase):

    def test_not_iterable(self):
        class TestModelAdmin(ModelAdmin):
            ordering = 10

        self.assertIsInvalid(
            TestModelAdmin, ValidationTestModel,
            "The value of 'ordering' must be a list or tuple.",
            'admin.E031'
        )

        class TestModelAdmin(ModelAdmin):
            ordering = ('non_existent_field',)

        self.assertIsInvalid(
            TestModelAdmin, ValidationTestModel,
            "The value of 'ordering[0]' refers to 'non_existent_field', "
            "which is not an attribute of 'modeladmin.ValidationTestModel'.",
            'admin.E033'
        )

    def test_random_marker_not_alone(self):
        class TestModelAdmin(ModelAdmin):
            ordering = ('?', 'name')

        self.assertIsInvalid(
            TestModelAdmin, ValidationTestModel,
            "The value of 'ordering' has the random ordering marker '?', but contains "
            "other fields as well.",
            'admin.E032',
            hint='Either remove the "?", or remove the other fields.'
        )

    def test_valid_random_marker_case(self):
        class TestModelAdmin(ModelAdmin):
            ordering = ('?',)

        self.assertIsValid(TestModelAdmin, ValidationTestModel)

    def test_valid_complex_case(self):
        class TestModelAdmin(ModelAdmin):
            ordering = ('band__name',)

        self.assertIsValid(TestModelAdmin, ValidationTestModel)

    def test_valid_case(self):
        class TestModelAdmin(ModelAdmin):
            ordering = ('name', 'pk')

        self.assertIsValid(TestModelAdmin, ValidationTestModel)


class ListSelectRelatedCheckTests(CheckTestCase):

    def test_invalid_type(self):
        class TestModelAdmin(ModelAdmin):
            list_select_related = 1

        self.assertIsInvalid(
            TestModelAdmin, ValidationTestModel,
            "The value of 'list_select_related' must be a boolean, tuple or list.",
            'admin.E117'
        )

    def test_valid_case(self):
        class TestModelAdmin(ModelAdmin):
            list_select_related = False

        self.assertIsValid(TestModelAdmin, ValidationTestModel)


class SaveAsCheckTests(CheckTestCase):

    def test_not_boolean(self):
        class TestModelAdmin(ModelAdmin):
            save_as = 1

        self.assertIsInvalid(
            TestModelAdmin, ValidationTestModel,
            "The value of 'save_as' must be a boolean.",
            'admin.E101'
        )

    def test_valid_case(self):
        class TestModelAdmin(ModelAdmin):
            save_as = True

        self.assertIsValid(TestModelAdmin, ValidationTestModel)


class SaveOnTopCheckTests(CheckTestCase):

    def test_not_boolean(self):
        class TestModelAdmin(ModelAdmin):
            save_on_top = 1

        self.assertIsInvalid(
            TestModelAdmin, ValidationTestModel,
            "The value of 'save_on_top' must be a boolean.",
            'admin.E102'
        )

    def test_valid_case(self):
        class TestModelAdmin(ModelAdmin):
            save_on_top = True

        self.assertIsValid(TestModelAdmin, ValidationTestModel)


class InlinesCheckTests(CheckTestCase):

    def test_not_iterable(self):
        class TestModelAdmin(ModelAdmin):
            inlines = 10

        self.assertIsInvalid(
            TestModelAdmin, ValidationTestModel,
            "The value of 'inlines' must be a list or tuple.",
            'admin.E103'
        )

    def test_not_model_admin(self):
        class ValidationTestInline:
            pass

        class TestModelAdmin(ModelAdmin):
            inlines = [ValidationTestInline]

        self.assertIsInvalidRegexp(
            TestModelAdmin, ValidationTestModel,
            r"'.*\.ValidationTestInline' must inherit from 'InlineModelAdmin'\.",
            'admin.E104'
        )

    def test_missing_model_field(self):
        class ValidationTestInline(TabularInline):
            pass

        class TestModelAdmin(ModelAdmin):
            inlines = [ValidationTestInline]

        self.assertIsInvalidRegexp(
            TestModelAdmin, ValidationTestModel,
            r"'.*\.ValidationTestInline' must have a 'model' attribute\.",
            'admin.E105')

    def test_invalid_model_type(self):
        class SomethingBad:
            pass

        class ValidationTestInline(TabularInline):
            model = SomethingBad

        class TestModelAdmin(ModelAdmin):
            inlines = [ValidationTestInline]

        self.assertIsInvalidRegexp(
            TestModelAdmin, ValidationTestModel,
            r"The value of '.*\.ValidationTestInline.model' must be a Model\.",
            'admin.E106'
        )

    def test_valid_case(self):
        class ValidationTestInline(TabularInline):
            model = ValidationTestInlineModel

        class TestModelAdmin(ModelAdmin):
            inlines = [ValidationTestInline]

        self.assertIsValid(TestModelAdmin, ValidationTestModel)


class FkNameCheckTests(CheckTestCase):

    def test_missing_field(self):
        class ValidationTestInline(TabularInline):
            model = ValidationTestInlineModel
            fk_name = 'non_existent_field'

        class TestModelAdmin(ModelAdmin):
            inlines = [ValidationTestInline]

        self.assertIsInvalid(
            TestModelAdmin, ValidationTestModel,
            "'modeladmin.ValidationTestInlineModel' has no field named 'non_existent_field'.",
            'admin.E202',
            invalid_obj=ValidationTestInline
        )

    def test_valid_case(self):
        class ValidationTestInline(TabularInline):
            model = ValidationTestInlineModel
            fk_name = 'parent'

        class TestModelAdmin(ModelAdmin):
            inlines = [ValidationTestInline]

        self.assertIsValid(TestModelAdmin, ValidationTestModel)


class ExtraCheckTests(CheckTestCase):

    def test_not_integer(self):
        class ValidationTestInline(TabularInline):
            model = ValidationTestInlineModel
            extra = 'hello'

        class TestModelAdmin(ModelAdmin):
            inlines = [ValidationTestInline]

        self.assertIsInvalid(
            TestModelAdmin, ValidationTestModel,
            "The value of 'extra' must be an integer.",
            'admin.E203',
            invalid_obj=ValidationTestInline
        )

    def test_valid_case(self):
        class ValidationTestInline(TabularInline):
            model = ValidationTestInlineModel
            extra = 2

        class TestModelAdmin(ModelAdmin):
            inlines = [ValidationTestInline]

        self.assertIsValid(TestModelAdmin, ValidationTestModel)


class MaxNumCheckTests(CheckTestCase):

    def test_not_integer(self):
        class ValidationTestInline(TabularInline):
            model = ValidationTestInlineModel
            max_num = 'hello'

        class TestModelAdmin(ModelAdmin):
            inlines = [ValidationTestInline]

        self.assertIsInvalid(
            TestModelAdmin, ValidationTestModel,
            "The value of 'max_num' must be an integer.",
            'admin.E204',
            invalid_obj=ValidationTestInline
        )

    def test_valid_case(self):
        class ValidationTestInline(TabularInline):
            model = ValidationTestInlineModel
            max_num = 2

        class TestModelAdmin(ModelAdmin):
            inlines = [ValidationTestInline]

        self.assertIsValid(TestModelAdmin, ValidationTestModel)


class MinNumCheckTests(CheckTestCase):

    def test_not_integer(self):
        class ValidationTestInline(TabularInline):
            model = ValidationTestInlineModel
            min_num = 'hello'

        class TestModelAdmin(ModelAdmin):
            inlines = [ValidationTestInline]

        self.assertIsInvalid(
            TestModelAdmin, ValidationTestModel,
            "The value of 'min_num' must be an integer.",
            'admin.E205',
            invalid_obj=ValidationTestInline
        )

    def test_valid_case(self):
        class ValidationTestInline(TabularInline):
            model = ValidationTestInlineModel
            min_num = 2

        class TestModelAdmin(ModelAdmin):
            inlines = [ValidationTestInline]

        self.assertIsValid(TestModelAdmin, ValidationTestModel)


class FormsetCheckTests(CheckTestCase):

    def test_invalid_type(self):
        class FakeFormSet:
            pass

        class ValidationTestInline(TabularInline):
            model = ValidationTestInlineModel
            formset = FakeFormSet

        class TestModelAdmin(ModelAdmin):
            inlines = [ValidationTestInline]

        self.assertIsInvalid(
            TestModelAdmin, ValidationTestModel,
            "The value of 'formset' must inherit from 'BaseModelFormSet'.",
            'admin.E206',
            invalid_obj=ValidationTestInline
        )

    def test_valid_case(self):
        class RealModelFormSet(BaseModelFormSet):
            pass

        class ValidationTestInline(TabularInline):
            model = ValidationTestInlineModel
            formset = RealModelFormSet

        class TestModelAdmin(ModelAdmin):
            inlines = [ValidationTestInline]

        self.assertIsValid(TestModelAdmin, ValidationTestModel)


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

    def test_both_list_editable_and_list_display_links(self):
        class ProductAdmin(ModelAdmin):
            list_editable = ('name',)
            list_display = ('name',)
            list_display_links = ('name',)
        self.assertIsInvalid(
            ProductAdmin, ValidationTestModel,
            "The value of 'name' cannot be in both 'list_editable' and "
            "'list_display_links'.",
            id='admin.E123',
        )
