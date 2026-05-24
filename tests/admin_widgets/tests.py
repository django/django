import gettext
import os
import re
import zoneinfo
from datetime import datetime, timedelta
from importlib import import_module
from pathlib import Path
from unittest import skipUnless

from django import forms
from django.conf import settings
from django.contrib import admin
from django.contrib.admin import widgets
from django.contrib.admin.tests import AdminPlaywrightTestCase
from django.contrib.auth.models import User
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models import (
    CharField,
    DateField,
    DateTimeField,
    ForeignKey,
    ManyToManyField,
    UUIDField,
)
from django.test import SimpleTestCase, TestCase, override_settings
from django.test.playwright import screenshot_cases
from django.test.utils import requires_tz_support
from django.urls import reverse
from django.utils import translation

from .models import (
    Advisor,
    Album,
    Band,
    Bee,
    Car,
    Company,
    Event,
    Honeycomb,
    Image,
    Individual,
    Inventory,
    Member,
    MyFileField,
    Profile,
    ReleaseEvent,
    School,
    Student,
    UnsafeLimitChoicesTo,
    VideoStream,
)
from .widgetadmin import site as widget_admin_site


class TestDataMixin:
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="super", password="secret", email=None
        )
        cls.u2 = User.objects.create_user(username="testser", password="secret")
        Car.objects.create(owner=cls.superuser, make="Volkswagen", model="Passat")
        Car.objects.create(owner=cls.u2, make="BMW", model="M3")


class AdminFormfieldForDBFieldTests(SimpleTestCase):
    """
    Tests for correct behavior of ModelAdmin.formfield_for_dbfield
    """

    def assertFormfield(self, model, fieldname, widgetclass, **admin_overrides):
        """
        Helper to call formfield_for_dbfield for a given model and field name
        and verify that the returned formfield is appropriate.
        """

        # Override any settings on the model admin
        class MyModelAdmin(admin.ModelAdmin):
            pass

        for k in admin_overrides:
            setattr(MyModelAdmin, k, admin_overrides[k])

        # Construct the admin, and ask it for a formfield
        ma = MyModelAdmin(model, admin.site)
        ff = ma.formfield_for_dbfield(model._meta.get_field(fieldname), request=None)

        # "unwrap" the widget wrapper, if needed
        if isinstance(ff.widget, widgets.RelatedFieldWidgetWrapper):
            widget = ff.widget.widget
        else:
            widget = ff.widget

        self.assertIsInstance(widget, widgetclass)

        # Return the formfield so that other tests can continue
        return ff

    def test_DateField(self):
        self.assertFormfield(Event, "start_date", widgets.AdminDateWidget)

    def test_DateTimeField(self):
        self.assertFormfield(Member, "birthdate", widgets.AdminSplitDateTime)

    def test_TimeField(self):
        self.assertFormfield(Event, "start_time", widgets.AdminTimeWidget)

    def test_TextField(self):
        self.assertFormfield(Event, "description", widgets.AdminTextareaWidget)

    def test_URLField(self):
        self.assertFormfield(Event, "link", widgets.AdminURLFieldWidget)

    def test_IntegerField(self):
        self.assertFormfield(Event, "min_age", widgets.AdminIntegerFieldWidget)

    def test_CharField(self):
        self.assertFormfield(Member, "name", widgets.AdminTextInputWidget)

    def test_EmailField(self):
        self.assertFormfield(Member, "email", widgets.AdminEmailInputWidget)

    def test_FileField(self):
        self.assertFormfield(Album, "cover_art", widgets.AdminFileWidget)

    def test_ForeignKey(self):
        self.assertFormfield(Event, "main_band", forms.Select)

    def test_raw_id_ForeignKey(self):
        self.assertFormfield(
            Event,
            "main_band",
            widgets.ForeignKeyRawIdWidget,
            raw_id_fields=["main_band"],
        )

    def test_radio_fields_ForeignKey(self):
        ff = self.assertFormfield(
            Event,
            "main_band",
            widgets.AdminRadioSelect,
            radio_fields={"main_band": admin.VERTICAL},
        )
        self.assertIsNone(ff.empty_label)

    def test_radio_fields_foreignkey_formfield_overrides_empty_label(self):
        class MyModelAdmin(admin.ModelAdmin):
            radio_fields = {"parent": admin.VERTICAL}
            formfield_overrides = {
                ForeignKey: {"empty_label": "Custom empty label"},
            }

        ma = MyModelAdmin(Inventory, admin.site)
        ff = ma.formfield_for_dbfield(Inventory._meta.get_field("parent"), request=None)
        self.assertEqual(ff.empty_label, "Custom empty label")

    def test_many_to_many(self):
        self.assertFormfield(Band, "members", forms.SelectMultiple)

    def test_raw_id_many_to_many(self):
        self.assertFormfield(
            Band, "members", widgets.ManyToManyRawIdWidget, raw_id_fields=["members"]
        )

    def test_filtered_many_to_many(self):
        self.assertFormfield(
            Band, "members", widgets.FilteredSelectMultiple, filter_vertical=["members"]
        )

    def test_formfield_overrides(self):
        self.assertFormfield(
            Event,
            "start_date",
            forms.TextInput,
            formfield_overrides={DateField: {"widget": forms.TextInput}},
        )

    def test_formfield_overrides_widget_instances(self):
        """
        Widget instances in formfield_overrides are not shared between
        different fields. (#19423)
        """

        class BandAdmin(admin.ModelAdmin):
            formfield_overrides = {
                CharField: {"widget": forms.TextInput(attrs={"size": "10"})}
            }

        ma = BandAdmin(Band, admin.site)
        f1 = ma.formfield_for_dbfield(Band._meta.get_field("name"), request=None)
        f2 = ma.formfield_for_dbfield(Band._meta.get_field("style"), request=None)
        self.assertNotEqual(f1.widget, f2.widget)
        self.assertEqual(f1.widget.attrs["maxlength"], "100")
        self.assertEqual(f2.widget.attrs["maxlength"], "20")
        self.assertEqual(f2.widget.attrs["size"], "10")

    def test_formfield_overrides_m2m_filter_widget(self):
        """
        The autocomplete_fields, raw_id_fields, filter_vertical, and
        filter_horizontal widgets for ManyToManyFields may be overridden by
        specifying a widget in formfield_overrides.
        """

        class BandAdmin(admin.ModelAdmin):
            filter_vertical = ["members"]
            formfield_overrides = {
                ManyToManyField: {"widget": forms.CheckboxSelectMultiple},
            }

        ma = BandAdmin(Band, admin.site)
        field = ma.formfield_for_dbfield(Band._meta.get_field("members"), request=None)
        self.assertIsInstance(field.widget.widget, forms.CheckboxSelectMultiple)

    def test_formfield_overrides_for_datetime_field(self):
        """
        Overriding the widget for DateTimeField doesn't overrides the default
        form_class for that field (#26449).
        """

        class MemberAdmin(admin.ModelAdmin):
            formfield_overrides = {
                DateTimeField: {"widget": widgets.AdminSplitDateTime}
            }

        ma = MemberAdmin(Member, admin.site)
        f1 = ma.formfield_for_dbfield(Member._meta.get_field("birthdate"), request=None)
        self.assertIsInstance(f1.widget, widgets.AdminSplitDateTime)
        self.assertIsInstance(f1, forms.SplitDateTimeField)

    def test_formfield_overrides_for_custom_field(self):
        """
        formfield_overrides works for a custom field class.
        """

        class AlbumAdmin(admin.ModelAdmin):
            formfield_overrides = {MyFileField: {"widget": forms.TextInput()}}

        ma = AlbumAdmin(Member, admin.site)
        f1 = ma.formfield_for_dbfield(
            Album._meta.get_field("backside_art"), request=None
        )
        self.assertIsInstance(f1.widget, forms.TextInput)

    def test_field_with_choices(self):
        self.assertFormfield(Member, "gender", forms.Select)

    def test_choices_with_radio_fields(self):
        self.assertFormfield(
            Member,
            "gender",
            widgets.AdminRadioSelect,
            radio_fields={"gender": admin.VERTICAL},
        )

    def test_inheritance(self):
        self.assertFormfield(Album, "backside_art", widgets.AdminFileWidget)

    def test_m2m_widgets(self):
        """m2m fields help text as it applies to admin app (#9321)."""

        class AdvisorAdmin(admin.ModelAdmin):
            filter_vertical = ["companies"]

        self.assertFormfield(
            Advisor,
            "companies",
            widgets.FilteredSelectMultiple,
            filter_vertical=["companies"],
        )
        ma = AdvisorAdmin(Advisor, admin.site)
        f = ma.formfield_for_dbfield(Advisor._meta.get_field("companies"), request=None)
        self.assertEqual(
            f.help_text,
            "Hold down “Control”, or “Command” on a Mac, to select more than one.",
        )

    def test_m2m_widgets_no_allow_multiple_selected(self):
        class NoAllowMultipleSelectedWidget(forms.SelectMultiple):
            allow_multiple_selected = False

        class AdvisorAdmin(admin.ModelAdmin):
            filter_vertical = ["companies"]
            formfield_overrides = {
                ManyToManyField: {"widget": NoAllowMultipleSelectedWidget},
            }

        self.assertFormfield(
            Advisor,
            "companies",
            widgets.FilteredSelectMultiple,
            filter_vertical=["companies"],
        )
        ma = AdvisorAdmin(Advisor, admin.site)
        f = ma.formfield_for_dbfield(Advisor._meta.get_field("companies"), request=None)
        self.assertEqual(f.help_text, "")


@override_settings(ROOT_URLCONF="admin_widgets.urls")
class AdminFormfieldForDBFieldWithRequestTests(TestDataMixin, TestCase):
    def test_filter_choices_by_request_user(self):
        """
        Ensure the user can only see their own cars in the foreign key
        dropdown.
        """
        self.client.force_login(self.superuser)
        response = self.client.get(reverse("admin:admin_widgets_cartire_add"))
        self.assertNotContains(response, "BMW M3")
        self.assertContains(response, "Volkswagen Passat")


