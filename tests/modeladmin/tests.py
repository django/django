from datetime import date

from django import forms
from django.contrib.admin.models import LogEntry
from django.contrib.admin.options import (
    HORIZONTAL, VERTICAL, ModelAdmin, TabularInline,
)
from django.contrib.admin.sites import AdminSite
from django.contrib.admin.widgets import AdminDateWidget, AdminRadioSelect
from django.contrib.auth.models import User
from django.forms.widgets import Select
from django.test import SimpleTestCase, TestCase

from .models import Band, Concert


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
        self.assertIsNone(ma.get_exclude(request, self.band))

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
        # get_fieldsets() is called when figuring out form fields (#18681).
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
        A lookup_allowed allows a parameter whose field lookup doesn't exist.
        (#21129).
        """
        class BandAdmin(ModelAdmin):
            fields = ['name']

        ma = BandAdmin(Band, self.site)
        self.assertTrue(ma.lookup_allowed('name__nonexistent', 'test_value'))

    def test_field_arguments(self):
        # If fields is specified, fieldsets_add and fieldsets_change should
        # just stick the fields into a formsets structure and return it.
        class BandAdmin(ModelAdmin):
            fields = ['name']

        ma = BandAdmin(Band, self.site)

        self.assertEqual(list(ma.get_fields(request)), ['name'])
        self.assertEqual(list(ma.get_fields(request, self.band)), ['name'])
        self.assertEqual(ma.get_fieldsets(request), [(None, {'fields': ['name']})])
        self.assertEqual(ma.get_fieldsets(request, self.band), [(None, {'fields': ['name']})])

    def test_field_arguments_restricted_on_form(self):
        # If fields or fieldsets is specified, it should exclude fields on the
        # Form class to the fields specified. This may cause errors to be
        # raised in the db layer if required model fields aren't in fields/
        # fieldsets, but that's preferable to ghost errors where a field in the
        # Form class isn't being displayed because it's not in fields/fieldsets.

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
        The custom ModelForm's `Meta.exclude` is respected when used in
        conjunction with `ModelAdmin.readonly_fields` and when no
        `ModelAdmin.exclude` is defined (#14496).
        """
        # With ModelAdmin
        class AdminBandForm(forms.ModelForm):
            class Meta:
                model = Band
                exclude = ['bio']

        class BandAdmin(ModelAdmin):
            readonly_fields = ['name']
            form = AdminBandForm

        ma = BandAdmin(Band, self.site)
        self.assertEqual(list(ma.get_form(request).base_fields), ['sign_date'])

        # With InlineModelAdmin
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
            inlines = [ConcertInline]

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
        The custom ModelForm's `Meta.exclude` is overridden if
        `ModelAdmin.exclude` or `InlineModelAdmin.exclude` are defined (#14496).
        """
        # With ModelAdmin
        class AdminBandForm(forms.ModelForm):
            class Meta:
                model = Band
                exclude = ['bio']

        class BandAdmin(ModelAdmin):
            exclude = ['name']
            form = AdminBandForm

        ma = BandAdmin(Band, self.site)
        self.assertEqual(list(ma.get_form(request).base_fields), ['bio', 'sign_date'])

        # With InlineModelAdmin
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
            inlines = [ConcertInline]

        ma = BandAdmin(Band, self.site)
        self.assertEqual(
            list(list(ma.get_formsets_with_inlines(request))[0][0]().forms[0].fields),
            ['main_band', 'opening_band', 'day', 'id', 'DELETE']
        )

    def test_overriding_get_exclude(self):
        class BandAdmin(ModelAdmin):
            def get_exclude(self, request, obj=None):
                return ['name']

        self.assertEqual(
            list(BandAdmin(Band, self.site).get_form(request).base_fields),
            ['bio', 'sign_date']
        )

    def test_get_exclude_overrides_exclude(self):
        class BandAdmin(ModelAdmin):
            exclude = ['bio']

            def get_exclude(self, request, obj=None):
                return ['name']

        self.assertEqual(
            list(BandAdmin(Band, self.site).get_form(request).base_fields),
            ['bio', 'sign_date']
        )

    def test_get_exclude_takes_obj(self):
        class BandAdmin(ModelAdmin):
            def get_exclude(self, request, obj=None):
                if obj:
                    return ['sign_date']
                return ['name']

        self.assertEqual(
            list(BandAdmin(Band, self.site).get_form(request, self.band).base_fields),
            ['name', 'bio']
        )

    def test_custom_form_validation(self):
        # If a form is specified, it should use it allowing custom validation
        # to work properly. This won't break any of the admin widgets or media.
        class AdminBandForm(forms.ModelForm):
            delete = forms.BooleanField()

        class BandAdmin(ModelAdmin):
            form = AdminBandForm

        ma = BandAdmin(Band, self.site)
        self.assertEqual(list(ma.get_form(request).base_fields), ['name', 'bio', 'sign_date', 'delete'])
        self.assertEqual(type(ma.get_form(request).base_fields['sign_date'].widget), AdminDateWidget)

    def test_form_exclude_kwarg_override(self):
        """
        The `exclude` kwarg passed to `ModelAdmin.get_form()` overrides all
        other declarations (#8999).
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
        The `exclude` kwarg passed to `InlineModelAdmin.get_formset()`
        overrides all other declarations (#8999).
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
            inlines = [ConcertInline]

        ma = BandAdmin(Band, self.site)
        self.assertEqual(
            list(list(ma.get_formsets_with_inlines(request))[0][0]().forms[0].fields),
            ['main_band', 'day', 'transport', 'id', 'DELETE']
        )

    def test_formset_overriding_get_exclude_with_form_fields(self):
        class AdminConcertForm(forms.ModelForm):
            class Meta:
                model = Concert
                fields = ['main_band', 'opening_band', 'day', 'transport']

        class ConcertInline(TabularInline):
            form = AdminConcertForm
            fk_name = 'main_band'
            model = Concert

            def get_exclude(self, request, obj=None):
                return ['opening_band']

        class BandAdmin(ModelAdmin):
            inlines = [ConcertInline]

        ma = BandAdmin(Band, self.site)
        self.assertEqual(
            list(list(ma.get_formsets_with_inlines(request))[0][0]().forms[0].fields),
            ['main_band', 'day', 'transport', 'id', 'DELETE']
        )

    def test_formset_overriding_get_exclude_with_form_exclude(self):
        class AdminConcertForm(forms.ModelForm):
            class Meta:
                model = Concert
                exclude = ['day']

        class ConcertInline(TabularInline):
            form = AdminConcertForm
            fk_name = 'main_band'
            model = Concert

            def get_exclude(self, request, obj=None):
                return ['opening_band']

        class BandAdmin(ModelAdmin):
            inlines = [ConcertInline]

        ma = BandAdmin(Band, self.site)
        self.assertEqual(
            list(list(ma.get_formsets_with_inlines(request))[0][0]().forms[0].fields),
            ['main_band', 'day', 'transport', 'id', 'DELETE']
        )

    def test_queryset_override(self):
        # If the queryset of a ModelChoiceField in a custom form is overridden,
        # RelatedFieldWidgetWrapper doesn't mess that up.
        band2 = Band.objects.create(name='The Beatles', bio='', sign_date=date(1962, 1, 1))

        ma = ModelAdmin(Concert, self.site)
        form = ma.get_form(request)()

        self.assertHTMLEqual(
            str(form["main_band"]),
            '<div class="related-widget-wrapper">'
            '<select name="main_band" id="id_main_band" required>'
            '<option value="" selected>---------</option>'
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
            '<option value="" selected>---------</option>'
            '<option value="%d">The Doors</option>'
            '</select></div>' % self.band.id
        )

    def test_regression_for_ticket_15820(self):
        """
        `obj` is passed from `InlineModelAdmin.get_fieldsets()` to
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
            inlines = [ConcertInline]

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
            inlines = [ConcertInline]

        ma = BandAdmin(Band, self.site)
        self.assertEqual(
            list(list(ma.get_formsets_with_inlines(request))[0][0]().forms[0].fields),
            ['extra', 'transport', 'id', 'DELETE', 'main_band']
        )

    def test_log_actions(self):
        ma = ModelAdmin(Band, self.site)
        mock_request = MockRequest()
        mock_request.user = User.objects.create(username='bill')
        self.assertEqual(ma.log_addition(mock_request, self.band, 'added'), LogEntry.objects.latest('id'))
        self.assertEqual(ma.log_change(mock_request, self.band, 'changed'), LogEntry.objects.latest('id'))
        self.assertEqual(ma.log_change(mock_request, self.band, 'deleted'), LogEntry.objects.latest('id'))


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
        has_add_permission returns True for users who can add objects and
        False for users who can't.
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
        has_change_permission returns True for users who can edit objects and
        False for users who can't.
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
        has_delete_permission returns True for users who can delete objects and
        False for users who can't.
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
        as_module_permission returns True for users who have any permission
        for the module and False for users who don't.
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
