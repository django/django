from django import forms
from django.contrib import admin
from django.contrib.admin import AdminSite
from django.contrib.contenttypes.admin import GenericStackedInline
from django.core import checks
from django.test import SimpleTestCase, override_settings

from .models import (
    Album, Author, Book, City, Influence, Song, State, TwoAlbumFKAndAnE,
)


class SongForm(forms.ModelForm):
    pass


class ValidFields(admin.ModelAdmin):
    form = SongForm
    fields = ['title']


class ValidFormFieldsets(admin.ModelAdmin):
    def get_form(self, request, obj=None, **kwargs):
        class ExtraFieldForm(SongForm):
            name = forms.CharField(max_length=50)
        return ExtraFieldForm

    fieldsets = (
        (None, {
            'fields': ('name',),
        }),
    )


class MyAdmin(admin.ModelAdmin):
    def check(self, **kwargs):
        return ['error!']


@override_settings(
    SILENCED_SYSTEM_CHECKS=['fields.W342'],  # ForeignKey(unique=True)
    INSTALLED_APPS=['django.contrib.auth', 'django.contrib.contenttypes', 'admin_checks']
)
class SystemChecksTestCase(SimpleTestCase):

    def test_checks_are_performed(self):
        admin.site.register(Song, MyAdmin)
        try:
            errors = checks.run_checks()
            expected = ['error!']
            self.assertEqual(errors, expected)
        finally:
            admin.site.unregister(Song)

    @override_settings(INSTALLED_APPS=['django.contrib.admin'])
    def test_contenttypes_dependency(self):
        errors = admin.checks.check_dependencies()
        expected = [
            checks.Error(
                "'django.contrib.contenttypes' must be in "
                "INSTALLED_APPS in order to use the admin application.",
                id="admin.E401",
            )
        ]
        self.assertEqual(errors, expected)

    @override_settings(TEMPLATES=[])
    def test_no_template_engines(self):
        self.assertEqual(admin.checks.check_dependencies(), [])

    @override_settings(
        INSTALLED_APPS=[
            'django.contrib.admin',
            'django.contrib.auth',
            'django.contrib.contenttypes',
        ],
        TEMPLATES=[{
            'BACKEND': 'django.template.backends.django.DjangoTemplates',
            'DIRS': [],
            'APP_DIRS': True,
            'OPTIONS': {
                'context_processors': [],
            },
        }],
    )
    def test_auth_contextprocessor_dependency(self):
        errors = admin.checks.check_dependencies()
        expected = [
            checks.Error(
                "'django.contrib.auth.context_processors.auth' must be in "
                "TEMPLATES in order to use the admin application.",
                id="admin.E402",
            )
        ]
        self.assertEqual(errors, expected)

    def test_custom_adminsite(self):
        class CustomAdminSite(admin.AdminSite):
            pass

        custom_site = CustomAdminSite()
        custom_site.register(Song, MyAdmin)
        try:
            errors = checks.run_checks()
            expected = ['error!']
            self.assertEqual(errors, expected)
        finally:
            custom_site.unregister(Song)

    def test_allows_checks_relying_on_other_modeladmins(self):
        class MyBookAdmin(admin.ModelAdmin):
            def check(self, **kwargs):
                errors = super().check(**kwargs)
                author_admin = self.admin_site._registry.get(Author)
                if author_admin is None:
                    errors.append('AuthorAdmin missing!')
                return errors

        class MyAuthorAdmin(admin.ModelAdmin):
            pass

        admin.site.register(Book, MyBookAdmin)
        admin.site.register(Author, MyAuthorAdmin)
        try:
            self.assertEqual(admin.site.check(None), [])
        finally:
            admin.site.unregister(Book)
            admin.site.unregister(Author)

    def test_field_name_not_in_list_display(self):
        class SongAdmin(admin.ModelAdmin):
            list_editable = ["original_release"]

        errors = SongAdmin(Song, AdminSite()).check()
        expected = [
            checks.Error(
                "The value of 'list_editable[0]' refers to 'original_release', "
                "which is not contained in 'list_display'.",
                obj=SongAdmin,
                id='admin.E122',
            )
        ]
        self.assertEqual(errors, expected)

    def test_list_editable_not_a_list_or_tuple(self):
        class SongAdmin(admin.ModelAdmin):
            list_editable = 'test'

        self.assertEqual(SongAdmin(Song, AdminSite()).check(), [
            checks.Error(
                "The value of 'list_editable' must be a list or tuple.",
                obj=SongAdmin,
                id='admin.E120',
            )
        ])

    def test_list_editable_missing_field(self):
        class SongAdmin(admin.ModelAdmin):
            list_editable = ('test',)

        self.assertEqual(SongAdmin(Song, AdminSite()).check(), [
            checks.Error(
                "The value of 'list_editable[0]' refers to 'test', which is "
                "not an attribute of 'admin_checks.Song'.",
                obj=SongAdmin,
                id='admin.E121',
            )
        ])

    def test_readonly_and_editable(self):
        class SongAdmin(admin.ModelAdmin):
            readonly_fields = ["original_release"]
            list_display = ["pk", "original_release"]
            list_editable = ["original_release"]
            fieldsets = [
                (None, {
                    "fields": ["title", "original_release"],
                }),
            ]
        errors = SongAdmin(Song, AdminSite()).check()
        expected = [
            checks.Error(
                "The value of 'list_editable[0]' refers to 'original_release', "
                "which is not editable through the admin.",
                obj=SongAdmin,
                id='admin.E125',
            )
        ]
        self.assertEqual(errors, expected)

    def test_editable(self):
        class SongAdmin(admin.ModelAdmin):
            list_display = ["pk", "title"]
            list_editable = ["title"]
            fieldsets = [
                (None, {
                    "fields": ["title", "original_release"],
                }),
            ]

        errors = SongAdmin(Song, AdminSite()).check()
        self.assertEqual(errors, [])

    def test_custom_modelforms_with_fields_fieldsets(self):
        """
        # Regression test for #8027: custom ModelForms with fields/fieldsets
        """
        errors = ValidFields(Song, AdminSite()).check()
        self.assertEqual(errors, [])

    def test_custom_get_form_with_fieldsets(self):
        """
        The fieldsets checks are skipped when the ModelAdmin.get_form() method
        is overridden.
        """
        errors = ValidFormFieldsets(Song, AdminSite()).check()
        self.assertEqual(errors, [])

    def test_fieldsets_fields_non_tuple(self):
        """
        The first fieldset's fields must be a list/tuple.
        """
        class NotATupleAdmin(admin.ModelAdmin):
            list_display = ["pk", "title"]
            list_editable = ["title"]
            fieldsets = [
                (None, {
                    "fields": "title"  # not a tuple
                }),
            ]

        errors = NotATupleAdmin(Song, AdminSite()).check()
        expected = [
            checks.Error(
                "The value of 'fieldsets[0][1]['fields']' must be a list or tuple.",
                obj=NotATupleAdmin,
                id='admin.E008',
            )
        ]
        self.assertEqual(errors, expected)

    def test_nonfirst_fieldset(self):
        """
        The second fieldset's fields must be a list/tuple.
        """
        class NotATupleAdmin(admin.ModelAdmin):
            fieldsets = [
                (None, {
                    "fields": ("title",)
                }),
                ('foo', {
                    "fields": "author"  # not a tuple
                }),
            ]

        errors = NotATupleAdmin(Song, AdminSite()).check()
        expected = [
            checks.Error(
                "The value of 'fieldsets[1][1]['fields']' must be a list or tuple.",
                obj=NotATupleAdmin,
                id='admin.E008',
            )
        ]
        self.assertEqual(errors, expected)

    def test_exclude_values(self):
        """
        Tests for basic system checks of 'exclude' option values (#12689)
        """
        class ExcludedFields1(admin.ModelAdmin):
            exclude = 'foo'

        errors = ExcludedFields1(Book, AdminSite()).check()
        expected = [
            checks.Error(
                "The value of 'exclude' must be a list or tuple.",
                obj=ExcludedFields1,
                id='admin.E014',
            )
        ]
        self.assertEqual(errors, expected)

    def test_exclude_duplicate_values(self):
        class ExcludedFields2(admin.ModelAdmin):
            exclude = ('name', 'name')

        errors = ExcludedFields2(Book, AdminSite()).check()
        expected = [
            checks.Error(
                "The value of 'exclude' contains duplicate field(s).",
                obj=ExcludedFields2,
                id='admin.E015',
            )
        ]
        self.assertEqual(errors, expected)

    def test_exclude_in_inline(self):
        class ExcludedFieldsInline(admin.TabularInline):
            model = Song
            exclude = 'foo'

        class ExcludedFieldsAlbumAdmin(admin.ModelAdmin):
            model = Album
            inlines = [ExcludedFieldsInline]

        errors = ExcludedFieldsAlbumAdmin(Album, AdminSite()).check()
        expected = [
            checks.Error(
                "The value of 'exclude' must be a list or tuple.",
                obj=ExcludedFieldsInline,
                id='admin.E014',
            )
        ]
        self.assertEqual(errors, expected)

    def test_exclude_inline_model_admin(self):
        """
        Regression test for #9932 - exclude in InlineModelAdmin should not
        contain the ForeignKey field used in ModelAdmin.model
        """
        class SongInline(admin.StackedInline):
            model = Song
            exclude = ['album']

        class AlbumAdmin(admin.ModelAdmin):
            model = Album
            inlines = [SongInline]

        errors = AlbumAdmin(Album, AdminSite()).check()
        expected = [
            checks.Error(
                "Cannot exclude the field 'album', because it is the foreign key "
                "to the parent model 'admin_checks.Album'.",
                obj=SongInline,
                id='admin.E201',
            )
        ]
        self.assertEqual(errors, expected)

    def test_valid_generic_inline_model_admin(self):
        """
        Regression test for #22034 - check that generic inlines don't look for
        normal ForeignKey relations.
        """
        class InfluenceInline(GenericStackedInline):
            model = Influence

        class SongAdmin(admin.ModelAdmin):
            inlines = [InfluenceInline]

        errors = SongAdmin(Song, AdminSite()).check()
        self.assertEqual(errors, [])

    def test_generic_inline_model_admin_non_generic_model(self):
        """
        A model without a GenericForeignKey raises problems if it's included
        in an GenericInlineModelAdmin definition.
        """
        class BookInline(GenericStackedInline):
            model = Book

        class SongAdmin(admin.ModelAdmin):
            inlines = [BookInline]

        errors = SongAdmin(Song, AdminSite()).check()
        expected = [
            checks.Error(
                "'admin_checks.Book' has no GenericForeignKey.",
                obj=BookInline,
                id='admin.E301',
            )
        ]
        self.assertEqual(errors, expected)

    def test_generic_inline_model_admin_bad_ct_field(self):
        """
        A GenericInlineModelAdmin errors if the ct_field points to a
        nonexistent field.
        """
        class InfluenceInline(GenericStackedInline):
            model = Influence
            ct_field = 'nonexistent'

        class SongAdmin(admin.ModelAdmin):
            inlines = [InfluenceInline]

        errors = SongAdmin(Song, AdminSite()).check()
        expected = [
            checks.Error(
                "'ct_field' references 'nonexistent', which is not a field on 'admin_checks.Influence'.",
                obj=InfluenceInline,
                id='admin.E302',
            )
        ]
        self.assertEqual(errors, expected)

    def test_generic_inline_model_admin_bad_fk_field(self):
        """
        A GenericInlineModelAdmin errors if the ct_fk_field points to a
        nonexistent field.
        """
        class InfluenceInline(GenericStackedInline):
            model = Influence
            ct_fk_field = 'nonexistent'

        class SongAdmin(admin.ModelAdmin):
            inlines = [InfluenceInline]

        errors = SongAdmin(Song, AdminSite()).check()
        expected = [
            checks.Error(
                "'ct_fk_field' references 'nonexistent', which is not a field on 'admin_checks.Influence'.",
                obj=InfluenceInline,
                id='admin.E303',
            )
        ]
        self.assertEqual(errors, expected)

    def test_generic_inline_model_admin_non_gfk_ct_field(self):
        """
        A GenericInlineModelAdmin raises problems if the ct_field points to a
        field that isn't part of a GenericForeignKey.
        """
        class InfluenceInline(GenericStackedInline):
            model = Influence
            ct_field = 'name'

        class SongAdmin(admin.ModelAdmin):
            inlines = [InfluenceInline]

        errors = SongAdmin(Song, AdminSite()).check()
        expected = [
            checks.Error(
                "'admin_checks.Influence' has no GenericForeignKey using "
                "content type field 'name' and object ID field 'object_id'.",
                obj=InfluenceInline,
                id='admin.E304',
            )
        ]
        self.assertEqual(errors, expected)

    def test_generic_inline_model_admin_non_gfk_fk_field(self):
        """
        A GenericInlineModelAdmin raises problems if the ct_fk_field points to
        a field that isn't part of a GenericForeignKey.
        """
        class InfluenceInline(GenericStackedInline):
            model = Influence
            ct_fk_field = 'name'

        class SongAdmin(admin.ModelAdmin):
            inlines = [InfluenceInline]

        errors = SongAdmin(Song, AdminSite()).check()
        expected = [
            checks.Error(
                "'admin_checks.Influence' has no GenericForeignKey using "
                "content type field 'content_type' and object ID field 'name'.",
                obj=InfluenceInline,
                id='admin.E304',
            )
        ]
        self.assertEqual(errors, expected)

    def test_app_label_in_admin_checks(self):
        class RawIdNonexistentAdmin(admin.ModelAdmin):
            raw_id_fields = ('nonexistent',)

        errors = RawIdNonexistentAdmin(Album, AdminSite()).check()
        expected = [
            checks.Error(
                "The value of 'raw_id_fields[0]' refers to 'nonexistent', "
                "which is not an attribute of 'admin_checks.Album'.",
                obj=RawIdNonexistentAdmin,
                id='admin.E002',
            )
        ]
        self.assertEqual(errors, expected)

    def test_fk_exclusion(self):
        """
        Regression test for #11709 - when testing for fk excluding (when exclude is
        given) make sure fk_name is honored or things blow up when there is more
        than one fk to the parent model.
        """
        class TwoAlbumFKAndAnEInline(admin.TabularInline):
            model = TwoAlbumFKAndAnE
            exclude = ("e",)
            fk_name = "album1"

        class MyAdmin(admin.ModelAdmin):
            inlines = [TwoAlbumFKAndAnEInline]

        errors = MyAdmin(Album, AdminSite()).check()
        self.assertEqual(errors, [])

    def test_inline_self_check(self):
        class TwoAlbumFKAndAnEInline(admin.TabularInline):
            model = TwoAlbumFKAndAnE

        class MyAdmin(admin.ModelAdmin):
            inlines = [TwoAlbumFKAndAnEInline]

        errors = MyAdmin(Album, AdminSite()).check()
        expected = [
            checks.Error(
                "'admin_checks.TwoAlbumFKAndAnE' has more than one ForeignKey to 'admin_checks.Album'.",
                obj=TwoAlbumFKAndAnEInline,
                id='admin.E202',
            )
        ]
        self.assertEqual(errors, expected)

    def test_inline_with_specified(self):
        class TwoAlbumFKAndAnEInline(admin.TabularInline):
            model = TwoAlbumFKAndAnE
            fk_name = "album1"

        class MyAdmin(admin.ModelAdmin):
            inlines = [TwoAlbumFKAndAnEInline]

        errors = MyAdmin(Album, AdminSite()).check()
        self.assertEqual(errors, [])

    def test_readonly(self):
        class SongAdmin(admin.ModelAdmin):
            readonly_fields = ("title",)

        errors = SongAdmin(Song, AdminSite()).check()
        self.assertEqual(errors, [])

    def test_readonly_on_method(self):
        def my_function(obj):
            pass

        class SongAdmin(admin.ModelAdmin):
            readonly_fields = (my_function,)

        errors = SongAdmin(Song, AdminSite()).check()
        self.assertEqual(errors, [])

    def test_readonly_on_modeladmin(self):
        class SongAdmin(admin.ModelAdmin):
            readonly_fields = ("readonly_method_on_modeladmin",)

            def readonly_method_on_modeladmin(self, obj):
                pass

        errors = SongAdmin(Song, AdminSite()).check()
        self.assertEqual(errors, [])

    def test_readonly_dynamic_attribute_on_modeladmin(self):
        class SongAdmin(admin.ModelAdmin):
            readonly_fields = ("dynamic_method",)

            def __getattr__(self, item):
                if item == "dynamic_method":
                    def method(obj):
                        pass
                    return method
                raise AttributeError

        errors = SongAdmin(Song, AdminSite()).check()
        self.assertEqual(errors, [])

    def test_readonly_method_on_model(self):
        class SongAdmin(admin.ModelAdmin):
            readonly_fields = ("readonly_method_on_model",)

        errors = SongAdmin(Song, AdminSite()).check()
        self.assertEqual(errors, [])

    def test_nonexistent_field(self):
        class SongAdmin(admin.ModelAdmin):
            readonly_fields = ("title", "nonexistent")

        errors = SongAdmin(Song, AdminSite()).check()
        expected = [
            checks.Error(
                "The value of 'readonly_fields[1]' is not a callable, an attribute "
                "of 'SongAdmin', or an attribute of 'admin_checks.Song'.",
                obj=SongAdmin,
                id='admin.E035',
            )
        ]
        self.assertEqual(errors, expected)

    def test_nonexistent_field_on_inline(self):
        class CityInline(admin.TabularInline):
            model = City
            readonly_fields = ['i_dont_exist']  # Missing attribute

        errors = CityInline(State, AdminSite()).check()
        expected = [
            checks.Error(
                "The value of 'readonly_fields[0]' is not a callable, an attribute "
                "of 'CityInline', or an attribute of 'admin_checks.City'.",
                obj=CityInline,
                id='admin.E035',
            )
        ]
        self.assertEqual(errors, expected)

    def test_readonly_fields_not_list_or_tuple(self):
        class SongAdmin(admin.ModelAdmin):
            readonly_fields = 'test'

        self.assertEqual(SongAdmin(Song, AdminSite()).check(), [
            checks.Error(
                "The value of 'readonly_fields' must be a list or tuple.",
                obj=SongAdmin,
                id='admin.E034',
            )
        ])

    def test_extra(self):
        class SongAdmin(admin.ModelAdmin):
            def awesome_song(self, instance):
                if instance.title == "Born to Run":
                    return "Best Ever!"
                return "Status unknown."

        errors = SongAdmin(Song, AdminSite()).check()
        self.assertEqual(errors, [])

    def test_readonly_lambda(self):
        class SongAdmin(admin.ModelAdmin):
            readonly_fields = (lambda obj: "test",)

        errors = SongAdmin(Song, AdminSite()).check()
        self.assertEqual(errors, [])

    def test_graceful_m2m_fail(self):
        """
        Regression test for #12203/#12237 - Fail more gracefully when a M2M field that
        specifies the 'through' option is included in the 'fields' or the 'fieldsets'
        ModelAdmin options.
        """
        class BookAdmin(admin.ModelAdmin):
            fields = ['authors']

        errors = BookAdmin(Book, AdminSite()).check()
        expected = [
            checks.Error(
                "The value of 'fields' cannot include the ManyToManyField 'authors', "
                "because that field manually specifies a relationship model.",
                obj=BookAdmin,
                id='admin.E013',
            )
        ]
        self.assertEqual(errors, expected)

    def test_cannot_include_through(self):
        class FieldsetBookAdmin(admin.ModelAdmin):
            fieldsets = (
                ('Header 1', {'fields': ('name',)}),
                ('Header 2', {'fields': ('authors',)}),
            )

        errors = FieldsetBookAdmin(Book, AdminSite()).check()
        expected = [
            checks.Error(
                "The value of 'fieldsets[1][1][\"fields\"]' cannot include the ManyToManyField "
                "'authors', because that field manually specifies a relationship model.",
                obj=FieldsetBookAdmin,
                id='admin.E013',
            )
        ]
        self.assertEqual(errors, expected)

    def test_nested_fields(self):
        class NestedFieldsAdmin(admin.ModelAdmin):
            fields = ('price', ('name', 'subtitle'))

        errors = NestedFieldsAdmin(Book, AdminSite()).check()
        self.assertEqual(errors, [])

    def test_nested_fieldsets(self):
        class NestedFieldsetAdmin(admin.ModelAdmin):
            fieldsets = (
                ('Main', {'fields': ('price', ('name', 'subtitle'))}),
            )

        errors = NestedFieldsetAdmin(Book, AdminSite()).check()
        self.assertEqual(errors, [])

    def test_explicit_through_override(self):
        """
        Regression test for #12209 -- If the explicitly provided through model
        is specified as a string, the admin should still be able use
        Model.m2m_field.through
        """
        class AuthorsInline(admin.TabularInline):
            model = Book.authors.through

        class BookAdmin(admin.ModelAdmin):
            inlines = [AuthorsInline]

        errors = BookAdmin(Book, AdminSite()).check()
        self.assertEqual(errors, [])

    def test_non_model_fields(self):
        """
        Regression for ensuring ModelAdmin.fields can contain non-model fields
        that broke with r11737
        """
        class SongForm(forms.ModelForm):
            extra_data = forms.CharField()

        class FieldsOnFormOnlyAdmin(admin.ModelAdmin):
            form = SongForm
            fields = ['title', 'extra_data']

        errors = FieldsOnFormOnlyAdmin(Song, AdminSite()).check()
        self.assertEqual(errors, [])

    def test_non_model_first_field(self):
        """
        Regression for ensuring ModelAdmin.field can handle first elem being a
        non-model field (test fix for UnboundLocalError introduced with r16225).
        """
        class SongForm(forms.ModelForm):
            extra_data = forms.CharField()

            class Meta:
                model = Song
                fields = '__all__'

        class FieldsOnFormOnlyAdmin(admin.ModelAdmin):
            form = SongForm
            fields = ['extra_data', 'title']

        errors = FieldsOnFormOnlyAdmin(Song, AdminSite()).check()
        self.assertEqual(errors, [])

    def test_check_sublists_for_duplicates(self):
        class MyModelAdmin(admin.ModelAdmin):
            fields = ['state', ['state']]

        errors = MyModelAdmin(Song, AdminSite()).check()
        expected = [
            checks.Error(
                "The value of 'fields' contains duplicate field(s).",
                obj=MyModelAdmin,
                id='admin.E006'
            )
        ]
        self.assertEqual(errors, expected)

    def test_check_fieldset_sublists_for_duplicates(self):
        class MyModelAdmin(admin.ModelAdmin):
            fieldsets = [
                (None, {
                    'fields': ['title', 'album', ('title', 'album')]
                }),
            ]

        errors = MyModelAdmin(Song, AdminSite()).check()
        expected = [
            checks.Error(
                "There are duplicate field(s) in 'fieldsets[0][1]'.",
                obj=MyModelAdmin,
                id='admin.E012'
            )
        ]
        self.assertEqual(errors, expected)

    def test_list_filter_works_on_through_field_even_when_apps_not_ready(self):
        """
        Ensure list_filter can access reverse fields even when the app registry
        is not ready; refs #24146.
        """
        class BookAdminWithListFilter(admin.ModelAdmin):
            list_filter = ['authorsbooks__featured']

        # Temporarily pretending apps are not ready yet. This issue can happen
        # if the value of 'list_filter' refers to a 'through__field'.
        Book._meta.apps.ready = False
        try:
            errors = BookAdminWithListFilter(Book, AdminSite()).check()
            self.assertEqual(errors, [])
        finally:
            Book._meta.apps.ready = True