@override_settings(ROOT_URLCONF="admin_widgets.urls")
class AdminForeignKeyWidgetChangeList(TestDataMixin, TestCase):
    def setUp(self):
        self.client.force_login(self.superuser)

    def test_changelist_ForeignKey(self):
        response = self.client.get(reverse("admin:admin_widgets_car_changelist"))
        self.assertContains(response, "/auth/user/add/")


@override_settings(ROOT_URLCONF="admin_widgets.urls")
class AdminForeignKeyRawIdWidget(TestDataMixin, TestCase):
    def setUp(self):
        self.client.force_login(self.superuser)

    def test_nonexistent_target_id(self):
        band = Band.objects.create(name="Bogey Blues")
        pk = band.pk
        band.delete()
        post_data = {
            "main_band": str(pk),
        }
        # Try posting with a nonexistent pk in a raw id field: this
        # should result in an error message, not a server exception.
        response = self.client.post(reverse("admin:admin_widgets_event_add"), post_data)
        self.assertContains(
            response,
            "Select a valid choice. That choice is not one of the available choices.",
        )

    def test_invalid_target_id(self):
        for test_str in ("Iñtërnâtiônàlizætiøn", "1234'", -1234):
            # This should result in an error message, not a server exception.
            response = self.client.post(
                reverse("admin:admin_widgets_event_add"), {"main_band": test_str}
            )

            self.assertContains(
                response,
                "Select a valid choice. That choice is not one of the available "
                "choices.",
            )

    def test_url_params_from_lookup_dict_any_iterable(self):
        lookup1 = widgets.url_params_from_lookup_dict({"color__in": ("red", "blue")})
        lookup2 = widgets.url_params_from_lookup_dict({"color__in": ["red", "blue"]})
        self.assertEqual(lookup1, {"color__in": "red,blue"})
        self.assertEqual(lookup1, lookup2)

    def test_url_params_from_lookup_dict_callable(self):
        def my_callable():
            return "works"

        lookup1 = widgets.url_params_from_lookup_dict({"myfield": my_callable})
        lookup2 = widgets.url_params_from_lookup_dict({"myfield": my_callable()})
        self.assertEqual(lookup1, lookup2)

    def test_label_and_url_for_value_invalid_uuid(self):
        field = Bee._meta.get_field("honeycomb")
        self.assertIsInstance(field.target_field, UUIDField)
        widget = widgets.ForeignKeyRawIdWidget(field.remote_field, admin.site)
        self.assertEqual(widget.label_and_url_for_value("invalid-uuid"), ("", ""))


class FilteredSelectMultipleWidgetTest(SimpleTestCase):
    def test_render(self):
        # Backslash in verbose_name to ensure it is JavaScript escaped.
        w = widgets.FilteredSelectMultiple("test\\", False)
        self.assertHTMLEqual(
            w.render("test", "test"),
            '<select multiple name="test" class="selectfilter" '
            'data-field-name="test\\" data-is-stacked="0">\n</select>',
        )

    def test_stacked_render(self):
        # Backslash in verbose_name to ensure it is JavaScript escaped.
        w = widgets.FilteredSelectMultiple("test\\", True)
        self.assertHTMLEqual(
            w.render("test", "test"),
            '<select multiple name="test" class="selectfilterstacked" '
            'data-field-name="test\\" data-is-stacked="1">\n</select>',
        )


class AdminDateWidgetTest(SimpleTestCase):
    def test_attrs(self):
        w = widgets.AdminDateWidget()
        self.assertHTMLEqual(
            w.render("test", datetime(2007, 12, 1, 9, 30)),
            '<p class="date">'
            '<input aria-describedby="id_test_timezone_warning_helptext" '
            'value="2007-12-01" type="text" class="vDateField" name="test" '
            'size="10"></p>',
        )
        # pass attrs to widget
        w = widgets.AdminDateWidget(attrs={"size": 20, "class": "myDateField"})
        self.assertHTMLEqual(
            w.render("test", datetime(2007, 12, 1, 9, 30)),
            '<p class="date">'
            '<input aria-describedby="id_test_timezone_warning_helptext" '
            'value="2007-12-01" type="text" class="myDateField" name="test" '
            'size="20"></p>',
        )


class AdminTimeWidgetTest(SimpleTestCase):
    def test_attrs(self):
        w = widgets.AdminTimeWidget()
        self.assertHTMLEqual(
            w.render("test", datetime(2007, 12, 1, 9, 30)),
            '<p class="time">'
            '<input aria-describedby="id_test_timezone_warning_helptext" '
            'value="09:30:00" type="text" class="vTimeField" name="test" '
            'size="8"></p>',
        )
        # pass attrs to widget
        w = widgets.AdminTimeWidget(attrs={"size": 20, "class": "myTimeField"})
        self.assertHTMLEqual(
            w.render("test", datetime(2007, 12, 1, 9, 30)),
            '<p class="time">'
            '<input aria-describedby="id_test_timezone_warning_helptext" '
            'value="09:30:00" type="text" class="myTimeField" name="test" '
            'size="20"></p>',
        )


class AdminSplitDateTimeWidgetTest(SimpleTestCase):
    def test_render(self):
        w = widgets.AdminSplitDateTime()
        self.assertHTMLEqual(
            w.render("test", datetime(2007, 12, 1, 9, 30), attrs={"id": "id_test"}),
            '<p class="datetime">'
            '<label for="id_test_0">Date:</label> '
            '<input aria-describedby="id_test_timezone_warning_helptext" '
            'value="2007-12-01" type="text" class="vDateField" '
            'name="test_0" size="10" id="id_test_0"><br>'
            '<label for="id_test_1">Time:</label> '
            '<input aria-describedby="id_test_timezone_warning_helptext" '
            'value="09:30:00" type="text" class="vTimeField" '
            'name="test_1" size="8" id="id_test_1"></p>',
        )

    def test_localization(self):
        w = widgets.AdminSplitDateTime()

        with translation.override("de-at"):
            w.is_localized = True
            self.assertHTMLEqual(
                w.render("test", datetime(2007, 12, 1, 9, 30), attrs={"id": "id_test"}),
                '<p class="datetime">'
                '<label for="id_test_0">Datum:</label> '
                '<input aria-describedby="id_test_timezone_warning_helptext" '
                'value="01.12.2007" type="text" '
                'class="vDateField" name="test_0" size="10" id="id_test_0"><br>'
                '<label for="id_test_1">Zeit:</label> '
                '<input aria-describedby="id_test_timezone_warning_helptext" '
                'value="09:30:00" type="text" class="vTimeField" '
                'name="test_1" size="8" id="id_test_1"></p>',
            )


class AdminURLWidgetTest(SimpleTestCase):
    def test_get_context_validates_url(self):
        w = widgets.AdminURLFieldWidget()
        for invalid in [
            "",
            "/not/a/full/url/",
            'javascript:alert("Danger XSS!")',
            "http://" + "한.글." * 1_000_000 + "com",
        ]:
            with self.subTest(url=invalid):
                self.assertFalse(w.get_context("name", invalid, {})["url_valid"])
        self.assertTrue(w.get_context("name", "http://example.com", {})["url_valid"])

    def test_render(self):
        w = widgets.AdminURLFieldWidget()
        self.assertHTMLEqual(
            w.render("test", ""), '<input class="vURLField" name="test" type="url">'
        )
        self.assertHTMLEqual(
            w.render("test", "http://example.com"),
            '<p class="url">Currently:<a href="http://example.com">'
            "http://example.com</a><br>"
            'Change:<input class="vURLField" name="test" type="url" '
            'value="http://example.com"></p>',
        )

    def test_render_idn(self):
        w = widgets.AdminURLFieldWidget()
        self.assertHTMLEqual(
            w.render("test", "http://example-äüö.com"),
            '<p class="url">Currently: <a href="http://example-%C3%A4%C3%BC%C3%B6.com">'
            "http://example-äüö.com</a><br>"
            'Change:<input class="vURLField" name="test" type="url" '
            'value="http://example-äüö.com"></p>',
        )
        # Does not use obsolete IDNA-2003 encoding (#36013).
        self.assertNotIn("fass.example.com", w.render("test", "http://faß.example.com"))

    def test_render_quoting(self):
        """
        WARNING: This test doesn't use assertHTMLEqual since it will get rid
        of some escapes which are tested here!
        """
        HREF_RE = re.compile('href="([^"]+)"')
        VALUE_RE = re.compile('value="([^"]+)"')
        TEXT_RE = re.compile("<a[^>]+>([^>]+)</a>")
        w = widgets.AdminURLFieldWidget()
        output = w.render("test", "http://example.com/<sometag>some-text</sometag>")
        self.assertEqual(
            HREF_RE.search(output)[1],
            "http://example.com/%3Csometag%3Esome-text%3C/sometag%3E",
        )
        self.assertEqual(
            TEXT_RE.search(output)[1],
            "http://example.com/&lt;sometag&gt;some-text&lt;/sometag&gt;",
        )
        self.assertEqual(
            VALUE_RE.search(output)[1],
            "http://example.com/&lt;sometag&gt;some-text&lt;/sometag&gt;",
        )
        output = w.render("test", "http://example-äüö.com/<sometag>some-text</sometag>")
        self.assertEqual(
            HREF_RE.search(output)[1],
            "http://example-%C3%A4%C3%BC%C3%B6.com/"
            "%3Csometag%3Esome-text%3C/sometag%3E",
        )
        self.assertEqual(
            TEXT_RE.search(output)[1],
            "http://example-äüö.com/&lt;sometag&gt;some-text&lt;/sometag&gt;",
        )
        self.assertEqual(
            VALUE_RE.search(output)[1],
            "http://example-äüö.com/&lt;sometag&gt;some-text&lt;/sometag&gt;",
        )
        output = w.render(
            "test", 'http://www.example.com/%C3%A4"><script>alert("XSS!")</script>"'
        )
        self.assertEqual(
            HREF_RE.search(output)[1],
            "http://www.example.com/%C3%A4%22%3E%3Cscript%3Ealert(%22XSS!%22)"
            "%3C/script%3E%22",
        )
        self.assertEqual(
            TEXT_RE.search(output)[1],
            "http://www.example.com/%C3%A4&quot;&gt;&lt;script&gt;"
            "alert(&quot;XSS!&quot;)&lt;/script&gt;&quot;",
        )
        self.assertEqual(
            VALUE_RE.search(output)[1],
            "http://www.example.com/%C3%A4&quot;&gt;&lt;script&gt;"
            "alert(&quot;XSS!&quot;)&lt;/script&gt;&quot;",
        )


