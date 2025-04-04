import gettext
import os
import re
import zoneinfo
from datetime import datetime, timedelta
from importlib import import_module
from unittest import skipUnless

from django import forms
from django.conf import settings
from django.contrib import admin
from django.contrib.admin import widgets
from django.contrib.admin.tests import AdminSeleniumTestCase
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
from django.test import SimpleTestCase, TestCase, ignore_warnings, override_settings
from django.test.selenium import screenshot_cases
from django.test.utils import requires_tz_support
from django.urls import reverse
from django.utils import translation
from django.utils.deprecation import RemovedInDjango60Warning

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

    @ignore_warnings(category=RemovedInDjango60Warning)
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
        Ensure the user can only see their own cars in the foreign key dropdown.
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

    @ignore_warnings(category=RemovedInDjango60Warning)
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

    @ignore_warnings(category=RemovedInDjango60Warning)
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
            '<input value="2007-12-01" type="text" class="vDateField" name="test" '
            'size="10"></p>',
        )
        # pass attrs to widget
        w = widgets.AdminDateWidget(attrs={"size": 20, "class": "myDateField"})
        self.assertHTMLEqual(
            w.render("test", datetime(2007, 12, 1, 9, 30)),
            '<p class="date">'
            '<input value="2007-12-01" type="text" class="myDateField" name="test" '
            'size="20"></p>',
        )


class AdminTimeWidgetTest(SimpleTestCase):
    def test_attrs(self):
        w = widgets.AdminTimeWidget()
        self.assertHTMLEqual(
            w.render("test", datetime(2007, 12, 1, 9, 30)),
            '<p class="time">'
            '<input value="09:30:00" type="text" class="vTimeField" name="test" '
            'size="8"></p>',
        )
        # pass attrs to widget
        w = widgets.AdminTimeWidget(attrs={"size": 20, "class": "myTimeField"})
        self.assertHTMLEqual(
            w.render("test", datetime(2007, 12, 1, 9, 30)),
            '<p class="time">'
            '<input value="09:30:00" type="text" class="myTimeField" name="test" '
            'size="20"></p>',
        )