class AdminUUIDWidgetTests(SimpleTestCase):
    def test_attrs(self):
        w = widgets.AdminUUIDInputWidget()
        self.assertHTMLEqual(
            w.render("test", "550e8400-e29b-41d4-a716-446655440000"),
            '<input value="550e8400-e29b-41d4-a716-446655440000" type="text" '
            'class="vUUIDField" name="test">',
        )
        w = widgets.AdminUUIDInputWidget(attrs={"class": "myUUIDInput"})
        self.assertHTMLEqual(
            w.render("test", "550e8400-e29b-41d4-a716-446655440000"),
            '<input value="550e8400-e29b-41d4-a716-446655440000" type="text" '
            'class="myUUIDInput" name="test">',
        )


@override_settings(ROOT_URLCONF="admin_widgets.urls")
class AdminFileWidgetTests(TestDataMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        band = Band.objects.create(name="Linkin Park")
        cls.album = band.album_set.create(
            name="Hybrid Theory", cover_art=r"albums\hybrid_theory.jpg"
        )

    def test_render(self):
        w = widgets.AdminFileWidget()
        self.assertHTMLEqual(
            w.render("test", self.album.cover_art),
            '<p class="file-upload">Currently: <a href="%(STORAGE_URL)salbums/'
            r'hybrid_theory.jpg">albums\hybrid_theory.jpg</a> '
            '<span class="clearable-file-input">'
            '<input type="checkbox" name="test-clear" id="test-clear_id"> '
            '<label for="test-clear_id">Clear</label></span><br>'
            'Change: <input type="file" name="test"></p>'
            % {
                "STORAGE_URL": default_storage.url(""),
            },
        )
        self.assertHTMLEqual(
            w.render("test", SimpleUploadedFile("test", b"content")),
            '<input type="file" name="test">',
        )

    def test_render_with_attrs_id(self):
        storage_url = default_storage.url("")
        w = widgets.AdminFileWidget()
        self.assertHTMLEqual(
            w.render("test", self.album.cover_art, attrs={"id": "test_id"}),
            f'<p class="file-upload">Currently: <a href="{storage_url}albums/'
            r'hybrid_theory.jpg">albums\hybrid_theory.jpg</a> '
            '<span class="clearable-file-input">'
            '<input type="checkbox" name="test-clear" id="test-clear_id"> '
            '<label for="test-clear_id">Clear</label></span><br>'
            'Change: <input type="file" name="test" id="test_id"></p>',
        )

    def test_render_required(self):
        widget = widgets.AdminFileWidget()
        widget.is_required = True
        self.assertHTMLEqual(
            widget.render("test", self.album.cover_art),
            '<p class="file-upload">Currently: <a href="%(STORAGE_URL)salbums/'
            r'hybrid_theory.jpg">albums\hybrid_theory.jpg</a><br>'
            'Change: <input type="file" name="test"></p>'
            % {
                "STORAGE_URL": default_storage.url(""),
            },
        )

    def test_render_disabled(self):
        widget = widgets.AdminFileWidget(attrs={"disabled": True})
        self.assertHTMLEqual(
            widget.render("test", self.album.cover_art),
            '<p class="file-upload">Currently: <a href="%(STORAGE_URL)salbums/'
            r'hybrid_theory.jpg">albums\hybrid_theory.jpg</a> '
            '<span class="clearable-file-input">'
            '<input type="checkbox" name="test-clear" id="test-clear_id" disabled>'
            '<label for="test-clear_id">Clear</label></span><br>'
            'Change: <input type="file" name="test" disabled></p>'
            % {
                "STORAGE_URL": default_storage.url(""),
            },
        )

    def test_render_checked(self):
        storage_url = default_storage.url("")
        widget = widgets.AdminFileWidget()
        widget.checked = True
        self.assertHTMLEqual(
            widget.render("test", self.album.cover_art),
            f'<p class="file-upload">Currently: <a href="{storage_url}albums/'
            r'hybrid_theory.jpg">albums\hybrid_theory.jpg</a> '
            '<span class="clearable-file-input">'
            '<input type="checkbox" name="test-clear" id="test-clear_id" checked>'
            '<label for="test-clear_id">Clear</label></span><br>'
            'Change: <input type="file" name="test" checked></p>',
        )

    def test_readonly_fields(self):
        """
        File widgets should render as a link when they're marked "read only."
        """
        self.client.force_login(self.superuser)
        response = self.client.get(
            reverse("admin:admin_widgets_album_change", args=(self.album.id,))
        )
        self.assertContains(
            response,
            '<div class="readonly"><a href="%(STORAGE_URL)salbums/hybrid_theory.jpg">'
            r"albums\hybrid_theory.jpg</a></div>"
            % {"STORAGE_URL": default_storage.url("")},
            html=True,
        )
        self.assertNotContains(
            response,
            '<input type="file" name="cover_art" id="id_cover_art">',
            html=True,
        )
        response = self.client.get(reverse("admin:admin_widgets_album_add"))
        self.assertContains(
            response,
            '<div class="readonly">-</div>',
            html=True,
        )


@override_settings(ROOT_URLCONF="admin_widgets.urls")
class ForeignKeyRawIdWidgetTest(TestCase):
    def test_render(self):
        band = Band.objects.create(name="Linkin Park")
        band.album_set.create(
            name="Hybrid Theory", cover_art=r"albums\hybrid_theory.jpg"
        )
        rel_uuid = Album._meta.get_field("band").remote_field
        w = widgets.ForeignKeyRawIdWidget(rel_uuid, widget_admin_site)
        self.assertHTMLEqual(
            w.render("test", band.uuid, attrs={}),
            '<div><input type="text" name="test" value="%(banduuid)s" '
            'class="vForeignKeyRawIdAdminField vUUIDField">'
            '<a href="/admin_widgets/band/?_to_field=uuid" class="related-lookup" '
            'id="lookup_id_test" title="Lookup"></a>&nbsp;<strong>'
            '<a href="/admin_widgets/band/%(bandpk)s/change/">Linkin Park</a>'
            "</strong></div>" % {"banduuid": band.uuid, "bandpk": band.pk},
        )

        rel_id = ReleaseEvent._meta.get_field("album").remote_field
        w = widgets.ForeignKeyRawIdWidget(rel_id, widget_admin_site)
        self.assertHTMLEqual(
            w.render("test", None, attrs={}),
            '<div><input type="text" name="test" class="vForeignKeyRawIdAdminField">'
            '<a href="/admin_widgets/album/?_to_field=id" class="related-lookup" '
            'id="lookup_id_test" title="Lookup"></a></div>',
        )

    def test_relations_to_non_primary_key(self):
        # ForeignKeyRawIdWidget works with fields which aren't related to
        # the model's primary key.
        apple = Inventory.objects.create(barcode=86, name="Apple")
        Inventory.objects.create(barcode=22, name="Pear")
        core = Inventory.objects.create(barcode=87, name="Core", parent=apple)
        rel = Inventory._meta.get_field("parent").remote_field
        w = widgets.ForeignKeyRawIdWidget(rel, widget_admin_site)
        self.assertHTMLEqual(
            w.render("test", core.parent_id, attrs={}),
            '<div><input type="text" name="test" value="86" '
            'class="vForeignKeyRawIdAdminField">'
            '<a href="/admin_widgets/inventory/?_to_field=barcode" '
            'class="related-lookup" id="lookup_id_test" title="Lookup"></a>'
            '&nbsp;<strong><a href="/admin_widgets/inventory/%(pk)s/change/">'
            "Apple</a></strong></div>" % {"pk": apple.pk},
        )

    def test_fk_related_model_not_in_admin(self):
        # FK to a model not registered with admin site. Raw ID widget should
        # have no magnifying glass link. See #16542
        big_honeycomb = Honeycomb.objects.create(location="Old tree")
        big_honeycomb.bee_set.create()
        rel = Bee._meta.get_field("honeycomb").remote_field

        w = widgets.ForeignKeyRawIdWidget(rel, widget_admin_site)
        self.assertHTMLEqual(
            w.render("honeycomb_widget", big_honeycomb.pk, attrs={}),
            '<input type="text" name="honeycomb_widget" value="%(hcombpk)s">'
            "&nbsp;<strong>%(hcomb)s</strong>"
            % {"hcombpk": big_honeycomb.pk, "hcomb": big_honeycomb},
        )

    def test_fk_to_self_model_not_in_admin(self):
        # FK to self, not registered with admin site. Raw ID widget should have
        # no magnifying glass link. See #16542
        subject1 = Individual.objects.create(name="Subject #1")
        Individual.objects.create(name="Child", parent=subject1)
        rel = Individual._meta.get_field("parent").remote_field

        w = widgets.ForeignKeyRawIdWidget(rel, widget_admin_site)
        self.assertHTMLEqual(
            w.render("individual_widget", subject1.pk, attrs={}),
            '<input type="text" name="individual_widget" value="%(subj1pk)s">'
            "&nbsp;<strong>%(subj1)s</strong>"
            % {"subj1pk": subject1.pk, "subj1": subject1},
        )

    def test_proper_manager_for_label_lookup(self):
        # see #9258
        rel = Inventory._meta.get_field("parent").remote_field
        w = widgets.ForeignKeyRawIdWidget(rel, widget_admin_site)

        hidden = Inventory.objects.create(barcode=93, name="Hidden", hidden=True)
        child_of_hidden = Inventory.objects.create(
            barcode=94, name="Child of hidden", parent=hidden
        )
        self.assertHTMLEqual(
            w.render("test", child_of_hidden.parent_id, attrs={}),
            '<div><input type="text" name="test" value="93" '
            '   class="vForeignKeyRawIdAdminField">'
            '<a href="/admin_widgets/inventory/?_to_field=barcode" '
            'class="related-lookup" id="lookup_id_test" title="Lookup"></a>'
            '&nbsp;<strong><a href="/admin_widgets/inventory/%(pk)s/change/">'
            "Hidden</a></strong></div>" % {"pk": hidden.pk},
        )

    def test_render_unsafe_limit_choices_to(self):
        rel = UnsafeLimitChoicesTo._meta.get_field("band").remote_field
        w = widgets.ForeignKeyRawIdWidget(rel, widget_admin_site)
        self.assertHTMLEqual(
            w.render("test", None),
            '<div><input type="text" name="test" class="vForeignKeyRawIdAdminField">'
            '<a href="/admin_widgets/band/?name=%22%26%3E%3Cescapeme&amp;'
            '_to_field=artist_ptr" class="related-lookup" id="lookup_id_test" '
            'title="Lookup"></a></div>',
        )

    def test_render_fk_as_pk_model(self):
        rel = VideoStream._meta.get_field("release_event").remote_field
        w = widgets.ForeignKeyRawIdWidget(rel, widget_admin_site)
        self.assertHTMLEqual(
            w.render("test", None),
            '<div><input type="text" name="test" class="vForeignKeyRawIdAdminField">'
            '<a href="/admin_widgets/releaseevent/?_to_field=album" '
            'class="related-lookup" id="lookup_id_test" title="Lookup"></a></div>',
        )


@override_settings(ROOT_URLCONF="admin_widgets.urls")
class ManyToManyRawIdWidgetTest(TestCase):
    def test_render(self):
        band = Band.objects.create(name="Linkin Park")

        m1 = Member.objects.create(name="Chester")
        m2 = Member.objects.create(name="Mike")
        band.members.add(m1, m2)
        rel = Band._meta.get_field("members").remote_field

        w = widgets.ManyToManyRawIdWidget(rel, widget_admin_site)
        self.assertHTMLEqual(
            w.render("test", [m1.pk, m2.pk], attrs={}),
            (
                '<div><input type="text" name="test" value="%(m1pk)s,%(m2pk)s" '
                '   class="vManyToManyRawIdAdminField">'
                '<a href="/admin_widgets/member/" class="related-lookup" '
                '   id="lookup_id_test" title="Lookup"></a></div>'
            )
            % {"m1pk": m1.pk, "m2pk": m2.pk},
        )

        self.assertHTMLEqual(
            w.render("test", [m1.pk]),
            (
                '<div><input type="text" name="test" value="%(m1pk)s" '
                '   class="vManyToManyRawIdAdminField">'
                '<a href="/admin_widgets/member/" class="related-lookup" '
                '   id="lookup_id_test" title="Lookup"></a></div>'
            )
            % {"m1pk": m1.pk},
        )

    def test_m2m_related_model_not_in_admin(self):
        # M2M relationship with model not registered with admin site. Raw ID
        # widget should have no magnifying glass link. See #16542
        consultor1 = Advisor.objects.create(name="Rockstar Techie")

        c1 = Company.objects.create(name="Doodle")
        c2 = Company.objects.create(name="Pear")
        consultor1.companies.add(c1, c2)
        rel = Advisor._meta.get_field("companies").remote_field

        w = widgets.ManyToManyRawIdWidget(rel, widget_admin_site)
        self.assertHTMLEqual(
            w.render("company_widget1", [c1.pk, c2.pk], attrs={}),
            '<input type="text" name="company_widget1" value="%(c1pk)s,%(c2pk)s">'
            % {"c1pk": c1.pk, "c2pk": c2.pk},
        )

        self.assertHTMLEqual(
            w.render("company_widget2", [c1.pk]),
            '<input type="text" name="company_widget2" value="%(c1pk)s">'
            % {"c1pk": c1.pk},
        )


@override_settings(ROOT_URLCONF="admin_widgets.urls")
class RelatedFieldWidgetWrapperTests(SimpleTestCase):
    def test_no_can_add_related(self):
        rel = Individual._meta.get_field("parent").remote_field
        w = widgets.AdminRadioSelect()
        # Used to fail with a name error.
        w = widgets.RelatedFieldWidgetWrapper(w, rel, widget_admin_site)
        self.assertFalse(w.can_add_related)

    def test_select_multiple_widget_cant_change_delete_related(self):
        rel = Individual._meta.get_field("parent").remote_field
        widget = forms.SelectMultiple()
        wrapper = widgets.RelatedFieldWidgetWrapper(
            widget,
            rel,
            widget_admin_site,
            can_add_related=True,
            can_change_related=True,
            can_delete_related=True,
        )
        self.assertTrue(wrapper.can_add_related)
        self.assertFalse(wrapper.can_change_related)
        self.assertFalse(wrapper.can_delete_related)

    def test_on_delete_cascade_rel_cant_delete_related(self):
        rel = Individual._meta.get_field("soulmate").remote_field
        widget = forms.Select()
        wrapper = widgets.RelatedFieldWidgetWrapper(
            widget,
            rel,
            widget_admin_site,
            can_add_related=True,
            can_change_related=True,
            can_delete_related=True,
        )
        self.assertTrue(wrapper.can_add_related)
        self.assertTrue(wrapper.can_change_related)
        self.assertFalse(wrapper.can_delete_related)

    def test_custom_widget_render(self):
        class CustomWidget(forms.Select):
            def render(self, *args, **kwargs):
                return "custom render output"

        rel = Album._meta.get_field("band").remote_field
        widget = CustomWidget()
        wrapper = widgets.RelatedFieldWidgetWrapper(
            widget,
            rel,
            widget_admin_site,
            can_add_related=True,
            can_change_related=True,
            can_delete_related=True,
        )
        output = wrapper.render("name", "value")
        self.assertIn("custom render output", output)

    def test_widget_delegates_value_omitted_from_data(self):
        class CustomWidget(forms.Select):
            def value_omitted_from_data(self, data, files, name):
                return False

        rel = Album._meta.get_field("band").remote_field
        widget = CustomWidget()
        wrapper = widgets.RelatedFieldWidgetWrapper(widget, rel, widget_admin_site)
        self.assertIs(wrapper.value_omitted_from_data({}, {}, "band"), False)

    def test_widget_is_hidden(self):
        rel = Album._meta.get_field("band").remote_field
        widget = forms.HiddenInput()
        widget.choices = ()
        wrapper = widgets.RelatedFieldWidgetWrapper(widget, rel, widget_admin_site)
        self.assertIs(wrapper.is_hidden, True)
        context = wrapper.get_context("band", None, {})
        self.assertIs(context["is_hidden"], True)
        output = wrapper.render("name", "value")
        # Related item links are hidden.
        self.assertNotIn("<a ", output)

    def test_widget_is_not_hidden(self):
        rel = Album._meta.get_field("band").remote_field
        widget = forms.Select()
        wrapper = widgets.RelatedFieldWidgetWrapper(widget, rel, widget_admin_site)
        self.assertIs(wrapper.is_hidden, False)
        context = wrapper.get_context("band", None, {})
        self.assertIs(context["is_hidden"], False)
        output = wrapper.render("name", "value")
        # Related item links are present.
        self.assertIn("<a ", output)

    def test_data_model_ref_when_model_name_is_camel_case(self):
        rel = VideoStream._meta.get_field("release_event").remote_field
        widget = forms.Select()
        wrapper = widgets.RelatedFieldWidgetWrapper(widget, rel, widget_admin_site)
        self.assertIs(wrapper.is_hidden, False)
        context = wrapper.get_context("release_event", None, {})
        self.assertEqual(context["model"], "release event")
        self.assertEqual(context["model_name"], "releaseevent")
        output = wrapper.render("stream", "value")
        expected = """
        <div class="related-widget-wrapper" data-model-ref="releaseevent">
          <select name="stream" data-context="available-source">
          </select>
          <a class="related-widget-wrapper-link add-related" id="add_id_stream"
             data-popup="yes" title="Add another release event"
             href="/admin_widgets/releaseevent/add/?_to_field=album&amp;_popup=1&_source_model=admin_widgets.videostream">
            <img src="/static/admin/img/icon-addlink.svg" alt="" width="24" height="24">
          </a>
        </div>
        """
        self.assertHTMLEqual(output, expected)

    def test_non_select_widget_cant_change_delete_related(self):
        main_band = Event._meta.get_field("main_band")
        widget = widgets.AdminRadioSelect()
        wrapper = widgets.RelatedFieldWidgetWrapper(
            widget,
            main_band,
            widget_admin_site,
            can_add_related=True,
            can_change_related=True,
            can_delete_related=True,
        )
        self.assertTrue(wrapper.can_add_related)
        self.assertFalse(wrapper.can_change_related)
        self.assertFalse(wrapper.can_delete_related)


@override_settings(ROOT_URLCONF="admin_widgets.urls")
class AdminWidgetPlaywrightTestCase(AdminPlaywrightTestCase):
    available_apps = ["admin_widgets"] + AdminPlaywrightTestCase.available_apps

    def setUp(self):
        self.u1 = User.objects.create_superuser(
            username="super", password="secret", email="super@example.com"
        )


class DateTimePickerPlaywrightTests(AdminWidgetPlaywrightTestCase):
    def test_show_hide_date_time_picker_widgets(self):
        """
        Pressing the ESC key or clicking on a widget value closes the date and
        time picker widgets.
        """
        self.admin_login(username="super", password="secret", login_url="/")
        # Open a page that has a date and time picker widgets
        self.page.goto(self.live_server_url + reverse("admin:admin_widgets_member_add"))

        # First, with the date picker widget ---------------------------------
        cal_icon = self.page.locator("#calendarlink0")
        calendarbox = self.page.locator("#calendarbox0")
        # The date picker is hidden
        self.expect(calendarbox).to_be_hidden()
        # Click the calendar icon
        cal_icon.click()
        # The date picker is visible
        self.expect(calendarbox).to_be_visible()
        # Press the ESC key
        self.page.keyboard.press("Escape")
        # The date picker is hidden again
        self.expect(calendarbox).to_be_hidden()
        # Click the calendar icon, then on the 15th of current month
        cal_icon.click()
        self.page.locator("#calendarbox0").get_by_text("15", exact=True).click()
        self.expect(calendarbox).to_be_hidden()
        self.expect(self.page.locator("#id_birthdate_0")).to_have_value(
            datetime.today().strftime("%Y-%m-") + "15",
        )

        # Then, with the time picker widget ----------------------------------
        time_icon = self.page.locator("#clocklink0")
        clockbox = self.page.locator("#clockbox0")
        # The time picker is hidden
        self.expect(clockbox).to_be_hidden()
        # Click the time icon
        time_icon.click()
        # The time picker is visible
        self.expect(clockbox).to_be_visible()
        self.expect(self.page.locator("ul.timelist li a")).to_have_text(
            ["Now", "Midnight", "6 a.m.", "Noon", "6 p.m."],
        )
        # Press the ESC key
        self.page.keyboard.press("Escape")
        # The time picker is hidden again
        self.expect(clockbox).to_be_hidden()
        # Click the time icon, then select the 'Noon' value
        time_icon.click()
        self.page.locator("#clockbox0").get_by_text("Noon").click()
        self.expect(clockbox).to_be_hidden()
        self.expect(self.page.locator("#id_birthdate_1")).to_have_value("12:00:00")

    def test_calendar_nonday_class(self):
        """
        Ensure cells that are not days of the month have the `nonday` CSS
        class. Refs #4574.
        """
        self.admin_login(username="super", password="secret", login_url="/")
        # Open a page that has a date and time picker widgets
        self.page.goto(self.live_server_url + reverse("admin:admin_widgets_member_add"))

        # fill in the birth date.
        self.page.locator("#id_birthdate_0").fill("2013-06-01")

        # Click the calendar icon
        self.page.locator("#calendarlink0").click()

        # get all the tds within the calendar
        calendar0 = self.page.locator("#calendarin0")
        tds = calendar0.locator("td").all()

        # make sure the first and last 6 cells have class nonday
        for td in tds[:6] + tds[-6:]:
            self.expect(td).to_have_class("nonday")

    def test_calendar_selected_class(self):
        """
        Ensure cell for the day in the input has the `selected` CSS class.
        Refs #4574.
        """
        self.admin_login(username="super", password="secret", login_url="/")
        # Open a page that has a date and time picker widgets
        self.page.goto(self.live_server_url + reverse("admin:admin_widgets_member_add"))

        # fill in the birth date.
        self.page.locator("#id_birthdate_0").fill("2013-06-01")

        # Click the calendar icon
        self.page.locator("#calendarlink0").click()

        # get all the tds within the calendar
        calendar0 = self.page.locator("#calendarin0")
        tds = calendar0.locator("td").all()

        # verify the selected cell
        selected = tds[6]
        self.expect(selected).to_have_class("selected")

        self.expect(selected).to_have_text("1")

    def test_calendar_no_selected_class(self):
        """
        Ensure no cells are given the selected class when the field is empty.
        Refs #4574.
        """
        self.admin_login(username="super", password="secret", login_url="/")
        # Open a page that has a date and time picker widgets
        self.page.goto(self.live_server_url + reverse("admin:admin_widgets_member_add"))

        # Click the calendar icon
        self.page.locator("#calendarlink0").click()

        # get all the tds within the calendar
        calendar0 = self.page.locator("#calendarin0")

        # verify there are no cells with the selected class
        self.expect(calendar0.locator("td.selected")).to_have_count(0)

    def test_calendar_show_date_from_input(self):
        """
        The calendar shows the date from the input field for every locale
        supported by Django.
        """
        self.admin_login(username="super", password="secret", login_url="/")

        # Enter test data
        member = Member.objects.create(
            name="Bob", birthdate=datetime(1984, 5, 15), gender="M"
        )

        # Get month name translations for every locale
        month_string = "May"
        path = os.path.join(
            os.path.dirname(import_module("django.contrib.admin").__file__), "locale"
        )
        url = reverse("admin:admin_widgets_member_change", args=(member.pk,))
        with self.small_screen_size():
            for language_code, language_name in settings.LANGUAGES:
                try:
                    catalog = gettext.translation("djangojs", path, [language_code])
                except OSError:
                    continue
                if month_string in catalog._catalog:
                    month_name = catalog._catalog[month_string]
                else:
                    month_name = month_string

                # Get the expected caption.
                may_translation = month_name
                expected_caption = "{:s} {:d}".format(may_translation, 1984)

                # Every locale.
                with override_settings(LANGUAGE_CODE=language_code):
                    # Open a page that has a date picker widget.
                    self.page.goto(self.live_server_url + url)
                    # Click on the calendar icon.
                    self.page.locator("#calendarlink0").click()
                    # The right month and year are displayed.
                    self.expect(self.page.locator("#calendarin0 caption")).to_have_text(
                        expected_caption
                    )

    def test_calendar_press_enter_focus_element(self):
        self.admin_login(username="super", password="secret", login_url="/")
        self.page.goto(self.live_server_url + reverse("admin:admin_widgets_member_add"))
        icon = self.page.locator("#calendarlink0")
        expected_focus = self.page.locator("div#calendarin0 table td.today a")
        icon.press("Enter")
        self.expect(expected_focus).to_be_focused()

    @override_settings(TIME_ZONE="Asia/Seoul")
    def test_timezone_warning_message(self):
        self.admin_login(username="super", password="secret", login_url="/")

        self.page.goto(self.live_server_url + reverse("admin:admin_widgets_member_add"))

        datetime_el = self.page.locator("p.datetime")
        warnings = self.page.locator("div.field-birthdate div.timezonewarning")
        self.expect(warnings).to_have_count(1)

        warning = warnings.first
        self.expect(warning).to_be_visible()
        # Warning messages are generally located just above the field block.
        self.assertTrue(
            warning.evaluate(
                "(el, dtEl) => el.nextElementSibling === dtEl",
                datetime_el.element_handle(),
            )
        )

        date = datetime_el.locator("input").first
        date.fill("invalid")
        self.page.locator("input[name='_save']").click()

        errors = self.page.locator("#id_birthdate_error")
        warning = self.page.locator("div.help.timezonewarning")
        # warning message appears above the error message.
        self.assertTrue(
            warning.evaluate(
                "(el, errEl) => el.nextElementSibling === errEl",
                errors.element_handle(),
            )
        )


@requires_tz_support
@override_settings(TIME_ZONE="Asia/Singapore")
class DateTimePickerShortcutsPlaywrightTests(AdminWidgetPlaywrightTestCase):
    def test_date_time_picker_shortcuts(self):
        """
        date/time/datetime picker shortcuts work in the current time zone.
        Refs #20663.

        This test case is fairly tricky, it relies on playwright still running
        the browser in the default time zone "America/Chicago" despite
        `override_settings` changing the time zone to "Asia/Singapore".
        """
        self.admin_login(username="super", password="secret", login_url="/")

        error_margin = timedelta(seconds=10)

        # If we are neighbouring a DST, we add an hour of error margin.
        tz = zoneinfo.ZoneInfo("America/Chicago")
        utc_now = datetime.now(zoneinfo.ZoneInfo("UTC"))
        tz_yesterday = (utc_now - timedelta(days=1)).astimezone(tz).tzname()
        tz_tomorrow = (utc_now + timedelta(days=1)).astimezone(tz).tzname()
        if tz_yesterday != tz_tomorrow:
            error_margin += timedelta(hours=1)

        self.page.goto(self.live_server_url + reverse("admin:admin_widgets_member_add"))
        self.page.locator("#id_name").fill("test")
        # Click on the "today" and "now" shortcuts.
        shortcuts = self.page.locator(".field-birthdate .datetimeshortcuts")

        now = datetime.now()
        for shortcut in shortcuts.all():
            shortcut.locator("a").first.click()

        # There is a time zone mismatch warning.
        # Warning: This would effectively fail if the TIME_ZONE defined in the
        # settings has the same UTC offset as "Asia/Singapore" because the
        # mismatch warning would be rightfully missing from the page.
        self.expect(
            self.page.locator(".field-birthdate .timezonewarning")
        ).to_have_count(1)

        # Submit the form.
        self.page.locator("input[name='_save']").click()
        self.expect(self.page.locator(".messagelist .success")).to_be_visible()

        # Make sure that "now" in JavaScript is within 10 seconds
        # from "now" on the server side.
        member = Member.objects.get(name="test")
        self.assertGreater(member.birthdate, now - error_margin)
        self.assertLess(member.birthdate, now + error_margin)


# The above tests run with Asia/Singapore which are on the positive side of
# UTC. Here we test with a timezone on the negative side.
@override_settings(TIME_ZONE="US/Eastern")
class DateTimePickerAltTimezonePlaywrightTests(DateTimePickerShortcutsPlaywrightTests):
    pass


class HorizontalVerticalFilterPlaywrightTests(AdminWidgetPlaywrightTestCase):
    def setUp(self):
        super().setUp()
        self.lisa = Student.objects.create(name="Lisa")
        self.john = Student.objects.create(name="John")
        self.bob = Student.objects.create(name="Bob")
        self.peter = Student.objects.create(name="Peter")
        self.jenny = Student.objects.create(name="Jenny")
        self.jason = Student.objects.create(name="Jason")
        self.cliff = Student.objects.create(name="Cliff")
        self.arthur = Student.objects.create(name="Arthur")
        self.school = School.objects.create(name="School of Awesome")

    def assertButtonsDisabled(
        self,
        mode,
        field_name,
        choose_btn_disabled=False,
        remove_btn_disabled=False,
        choose_all_btn_disabled=False,
        remove_all_btn_disabled=False,
    ):
        choose_button = self.page.locator("#id_%s_add" % field_name)
        choose_all_button = self.page.locator("#id_%s_add_all" % field_name)
        remove_button = self.page.locator("#id_%s_remove" % field_name)
        remove_all_button = self.page.locator("#id_%s_remove_all" % field_name)
        if choose_btn_disabled:
            self.expect(choose_button).to_be_disabled()
        else:
            self.expect(choose_button).to_be_enabled()
        if remove_btn_disabled:
            self.expect(remove_button).to_be_disabled()
        else:
            self.expect(remove_button).to_be_enabled()
        if mode == "horizontal":
            if choose_all_btn_disabled:
                self.expect(choose_all_button).to_be_disabled()
            else:
                self.expect(choose_all_button).to_be_enabled()
            if remove_all_btn_disabled:
                self.expect(remove_all_button).to_be_disabled()
            else:
                self.expect(remove_all_button).to_be_enabled()

    def execute_basic_operations(self, mode, field_name):
        original_url = self.page.url

        from_box = "#id_%s_from" % field_name
        to_box = "#id_%s_to" % field_name
        choose_button = "#id_%s_add" % field_name
        choose_all_button = "#id_%s_add_all" % field_name
        remove_button = "#id_%s_remove" % field_name
        remove_all_button = "#id_%s_remove_all" % field_name

        # Initial positions ---------------------------------------------------
        self.assertEqual(
            [
                el.get_attribute("value")
                for el in self.page.locator(f"{from_box} > option").all()
            ],
            [
                str(self.arthur.id),
                str(self.bob.id),
                str(self.cliff.id),
                str(self.jason.id),
                str(self.jenny.id),
                str(self.john.id),
            ],
        )
        self.assertEqual(
            [
                el.get_attribute("value")
                for el in self.page.locator(f"{to_box} > option").all()
            ],
            [str(self.lisa.id), str(self.peter.id)],
        )
        self.assertButtonsDisabled(
            mode,
            field_name,
            choose_btn_disabled=True,
            remove_btn_disabled=True,
            choose_all_btn_disabled=False,
            remove_all_btn_disabled=False,
        )

        # Click 'Choose all' --------------------------------------------------
        if mode == "horizontal":
            self.page.locator(choose_all_button).click()
        elif mode == "vertical":
            # There's no 'Choose all' button in vertical mode, so individually
            # select all options and click 'Choose'.
            all_values = [
                el.get_attribute("value")
                for el in self.page.locator(f"{from_box} > option").all()
            ]
            self.page.locator(from_box).select_option(value=all_values)
            self.page.locator(choose_button).click()
        self.assertEqual(
            [
                el.get_attribute("value")
                for el in self.page.locator(f"{from_box} > option").all()
            ],
            [],
        )
        self.assertEqual(
            [
                el.get_attribute("value")
                for el in self.page.locator(f"{to_box} > option").all()
            ],
            [
                str(self.lisa.id),
                str(self.peter.id),
                str(self.arthur.id),
                str(self.bob.id),
                str(self.cliff.id),
                str(self.jason.id),
                str(self.jenny.id),
                str(self.john.id),
            ],
        )
        self.assertButtonsDisabled(
            mode,
            field_name,
            choose_btn_disabled=True,
            remove_btn_disabled=True,
            choose_all_btn_disabled=True,
            remove_all_btn_disabled=False,
        )

        # Click 'Remove all' --------------------------------------------------
        if mode == "horizontal":
            self.page.locator(remove_all_button).click()
        elif mode == "vertical":
            # There's no 'Remove all' button in vertical mode, so individually
            # select all options and click 'Remove'.
            all_values = [
                el.get_attribute("value")
                for el in self.page.locator(f"{to_box} > option").all()
            ]
            self.page.locator(to_box).select_option(value=all_values)
            self.page.locator(remove_button).click()
        self.assertEqual(
            [
                el.get_attribute("value")
                for el in self.page.locator(f"{from_box} > option").all()
            ],
            [
                str(self.lisa.id),
                str(self.peter.id),
                str(self.arthur.id),
                str(self.bob.id),
                str(self.cliff.id),
                str(self.jason.id),
                str(self.jenny.id),
                str(self.john.id),
            ],
        )
        self.assertEqual(
            [
                el.get_attribute("value")
                for el in self.page.locator(f"{to_box} > option").all()
            ],
            [],
        )
        self.assertButtonsDisabled(
            mode,
            field_name,
            choose_btn_disabled=True,
            remove_btn_disabled=True,
            choose_all_btn_disabled=False,
            remove_all_btn_disabled=True,
        )

        # Choose some options ------------------------------------------------
        from_lisa_option = self.page.locator(
            '{} > option[value="{}"]'.format(from_box, self.lisa.id)
        )

        # Check the title attribute is there for tool tips: ticket #20821
        self.expect(from_lisa_option).to_have_attribute(
            "title", from_lisa_option.inner_text()
        )

        self.page.locator(from_box).select_option(
            value=[
                str(self.lisa.id),
                str(self.jason.id),
                str(self.bob.id),
                str(self.john.id),
            ]
        )
        self.assertButtonsDisabled(
            mode,
            field_name,
            choose_btn_disabled=False,
            remove_btn_disabled=True,
            choose_all_btn_disabled=False,
            remove_all_btn_disabled=True,
        )
        self.page.locator(choose_button).click()
        self.assertButtonsDisabled(
            mode,
            field_name,
            choose_btn_disabled=True,
            remove_btn_disabled=True,
            choose_all_btn_disabled=False,
            remove_all_btn_disabled=False,
        )

        self.assertEqual(
            [
                el.get_attribute("value")
                for el in self.page.locator(f"{from_box} > option").all()
            ],
            [
                str(self.peter.id),
                str(self.arthur.id),
                str(self.cliff.id),
                str(self.jenny.id),
            ],
        )
        self.assertEqual(
            [
                el.get_attribute("value")
                for el in self.page.locator(f"{to_box} > option").all()
            ],
            [
                str(self.lisa.id),
                str(self.bob.id),
                str(self.jason.id),
                str(self.john.id),
            ],
        )

        # Check the tooltip is still there after moving: ticket #20821
        to_lisa_option = self.page.locator(
            '{} > option[value="{}"]'.format(to_box, self.lisa.id)
        )
        self.expect(to_lisa_option).to_have_attribute(
            "title", to_lisa_option.inner_text()
        )

        # Remove some options -------------------------------------------------
        self.page.locator(to_box).select_option(
            value=[str(self.lisa.id), str(self.bob.id)]
        )
        self.assertButtonsDisabled(
            mode,
            field_name,
            choose_btn_disabled=True,
            remove_btn_disabled=False,
            choose_all_btn_disabled=False,
            remove_all_btn_disabled=False,
        )
        self.page.locator(remove_button).click()
        self.assertButtonsDisabled(
            mode,
            field_name,
            choose_btn_disabled=True,
            remove_btn_disabled=True,
            choose_all_btn_disabled=False,
            remove_all_btn_disabled=False,
        )

        self.assertEqual(
            [
                el.get_attribute("value")
                for el in self.page.locator(f"{from_box} > option").all()
            ],
            [
                str(self.peter.id),
                str(self.arthur.id),
                str(self.cliff.id),
                str(self.jenny.id),
                str(self.lisa.id),
                str(self.bob.id),
            ],
        )
        self.assertEqual(
            [
                el.get_attribute("value")
                for el in self.page.locator(f"{to_box} > option").all()
            ],
            [str(self.jason.id), str(self.john.id)],
        )

        # Choose some more options --------------------------------------------
        self.page.locator(from_box).select_option(
            value=[str(self.arthur.id), str(self.cliff.id)]
        )
        self.page.locator(choose_button).click()

        self.assertEqual(
            [
                el.get_attribute("value")
                for el in self.page.locator(f"{from_box} > option").all()
            ],
            [
                str(self.peter.id),
                str(self.jenny.id),
                str(self.lisa.id),
                str(self.bob.id),
            ],
        )
        self.assertEqual(
            [
                el.get_attribute("value")
                for el in self.page.locator(f"{to_box} > option").all()
            ],
            [
                str(self.jason.id),
                str(self.john.id),
                str(self.arthur.id),
                str(self.cliff.id),
            ],
        )

        # Choose some more options --------------------------------------------
        self.page.locator(from_box).select_option(
            value=[str(self.peter.id), str(self.lisa.id)]
        )

        # Confirm they're selected after clicking inactive buttons: ticket
        # #26575
        self.assertEqual(
            [
                el.get_attribute("value")
                for el in self.page.locator(f"{from_box} > option:checked").all()
            ],
            [str(self.peter.id), str(self.lisa.id)],
        )
        self.page.locator(remove_button).click(force=True)
        self.assertEqual(
            [
                el.get_attribute("value")
                for el in self.page.locator(f"{from_box} > option:checked").all()
            ],
            [str(self.peter.id), str(self.lisa.id)],
        )

        # Unselect the options ------------------------------------------------
        self.page.locator(from_box).select_option([])

        # Choose some more options --------------------------------------------
        self.page.locator(to_box).select_option(
            value=[str(self.jason.id), str(self.john.id)]
        )

        # Confirm they're selected after clicking inactive buttons: ticket
        # #26575
        self.assertEqual(
            [
                el.get_attribute("value")
                for el in self.page.locator(f"{to_box} > option:checked").all()
            ],
            [str(self.jason.id), str(self.john.id)],
        )
        self.page.locator(choose_button).click(force=True)
        self.assertEqual(
            [
                el.get_attribute("value")
                for el in self.page.locator(f"{to_box} > option:checked").all()
            ],
            [str(self.jason.id), str(self.john.id)],
        )

        # Unselect the options ------------------------------------------------
        self.page.locator(to_box).select_option([])

        # Pressing buttons shouldn't change the URL.
        self.assertEqual(self.page.url, original_url)

    def test_basic(self):
        self.school.students.set([self.lisa, self.peter])
        self.school.alumni.set([self.lisa, self.peter])

        with self.small_screen_size():
            self.admin_login(username="super", password="secret", login_url="/")
            self.page.goto(
                self.live_server_url
                + reverse("admin:admin_widgets_school_change", args=(self.school.id,))
            )

            self.execute_basic_operations("vertical", "students")
            self.execute_basic_operations("horizontal", "alumni")

            # Save, everything should be stored properly stored in the
            # database.
            self.page.locator('input[value="Save"]').click()
            self.page.wait_for_load_state("load")
        self.school = School.objects.get(id=self.school.id)  # Reload from database
        self.assertEqual(
            list(self.school.students.all()),
            [self.arthur, self.cliff, self.jason, self.john],
        )
        self.assertEqual(
            list(self.school.alumni.all()),
            [self.arthur, self.cliff, self.jason, self.john],
        )

    def test_filter(self):
        """
        Typing in the search box filters out options displayed in the 'from'
        box.
        """
        self.school.students.set([self.lisa, self.peter])
        self.school.alumni.set([self.lisa, self.peter])

        with self.small_screen_size():
            self.admin_login(username="super", password="secret", login_url="/")
            self.page.goto(
                self.live_server_url
                + reverse("admin:admin_widgets_school_change", args=(self.school.id,))
            )

            for field_name in ["students", "alumni"]:
                from_box = "#id_%s_from" % field_name
                to_box = "#id_%s_to" % field_name
                choose_link = "#id_%s_add" % field_name
                remove_link = "#id_%s_remove" % field_name
                input = self.page.locator("#id_%s_input" % field_name)
                # Initial values.
                self.assertEqual(
                    [
                        el.get_attribute("value")
                        for el in self.page.locator(f"{from_box} > option").all()
                    ],
                    [
                        str(self.arthur.id),
                        str(self.bob.id),
                        str(self.cliff.id),
                        str(self.jason.id),
                        str(self.jenny.id),
                        str(self.john.id),
                    ],
                )
                # Typing in some characters filters out non-matching options.
                input.press("a")
                self.assertEqual(
                    [
                        el.get_attribute("value")
                        for el in self.page.locator(f"{from_box} > option").all()
                    ],
                    [str(self.arthur.id), str(self.jason.id)],
                )
                input.press("R")
                self.assertEqual(
                    [
                        el.get_attribute("value")
                        for el in self.page.locator(f"{from_box} > option").all()
                    ],
                    [str(self.arthur.id)],
                )
                # Clearing the text box makes the other options reappear.
                input.press("Backspace")
                self.assertEqual(
                    [
                        el.get_attribute("value")
                        for el in self.page.locator(f"{from_box} > option").all()
                    ],
                    [str(self.arthur.id), str(self.jason.id)],
                )
                input.press("Backspace")
                self.assertEqual(
                    [
                        el.get_attribute("value")
                        for el in self.page.locator(f"{from_box} > option").all()
                    ],
                    [
                        str(self.arthur.id),
                        str(self.bob.id),
                        str(self.cliff.id),
                        str(self.jason.id),
                        str(self.jenny.id),
                        str(self.john.id),
                    ],
                )

                # Choosing a filtered option sends it properly to the 'to' box.
                input.press("a")
                self.assertEqual(
                    [
                        el.get_attribute("value")
                        for el in self.page.locator(f"{from_box} > option").all()
                    ],
                    [str(self.arthur.id), str(self.jason.id)],
                )
                self.page.locator(from_box).select_option(value=str(self.jason.id))
                self.page.locator(choose_link).click()
                self.assertEqual(
                    [
                        el.get_attribute("value")
                        for el in self.page.locator(f"{from_box} > option").all()
                    ],
                    [str(self.arthur.id)],
                )
                self.assertEqual(
                    [
                        el.get_attribute("value")
                        for el in self.page.locator(f"{to_box} > option").all()
                    ],
                    [
                        str(self.lisa.id),
                        str(self.peter.id),
                        str(self.jason.id),
                    ],
                )

                self.page.locator(to_box).select_option(value=str(self.lisa.id))
                self.page.locator(remove_link).click()
                self.assertEqual(
                    [
                        el.get_attribute("value")
                        for el in self.page.locator(f"{from_box} > option").all()
                    ],
                    [str(self.arthur.id), str(self.lisa.id)],
                )
                self.assertEqual(
                    [
                        el.get_attribute("value")
                        for el in self.page.locator(f"{to_box} > option").all()
                    ],
                    [str(self.peter.id), str(self.jason.id)],
                )

                input.fill("")  # Clear text box
                self.assertEqual(
                    [
                        el.get_attribute("value")
                        for el in self.page.locator(f"{from_box} > option").all()
                    ],
                    [
                        str(self.arthur.id),
                        str(self.bob.id),
                        str(self.cliff.id),
                        str(self.jenny.id),
                        str(self.john.id),
                        str(self.lisa.id),
                    ],
                )
                self.assertEqual(
                    [
                        el.get_attribute("value")
                        for el in self.page.locator(f"{to_box} > option").all()
                    ],
                    [str(self.peter.id), str(self.jason.id)],
                )

                # Pressing enter on a filtered option sends it properly to
                # the 'to' box.
                self.page.locator(to_box).select_option(value=str(self.jason.id))
                self.page.locator(remove_link).click()
                input.press_sequentially("ja")
                self.assertEqual(
                    [
                        el.get_attribute("value")
                        for el in self.page.locator(f"{from_box} > option").all()
                    ],
                    [str(self.jason.id)],
                )
                input.press("Enter")
                self.assertEqual(
                    [
                        el.get_attribute("value")
                        for el in self.page.locator(f"{to_box} > option").all()
                    ],
                    [str(self.peter.id), str(self.jason.id)],
                )
                input.fill("")

            # Save, everything should be stored properly in the database.
            self.page.locator('input[value="Save"]').click()
            self.page.wait_for_load_state("load")
        self.school = School.objects.get(id=self.school.id)  # Reload from database
        self.assertEqual(list(self.school.students.all()), [self.jason, self.peter])
        self.assertEqual(list(self.school.alumni.all()), [self.jason, self.peter])

    def test_back_button_bug(self):
        """
        Some browsers had a bug where navigating away from the change page
        and then clicking the browser's back button would clear the
        filter_horizontal/filter_vertical widgets (#13614).
        """
        self.school.students.set([self.lisa, self.peter])
        self.school.alumni.set([self.lisa, self.peter])
        self.admin_login(username="super", password="secret", login_url="/")
        change_url = reverse(
            "admin:admin_widgets_school_change", args=(self.school.id,)
        )
        self.page.goto(self.live_server_url + change_url)
        # Navigate away and go back to the change form page.
        self.page.get_by_role("link", name="Home").click()
        self.page.go_back()
        expected_unselected_values = [
            str(self.arthur.id),
            str(self.bob.id),
            str(self.cliff.id),
            str(self.jason.id),
            str(self.jenny.id),
            str(self.john.id),
        ]
        expected_selected_values = [str(self.lisa.id), str(self.peter.id)]
        # Everything is still in place
        self.assertEqual(
            [
                el.get_attribute("value")
                for el in self.page.locator("#id_students_from > option").all()
            ],
            expected_unselected_values,
        )
        self.assertEqual(
            [
                el.get_attribute("value")
                for el in self.page.locator("#id_students_to > option").all()
            ],
            expected_selected_values,
        )
        self.assertEqual(
            [
                el.get_attribute("value")
                for el in self.page.locator("#id_alumni_from > option").all()
            ],
            expected_unselected_values,
        )
        self.assertEqual(
            [
                el.get_attribute("value")
                for el in self.page.locator("#id_alumni_to > option").all()
            ],
            expected_selected_values,
        )

    def test_refresh_page(self):
        """
        Horizontal and vertical filter widgets keep selected options on page
        reload (#22955).
        """
        self.school.students.add(self.arthur, self.jason)
        self.school.alumni.add(self.arthur, self.jason)

        self.admin_login(username="super", password="secret", login_url="/")
        change_url = reverse(
            "admin:admin_widgets_school_change", args=(self.school.id,)
        )
        self.page.goto(self.live_server_url + change_url)

        self.expect(self.page.locator("#id_students_to > option")).to_have_count(2)

        self.page.reload()

        self.expect(self.page.locator("#id_students_to > option")).to_have_count(2)

    def test_form_submission_via_enter_key_with_filter_horizontal(self):
        """
        The main form can be submitted correctly by pressing the enter key.
        There is no shadowing from other buttons inside the form.
        """
        self.school.students.set([self.peter])
        self.school.alumni.set([self.lisa])

        self.admin_login(username="super", password="secret", login_url="/")
        self.page.goto(
            self.live_server_url
            + reverse("admin:admin_widgets_school_change", args=(self.school.id,))
        )

        self.page.locator("#id_students_from").select_option(value=str(self.lisa.id))
        self.page.locator("#id_students_add").click()
        self.page.locator("#id_alumni_from").select_option(value=str(self.peter.id))
        self.page.locator("#id_alumni_add").click()

        # Trigger form submission via Enter key on a text input field.
        name_input = self.page.locator("#id_name")
        name_input.click()
        name_input.press("Enter")

        # Form was submitted, success message should be shown.
        success = self.page.locator("li.success")
        self.expect(success).to_contain_text("was changed successfully.")

        # Changes should be stored properly in the database.
        school = School.objects.get(id=self.school.id)
        self.assertSequenceEqual(
            school.students.all().order_by("name"), [self.lisa, self.peter]
        )
        self.assertSequenceEqual(
            school.alumni.all().order_by("name"), [self.lisa, self.peter]
        )

    @screenshot_cases(["desktop_size", "mobile_size", "rtl", "dark", "high_contrast"])
    def test_vertical_arrow_buttons_layout(self):
        self.admin_login(username="super", password="secret", login_url="/")
        self.page.goto(
            self.live_server_url
            + reverse("admin:admin_widgets_school_change", args=(self.school.id,))
        )
        self.page.locator(".field-students").scroll_into_view_if_needed()
        buttons = self.page.locator("div.selector.stacked ul.selector-chooser")
        self.expect(buttons).to_be_visible()
        self.take_screenshot("arrow_buttons")


class AdminRawIdWidgetPlaywrightTests(AdminWidgetPlaywrightTestCase):
    def setUp(self):
        super().setUp()
        self.blues = Band.objects.create(name="Bogey Blues")
        self.potatoes = Band.objects.create(name="Green Potatoes")

    @screenshot_cases(["desktop_size", "mobile_size", "rtl", "dark", "high_contrast"])
    def test_ForeignKey(self):
        self.admin_login(username="super", password="secret", login_url="/")
        self.page.goto(self.live_server_url + reverse("admin:admin_widgets_event_add"))
        self.take_screenshot("raw_id_widget")

        main_band_input = self.page.locator("#id_main_band")

        # No value has been selected yet.
        self.expect(main_band_input).to_have_value("")

        # Open the popup window and click on a band.
        with self.page.expect_popup() as popup_info:
            self.page.locator("#lookup_id_main_band").click()
        popup = popup_info.value
        link = popup.get_by_role("link", name="Bogey Blues")
        self.expect(link).to_have_attribute(
            "href", re.compile(rf"/band/{self.blues.pk}/")
        )
        with popup.expect_event("close"):
            link.evaluate("el => setTimeout(() => el.click())")

        # The field now contains the selected band's id.
        self.expect(main_band_input).to_have_value(str(self.blues.pk))

        # Reopen the popup window and click on another band.
        with self.page.expect_popup() as popup_info:
            self.page.locator("#lookup_id_main_band").click()
        popup = popup_info.value
        link = popup.get_by_role("link", name="Green Potatoes")
        self.expect(link).to_have_attribute(
            "href", re.compile(rf"/band/{self.potatoes.pk}/")
        )
        with popup.expect_event("close"):
            link.evaluate("el => setTimeout(() => el.click())")

        # The field now contains the other selected band's id.
        self.expect(main_band_input).to_have_value(str(self.potatoes.pk))

    def test_many_to_many(self):
        self.admin_login(username="super", password="secret", login_url="/")
        self.page.goto(self.live_server_url + reverse("admin:admin_widgets_event_add"))

        supporting_bands_input = self.page.locator("#id_supporting_bands")

        # No value has been selected yet.
        self.expect(supporting_bands_input).to_have_value("")

        # Help text for the field is displayed.
        help_text = self.page.locator(".field-supporting_bands div.help")
        self.expect(help_text).to_have_text("Supporting Bands.")

        # Open the popup window and click on a band.
        with self.page.expect_popup() as popup_info:
            self.page.locator("#lookup_id_supporting_bands").click()
        popup = popup_info.value
        link = popup.get_by_role("link", name="Bogey Blues")
        self.expect(link).to_have_attribute(
            "href", re.compile(rf"/band/{self.blues.pk}/")
        )
        with popup.expect_event("close"):
            link.evaluate("el => setTimeout(() => el.click())")

        # The field now contains the selected band's id.
        self.expect(supporting_bands_input).to_have_value(str(self.blues.pk))

        # Reopen the popup window and click on another band.
        with self.page.expect_popup() as popup_info:
            self.page.locator("#lookup_id_supporting_bands").click()
        popup = popup_info.value
        link = popup.get_by_role("link", name="Green Potatoes")
        self.expect(link).to_have_attribute(
            "href", re.compile(rf"/band/{self.potatoes.pk}/")
        )
        with popup.expect_event("close"):
            link.evaluate("el => setTimeout(() => el.click())")

        # The field now contains the two selected bands' ids.
        self.expect(supporting_bands_input).to_have_value(
            f"{self.blues.pk},{self.potatoes.pk}",
        )


class RelatedFieldWidgetPlaywrightTests(AdminWidgetPlaywrightTestCase):
    def test_ForeignKey_using_to_field(self):
        self.admin_login(username="super", password="secret", login_url="/")
        self.page.goto(
            self.live_server_url + reverse("admin:admin_widgets_profile_add")
        )

        # Click the Add User button to add new
        with self.page.expect_popup() as popup_info:
            self.page.locator("#add_id_user").click()
        popup = popup_info.value
        popup.locator("#id_password").fill("password")

        username_value = "newuser"
        popup.locator("#id_username").fill(username_value)

        save_button_css_selector = ".submit-row > input[type=submit]"
        with popup.expect_event("close"):
            popup.locator(save_button_css_selector).click()

        # The field now contains the new user
        self.page.locator("#view_id_user").click()
        self.expect(self.page.locator("#id_username")).to_have_value("newuser")
        self.page.go_back()

        # Chrome and Safari don't update related object links when selecting
        # the same option as previously submitted. As a consequence, the
        # "pencil" and "eye" buttons remain disable, so select
        # "- Select an option -" first.
        self.page.locator("#id_user").select_option(index=0)
        self.page.locator("#id_user").select_option(value="newuser")
        # Click the Change User button to change it
        with self.page.expect_popup() as popup_info:
            self.page.locator("#change_id_user").click()
        popup = popup_info.value

        username_value = "changednewuser"
        popup.locator("#id_username").fill(username_value)

        with popup.expect_event("close"):
            popup.locator(save_button_css_selector).click()

        # The field now contains the changed user
        self.page.locator("#view_id_user").click()
        self.expect(self.page.locator("#id_username")).to_have_value("changednewuser")
        self.page.go_back()

        self.page.locator("#id_user").select_option(value="changednewuser")
        # Go ahead and submit the form to make sure it works
        self.page.locator("input[name='_save']").click()
        self.expect(self.page.locator("li.success")).to_have_text(
            "The profile “changednewuser” was added successfully.",
        )
        profiles = Profile.objects.all()
        self.assertEqual(len(profiles), 1)
        self.assertEqual(profiles[0].user.username, username_value)


@skipUnless(Image, "Pillow not installed")
class ImageFieldWidgetsPlaywrightTests(AdminWidgetPlaywrightTestCase):
    name_input_id = "id_name"
    photo_input_id = "id_photo"
    tests_files_folder = "%s/files" % Path(__file__).parent.parent
    clear_checkbox_id = "photo-clear_id"

    def _run_image_upload_path(self):
        self.admin_login(username="super", password="secret", login_url="/")
        self.page.goto(
            self.live_server_url + reverse("admin:admin_widgets_student_add"),
        )
        # Add a student.
        self.page.locator(f"#{self.name_input_id}").fill("Joe Doe")
        self.page.locator(f"#{self.photo_input_id}").set_input_files(
            f"{self.tests_files_folder}/test.png"
        )
        self.page.locator("input[value='Save and continue editing']").click()
        self.expect(self.page.locator(".messagelist .success")).to_be_visible()
        student = Student.objects.last()
        self.assertEqual(student.name, "Joe Doe")
        self.assertRegex(student.photo.name, r"^photos\/(test|test_.+).png")

    def test_clearablefileinput_widget(self):
        self._run_image_upload_path()
        self.page.locator(f"#{self.clear_checkbox_id}").click()
        self.page.locator("input[value='Save and continue editing']").click()
        self.expect(self.page.locator(".messagelist .success")).to_be_visible()
        student = Student.objects.last()
        self.assertEqual(student.name, "Joe Doe")
        self.assertEqual(student.photo.name, "")
        # "Currently" with "Clear" checkbox and "Change" are not shown.
        photo_field_row = self.page.locator(".field-photo")
        self.expect(photo_field_row).not_to_contain_text("Currently")
        self.expect(photo_field_row).not_to_contain_text("Change")

    def test_clearablefileinput_widget_invalid_file(self):
        self._run_image_upload_path()
        self.page.locator(f"#{self.photo_input_id}").set_input_files(
            f"{self.tests_files_folder}/brokenimg.png"
        )
        self.page.locator("input[value='Save and continue editing']").click()
        self.expect(self.page.locator(".errorlist li")).to_have_text(
            "Upload a valid image. The file you uploaded was either not an image "
            "or a corrupted image.",
        )
        # "Currently" with "Clear" checkbox and "Change" still shown.
        photo_field_row = self.page.locator(".field-photo")
        self.expect(photo_field_row).to_contain_text("Currently")
        self.expect(photo_field_row).to_contain_text("Change")

    def test_clearablefileinput_widget_preserve_clear_checkbox(self):
        self._run_image_upload_path()
        # "Clear" is not checked by default.
        self.expect(self.page.locator(f"#{self.clear_checkbox_id}")).not_to_be_checked()
        # "Clear" was checked, but a validation error is raised.
        self.page.locator(f"#{self.name_input_id}").clear()
        self.page.locator(f"#{self.clear_checkbox_id}").click()
        self.page.locator("input[value='Save and continue editing']").click()
        self.expect(self.page.locator(".errorlist li")).to_have_text(
            "This field is required.",
        )
        # "Clear" persists checked.
        self.expect(self.page.locator(f"#{self.clear_checkbox_id}")).to_be_checked()