class AdminSplitDateTimeWidgetTest(SimpleTestCase):
    def test_render(self):
        w = widgets.AdminSplitDateTime()
        self.assertHTMLEqual(
            w.render("test", datetime(2007, 12, 1, 9, 30)),
            '<p class="datetime">'
            'Date: <input value="2007-12-01" type="text" class="vDateField" '
            'name="test_0" size="10"><br>'
            'Time: <input value="09:30:00" type="text" class="vTimeField" '
            'name="test_1" size="8"></p>',
        )

    def test_localization(self):
        w = widgets.AdminSplitDateTime()

        with translation.override("de-at"):
            w.is_localized = True
            self.assertHTMLEqual(
                w.render("test", datetime(2007, 12, 1, 9, 30)),
                '<p class="datetime">'
                'Datum: <input value="01.12.2007" type="text" '
                'class="vDateField" name="test_0"size="10"><br>'
                'Zeit: <input value="09:30:00" type="text" class="vTimeField" '
                'name="test_1" size="8"></p>',
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
            '<p class="url">Currently: <a href="http://xn--example--7za4pnc.com">'
            "http://example-äüö.com</a><br>"
            'Change:<input class="vURLField" name="test" type="url" '
            'value="http://example-äüö.com"></p>',
        )

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
            "http://xn--example--7za4pnc.com/%3Csometag%3Esome-text%3C/sometag%3E",
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
             href="/admin_widgets/releaseevent/add/?_to_field=album&amp;_popup=1">
            <img src="/static/admin/img/icon-addlink.svg" alt="" width="20" height="20">
          </a>
        </div>
        """
        self.assertHTMLEqual(output, expected)


@override_settings(ROOT_URLCONF="admin_widgets.urls")
class AdminWidgetSeleniumTestCase(AdminSeleniumTestCase):
    available_apps = ["admin_widgets"] + AdminSeleniumTestCase.available_apps

    def setUp(self):
        self.u1 = User.objects.create_superuser(
            username="super", password="secret", email="super@example.com"
        )


class DateTimePickerSeleniumTests(AdminWidgetSeleniumTestCase):
    def test_show_hide_date_time_picker_widgets(self):
        """
        Pressing the ESC key or clicking on a widget value closes the date and
        time picker widgets.
        """
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys

        self.admin_login(username="super", password="secret", login_url="/")
        # Open a page that has a date and time picker widgets
        self.selenium.get(
            self.live_server_url + reverse("admin:admin_widgets_member_add")
        )

        # First, with the date picker widget ---------------------------------
        cal_icon = self.selenium.find_element(By.ID, "calendarlink0")
        # The date picker is hidden
        self.assertFalse(
            self.selenium.find_element(By.ID, "calendarbox0").is_displayed()
        )
        # Click the calendar icon
        cal_icon.click()
        # The date picker is visible
        self.assertTrue(
            self.selenium.find_element(By.ID, "calendarbox0").is_displayed()
        )
        # Press the ESC key
        self.selenium.find_element(By.TAG_NAME, "body").send_keys([Keys.ESCAPE])
        # The date picker is hidden again
        self.assertFalse(
            self.selenium.find_element(By.ID, "calendarbox0").is_displayed()
        )
        # Click the calendar icon, then on the 15th of current month
        cal_icon.click()
        self.selenium.find_element(By.XPATH, "//a[contains(text(), '15')]").click()
        self.assertFalse(
            self.selenium.find_element(By.ID, "calendarbox0").is_displayed()
        )
        self.assertEqual(
            self.selenium.find_element(By.ID, "id_birthdate_0").get_attribute("value"),
            datetime.today().strftime("%Y-%m-") + "15",
        )

        # Then, with the time picker widget ----------------------------------
        time_icon = self.selenium.find_element(By.ID, "clocklink0")
        # The time picker is hidden
        self.assertFalse(self.selenium.find_element(By.ID, "clockbox0").is_displayed())
        # Click the time icon
        time_icon.click()
        # The time picker is visible
        self.assertTrue(self.selenium.find_element(By.ID, "clockbox0").is_displayed())
        self.assertEqual(
            [
                x.text
                for x in self.selenium.find_elements(
                    By.XPATH, "//ul[@class='timelist']/li/a"
                )
            ],
            ["Now", "Midnight", "6 a.m.", "Noon", "6 p.m."],
        )
        # Press the ESC key
        self.selenium.find_element(By.TAG_NAME, "body").send_keys([Keys.ESCAPE])
        # The time picker is hidden again
        self.assertFalse(self.selenium.find_element(By.ID, "clockbox0").is_displayed())
        # Click the time icon, then select the 'Noon' value
        time_icon.click()
        self.selenium.find_element(By.XPATH, "//a[contains(text(), 'Noon')]").click()
        self.assertFalse(self.selenium.find_element(By.ID, "clockbox0").is_displayed())
        self.assertEqual(
            self.selenium.find_element(By.ID, "id_birthdate_1").get_attribute("value"),
            "12:00:00",
        )

    def test_calendar_nonday_class(self):
        """
        Ensure cells that are not days of the month have the `nonday` CSS class.
        Refs #4574.
        """
        from selenium.webdriver.common.by import By

        self.admin_login(username="super", password="secret", login_url="/")
        # Open a page that has a date and time picker widgets
        self.selenium.get(
            self.live_server_url + reverse("admin:admin_widgets_member_add")
        )

        # fill in the birth date.
        self.selenium.find_element(By.ID, "id_birthdate_0").send_keys("2013-06-01")

        # Click the calendar icon
        self.selenium.find_element(By.ID, "calendarlink0").click()

        # get all the tds within the calendar
        calendar0 = self.selenium.find_element(By.ID, "calendarin0")
        tds = calendar0.find_elements(By.TAG_NAME, "td")

        # make sure the first and last 6 cells have class nonday
        for td in tds[:6] + tds[-6:]:
            self.assertEqual(td.get_attribute("class"), "nonday")

    def test_calendar_selected_class(self):
        """
        Ensure cell for the day in the input has the `selected` CSS class.
        Refs #4574.
        """
        from selenium.webdriver.common.by import By

        self.admin_login(username="super", password="secret", login_url="/")
        # Open a page that has a date and time picker widgets
        self.selenium.get(
            self.live_server_url + reverse("admin:admin_widgets_member_add")
        )

        # fill in the birth date.
        self.selenium.find_element(By.ID, "id_birthdate_0").send_keys("2013-06-01")

        # Click the calendar icon
        self.selenium.find_element(By.ID, "calendarlink0").click()

        # get all the tds within the calendar
        calendar0 = self.selenium.find_element(By.ID, "calendarin0")
        tds = calendar0.find_elements(By.TAG_NAME, "td")

        # verify the selected cell
        selected = tds[6]
        self.assertEqual(selected.get_attribute("class"), "selected")

        self.assertEqual(selected.text, "1")

    def test_calendar_no_selected_class(self):
        """
        Ensure no cells are given the selected class when the field is empty.
        Refs #4574.
        """
        from selenium.webdriver.common.by import By

        self.admin_login(username="super", password="secret", login_url="/")
        # Open a page that has a date and time picker widgets
        self.selenium.get(
            self.live_server_url + reverse("admin:admin_widgets_member_add")
        )

        # Click the calendar icon
        self.selenium.find_element(By.ID, "calendarlink0").click()

        # get all the tds within the calendar
        calendar0 = self.selenium.find_element(By.ID, "calendarin0")
        tds = calendar0.find_elements(By.TAG_NAME, "td")

        # verify there are no cells with the selected class
        selected = [td for td in tds if td.get_attribute("class") == "selected"]

        self.assertEqual(len(selected), 0)

    def test_calendar_show_date_from_input(self):
        """
        The calendar shows the date from the input field for every locale
        supported by Django.
        """
        from selenium.webdriver.common.by import By

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
                expected_caption = "{:s} {:d}".format(may_translation.upper(), 1984)

                # Every locale.
                with override_settings(LANGUAGE_CODE=language_code):
                    # Open a page that has a date picker widget.
                    self.selenium.get(self.live_server_url + url)
                    # Click on the calendar icon.
                    self.selenium.find_element(By.ID, "calendarlink0").click()
                    # The right month and year are displayed.
                    self.wait_for_text("#calendarin0 caption", expected_caption)


@requires_tz_support
@override_settings(TIME_ZONE="Asia/Singapore")
class DateTimePickerShortcutsSeleniumTests(AdminWidgetSeleniumTestCase):
    def test_date_time_picker_shortcuts(self):
        """
        date/time/datetime picker shortcuts work in the current time zone.
        Refs #20663.

        This test case is fairly tricky, it relies on selenium still running the browser
        in the default time zone "America/Chicago" despite `override_settings` changing
        the time zone to "Asia/Singapore".
        """
        from selenium.webdriver.common.by import By

        self.admin_login(username="super", password="secret", login_url="/")

        error_margin = timedelta(seconds=10)

        # If we are neighbouring a DST, we add an hour of error margin.
        tz = zoneinfo.ZoneInfo("America/Chicago")
        utc_now = datetime.now(zoneinfo.ZoneInfo("UTC"))
        tz_yesterday = (utc_now - timedelta(days=1)).astimezone(tz).tzname()
        tz_tomorrow = (utc_now + timedelta(days=1)).astimezone(tz).tzname()
        if tz_yesterday != tz_tomorrow:
            error_margin += timedelta(hours=1)

        self.selenium.get(
            self.live_server_url + reverse("admin:admin_widgets_member_add")
        )

        self.selenium.find_element(By.ID, "id_name").send_keys("test")

        # Click on the "today" and "now" shortcuts.
        shortcuts = self.selenium.find_elements(
            By.CSS_SELECTOR, ".field-birthdate .datetimeshortcuts"
        )

        now = datetime.now()
        for shortcut in shortcuts:
            shortcut.find_element(By.TAG_NAME, "a").click()

        # There is a time zone mismatch warning.
        # Warning: This would effectively fail if the TIME_ZONE defined in the
        # settings has the same UTC offset as "Asia/Singapore" because the
        # mismatch warning would be rightfully missing from the page.
        self.assertCountSeleniumElements(".field-birthdate .timezonewarning", 1)

        # Submit the form.
        with self.wait_page_loaded():
            self.selenium.find_element(By.NAME, "_save").click()

        # Make sure that "now" in JavaScript is within 10 seconds
        # from "now" on the server side.
        member = Member.objects.get(name="test")
        self.assertGreater(member.birthdate, now - error_margin)
        self.assertLess(member.birthdate, now + error_margin)


# The above tests run with Asia/Singapore which are on the positive side of
# UTC. Here we test with a timezone on the negative side.
@override_settings(TIME_ZONE="US/Eastern")
class DateTimePickerAltTimezoneSeleniumTests(DateTimePickerShortcutsSeleniumTests):
    pass


class HorizontalVerticalFilterSeleniumTests(AdminWidgetSeleniumTestCase):
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

    def assertActiveButtons(
        self, mode, field_name, choose, remove, choose_all=None, remove_all=None
    ):
        choose_button = "#id_%s_add" % field_name
        choose_all_button = "#id_%s_add_all" % field_name
        remove_button = "#id_%s_remove" % field_name
        remove_all_button = "#id_%s_remove_all" % field_name
        self.assertEqual(self.has_css_class(choose_button, "active"), choose)
        self.assertEqual(self.has_css_class(remove_button, "active"), remove)
        if mode == "horizontal":
            self.assertEqual(
                self.has_css_class(choose_all_button, "active"), choose_all
            )
            self.assertEqual(
                self.has_css_class(remove_all_button, "active"), remove_all
            )

    def execute_basic_operations(self, mode, field_name):
        from selenium.webdriver.common.by import By

        original_url = self.selenium.current_url

        from_box = "#id_%s_from" % field_name
        to_box = "#id_%s_to" % field_name
        choose_button = "id_%s_add" % field_name
        choose_all_button = "id_%s_add_all" % field_name
        remove_button = "id_%s_remove" % field_name
        remove_all_button = "id_%s_remove_all" % field_name

        # Initial positions ---------------------------------------------------
        self.assertSelectOptions(
            from_box,
            [
                str(self.arthur.id),
                str(self.bob.id),
                str(self.cliff.id),
                str(self.jason.id),
                str(self.jenny.id),
                str(self.john.id),
            ],
        )
        self.assertSelectOptions(to_box, [str(self.lisa.id), str(self.peter.id)])
        self.assertActiveButtons(mode, field_name, False, False, True, True)

        # Click 'Choose all' --------------------------------------------------
        if mode == "horizontal":
            self.selenium.find_element(By.ID, choose_all_button).click()
        elif mode == "vertical":
            # There 's no 'Choose all' button in vertical mode, so individually
            # select all options and click 'Choose'.
            for option in self.selenium.find_elements(
                By.CSS_SELECTOR, from_box + " > option"
            ):
                option.click()
            self.selenium.find_element(By.ID, choose_button).click()
        self.assertSelectOptions(from_box, [])
        self.assertSelectOptions(
            to_box,
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
        self.assertActiveButtons(mode, field_name, False, False, False, True)

        # Click 'Remove all' --------------------------------------------------
        if mode == "horizontal":
            self.selenium.find_element(By.ID, remove_all_button).click()
        elif mode == "vertical":
            # There 's no 'Remove all' button in vertical mode, so individually
            # select all options and click 'Remove'.
            for option in self.selenium.find_elements(
                By.CSS_SELECTOR, to_box + " > option"
            ):
                option.click()
            self.selenium.find_element(By.ID, remove_button).click()
        self.assertSelectOptions(
            from_box,
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
        self.assertSelectOptions(to_box, [])
        self.assertActiveButtons(mode, field_name, False, False, True, False)

        # Choose some options ------------------------------------------------
        from_lisa_select_option = self.selenium.find_element(
            By.CSS_SELECTOR, '{} > option[value="{}"]'.format(from_box, self.lisa.id)
        )

        # Check the title attribute is there for tool tips: ticket #20821
        self.assertEqual(
            from_lisa_select_option.get_attribute("title"),
            from_lisa_select_option.get_attribute("text"),
        )

        self.select_option(from_box, str(self.lisa.id))
        self.select_option(from_box, str(self.jason.id))
        self.select_option(from_box, str(self.bob.id))
        self.select_option(from_box, str(self.john.id))
        self.assertActiveButtons(mode, field_name, True, False, True, False)
        self.selenium.find_element(By.ID, choose_button).click()
        self.assertActiveButtons(mode, field_name, False, False, True, True)

        self.assertSelectOptions(
            from_box,
            [
                str(self.peter.id),
                str(self.arthur.id),
                str(self.cliff.id),
                str(self.jenny.id),
            ],
        )
        self.assertSelectOptions(
            to_box,
            [
                str(self.lisa.id),
                str(self.bob.id),
                str(self.jason.id),
                str(self.john.id),
            ],
        )

        # Check the tooltip is still there after moving: ticket #20821
        to_lisa_select_option = self.selenium.find_element(
            By.CSS_SELECTOR, '{} > option[value="{}"]'.format(to_box, self.lisa.id)
        )
        self.assertEqual(
            to_lisa_select_option.get_attribute("title"),
            to_lisa_select_option.get_attribute("text"),
        )

        # Remove some options -------------------------------------------------
        self.select_option(to_box, str(self.lisa.id))
        self.select_option(to_box, str(self.bob.id))
        self.assertActiveButtons(mode, field_name, False, True, True, True)
        self.selenium.find_element(By.ID, remove_button).click()
        self.assertActiveButtons(mode, field_name, False, False, True, True)

        self.assertSelectOptions(
            from_box,
            [
                str(self.peter.id),
                str(self.arthur.id),
                str(self.cliff.id),
                str(self.jenny.id),
                str(self.lisa.id),
                str(self.bob.id),
            ],
        )
        self.assertSelectOptions(to_box, [str(self.jason.id), str(self.john.id)])

        # Choose some more options --------------------------------------------
        self.select_option(from_box, str(self.arthur.id))
        self.select_option(from_box, str(self.cliff.id))
        self.selenium.find_element(By.ID, choose_button).click()

        self.assertSelectOptions(
            from_box,
            [
                str(self.peter.id),
                str(self.jenny.id),
                str(self.lisa.id),
                str(self.bob.id),
            ],
        )
        self.assertSelectOptions(
            to_box,
            [
                str(self.jason.id),
                str(self.john.id),
                str(self.arthur.id),
                str(self.cliff.id),
            ],
        )

        # Choose some more options --------------------------------------------
        self.select_option(from_box, str(self.peter.id))
        self.select_option(from_box, str(self.lisa.id))

        # Confirm they're selected after clicking inactive buttons: ticket #26575
        self.assertSelectedOptions(from_box, [str(self.peter.id), str(self.lisa.id)])
        self.selenium.find_element(By.ID, remove_button).click()
        self.assertSelectedOptions(from_box, [str(self.peter.id), str(self.lisa.id)])

        # Unselect the options ------------------------------------------------
        self.deselect_option(from_box, str(self.peter.id))
        self.deselect_option(from_box, str(self.lisa.id))

        # Choose some more options --------------------------------------------
        self.select_option(to_box, str(self.jason.id))
        self.select_option(to_box, str(self.john.id))

        # Confirm they're selected after clicking inactive buttons: ticket #26575
        self.assertSelectedOptions(to_box, [str(self.jason.id), str(self.john.id)])
        self.selenium.find_element(By.ID, choose_button).click()
        self.assertSelectedOptions(to_box, [str(self.jason.id), str(self.john.id)])

        # Unselect the options ------------------------------------------------
        self.deselect_option(to_box, str(self.jason.id))
        self.deselect_option(to_box, str(self.john.id))

        # Pressing buttons shouldn't change the URL.
        self.assertEqual(self.selenium.current_url, original_url)

    def test_basic(self):
        from selenium.webdriver.common.by import By

        self.school.students.set([self.lisa, self.peter])
        self.school.alumni.set([self.lisa, self.peter])

        with self.small_screen_size():
            self.admin_login(username="super", password="secret", login_url="/")
            self.selenium.get(
                self.live_server_url
                + reverse("admin:admin_widgets_school_change", args=(self.school.id,))
            )

            self.wait_page_ready()
            self.execute_basic_operations("vertical", "students")
            self.execute_basic_operations("horizontal", "alumni")

            # Save, everything should be stored properly stored in the
            # database.
            self.selenium.find_element(By.XPATH, '//input[@value="Save"]').click()
            self.wait_page_ready()
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
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys

        self.school.students.set([self.lisa, self.peter])
        self.school.alumni.set([self.lisa, self.peter])

        with self.small_screen_size():
            self.admin_login(username="super", password="secret", login_url="/")
            self.selenium.get(
                self.live_server_url
                + reverse("admin:admin_widgets_school_change", args=(self.school.id,))
            )

            for field_name in ["students", "alumni"]:
                from_box = "#id_%s_from" % field_name
                to_box = "#id_%s_to" % field_name
                choose_link = "id_%s_add" % field_name
                remove_link = "id_%s_remove" % field_name
                input = self.selenium.find_element(By.ID, "id_%s_input" % field_name)
                # Initial values.
                self.assertSelectOptions(
                    from_box,
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
                input.send_keys("a")
                self.assertSelectOptions(
                    from_box, [str(self.arthur.id), str(self.jason.id)]
                )
                input.send_keys("R")
                self.assertSelectOptions(from_box, [str(self.arthur.id)])
                # Clearing the text box makes the other options reappear.
                input.send_keys([Keys.BACK_SPACE])
                self.assertSelectOptions(
                    from_box, [str(self.arthur.id), str(self.jason.id)]
                )
                input.send_keys([Keys.BACK_SPACE])
                self.assertSelectOptions(
                    from_box,
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
                input.send_keys("a")
                self.assertSelectOptions(
                    from_box, [str(self.arthur.id), str(self.jason.id)]
                )
                self.select_option(from_box, str(self.jason.id))
                self.selenium.find_element(By.ID, choose_link).click()
                self.assertSelectOptions(from_box, [str(self.arthur.id)])
                self.assertSelectOptions(
                    to_box,
                    [
                        str(self.lisa.id),
                        str(self.peter.id),
                        str(self.jason.id),
                    ],
                )

                self.select_option(to_box, str(self.lisa.id))
                self.selenium.find_element(By.ID, remove_link).click()
                self.assertSelectOptions(
                    from_box, [str(self.arthur.id), str(self.lisa.id)]
                )
                self.assertSelectOptions(
                    to_box, [str(self.peter.id), str(self.jason.id)]
                )

                input.send_keys([Keys.BACK_SPACE])  # Clear text box
                self.assertSelectOptions(
                    from_box,
                    [
                        str(self.arthur.id),
                        str(self.bob.id),
                        str(self.cliff.id),
                        str(self.jenny.id),
                        str(self.john.id),
                        str(self.lisa.id),
                    ],
                )
                self.assertSelectOptions(
                    to_box, [str(self.peter.id), str(self.jason.id)]
                )

                # Pressing enter on a filtered option sends it properly to
                # the 'to' box.
                self.select_option(to_box, str(self.jason.id))
                self.selenium.find_element(By.ID, remove_link).click()
                input.send_keys("ja")
                self.assertSelectOptions(from_box, [str(self.jason.id)])
                input.send_keys([Keys.ENTER])
                self.assertSelectOptions(
                    to_box, [str(self.peter.id), str(self.jason.id)]
                )
                input.send_keys([Keys.BACK_SPACE, Keys.BACK_SPACE])

            # Save, everything should be stored properly in the database.
            with self.wait_page_loaded():
                self.selenium.find_element(By.XPATH, '//input[@value="Save"]').click()
        self.school = School.objects.get(id=self.school.id)  # Reload from database
        self.assertEqual(list(self.school.students.all()), [self.jason, self.peter])
        self.assertEqual(list(self.school.alumni.all()), [self.jason, self.peter])

    def test_back_button_bug(self):
        """
        Some browsers had a bug where navigating away from the change page
        and then clicking the browser's back button would clear the
        filter_horizontal/filter_vertical widgets (#13614).
        """
        from selenium.webdriver.common.by import By

        self.school.students.set([self.lisa, self.peter])
        self.school.alumni.set([self.lisa, self.peter])
        self.admin_login(username="super", password="secret", login_url="/")
        change_url = reverse(
            "admin:admin_widgets_school_change", args=(self.school.id,)
        )
        self.selenium.get(self.live_server_url + change_url)
        # Navigate away and go back to the change form page.
        self.selenium.find_element(By.LINK_TEXT, "Home").click()
        self.selenium.back()
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
        self.assertSelectOptions("#id_students_from", expected_unselected_values)
        self.assertSelectOptions("#id_students_to", expected_selected_values)
        self.assertSelectOptions("#id_alumni_from", expected_unselected_values)
        self.assertSelectOptions("#id_alumni_to", expected_selected_values)

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
        self.selenium.get(self.live_server_url + change_url)

        self.assertCountSeleniumElements("#id_students_to > option", 2)

        # self.selenium.refresh() or send_keys(Keys.F5) does hard reload and
        # doesn't replicate what happens when a user clicks the browser's
        # 'Refresh' button.
        with self.wait_page_loaded():
            self.selenium.execute_script("location.reload()")

        self.assertCountSeleniumElements("#id_students_to > option", 2)


@ignore_warnings(category=RemovedInDjango60Warning)
class AdminRawIdWidgetSeleniumTests(AdminWidgetSeleniumTestCase):
    def setUp(self):
        super().setUp()
        Band.objects.create(id=42, name="Bogey Blues")
        Band.objects.create(id=98, name="Green Potatoes")

    @screenshot_cases(["desktop_size", "mobile_size", "rtl", "dark", "high_contrast"])
    def test_ForeignKey(self):
        from selenium.webdriver.common.by import By

        self.admin_login(username="super", password="secret", login_url="/")
        self.selenium.get(
            self.live_server_url + reverse("admin:admin_widgets_event_add")
        )
        main_window = self.selenium.current_window_handle
        self.take_screenshot("raw_id_widget")

        # No value has been selected yet
        self.assertEqual(
            self.selenium.find_element(By.ID, "id_main_band").get_attribute("value"), ""
        )

        # Open the popup window and click on a band
        self.selenium.find_element(By.ID, "lookup_id_main_band").click()
        self.wait_for_and_switch_to_popup()
        link = self.selenium.find_element(By.LINK_TEXT, "Bogey Blues")
        self.assertIn("/band/42/", link.get_attribute("href"))
        link.click()

        # The field now contains the selected band's id
        self.selenium.switch_to.window(main_window)
        self.wait_for_value("#id_main_band", "42")

        # Reopen the popup window and click on another band
        self.selenium.find_element(By.ID, "lookup_id_main_band").click()
        self.wait_for_and_switch_to_popup()
        link = self.selenium.find_element(By.LINK_TEXT, "Green Potatoes")
        self.assertIn("/band/98/", link.get_attribute("href"))
        link.click()

        # The field now contains the other selected band's id
        self.selenium.switch_to.window(main_window)
        self.wait_for_value("#id_main_band", "98")

    def test_many_to_many(self):
        from selenium.webdriver.common.by import By

        self.admin_login(username="super", password="secret", login_url="/")
        self.selenium.get(
            self.live_server_url + reverse("admin:admin_widgets_event_add")
        )
        main_window = self.selenium.current_window_handle

        # No value has been selected yet
        self.assertEqual(
            self.selenium.find_element(By.ID, "id_supporting_bands").get_attribute(
                "value"
            ),
            "",
        )

        # Help text for the field is displayed
        self.assertEqual(
            self.selenium.find_element(
                By.CSS_SELECTOR, ".field-supporting_bands div.help"
            ).text,
            "Supporting Bands.",
        )

        # Open the popup window and click on a band
        self.selenium.find_element(By.ID, "lookup_id_supporting_bands").click()
        self.wait_for_and_switch_to_popup()
        link = self.selenium.find_element(By.LINK_TEXT, "Bogey Blues")
        self.assertIn("/band/42/", link.get_attribute("href"))
        link.click()

        # The field now contains the selected band's id
        self.selenium.switch_to.window(main_window)
        self.wait_for_value("#id_supporting_bands", "42")

        # Reopen the popup window and click on another band
        self.selenium.find_element(By.ID, "lookup_id_supporting_bands").click()
        self.wait_for_and_switch_to_popup()
        link = self.selenium.find_element(By.LINK_TEXT, "Green Potatoes")
        self.assertIn("/band/98/", link.get_attribute("href"))
        link.click()

        # The field now contains the two selected bands' ids
        self.selenium.switch_to.window(main_window)
        self.wait_for_value("#id_supporting_bands", "42,98")


class RelatedFieldWidgetSeleniumTests(AdminWidgetSeleniumTestCase):
    def test_ForeignKey_using_to_field(self):
        from selenium.webdriver import ActionChains
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import Select

        self.admin_login(username="super", password="secret", login_url="/")
        with self.wait_page_loaded():
            self.selenium.get(
                self.live_server_url + reverse("admin:admin_widgets_profile_add")
            )

        main_window = self.selenium.current_window_handle
        # Click the Add User button to add new
        self.selenium.find_element(By.ID, "add_id_user").click()
        self.wait_for_and_switch_to_popup()
        password_field = self.selenium.find_element(By.ID, "id_password")
        password_field.send_keys("password")

        username_field = self.selenium.find_element(By.ID, "id_username")
        username_value = "newuser"
        username_field.send_keys(username_value)

        save_button_css_selector = ".submit-row > input[type=submit]"
        self.selenium.find_element(By.CSS_SELECTOR, save_button_css_selector).click()
        self.selenium.switch_to.window(main_window)
        # The field now contains the new user
        self.selenium.find_element(By.CSS_SELECTOR, "#id_user option[value=newuser]")

        self.selenium.find_element(By.ID, "view_id_user").click()
        self.wait_for_value("#id_username", "newuser")
        self.selenium.back()

        # Chrome and Safari don't update related object links when selecting
        # the same option as previously submitted. As a consequence, the
        # "pencil" and "eye" buttons remain disable, so select "---------"
        # first.
        select = Select(self.selenium.find_element(By.ID, "id_user"))
        select.select_by_index(0)
        select.select_by_value("newuser")
        # Click the Change User button to change it
        self.selenium.find_element(By.ID, "change_id_user").click()
        self.wait_for_and_switch_to_popup()

        username_field = self.selenium.find_element(By.ID, "id_username")
        username_value = "changednewuser"
        username_field.clear()
        username_field.send_keys(username_value)

        save_button_css_selector = ".submit-row > input[type=submit]"
        self.selenium.find_element(By.CSS_SELECTOR, save_button_css_selector).click()
        self.selenium.switch_to.window(main_window)
        self.selenium.find_element(
            By.CSS_SELECTOR, "#id_user option[value=changednewuser]"
        )

        element = self.selenium.find_element(By.ID, "view_id_user")
        ActionChains(self.selenium).move_to_element(element).click(element).perform()
        self.wait_for_value("#id_username", "changednewuser")
        self.selenium.back()

        select = Select(self.selenium.find_element(By.ID, "id_user"))
        select.select_by_value("changednewuser")
        # Go ahead and submit the form to make sure it works
        self.selenium.find_element(By.CSS_SELECTOR, save_button_css_selector).click()
        self.wait_for_text(
            "li.success", "The profile “changednewuser” was added successfully."
        )
        profiles = Profile.objects.all()
        self.assertEqual(len(profiles), 1)
        self.assertEqual(profiles[0].user.username, username_value)


@skipUnless(Image, "Pillow not installed")
class ImageFieldWidgetsSeleniumTests(AdminWidgetSeleniumTestCase):
    name_input_id = "id_name"
    photo_input_id = "id_photo"
    tests_files_folder = "%s/files" % os.getcwd()
    clear_checkbox_id = "photo-clear_id"

    def _submit_and_wait(self):
        from selenium.webdriver.common.by import By

        with self.wait_page_loaded():
            self.selenium.find_element(
                By.CSS_SELECTOR, "input[value='Save and continue editing']"
            ).click()

    def _run_image_upload_path(self):
        from selenium.webdriver.common.by import By

        self.admin_login(username="super", password="secret", login_url="/")
        self.selenium.get(
            self.live_server_url + reverse("admin:admin_widgets_student_add"),
        )
        # Add a student.
        name_input = self.selenium.find_element(By.ID, self.name_input_id)
        name_input.send_keys("Joe Doe")
        photo_input = self.selenium.find_element(By.ID, self.photo_input_id)
        photo_input.send_keys(f"{self.tests_files_folder}/test.png")
        self._submit_and_wait()
        student = Student.objects.last()
        self.assertEqual(student.name, "Joe Doe")
        self.assertRegex(student.photo.name, r"^photos\/(test|test_.+).png")

    def test_clearablefileinput_widget(self):
        from selenium.webdriver.common.by import By

        self._run_image_upload_path()
        self.selenium.find_element(By.ID, self.clear_checkbox_id).click()
        self._submit_and_wait()
        student = Student.objects.last()
        self.assertEqual(student.name, "Joe Doe")
        self.assertEqual(student.photo.name, "")
        # "Currently" with "Clear" checkbox and "Change" are not shown.
        photo_field_row = self.selenium.find_element(By.CSS_SELECTOR, ".field-photo")
        self.assertNotIn("Currently", photo_field_row.text)
        self.assertNotIn("Change", photo_field_row.text)

    def test_clearablefileinput_widget_invalid_file(self):
        from selenium.webdriver.common.by import By

        self._run_image_upload_path()
        # Uploading non-image files is not supported by Safari with Selenium,
        # so upload a broken one instead.
        photo_input = self.selenium.find_element(By.ID, self.photo_input_id)
        photo_input.send_keys(f"{self.tests_files_folder}/brokenimg.png")
        self._submit_and_wait()
        self.assertEqual(
            self.selenium.find_element(By.CSS_SELECTOR, ".errorlist li").text,
            (
                "Upload a valid image. The file you uploaded was either not an image "
                "or a corrupted image."
            ),
        )
        # "Currently" with "Clear" checkbox and "Change" still shown.
        photo_field_row = self.selenium.find_element(By.CSS_SELECTOR, ".field-photo")
        self.assertIn("Currently", photo_field_row.text)
        self.assertIn("Change", photo_field_row.text)

    def test_clearablefileinput_widget_preserve_clear_checkbox(self):
        from selenium.webdriver.common.by import By

        self._run_image_upload_path()
        # "Clear" is not checked by default.
        self.assertIs(
            self.selenium.find_element(By.ID, self.clear_checkbox_id).is_selected(),
            False,
        )
        # "Clear" was checked, but a validation error is raised.
        name_input = self.selenium.find_element(By.ID, self.name_input_id)
        name_input.clear()
        self.selenium.find_element(By.ID, self.clear_checkbox_id).click()
        self._submit_and_wait()
        self.assertEqual(
            self.selenium.find_element(By.CSS_SELECTOR, ".errorlist li").text,
            "This field is required.",
        )
        # "Clear" persists checked.
        self.assertIs(
            self.selenium.find_element(By.ID, self.clear_checkbox_id).is_selected(),
            True,
        )
