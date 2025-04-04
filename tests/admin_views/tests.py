import datetime
import os
import re
import unittest
import zoneinfo
from unittest import mock
from urllib.parse import parse_qsl, urljoin, urlsplit

from django import forms
from django.contrib import admin
from django.contrib.admin import AdminSite, ModelAdmin
from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.contrib.admin.models import ADDITION, DELETION, LogEntry
from django.contrib.admin.options import TO_FIELD_VAR
from django.contrib.admin.templatetags.admin_urls import add_preserved_filters
from django.contrib.admin.tests import AdminSeleniumTestCase
from django.contrib.admin.utils import quote
from django.contrib.admin.views.main import IS_POPUP_VAR
from django.contrib.auth import REDIRECT_FIELD_NAME, get_permission_codename
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import AdminPasswordChangeForm
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.core import mail
from django.core.checks import Error
from django.core.files import temp as tempfile
from django.db import connection
from django.forms.utils import ErrorList
from django.template.response import TemplateResponse
from django.test import (
    RequestFactory,
    TestCase,
    ignore_warnings,
    modify_settings,
    override_settings,
    skipUnlessDBFeature,
)
from django.test.selenium import screenshot_cases
from django.test.utils import override_script_prefix
from django.urls import NoReverseMatch, resolve, reverse
from django.utils import formats, translation
from django.utils.cache import get_max_age
from django.utils.deprecation import RemovedInDjango60Warning
from django.utils.encoding import iri_to_uri
from django.utils.html import escape
from django.utils.http import urlencode

from . import customadmin
from .admin import CityAdmin, site, site2
from .models import (
    Actor,
    AdminOrderedAdminMethod,
    AdminOrderedCallable,
    AdminOrderedField,
    AdminOrderedModelMethod,
    Album,
    Answer,
    Answer2,
    Article,
    BarAccount,
    Book,
    Bookmark,
    Box,
    Category,
    Chapter,
    ChapterXtra1,
    ChapterXtra2,
    Character,
    Child,
    Choice,
    City,
    Collector,
    Color,
    ComplexSortedPerson,
    CoverLetter,
    CustomArticle,
    CyclicOne,
    CyclicTwo,
    DooHickey,
    Employee,
    EmptyModel,
    Fabric,
    FancyDoodad,
    FieldOverridePost,
    FilteredManager,
    FooAccount,
    FoodDelivery,
    FunkyTag,
    Gallery,
    Grommet,
    Inquisition,
    Language,
    Link,
    MainPrepopulated,
    Media,
    ModelWithStringPrimaryKey,
    OtherStory,
    Paper,
    Parent,
    ParentWithDependentChildren,
    ParentWithUUIDPK,
    Person,
    Persona,
    Picture,
    Pizza,
    Plot,
    PlotDetails,
    PluggableSearchPerson,
    Podcast,
    Post,
    PrePopulatedPost,
    Promo,
    Question,
    ReadablePizza,
    ReadOnlyPizza,
    ReadOnlyRelatedField,
    Recommendation,
    Recommender,
    RelatedPrepopulated,
    RelatedWithUUIDPKModel,
    Report,
    Restaurant,
    RowLevelChangePermissionModel,
    SecretHideout,
    Section,
    ShortMessage,
    Simple,
    Song,
    State,
    Story,
    SuperSecretHideout,
    SuperVillain,
    Telegram,
    TitleTranslation,
    Topping,
    Traveler,
    UnchangeableObject,
    UndeletableObject,
    UnorderedObject,
    UserProxy,
    Villain,
    Vodcast,
    Whatsit,
    Widget,
    Worker,
    WorkHour,
)

ERROR_MESSAGE = "Please enter the correct username and password \
for a staff account. Note that both fields may be case-sensitive."

MULTIPART_ENCTYPE = 'enctype="multipart/form-data"'


def make_aware_datetimes(dt, iana_key):
    """Makes one aware datetime for each supported time zone provider."""
    yield dt.replace(tzinfo=zoneinfo.ZoneInfo(iana_key))


class AdminFieldExtractionMixin:
    """
    Helper methods for extracting data from AdminForm.
    """

    def get_admin_form_fields(self, response):
        """
        Return a list of AdminFields for the AdminForm in the response.
        """
        fields = []
        for fieldset in response.context["adminform"]:
            for field_line in fieldset:
                fields.extend(field_line)
        return fields

    def get_admin_readonly_fields(self, response):
        """
        Return the readonly fields for the response's AdminForm.
        """
        return [f for f in self.get_admin_form_fields(response) if f.is_readonly]

    def get_admin_readonly_field(self, response, field_name):
        """
        Return the readonly field for the given field_name.
        """
        admin_readonly_fields = self.get_admin_readonly_fields(response)
        for field in admin_readonly_fields:
            if field.field["name"] == field_name:
                return field


@override_settings(ROOT_URLCONF="admin_views.urls", USE_I18N=True, LANGUAGE_CODE="en")
class AdminViewBasicTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="super", password="secret", email="super@example.com"
        )
        cls.s1 = Section.objects.create(name="Test section")
        cls.a1 = Article.objects.create(
            content="<p>Middle content</p>",
            date=datetime.datetime(2008, 3, 18, 11, 54, 58),
            section=cls.s1,
            title="Article 1",
        )
        cls.a2 = Article.objects.create(
            content="<p>Oldest content</p>",
            date=datetime.datetime(2000, 3, 18, 11, 54, 58),
            section=cls.s1,
            title="Article 2",
        )
        cls.a3 = Article.objects.create(
            content="<p>Newest content</p>",
            date=datetime.datetime(2009, 3, 18, 11, 54, 58),
            section=cls.s1,
        )
        cls.p1 = PrePopulatedPost.objects.create(
            title="A Long Title", published=True, slug="a-long-title"
        )
        cls.color1 = Color.objects.create(value="Red", warm=True)
        cls.color2 = Color.objects.create(value="Orange", warm=True)
        cls.color3 = Color.objects.create(value="Blue", warm=False)
        cls.color4 = Color.objects.create(value="Green", warm=False)
        cls.fab1 = Fabric.objects.create(surface="x")
        cls.fab2 = Fabric.objects.create(surface="y")
        cls.fab3 = Fabric.objects.create(surface="plain")
        cls.b1 = Book.objects.create(name="Book 1")
        cls.b2 = Book.objects.create(name="Book 2")
        cls.pro1 = Promo.objects.create(name="Promo 1", book=cls.b1)
        cls.pro1 = Promo.objects.create(name="Promo 2", book=cls.b2)
        cls.chap1 = Chapter.objects.create(
            title="Chapter 1", content="[ insert contents here ]", book=cls.b1
        )
        cls.chap2 = Chapter.objects.create(
            title="Chapter 2", content="[ insert contents here ]", book=cls.b1
        )
        cls.chap3 = Chapter.objects.create(
            title="Chapter 1", content="[ insert contents here ]", book=cls.b2
        )
        cls.chap4 = Chapter.objects.create(
            title="Chapter 2", content="[ insert contents here ]", book=cls.b2
        )
        cls.cx1 = ChapterXtra1.objects.create(chap=cls.chap1, xtra="ChapterXtra1 1")
        cls.cx2 = ChapterXtra1.objects.create(chap=cls.chap3, xtra="ChapterXtra1 2")
        Actor.objects.create(name="Palin", age=27)

        # Post data for edit inline
        cls.inline_post_data = {
            "name": "Test section",
            # inline data
            "article_set-TOTAL_FORMS": "6",
            "article_set-INITIAL_FORMS": "3",
            "article_set-MAX_NUM_FORMS": "0",
            "article_set-0-id": cls.a1.pk,
            # there is no title in database, give one here or formset will fail.
            "article_set-0-title": "Norske bostaver æøå skaper problemer",
            "article_set-0-content": "&lt;p&gt;Middle content&lt;/p&gt;",
            "article_set-0-date_0": "2008-03-18",
            "article_set-0-date_1": "11:54:58",
            "article_set-0-section": cls.s1.pk,
            "article_set-1-id": cls.a2.pk,
            "article_set-1-title": "Need a title.",
            "article_set-1-content": "&lt;p&gt;Oldest content&lt;/p&gt;",
            "article_set-1-date_0": "2000-03-18",
            "article_set-1-date_1": "11:54:58",
            "article_set-2-id": cls.a3.pk,
            "article_set-2-title": "Need a title.",
            "article_set-2-content": "&lt;p&gt;Newest content&lt;/p&gt;",
            "article_set-2-date_0": "2009-03-18",
            "article_set-2-date_1": "11:54:58",
            "article_set-3-id": "",
            "article_set-3-title": "",
            "article_set-3-content": "",
            "article_set-3-date_0": "",
            "article_set-3-date_1": "",
            "article_set-4-id": "",
            "article_set-4-title": "",
            "article_set-4-content": "",
            "article_set-4-date_0": "",
            "article_set-4-date_1": "",
            "article_set-5-id": "",
            "article_set-5-title": "",
            "article_set-5-content": "",
            "article_set-5-date_0": "",
            "article_set-5-date_1": "",
        }

    def setUp(self):
        self.client.force_login(self.superuser)

    def assertContentBefore(self, response, text1, text2, failing_msg=None):
        """
        Testing utility asserting that text1 appears before text2 in response
        content.
        """
        self.assertEqual(response.status_code, 200)
        self.assertLess(
            response.content.index(text1.encode()),
            response.content.index(text2.encode()),
            (failing_msg or "")
            + "\nResponse:\n"
            + response.content.decode(response.charset),
        )


class AdminViewBasicTest(AdminViewBasicTestCase):
    def test_trailing_slash_required(self):
        """
        If you leave off the trailing slash, app should redirect and add it.
        """
        add_url = reverse("admin:admin_views_article_add")
        response = self.client.get(add_url[:-1])
        self.assertRedirects(response, add_url, status_code=301)

    def test_basic_add_GET(self):
        """
        A smoke test to ensure GET on the add_view works.
        """
        response = self.client.get(reverse("admin:admin_views_section_add"))
        self.assertIsInstance(response, TemplateResponse)
        self.assertEqual(response.status_code, 200)

    def test_add_with_GET_args(self):
        response = self.client.get(
            reverse("admin:admin_views_section_add"), {"name": "My Section"}
        )
        self.assertContains(
            response,
            'value="My Section"',
            msg_prefix="Couldn't find an input with the right value in the response",
        )

    def test_add_query_string_persists(self):
        save_options = [
            {"_addanother": "1"},  # "Save and add another".
            {"_continue": "1"},  # "Save and continue editing".
            {"_saveasnew": "1"},  # "Save as new".
        ]
        other_options = [
            "",
            "_changelist_filters=is_staff__exact%3D0",
            f"{IS_POPUP_VAR}=1",
            f"{TO_FIELD_VAR}=id",
        ]
        url = reverse("admin:auth_user_add")
        for i, save_option in enumerate(save_options):
            for j, other_option in enumerate(other_options):
                with self.subTest(save_option=save_option, other_option=other_option):
                    qsl = "username=newuser"
                    if other_option:
                        qsl = f"{qsl}&{other_option}"
                    response = self.client.post(
                        f"{url}?{qsl}",
                        {
                            "username": f"newuser{i}{j}",
                            "password1": "newpassword",
                            "password2": "newpassword",
                            **save_option,
                        },
                    )
                    parsed_url = urlsplit(response.url)
                    self.assertEqual(parsed_url.query, qsl)

    def test_change_query_string_persists(self):
        save_options = [
            {"_addanother": "1"},  # "Save and add another".
            {"_continue": "1"},  # "Save and continue editing".
        ]
        other_options = [
            "",
            "_changelist_filters=warm%3D1",
            f"{IS_POPUP_VAR}=1",
            f"{TO_FIELD_VAR}=id",
        ]
        url = reverse("admin:admin_views_color_change", args=(self.color1.pk,))
        for save_option in save_options:
            for other_option in other_options:
                with self.subTest(save_option=save_option, other_option=other_option):
                    qsl = "value=blue"
                    if other_option:
                        qsl = f"{qsl}&{other_option}"
                    response = self.client.post(
                        f"{url}?{qsl}",
                        {
                            "value": "gold",
                            "warm": True,
                            **save_option,
                        },
                    )
                    parsed_url = urlsplit(response.url)
                    self.assertEqual(parsed_url.query, qsl)

    def test_basic_edit_GET(self):
        """
        A smoke test to ensure GET on the change_view works.
        """
        response = self.client.get(
            reverse("admin:admin_views_section_change", args=(self.s1.pk,))
        )
        self.assertIsInstance(response, TemplateResponse)
        self.assertEqual(response.status_code, 200)

    def test_basic_edit_GET_string_PK(self):
        """
        GET on the change_view (when passing a string as the PK argument for a
        model with an integer PK field) redirects to the index page with a
        message saying the object doesn't exist.
        """
        response = self.client.get(
            reverse("admin:admin_views_section_change", args=(quote("abc/<b>"),)),
            follow=True,
        )
        self.assertRedirects(response, reverse("admin:index"))
        self.assertEqual(
            [m.message for m in response.context["messages"]],
            ["section with ID “abc/<b>” doesn’t exist. Perhaps it was deleted?"],
        )

    def test_basic_edit_GET_old_url_redirect(self):
        """
        The change URL changed in Django 1.9, but the old one still redirects.
        """
        response = self.client.get(
            reverse("admin:admin_views_section_change", args=(self.s1.pk,)).replace(
                "change/", ""
            )
        )
        self.assertRedirects(
            response, reverse("admin:admin_views_section_change", args=(self.s1.pk,))
        )

    def test_basic_inheritance_GET_string_PK(self):
        """
        GET on the change_view (for inherited models) redirects to the index
        page with a message saying the object doesn't exist.
        """
        response = self.client.get(
            reverse("admin:admin_views_supervillain_change", args=("abc",)), follow=True
        )
        self.assertRedirects(response, reverse("admin:index"))
        self.assertEqual(
            [m.message for m in response.context["messages"]],
            ["super villain with ID “abc” doesn’t exist. Perhaps it was deleted?"],
        )

    def test_basic_add_POST(self):
        """
        A smoke test to ensure POST on add_view works.
        """
        post_data = {
            "name": "Another Section",
            # inline data
            "article_set-TOTAL_FORMS": "3",
            "article_set-INITIAL_FORMS": "0",
            "article_set-MAX_NUM_FORMS": "0",
        }
        response = self.client.post(reverse("admin:admin_views_section_add"), post_data)
        self.assertEqual(response.status_code, 302)  # redirect somewhere

    def test_popup_add_POST(self):
        """HTTP response from a popup is properly escaped."""
        post_data = {
            IS_POPUP_VAR: "1",
            "title": "title with a new\nline",
            "content": "some content",
            "date_0": "2010-09-10",
            "date_1": "14:55:39",
        }
        response = self.client.post(reverse("admin:admin_views_article_add"), post_data)
        self.assertContains(response, "title with a new\\nline")

    def test_basic_edit_POST(self):
        """
        A smoke test to ensure POST on edit_view works.
        """
        url = reverse("admin:admin_views_section_change", args=(self.s1.pk,))
        response = self.client.post(url, self.inline_post_data)
        self.assertEqual(response.status_code, 302)  # redirect somewhere

    def test_edit_save_as(self):
        """
        Test "save as".
        """
        post_data = self.inline_post_data.copy()
        post_data.update(
            {
                "_saveasnew": "Save+as+new",
                "article_set-1-section": "1",
                "article_set-2-section": "1",
                "article_set-3-section": "1",
                "article_set-4-section": "1",
                "article_set-5-section": "1",
            }
        )
        response = self.client.post(
            reverse("admin:admin_views_section_change", args=(self.s1.pk,)), post_data
        )
        self.assertEqual(response.status_code, 302)  # redirect somewhere

    def test_edit_save_as_delete_inline(self):
        """
        Should be able to "Save as new" while also deleting an inline.
        """
        post_data = self.inline_post_data.copy()
        post_data.update(
            {
                "_saveasnew": "Save+as+new",
                "article_set-1-section": "1",
                "article_set-2-section": "1",
                "article_set-2-DELETE": "1",
                "article_set-3-section": "1",
            }
        )
        response = self.client.post(
            reverse("admin:admin_views_section_change", args=(self.s1.pk,)), post_data
        )
        self.assertEqual(response.status_code, 302)
        # started with 3 articles, one was deleted.
        self.assertEqual(Section.objects.latest("id").article_set.count(), 2)

    def test_change_list_column_field_classes(self):
        response = self.client.get(reverse("admin:admin_views_article_changelist"))
        # callables display the callable name.
        self.assertContains(response, "column-callable_year")
        self.assertContains(response, "field-callable_year")
        # lambdas display as "lambda" + index that they appear in list_display.
        self.assertContains(response, "column-lambda8")
        self.assertContains(response, "field-lambda8")

    def test_change_list_sorting_callable(self):
        """
        Ensure we can sort on a list_display field that is a callable
        (column 2 is callable_year in ArticleAdmin)
        """
        response = self.client.get(
            reverse("admin:admin_views_article_changelist"), {"o": 2}
        )
        self.assertContentBefore(
            response,
            "Oldest content",
            "Middle content",
            "Results of sorting on callable are out of order.",
        )
        self.assertContentBefore(
            response,
            "Middle content",
            "Newest content",
            "Results of sorting on callable are out of order.",
        )

    def test_change_list_boolean_display_property(self):
        response = self.client.get(reverse("admin:admin_views_article_changelist"))
        self.assertContains(
            response,
            '<td class="field-model_property_is_from_past">'
            '<img src="/static/admin/img/icon-yes.svg" alt="True"></td>',
        )

    def test_change_list_sorting_property(self):
        """
        Sort on a list_display field that is a property (column 10 is
        a property in Article model).
        """
        response = self.client.get(
            reverse("admin:admin_views_article_changelist"), {"o": 10}
        )
        self.assertContentBefore(
            response,
            "Oldest content",
            "Middle content",
            "Results of sorting on property are out of order.",
        )
        self.assertContentBefore(
            response,
            "Middle content",
            "Newest content",
            "Results of sorting on property are out of order.",
        )

    def test_change_list_sorting_callable_query_expression(self):
        """Query expressions may be used for admin_order_field."""
        tests = [
            ("order_by_expression", 9),
            ("order_by_f_expression", 12),
            ("order_by_orderby_expression", 13),
        ]
        for admin_order_field, index in tests:
            with self.subTest(admin_order_field):
                response = self.client.get(
                    reverse("admin:admin_views_article_changelist"),
                    {"o": index},
                )
                self.assertContentBefore(
                    response,
                    "Oldest content",
                    "Middle content",
                    "Results of sorting on callable are out of order.",
                )
                self.assertContentBefore(
                    response,
                    "Middle content",
                    "Newest content",
                    "Results of sorting on callable are out of order.",
                )

    def test_change_list_sorting_callable_query_expression_reverse(self):
        tests = [
            ("order_by_expression", -9),
            ("order_by_f_expression", -12),
            ("order_by_orderby_expression", -13),
        ]
        for admin_order_field, index in tests:
            with self.subTest(admin_order_field):
                response = self.client.get(
                    reverse("admin:admin_views_article_changelist"),
                    {"o": index},
                )
                self.assertContentBefore(
                    response,
                    "Middle content",
                    "Oldest content",
                    "Results of sorting on callable are out of order.",
                )
                self.assertContentBefore(
                    response,
                    "Newest content",
                    "Middle content",
                    "Results of sorting on callable are out of order.",
                )

    def test_change_list_sorting_model(self):
        """
        Ensure we can sort on a list_display field that is a Model method
        (column 3 is 'model_year' in ArticleAdmin)
        """
        response = self.client.get(
            reverse("admin:admin_views_article_changelist"), {"o": "-3"}
        )
        self.assertContentBefore(
            response,
            "Newest content",
            "Middle content",
            "Results of sorting on Model method are out of order.",
        )
        self.assertContentBefore(
            response,
            "Middle content",
            "Oldest content",
            "Results of sorting on Model method are out of order.",
        )

    def test_change_list_sorting_model_admin(self):
        """
        Ensure we can sort on a list_display field that is a ModelAdmin method
        (column 4 is 'modeladmin_year' in ArticleAdmin)
        """
        response = self.client.get(
            reverse("admin:admin_views_article_changelist"), {"o": "4"}
        )
        self.assertContentBefore(
            response,
            "Oldest content",
            "Middle content",
            "Results of sorting on ModelAdmin method are out of order.",
        )
        self.assertContentBefore(
            response,
            "Middle content",
            "Newest content",
            "Results of sorting on ModelAdmin method are out of order.",
        )

    def test_change_list_sorting_model_admin_reverse(self):
        """
        Ensure we can sort on a list_display field that is a ModelAdmin
        method in reverse order (i.e. admin_order_field uses the '-' prefix)
        (column 6 is 'model_year_reverse' in ArticleAdmin)
        """
        td = '<td class="field-model_property_year">%s</td>'
        td_2000, td_2008, td_2009 = td % 2000, td % 2008, td % 2009
        response = self.client.get(
            reverse("admin:admin_views_article_changelist"), {"o": "6"}
        )
        self.assertContentBefore(
            response,
            td_2009,
            td_2008,
            "Results of sorting on ModelAdmin method are out of order.",
        )
        self.assertContentBefore(
            response,
            td_2008,
            td_2000,
            "Results of sorting on ModelAdmin method are out of order.",
        )
        # Let's make sure the ordering is right and that we don't get a
        # FieldError when we change to descending order
        response = self.client.get(
            reverse("admin:admin_views_article_changelist"), {"o": "-6"}
        )
        self.assertContentBefore(
            response,
            td_2000,
            td_2008,
            "Results of sorting on ModelAdmin method are out of order.",
        )
        self.assertContentBefore(
            response,
            td_2008,
            td_2009,
            "Results of sorting on ModelAdmin method are out of order.",
        )

    def test_change_list_sorting_multiple(self):
        p1 = Person.objects.create(name="Chris", gender=1, alive=True)
        p2 = Person.objects.create(name="Chris", gender=2, alive=True)
        p3 = Person.objects.create(name="Bob", gender=1, alive=True)
        link1 = reverse("admin:admin_views_person_change", args=(p1.pk,))
        link2 = reverse("admin:admin_views_person_change", args=(p2.pk,))
        link3 = reverse("admin:admin_views_person_change", args=(p3.pk,))

        # Sort by name, gender
        response = self.client.get(
            reverse("admin:admin_views_person_changelist"), {"o": "1.2"}
        )
        self.assertContentBefore(response, link3, link1)
        self.assertContentBefore(response, link1, link2)

        # Sort by gender descending, name
        response = self.client.get(
            reverse("admin:admin_views_person_changelist"), {"o": "-2.1"}
        )
        self.assertContentBefore(response, link2, link3)
        self.assertContentBefore(response, link3, link1)

    def test_change_list_sorting_preserve_queryset_ordering(self):
        """
        If no ordering is defined in `ModelAdmin.ordering` or in the query
        string, then the underlying order of the queryset should not be
        changed, even if it is defined in `Modeladmin.get_queryset()`.
        Refs #11868, #7309.
        """
        p1 = Person.objects.create(name="Amy", gender=1, alive=True, age=80)
        p2 = Person.objects.create(name="Bob", gender=1, alive=True, age=70)
        p3 = Person.objects.create(name="Chris", gender=2, alive=False, age=60)
        link1 = reverse("admin:admin_views_person_change", args=(p1.pk,))
        link2 = reverse("admin:admin_views_person_change", args=(p2.pk,))
        link3 = reverse("admin:admin_views_person_change", args=(p3.pk,))

        response = self.client.get(reverse("admin:admin_views_person_changelist"), {})
        self.assertContentBefore(response, link3, link2)
        self.assertContentBefore(response, link2, link1)

    def test_change_list_sorting_model_meta(self):
        # Test ordering on Model Meta is respected

        l1 = Language.objects.create(iso="ur", name="Urdu")
        l2 = Language.objects.create(iso="ar", name="Arabic")
        link1 = reverse("admin:admin_views_language_change", args=(quote(l1.pk),))
        link2 = reverse("admin:admin_views_language_change", args=(quote(l2.pk),))

        response = self.client.get(reverse("admin:admin_views_language_changelist"), {})
        self.assertContentBefore(response, link2, link1)

        # Test we can override with query string
        response = self.client.get(
            reverse("admin:admin_views_language_changelist"), {"o": "-1"}
        )
        self.assertContentBefore(response, link1, link2)

    def test_change_list_sorting_override_model_admin(self):
        # Test ordering on Model Admin is respected, and overrides Model Meta
        dt = datetime.datetime.now()
        p1 = Podcast.objects.create(name="A", release_date=dt)
        p2 = Podcast.objects.create(name="B", release_date=dt - datetime.timedelta(10))
        link1 = reverse("admin:admin_views_podcast_change", args=(p1.pk,))
        link2 = reverse("admin:admin_views_podcast_change", args=(p2.pk,))

        response = self.client.get(reverse("admin:admin_views_podcast_changelist"), {})
        self.assertContentBefore(response, link1, link2)

    def test_multiple_sort_same_field(self):
        # The changelist displays the correct columns if two columns correspond
        # to the same ordering field.
        dt = datetime.datetime.now()
        p1 = Podcast.objects.create(name="A", release_date=dt)
        p2 = Podcast.objects.create(name="B", release_date=dt - datetime.timedelta(10))
        link1 = reverse("admin:admin_views_podcast_change", args=(quote(p1.pk),))
        link2 = reverse("admin:admin_views_podcast_change", args=(quote(p2.pk),))

        response = self.client.get(reverse("admin:admin_views_podcast_changelist"), {})
        self.assertContentBefore(response, link1, link2)

        p1 = ComplexSortedPerson.objects.create(name="Bob", age=10)
        p2 = ComplexSortedPerson.objects.create(name="Amy", age=20)
        link1 = reverse("admin:admin_views_complexsortedperson_change", args=(p1.pk,))
        link2 = reverse("admin:admin_views_complexsortedperson_change", args=(p2.pk,))

        response = self.client.get(
            reverse("admin:admin_views_complexsortedperson_changelist"), {}
        )
        # Should have 5 columns (including action checkbox col)
        result_list_table_re = re.compile('<table id="result_list">(.*?)</thead>')
        result_list_table_head = result_list_table_re.search(str(response.content))[0]
        self.assertEqual(result_list_table_head.count('<th scope="col"'), 5)

        self.assertContains(response, "Name")
        self.assertContains(response, "Colored name")

        # Check order
        self.assertContentBefore(response, "Name", "Colored name")

        # Check sorting - should be by name
        self.assertContentBefore(response, link2, link1)

    def test_sort_indicators_admin_order(self):
        """
        The admin shows default sort indicators for all kinds of 'ordering'
        fields: field names, method on the model admin and model itself, and
        other callables. See #17252.
        """
        models = [
            (AdminOrderedField, "adminorderedfield"),
            (AdminOrderedModelMethod, "adminorderedmodelmethod"),
            (AdminOrderedAdminMethod, "adminorderedadminmethod"),
            (AdminOrderedCallable, "adminorderedcallable"),
        ]
        for model, url in models:
            model.objects.create(stuff="The Last Item", order=3)
            model.objects.create(stuff="The First Item", order=1)
            model.objects.create(stuff="The Middle Item", order=2)
            response = self.client.get(
                reverse("admin:admin_views_%s_changelist" % url), {}
            )
            # Should have 3 columns including action checkbox col.
            result_list_table_re = re.compile('<table id="result_list">(.*?)</thead>')
            result_list_table_head = result_list_table_re.search(str(response.content))[
                0
            ]
            self.assertEqual(result_list_table_head.count('<th scope="col"'), 3)
            # Check if the correct column was selected. 2 is the index of the
            # 'order' column in the model admin's 'list_display' with 0 being
            # the implicit 'action_checkbox' and 1 being the column 'stuff'.
            self.assertEqual(
                response.context["cl"].get_ordering_field_columns(), {2: "asc"}
            )
            # Check order of records.
            self.assertContentBefore(response, "The First Item", "The Middle Item")
            self.assertContentBefore(response, "The Middle Item", "The Last Item")

    def test_has_related_field_in_list_display_fk(self):
        """Joins shouldn't be performed for <FK>_id fields in list display."""
        state = State.objects.create(name="Karnataka")
        City.objects.create(state=state, name="Bangalore")
        response = self.client.get(reverse("admin:admin_views_city_changelist"), {})

        response.context["cl"].list_display = ["id", "name", "state"]
        self.assertIs(response.context["cl"].has_related_field_in_list_display(), True)

        response.context["cl"].list_display = ["id", "name", "state_id"]
        self.assertIs(response.context["cl"].has_related_field_in_list_display(), False)

    def test_has_related_field_in_list_display_o2o(self):
        """Joins shouldn't be performed for <O2O>_id fields in list display."""
        media = Media.objects.create(name="Foo")
        Vodcast.objects.create(media=media)
        response = self.client.get(reverse("admin:admin_views_vodcast_changelist"), {})

        response.context["cl"].list_display = ["media"]
        self.assertIs(response.context["cl"].has_related_field_in_list_display(), True)

        response.context["cl"].list_display = ["media_id"]
        self.assertIs(response.context["cl"].has_related_field_in_list_display(), False)

    def test_limited_filter(self):
        """
        Admin changelist filters do not contain objects excluded via
        limit_choices_to.
        """
        response = self.client.get(reverse("admin:admin_views_thing_changelist"))
        self.assertContains(
            response,
            '<nav id="changelist-filter" aria-labelledby="changelist-filter-header">',
            msg_prefix="Expected filter not found in changelist view",
        )
        self.assertNotContains(
            response,
            '<a href="?color__id__exact=3">Blue</a>',
            msg_prefix="Changelist filter not correctly limited by limit_choices_to",
        )

    def test_change_list_facet_toggle(self):
        # Toggle is visible when show_facet is the default of
        # admin.ShowFacets.ALLOW.
        admin_url = reverse("admin:admin_views_album_changelist")
        response = self.client.get(admin_url)
        self.assertContains(
            response,
            '<a href="?_facets=True" class="viewlink">Show counts</a>',
            msg_prefix="Expected facet filter toggle not found in changelist view",
        )
        response = self.client.get(f"{admin_url}?_facets=True")
        self.assertContains(
            response,
            '<a href="?" class="hidelink">Hide counts</a>',
            msg_prefix="Expected facet filter toggle not found in changelist view",
        )
        # Toggle is not visible when show_facet is admin.ShowFacets.ALWAYS.
        response = self.client.get(reverse("admin:admin_views_workhour_changelist"))
        self.assertNotContains(
            response,
            "Show counts",
            msg_prefix="Expected not to find facet filter toggle in changelist view",
        )
        self.assertNotContains(
            response,
            "Hide counts",
            msg_prefix="Expected not to find facet filter toggle in changelist view",
        )
        # Toggle is not visible when show_facet is admin.ShowFacets.NEVER.
        response = self.client.get(reverse("admin:admin_views_fooddelivery_changelist"))
        self.assertNotContains(
            response,
            "Show counts",
            msg_prefix="Expected not to find facet filter toggle in changelist view",
        )
        self.assertNotContains(
            response,
            "Hide counts",
            msg_prefix="Expected not to find facet filter toggle in changelist view",
        )

    def test_relation_spanning_filters(self):
        changelist_url = reverse("admin:admin_views_chapterxtra1_changelist")
        response = self.client.get(changelist_url)
        self.assertContains(
            response,
            '<nav id="changelist-filter" aria-labelledby="changelist-filter-header">',
        )
        filters = {
            "chap__id__exact": {
                "values": [c.id for c in Chapter.objects.all()],
                "test": lambda obj, value: obj.chap.id == value,
            },
            "chap__title": {
                "values": [c.title for c in Chapter.objects.all()],
                "test": lambda obj, value: obj.chap.title == value,
            },
            "chap__book__id__exact": {
                "values": [b.id for b in Book.objects.all()],
                "test": lambda obj, value: obj.chap.book.id == value,
            },
            "chap__book__name": {
                "values": [b.name for b in Book.objects.all()],
                "test": lambda obj, value: obj.chap.book.name == value,
            },
            "chap__book__promo__id__exact": {
                "values": [p.id for p in Promo.objects.all()],
                "test": lambda obj, value: obj.chap.book.promo_set.filter(
                    id=value
                ).exists(),
            },
            "chap__book__promo__name": {
                "values": [p.name for p in Promo.objects.all()],
                "test": lambda obj, value: obj.chap.book.promo_set.filter(
                    name=value
                ).exists(),
            },
            # A forward relation (book) after a reverse relation (promo).
            "guest_author__promo__book__id__exact": {
                "values": [p.id for p in Book.objects.all()],
                "test": lambda obj, value: obj.guest_author.promo_set.filter(
                    book=value
                ).exists(),
            },
        }
        for filter_path, params in filters.items():
            for value in params["values"]:
                query_string = urlencode({filter_path: value})
                # ensure filter link exists
                self.assertContains(response, '<a href="?%s"' % query_string)
                # ensure link works
                filtered_response = self.client.get(
                    "%s?%s" % (changelist_url, query_string)
                )
                self.assertEqual(filtered_response.status_code, 200)
                # ensure changelist contains only valid objects
                for obj in filtered_response.context["cl"].queryset.all():
                    self.assertTrue(params["test"](obj, value))

    def test_incorrect_lookup_parameters(self):
        """Ensure incorrect lookup parameters are handled gracefully."""
        changelist_url = reverse("admin:admin_views_thing_changelist")
        response = self.client.get(changelist_url, {"notarealfield": "5"})
        self.assertRedirects(response, "%s?e=1" % changelist_url)

        # Spanning relationships through a nonexistent related object (Refs #16716)
        response = self.client.get(changelist_url, {"notarealfield__whatever": "5"})
        self.assertRedirects(response, "%s?e=1" % changelist_url)

        response = self.client.get(
            changelist_url, {"color__id__exact": "StringNotInteger!"}
        )
        self.assertRedirects(response, "%s?e=1" % changelist_url)

        # Regression test for #18530
        response = self.client.get(changelist_url, {"pub_date__gte": "foo"})
        self.assertRedirects(response, "%s?e=1" % changelist_url)

    def test_isnull_lookups(self):
        """Ensure is_null is handled correctly."""
        Article.objects.create(
            title="I Could Go Anywhere",
            content="Versatile",
            date=datetime.datetime.now(),
        )
        changelist_url = reverse("admin:admin_views_article_changelist")
        response = self.client.get(changelist_url)
        self.assertContains(response, "4 articles")
        response = self.client.get(changelist_url, {"section__isnull": "false"})
        self.assertContains(response, "3 articles")
        response = self.client.get(changelist_url, {"section__isnull": "0"})
        self.assertContains(response, "3 articles")
        response = self.client.get(changelist_url, {"section__isnull": "true"})
        self.assertContains(response, "1 article")
        response = self.client.get(changelist_url, {"section__isnull": "1"})
        self.assertContains(response, "1 article")

    def test_logout_and_password_change_URLs(self):
        response = self.client.get(reverse("admin:admin_views_article_changelist"))
        self.assertContains(
            response,
            '<form id="logout-form" method="post" action="%s">'
            % reverse("admin:logout"),
        )
        self.assertContains(
            response, '<a href="%s">' % reverse("admin:password_change")
        )

    def test_named_group_field_choices_change_list(self):
        """
        Ensures the admin changelist shows correct values in the relevant column
        for rows corresponding to instances of a model in which a named group
        has been used in the choices option of a field.
        """
        link1 = reverse("admin:admin_views_fabric_change", args=(self.fab1.pk,))
        link2 = reverse("admin:admin_views_fabric_change", args=(self.fab2.pk,))
        response = self.client.get(reverse("admin:admin_views_fabric_changelist"))
        fail_msg = (
            "Changelist table isn't showing the right human-readable values "
            "set by a model field 'choices' option named group."
        )
        self.assertContains(
            response,
            '<a href="%s">Horizontal</a>' % link1,
            msg_prefix=fail_msg,
            html=True,
        )
        self.assertContains(
            response,
            '<a href="%s">Vertical</a>' % link2,
            msg_prefix=fail_msg,
            html=True,
        )

    def test_named_group_field_choices_filter(self):
        """
        Ensures the filter UI shows correctly when at least one named group has
        been used in the choices option of a model field.
        """
        response = self.client.get(reverse("admin:admin_views_fabric_changelist"))
        fail_msg = (
            "Changelist filter isn't showing options contained inside a model "
            "field 'choices' option named group."
        )
        self.assertContains(
            response,
            '<nav id="changelist-filter" aria-labelledby="changelist-filter-header">',
        )
        self.assertContains(
            response,
            '<a href="?surface__exact=x">Horizontal</a>',
            msg_prefix=fail_msg,
            html=True,
        )
        self.assertContains(
            response,
            '<a href="?surface__exact=y">Vertical</a>',
            msg_prefix=fail_msg,
            html=True,
        )

    def test_change_list_null_boolean_display(self):
        Post.objects.create(public=None)
        response = self.client.get(reverse("admin:admin_views_post_changelist"))
        self.assertContains(response, "icon-unknown.svg")

    def test_display_decorator_with_boolean_and_empty_value(self):
        msg = (
            "The boolean and empty_value arguments to the @display decorator "
            "are mutually exclusive."
        )
        with self.assertRaisesMessage(ValueError, msg):

            class BookAdmin(admin.ModelAdmin):
                @admin.display(boolean=True, empty_value="(Missing)")
                def is_published(self, obj):
                    return obj.publish_date is not None

    def test_i18n_language_non_english_default(self):
        """
        Check if the JavaScript i18n view returns an empty language catalog
        if the default language is non-English but the selected language
        is English. See #13388 and #3594 for more details.
        """
        with self.settings(LANGUAGE_CODE="fr"), translation.override("en-us"):
            response = self.client.get(reverse("admin:jsi18n"))
            self.assertNotContains(response, "Choisir une heure")

    def test_i18n_language_non_english_fallback(self):
        """
        Makes sure that the fallback language is still working properly
        in cases where the selected language cannot be found.
        """
        with self.settings(LANGUAGE_CODE="fr"), translation.override("none"):
            response = self.client.get(reverse("admin:jsi18n"))
            self.assertContains(response, "Choisir une heure")

    def test_jsi18n_with_context(self):
        response = self.client.get(reverse("admin-extra-context:jsi18n"))
        self.assertEqual(response.status_code, 200)

    def test_jsi18n_format_fallback(self):
        """
        The JavaScript i18n view doesn't return localized date/time formats
        when the selected language cannot be found.
        """
        with self.settings(LANGUAGE_CODE="ru"), translation.override("none"):
            response = self.client.get(reverse("admin:jsi18n"))
            self.assertNotContains(response, "%d.%m.%Y %H:%M:%S")
            self.assertContains(response, "%Y-%m-%d %H:%M:%S")

    def test_disallowed_filtering(self):
        with self.assertLogs("django.security.DisallowedModelAdminLookup", "ERROR"):
            response = self.client.get(
                "%s?owner__email__startswith=fuzzy"
                % reverse("admin:admin_views_album_changelist")
            )
        self.assertEqual(response.status_code, 400)

        # Filters are allowed if explicitly included in list_filter
        response = self.client.get(
            "%s?color__value__startswith=red"
            % reverse("admin:admin_views_thing_changelist")
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.get(
            "%s?color__value=red" % reverse("admin:admin_views_thing_changelist")
        )
        self.assertEqual(response.status_code, 200)

        # Filters should be allowed if they involve a local field without the
        # need to allow them in list_filter or date_hierarchy.
        response = self.client.get(
            "%s?age__gt=30" % reverse("admin:admin_views_person_changelist")
        )
        self.assertEqual(response.status_code, 200)

        e1 = Employee.objects.create(
            name="Anonymous", gender=1, age=22, alive=True, code="123"
        )
        e2 = Employee.objects.create(
            name="Visitor", gender=2, age=19, alive=True, code="124"
        )
        WorkHour.objects.create(datum=datetime.datetime.now(), employee=e1)
        WorkHour.objects.create(datum=datetime.datetime.now(), employee=e2)
        response = self.client.get(reverse("admin:admin_views_workhour_changelist"))
        self.assertContains(response, "employee__person_ptr__exact")
        response = self.client.get(
            "%s?employee__person_ptr__exact=%d"
            % (reverse("admin:admin_views_workhour_changelist"), e1.pk)
        )
        self.assertEqual(response.status_code, 200)

    def test_disallowed_to_field(self):
        url = reverse("admin:admin_views_section_changelist")
        with self.assertLogs("django.security.DisallowedModelAdminToField", "ERROR"):
            response = self.client.get(url, {TO_FIELD_VAR: "missing_field"})
        self.assertEqual(response.status_code, 400)

        # Specifying a field that is not referred by any other model registered
        # to this admin site should raise an exception.
        with self.assertLogs("django.security.DisallowedModelAdminToField", "ERROR"):
            response = self.client.get(
                reverse("admin:admin_views_section_changelist"), {TO_FIELD_VAR: "name"}
            )
        self.assertEqual(response.status_code, 400)

        # Primary key should always be allowed, even if the referenced model
        # isn't registered.
        response = self.client.get(
            reverse("admin:admin_views_notreferenced_changelist"), {TO_FIELD_VAR: "id"}
        )
        self.assertEqual(response.status_code, 200)

        # Specifying a field referenced by another model though a m2m should be
        # allowed.
        response = self.client.get(
            reverse("admin:admin_views_recipe_changelist"), {TO_FIELD_VAR: "rname"}
        )
        self.assertEqual(response.status_code, 200)

        # Specifying a field referenced through a reverse m2m relationship
        # should be allowed.
        response = self.client.get(
            reverse("admin:admin_views_ingredient_changelist"), {TO_FIELD_VAR: "iname"}
        )
        self.assertEqual(response.status_code, 200)

        # Specifying a field that is not referred by any other model directly
        # registered to this admin site but registered through inheritance
        # should be allowed.
        response = self.client.get(
            reverse("admin:admin_views_referencedbyparent_changelist"),
            {TO_FIELD_VAR: "name"},
        )
        self.assertEqual(response.status_code, 200)

        # Specifying a field that is only referred to by a inline of a
        # registered model should be allowed.
        response = self.client.get(
            reverse("admin:admin_views_referencedbyinline_changelist"),
            {TO_FIELD_VAR: "name"},
        )
        self.assertEqual(response.status_code, 200)

        # #25622 - Specifying a field of a model only referred by a generic
        # relation should raise DisallowedModelAdminToField.
        url = reverse("admin:admin_views_referencedbygenrel_changelist")
        with self.assertLogs("django.security.DisallowedModelAdminToField", "ERROR"):
            response = self.client.get(url, {TO_FIELD_VAR: "object_id"})
        self.assertEqual(response.status_code, 400)

        # We also want to prevent the add, change, and delete views from
        # leaking a disallowed field value.
        with self.assertLogs("django.security.DisallowedModelAdminToField", "ERROR"):
            response = self.client.post(
                reverse("admin:admin_views_section_add"), {TO_FIELD_VAR: "name"}
            )
        self.assertEqual(response.status_code, 400)

        section = Section.objects.create()
        url = reverse("admin:admin_views_section_change", args=(section.pk,))
        with self.assertLogs("django.security.DisallowedModelAdminToField", "ERROR"):
            response = self.client.post(url, {TO_FIELD_VAR: "name"})
        self.assertEqual(response.status_code, 400)

        url = reverse("admin:admin_views_section_delete", args=(section.pk,))
        with self.assertLogs("django.security.DisallowedModelAdminToField", "ERROR"):
            response = self.client.post(url, {TO_FIELD_VAR: "name"})
        self.assertEqual(response.status_code, 400)

    def test_allowed_filtering_15103(self):
        """
        Regressions test for ticket 15103 - filtering on fields defined in a
        ForeignKey 'limit_choices_to' should be allowed, otherwise raw_id_fields
        can break.
        """
        # Filters should be allowed if they are defined on a ForeignKey
        # pointing to this model.
        url = "%s?leader__name=Palin&leader__age=27" % reverse(
            "admin:admin_views_inquisition_changelist"
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_popup_dismiss_related(self):
        """
        Regression test for ticket 20664 - ensure the pk is properly quoted.
        """
        actor = Actor.objects.create(name="Palin", age=27)
        response = self.client.get(
            "%s?%s" % (reverse("admin:admin_views_actor_changelist"), IS_POPUP_VAR)
        )
        self.assertContains(response, 'data-popup-opener="%s"' % actor.pk)

    def test_hide_change_password(self):
        """
        Tests if the "change password" link in the admin is hidden if the User
        does not have a usable password set.
        (against 9bea85795705d015cdadc82c68b99196a8554f5c)
        """
        user = User.objects.get(username="super")
        user.set_unusable_password()
        user.save()
        self.client.force_login(user)
        response = self.client.get(reverse("admin:index"))
        self.assertNotContains(
            response,
            reverse("admin:password_change"),
            msg_prefix=(
                'The "change password" link should not be displayed if a user does not '
                "have a usable password."
            ),
        )

    def test_change_view_with_show_delete_extra_context(self):
        """
        The 'show_delete' context variable in the admin's change view controls
        the display of the delete button.
        """
        instance = UndeletableObject.objects.create(name="foo")
        response = self.client.get(
            reverse("admin:admin_views_undeletableobject_change", args=(instance.pk,))
        )
        self.assertNotContains(response, "deletelink")

    def test_change_view_logs_m2m_field_changes(self):
        """Changes to ManyToManyFields are included in the object's history."""
        pizza = ReadablePizza.objects.create(name="Cheese")
        cheese = Topping.objects.create(name="cheese")
        post_data = {"name": pizza.name, "toppings": [cheese.pk]}
        response = self.client.post(
            reverse("admin:admin_views_readablepizza_change", args=(pizza.pk,)),
            post_data,
        )
        self.assertRedirects(
            response, reverse("admin:admin_views_readablepizza_changelist")
        )
        pizza_ctype = ContentType.objects.get_for_model(
            ReadablePizza, for_concrete_model=False
        )
        log = LogEntry.objects.filter(
            content_type=pizza_ctype, object_id=pizza.pk
        ).first()
        self.assertEqual(log.get_change_message(), "Changed Toppings.")

    def test_allows_attributeerror_to_bubble_up(self):
        """
        AttributeErrors are allowed to bubble when raised inside a change list
        view. Requires a model to be created so there's something to display.
        Refs: #16655, #18593, and #18747
        """
        Simple.objects.create()
        with self.assertRaises(AttributeError):
            self.client.get(reverse("admin:admin_views_simple_changelist"))

    def test_changelist_with_no_change_url(self):
        """
        ModelAdmin.changelist_view shouldn't result in a NoReverseMatch if url
        for change_view is removed from get_urls (#20934).
        """
        o = UnchangeableObject.objects.create()
        response = self.client.get(
            reverse("admin:admin_views_unchangeableobject_changelist")
        )
        # Check the format of the shown object -- shouldn't contain a change link
        self.assertContains(
            response, '<th class="field-__str__">%s</th>' % o, html=True
        )

    def test_invalid_appindex_url(self):
        """
        #21056 -- URL reversing shouldn't work for nonexistent apps.
        """
        good_url = "/test_admin/admin/admin_views/"
        confirm_good_url = reverse(
            "admin:app_list", kwargs={"app_label": "admin_views"}
        )
        self.assertEqual(good_url, confirm_good_url)

        with self.assertRaises(NoReverseMatch):
            reverse("admin:app_list", kwargs={"app_label": "this_should_fail"})
        with self.assertRaises(NoReverseMatch):
            reverse("admin:app_list", args=("admin_views2",))

    def test_resolve_admin_views(self):
        index_match = resolve("/test_admin/admin4/")
        list_match = resolve("/test_admin/admin4/auth/user/")
        self.assertIs(index_match.func.admin_site, customadmin.simple_site)
        self.assertIsInstance(
            list_match.func.model_admin, customadmin.CustomPwdTemplateUserAdmin
        )

    def test_adminsite_display_site_url(self):
        """
        #13749 - Admin should display link to front-end site 'View site'
        """
        url = reverse("admin:index")
        response = self.client.get(url)
        self.assertEqual(response.context["site_url"], "/my-site-url/")
        self.assertContains(response, '<a href="/my-site-url/">View site</a>')

    def test_date_hierarchy_empty_queryset(self):
        self.assertIs(Question.objects.exists(), False)
        response = self.client.get(reverse("admin:admin_views_answer2_changelist"))
        self.assertEqual(response.status_code, 200)

    @override_settings(TIME_ZONE="America/Sao_Paulo", USE_TZ=True)
    def test_date_hierarchy_timezone_dst(self):
        # This datetime doesn't exist in this timezone due to DST.
        for date in make_aware_datetimes(
            datetime.datetime(2016, 10, 16, 15), "America/Sao_Paulo"
        ):
            with self.subTest(repr(date.tzinfo)):
                q = Question.objects.create(question="Why?", expires=date)
                Answer2.objects.create(question=q, answer="Because.")
                response = self.client.get(
                    reverse("admin:admin_views_answer2_changelist")
                )
                self.assertContains(response, "question__expires__day=16")
                self.assertContains(response, "question__expires__month=10")
                self.assertContains(response, "question__expires__year=2016")

    @override_settings(TIME_ZONE="America/Los_Angeles", USE_TZ=True)
    def test_date_hierarchy_local_date_differ_from_utc(self):
        # This datetime is 2017-01-01 in UTC.
        for date in make_aware_datetimes(
            datetime.datetime(2016, 12, 31, 16), "America/Los_Angeles"
        ):
            with self.subTest(repr(date.tzinfo)):
                q = Question.objects.create(question="Why?", expires=date)
                Answer2.objects.create(question=q, answer="Because.")
                response = self.client.get(
                    reverse("admin:admin_views_answer2_changelist")
                )
                self.assertContains(response, "question__expires__day=31")
                self.assertContains(response, "question__expires__month=12")
                self.assertContains(response, "question__expires__year=2016")

    def test_sortable_by_columns_subset(self):
        expected_sortable_fields = ("date", "callable_year")
        expected_not_sortable_fields = (
            "content",
            "model_year",
            "modeladmin_year",
            "model_year_reversed",
            "section",
        )
        response = self.client.get(reverse("admin6:admin_views_article_changelist"))
        for field_name in expected_sortable_fields:
            self.assertContains(
                response, '<th scope="col" class="sortable column-%s">' % field_name
            )
        for field_name in expected_not_sortable_fields:
            self.assertContains(
                response, '<th scope="col" class="column-%s">' % field_name
            )

    def test_get_sortable_by_columns_subset(self):
        response = self.client.get(reverse("admin6:admin_views_actor_changelist"))
        self.assertContains(response, '<th scope="col" class="sortable column-age">')
        self.assertContains(response, '<th scope="col" class="column-name">')

    def test_sortable_by_no_column(self):
        expected_not_sortable_fields = ("title", "book")
        response = self.client.get(reverse("admin6:admin_views_chapter_changelist"))
        for field_name in expected_not_sortable_fields:
            self.assertContains(
                response, '<th scope="col" class="column-%s">' % field_name
            )
        self.assertNotContains(response, '<th scope="col" class="sortable column')

    def test_get_sortable_by_no_column(self):
        response = self.client.get(reverse("admin6:admin_views_color_changelist"))
        self.assertContains(response, '<th scope="col" class="column-value">')
        self.assertNotContains(response, '<th scope="col" class="sortable column')

    def test_app_index_context(self):
        response = self.client.get(reverse("admin:app_list", args=("admin_views",)))
        self.assertContains(
            response,
            "<title>Admin_Views administration | Django site admin</title>",
        )
        self.assertEqual(response.context["title"], "Admin_Views administration")
        self.assertEqual(response.context["app_label"], "admin_views")
        # Models are sorted alphabetically by default.
        models = [model["name"] for model in response.context["app_list"][0]["models"]]
        self.assertSequenceEqual(models, sorted(models))

    def test_app_index_context_reordered(self):
        self.client.force_login(self.superuser)
        response = self.client.get(reverse("admin2:app_list", args=("admin_views",)))
        self.assertContains(
            response,
            "<title>Admin_Views administration | Django site admin</title>",
        )
        # Models are in reverse order.
        models = [model["name"] for model in response.context["app_list"][0]["models"]]
        self.assertSequenceEqual(models, sorted(models, reverse=True))

    def test_change_view_subtitle_per_object(self):
        response = self.client.get(
            reverse("admin:admin_views_article_change", args=(self.a1.pk,)),
        )
        self.assertContains(
            response,
            "<title>Article 1 | Change article | Django site admin</title>",
        )
        self.assertContains(response, "<h1>Change article</h1>")
        self.assertContains(response, "<h2>Article 1</h2>")
        response = self.client.get(
            reverse("admin:admin_views_article_change", args=(self.a2.pk,)),
        )
        self.assertContains(
            response,
            "<title>Article 2 | Change article | Django site admin</title>",
        )
        self.assertContains(response, "<h1>Change article</h1>")
        self.assertContains(response, "<h2>Article 2</h2>")

    def test_error_in_titles(self):
        for url, subtitle in [
            (
                reverse("admin:admin_views_article_change", args=(self.a1.pk,)),
                "Article 1 | Change article",
            ),
            (reverse("admin:admin_views_article_add"), "Add article"),
            (reverse("admin:login"), "Log in"),
            (reverse("admin:password_change"), "Password change"),
            (
                reverse("admin:auth_user_password_change", args=(self.superuser.id,)),
                "Change password: super",
            ),
        ]:
            with self.subTest(url=url, subtitle=subtitle):
                response = self.client.post(url, {})
                self.assertContains(response, f"<title>Error: {subtitle}")

    def test_view_subtitle_per_object(self):
        viewuser = User.objects.create_user(
            username="viewuser",
            password="secret",
            is_staff=True,
        )
        viewuser.user_permissions.add(
            get_perm(Article, get_permission_codename("view", Article._meta)),
        )
        self.client.force_login(viewuser)
        response = self.client.get(
            reverse("admin:admin_views_article_change", args=(self.a1.pk,)),
        )
        self.assertContains(
            response,
            "<title>Article 1 | View article | Django site admin</title>",
        )
        self.assertContains(response, "<h1>View article</h1>")
        self.assertContains(response, "<h2>Article 1</h2>")
        response = self.client.get(
            reverse("admin:admin_views_article_change", args=(self.a2.pk,)),
        )
        self.assertContains(
            response,
            "<title>Article 2 | View article | Django site admin</title>",
        )
        self.assertContains(response, "<h1>View article</h1>")
        self.assertContains(response, "<h2>Article 2</h2>")

    def test_formset_kwargs_can_be_overridden(self):
        response = self.client.get(reverse("admin:admin_views_city_add"))
        self.assertContains(response, "overridden_name")

    def test_render_views_no_subtitle(self):
        tests = [
            reverse("admin:index"),
            reverse("admin:password_change"),
            reverse("admin:app_list", args=("admin_views",)),
            reverse("admin:admin_views_article_delete", args=(self.a1.pk,)),
            reverse("admin:admin_views_article_history", args=(self.a1.pk,)),
        ]
        for url in tests:
            with self.subTest(url=url):
                with self.assertNoLogs("django.template", "DEBUG"):
                    self.client.get(url)
        # Login must be after logout.
        with self.assertNoLogs("django.template", "DEBUG"):
            self.client.post(reverse("admin:logout"))
            self.client.get(reverse("admin:login"))

    def test_render_delete_selected_confirmation_no_subtitle(self):
        post_data = {
            "action": "delete_selected",
            "selected_across": "0",
            "index": "0",
            "_selected_action": self.a1.pk,
        }
        with self.assertNoLogs("django.template", "DEBUG"):
            self.client.post(reverse("admin:admin_views_article_changelist"), post_data)

    @override_settings(
        AUTH_PASSWORD_VALIDATORS=[
            {
                "NAME": (
                    "django.contrib.auth.password_validation."
                    "UserAttributeSimilarityValidator"
                )
            },
            {
                "NAME": (
                    "django.contrib.auth.password_validation."
                    "NumericPasswordValidator"
                )
            },
        ]
    )
    def test_password_change_helptext(self):
        response = self.client.get(reverse("admin:password_change"))
        self.assertContains(
            response, '<div class="help" id="id_new_password1_helptext">'
        )

    def test_enable_zooming_on_mobile(self):
        response = self.client.get(reverse("admin:index"))
        self.assertContains(
            response,
            '<meta name="viewport" content="width=device-width, initial-scale=1.0">',
        )

    def test_header(self):
        response = self.client.get(reverse("admin:index"))
        self.assertContains(response, '<header id="header">')
        self.client.logout()
        response = self.client.get(reverse("admin:login"))
        self.assertContains(response, '<header id="header">')

    def test_main_content(self):
        response = self.client.get(reverse("admin:index"))
        self.assertContains(
            response,
            '<main id="content-start" class="content" tabindex="-1">',
        )

    def test_footer(self):
        response = self.client.get(reverse("admin:index"))
        self.assertContains(response, '<footer id="footer">')
        self.client.logout()
        response = self.client.get(reverse("admin:login"))
        self.assertContains(response, '<footer id="footer">')

    def test_aria_describedby_for_add_and_change_links(self):
        response = self.client.get(reverse("admin:index"))
        tests = [
            ("admin_views", "actor"),
            ("admin_views", "worker"),
            ("auth", "group"),
            ("auth", "user"),
        ]
        for app_label, model_name in tests:
            with self.subTest(app_label=app_label, model_name=model_name):
                row_id = f"{app_label}-{model_name}"
                self.assertContains(response, f'<th scope="row" id="{row_id}">')
                self.assertContains(
                    response,
                    f'<a href="/test_admin/admin/{app_label}/{model_name}/" '
                    f'class="changelink" aria-describedby="{row_id}">Change</a>',
                )
                self.assertContains(
                    response,
                    f'<a href="/test_admin/admin/{app_label}/{model_name}/add/" '
                    f'class="addlink" aria-describedby="{row_id}">Add</a>',
                )


@override_settings(
    AUTH_PASSWORD_VALIDATORS=[
        {
            "NAME": (
                "django.contrib.auth.password_validation."
                "UserAttributeSimilarityValidator"
            )
        },
        {
            "NAME": (
                "django.contrib.auth.password_validation." "NumericPasswordValidator"
            )
        },
    ],
    TEMPLATES=[
        {
            "BACKEND": "django.template.backends.django.DjangoTemplates",
            # Put this app's and the shared tests templates dirs in DIRS to
            # take precedence over the admin's templates dir.
            "DIRS": [
                os.path.join(os.path.dirname(__file__), "templates"),
                os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates"),
            ],
            "APP_DIRS": True,
            "OPTIONS": {
                "context_processors": [
                    "django.template.context_processors.request",
                    "django.contrib.auth.context_processors.auth",
                    "django.contrib.messages.context_processors.messages",
                ],
            },
        }
    ],
)
class AdminCustomTemplateTests(AdminViewBasicTestCase):
    def test_custom_model_admin_templates(self):
        # Test custom change list template with custom extra context
        response = self.client.get(
            reverse("admin:admin_views_customarticle_changelist")
        )
        self.assertContains(response, "var hello = 'Hello!';")
        self.assertTemplateUsed(response, "custom_admin/change_list.html")

        # Test custom add form template
        response = self.client.get(reverse("admin:admin_views_customarticle_add"))
        self.assertTemplateUsed(response, "custom_admin/add_form.html")

        # Add an article so we can test delete, change, and history views
        post = self.client.post(
            reverse("admin:admin_views_customarticle_add"),
            {
                "content": "<p>great article</p>",
                "date_0": "2008-03-18",
                "date_1": "10:54:39",
            },
        )
        self.assertRedirects(
            post, reverse("admin:admin_views_customarticle_changelist")
        )
        self.assertEqual(CustomArticle.objects.count(), 1)
        article_pk = CustomArticle.objects.all()[0].pk

        # Test custom delete, change, and object history templates
        # Test custom change form template
        response = self.client.get(
            reverse("admin:admin_views_customarticle_change", args=(article_pk,))
        )
        self.assertTemplateUsed(response, "custom_admin/change_form.html")
        response = self.client.get(
            reverse("admin:admin_views_customarticle_delete", args=(article_pk,))
        )
        self.assertTemplateUsed(response, "custom_admin/delete_confirmation.html")
        response = self.client.post(
            reverse("admin:admin_views_customarticle_changelist"),
            data={
                "index": 0,
                "action": ["delete_selected"],
                "_selected_action": ["1"],
            },
        )
        self.assertTemplateUsed(
            response, "custom_admin/delete_selected_confirmation.html"
        )
        response = self.client.get(
            reverse("admin:admin_views_customarticle_history", args=(article_pk,))
        )
        self.assertTemplateUsed(response, "custom_admin/object_history.html")

        # A custom popup response template may be specified by
        # ModelAdmin.popup_response_template.
        response = self.client.post(
            reverse("admin:admin_views_customarticle_add") + "?%s=1" % IS_POPUP_VAR,
            {
                "content": "<p>great article</p>",
                "date_0": "2008-03-18",
                "date_1": "10:54:39",
                IS_POPUP_VAR: "1",
            },
        )
        self.assertEqual(response.template_name, "custom_admin/popup_response.html")

    def test_extended_bodyclass_template_change_form(self):
        """
        The admin/change_form.html template uses block.super in the
        bodyclass block.
        """
        response = self.client.get(reverse("admin:admin_views_section_add"))
        self.assertContains(response, "bodyclass_consistency_check ")

    def test_extended_extrabody(self):
        response = self.client.get(reverse("admin:admin_views_section_add"))
        self.assertContains(response, "extrabody_check\n</body>")

    def test_change_password_template(self):
        user = User.objects.get(username="super")
        response = self.client.get(
            reverse("admin:auth_user_password_change", args=(user.id,))
        )
        # The auth/user/change_password.html template uses super in the
        # bodyclass block.
        self.assertContains(response, "bodyclass_consistency_check ")

        # When a site has multiple passwords in the browser's password manager,
        # a browser pop up asks which user the new password is for. To prevent
        # this, the username is added to the change password form.
        self.assertContains(
            response, '<input type="text" name="username" value="super" class="hidden">'
        )

        # help text for passwords has an id.
        self.assertContains(
            response,
            '<div class="help" id="id_password1_helptext"><ul><li>'
            "Your password can’t be too similar to your other personal information."
            "</li><li>Your password can’t be entirely numeric.</li></ul></div>",
        )
        self.assertContains(
            response,
            '<div class="help" id="id_password2_helptext">'
            "Enter the same password as before, for verification.</div>",
        )

    def test_change_password_template_helptext_no_id(self):
        user = User.objects.get(username="super")

        class EmptyIdForLabelTextInput(forms.TextInput):
            def id_for_label(self, id):
                return None

        class EmptyIdForLabelHelpTextPasswordChangeForm(AdminPasswordChangeForm):
            password1 = forms.CharField(
                help_text="Your new password", widget=EmptyIdForLabelTextInput()
            )

        class CustomUserAdmin(UserAdmin):
            change_password_form = EmptyIdForLabelHelpTextPasswordChangeForm

        request = RequestFactory().get(
            reverse("admin:auth_user_password_change", args=(user.id,))
        )
        request.user = user
        user_admin = CustomUserAdmin(User, site)
        response = user_admin.user_change_password(request, str(user.pk))
        self.assertContains(response, '<div class="help">')

    def test_extended_bodyclass_template_index(self):
        """
        The admin/index.html template uses block.super in the bodyclass block.
        """
        response = self.client.get(reverse("admin:index"))
        self.assertContains(response, "bodyclass_consistency_check ")

    def test_extended_bodyclass_change_list(self):
        """
        The admin/change_list.html' template uses block.super
        in the bodyclass block.
        """
        response = self.client.get(reverse("admin:admin_views_article_changelist"))
        self.assertContains(response, "bodyclass_consistency_check ")

    def test_extended_bodyclass_template_login(self):
        """
        The admin/login.html template uses block.super in the
        bodyclass block.
        """
        self.client.logout()
        response = self.client.get(reverse("admin:login"))
        self.assertContains(response, "bodyclass_consistency_check ")

    def test_extended_bodyclass_template_delete_confirmation(self):
        """
        The admin/delete_confirmation.html template uses
        block.super in the bodyclass block.
        """
        group = Group.objects.create(name="foogroup")
        response = self.client.get(reverse("admin:auth_group_delete", args=(group.id,)))
        self.assertContains(response, "bodyclass_consistency_check ")

    def test_extended_bodyclass_template_delete_selected_confirmation(self):
        """
        The admin/delete_selected_confirmation.html template uses
        block.super in bodyclass block.
        """
        group = Group.objects.create(name="foogroup")
        post_data = {
            "action": "delete_selected",
            "selected_across": "0",
            "index": "0",
            "_selected_action": group.id,
        }
        response = self.client.post(reverse("admin:auth_group_changelist"), post_data)
        self.assertEqual(response.context["site_header"], "Django administration")
        self.assertContains(response, "bodyclass_consistency_check ")

    def test_filter_with_custom_template(self):
        """
        A custom template can be used to render an admin filter.
        """
        response = self.client.get(reverse("admin:admin_views_color2_changelist"))
        self.assertTemplateUsed(response, "custom_filter_template.html")


@override_settings(ROOT_URLCONF="admin_views.urls")
class AdminViewFormUrlTest(TestCase):
    current_app = "admin3"

    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="super", password="secret", email="super@example.com"
        )
        cls.s1 = Section.objects.create(name="Test section")
        cls.a1 = Article.objects.create(
            content="<p>Middle content</p>",
            date=datetime.datetime(2008, 3, 18, 11, 54, 58),
            section=cls.s1,
        )
        cls.a2 = Article.objects.create(
            content="<p>Oldest content</p>",
            date=datetime.datetime(2000, 3, 18, 11, 54, 58),
            section=cls.s1,
        )
        cls.a3 = Article.objects.create(
            content="<p>Newest content</p>",
            date=datetime.datetime(2009, 3, 18, 11, 54, 58),
            section=cls.s1,
        )
        cls.p1 = PrePopulatedPost.objects.create(
            title="A Long Title", published=True, slug="a-long-title"
        )

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_change_form_URL_has_correct_value(self):
        """
        change_view has form_url in response.context
        """
        response = self.client.get(
            reverse(
                "admin:admin_views_section_change",
                args=(self.s1.pk,),
                current_app=self.current_app,
            )
        )
        self.assertIn(
            "form_url", response.context, msg="form_url not present in response.context"
        )
        self.assertEqual(response.context["form_url"], "pony")

    def test_initial_data_can_be_overridden(self):
        """
        The behavior for setting initial form data can be overridden in the
        ModelAdmin class. Usually, the initial value is set via the GET params.
        """
        response = self.client.get(
            reverse("admin:admin_views_restaurant_add", current_app=self.current_app),
            {"name": "test_value"},
        )
        # this would be the usual behaviour
        self.assertNotContains(response, 'value="test_value"')
        # this is the overridden behaviour
        self.assertContains(response, 'value="overridden_value"')


@override_settings(ROOT_URLCONF="admin_views.urls")
class AdminJavaScriptTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="super", password="secret", email="super@example.com"
        )

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_js_minified_only_if_debug_is_false(self):
        """
        The minified versions of the JS files are only used when DEBUG is False.
        """
        with override_settings(DEBUG=False):
            response = self.client.get(reverse("admin:admin_views_section_add"))
            self.assertNotContains(response, "vendor/jquery/jquery.js")
            self.assertContains(response, "vendor/jquery/jquery.min.js")
            self.assertContains(response, "prepopulate.js")
            self.assertContains(response, "actions.js")
            self.assertContains(response, "inlines.js")
        with override_settings(DEBUG=True):
            response = self.client.get(reverse("admin:admin_views_section_add"))
            self.assertContains(response, "vendor/jquery/jquery.js")
            self.assertNotContains(response, "vendor/jquery/jquery.min.js")
            self.assertContains(response, "prepopulate.js")
            self.assertContains(response, "actions.js")
            self.assertContains(response, "inlines.js")


@override_settings(ROOT_URLCONF="admin_views.urls")
class SaveAsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="super", password="secret", email="super@example.com"
        )
        cls.per1 = Person.objects.create(name="John Mauchly", gender=1, alive=True)

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_save_as_duplication(self):
        """'save as' creates a new person"""
        post_data = {"_saveasnew": "", "name": "John M", "gender": 1, "age": 42}
        response = self.client.post(
            reverse("admin:admin_views_person_change", args=(self.per1.pk,)), post_data
        )
        self.assertEqual(len(Person.objects.filter(name="John M")), 1)
        self.assertEqual(len(Person.objects.filter(id=self.per1.pk)), 1)
        new_person = Person.objects.latest("id")
        self.assertRedirects(
            response, reverse("admin:admin_views_person_change", args=(new_person.pk,))
        )

    def test_save_as_continue_false(self):
        """
        Saving a new object using "Save as new" redirects to the changelist
        instead of the change view when ModelAdmin.save_as_continue=False.
        """
        post_data = {"_saveasnew": "", "name": "John M", "gender": 1, "age": 42}
        url = reverse(
            "admin:admin_views_person_change",
            args=(self.per1.pk,),
            current_app=site2.name,
        )
        response = self.client.post(url, post_data)
        self.assertEqual(len(Person.objects.filter(name="John M")), 1)
        self.assertEqual(len(Person.objects.filter(id=self.per1.pk)), 1)
        self.assertRedirects(
            response,
            reverse("admin:admin_views_person_changelist", current_app=site2.name),
        )

    def test_save_as_new_with_validation_errors(self):
        """
        When you click "Save as new" and have a validation error,
        you only see the "Save as new" button and not the other save buttons,
        and that only the "Save as" button is visible.
        """
        response = self.client.post(
            reverse("admin:admin_views_person_change", args=(self.per1.pk,)),
            {
                "_saveasnew": "",
                "gender": "invalid",
                "_addanother": "fail",
            },
        )
        self.assertContains(response, "Please correct the errors below.")
        self.assertFalse(response.context["show_save_and_add_another"])
        self.assertFalse(response.context["show_save_and_continue"])
        self.assertTrue(response.context["show_save_as_new"])

    def test_save_as_new_with_validation_errors_with_inlines(self):
        parent = Parent.objects.create(name="Father")
        child = Child.objects.create(parent=parent, name="Child")
        response = self.client.post(
            reverse("admin:admin_views_parent_change", args=(parent.pk,)),
            {
                "_saveasnew": "Save as new",
                "child_set-0-parent": parent.pk,
                "child_set-0-id": child.pk,
                "child_set-0-name": "Child",
                "child_set-INITIAL_FORMS": 1,
                "child_set-MAX_NUM_FORMS": 1000,
                "child_set-MIN_NUM_FORMS": 0,
                "child_set-TOTAL_FORMS": 4,
                "name": "_invalid",
            },
        )
        self.assertContains(response, "Please correct the error below.")
        self.assertFalse(response.context["show_save_and_add_another"])
        self.assertFalse(response.context["show_save_and_continue"])
        self.assertTrue(response.context["show_save_as_new"])

    def test_save_as_new_with_inlines_with_validation_errors(self):
        parent = Parent.objects.create(name="Father")
        child = Child.objects.create(parent=parent, name="Child")
        response = self.client.post(
            reverse("admin:admin_views_parent_change", args=(parent.pk,)),
            {
                "_saveasnew": "Save as new",
                "child_set-0-parent": parent.pk,
                "child_set-0-id": child.pk,
                "child_set-0-name": "_invalid",
                "child_set-INITIAL_FORMS": 1,
                "child_set-MAX_NUM_FORMS": 1000,
                "child_set-MIN_NUM_FORMS": 0,
                "child_set-TOTAL_FORMS": 4,
                "name": "Father",
            },
        )
        self.assertContains(response, "Please correct the error below.")
        self.assertFalse(response.context["show_save_and_add_another"])
        self.assertFalse(response.context["show_save_and_continue"])
        self.assertTrue(response.context["show_save_as_new"])


@override_settings(ROOT_URLCONF="admin_views.urls")
class CustomModelAdminTest(AdminViewBasicTestCase):
    def test_custom_admin_site_login_form(self):
        self.client.logout()
        response = self.client.get(reverse("admin2:index"), follow=True)
        self.assertIsInstance(response, TemplateResponse)
        self.assertEqual(response.status_code, 200)
        login = self.client.post(
            reverse("admin2:login"),
            {
                REDIRECT_FIELD_NAME: reverse("admin2:index"),
                "username": "customform",
                "password": "secret",
            },
            follow=True,
        )
        self.assertIsInstance(login, TemplateResponse)
        self.assertContains(login, "custom form error")
        self.assertContains(login, "path/to/media.css")

    def test_custom_admin_site_login_template(self):
        self.client.logout()
        response = self.client.get(reverse("admin2:index"), follow=True)
        self.assertIsInstance(response, TemplateResponse)
        self.assertTemplateUsed(response, "custom_admin/login.html")
        self.assertContains(response, "Hello from a custom login template")

    def test_custom_admin_site_logout_template(self):
        response = self.client.post(reverse("admin2:logout"))
        self.assertIsInstance(response, TemplateResponse)
        self.assertTemplateUsed(response, "custom_admin/logout.html")
        self.assertContains(response, "Hello from a custom logout template")

    def test_custom_admin_site_index_view_and_template(self):
        response = self.client.get(reverse("admin2:index"))
        self.assertIsInstance(response, TemplateResponse)
        self.assertTemplateUsed(response, "custom_admin/index.html")
        self.assertContains(response, "Hello from a custom index template *bar*")

    def test_custom_admin_site_app_index_view_and_template(self):
        response = self.client.get(reverse("admin2:app_list", args=("admin_views",)))
        self.assertIsInstance(response, TemplateResponse)
        self.assertTemplateUsed(response, "custom_admin/app_index.html")
        self.assertContains(response, "Hello from a custom app_index template")

    def test_custom_admin_site_password_change_template(self):
        response = self.client.get(reverse("admin2:password_change"))
        self.assertIsInstance(response, TemplateResponse)
        self.assertTemplateUsed(response, "custom_admin/password_change_form.html")
        self.assertContains(
            response, "Hello from a custom password change form template"
        )

    def test_custom_admin_site_password_change_with_extra_context(self):
        response = self.client.get(reverse("admin2:password_change"))
        self.assertIsInstance(response, TemplateResponse)
        self.assertTemplateUsed(response, "custom_admin/password_change_form.html")
        self.assertContains(response, "eggs")

    def test_custom_admin_site_password_change_done_template(self):
        response = self.client.get(reverse("admin2:password_change_done"))
        self.assertIsInstance(response, TemplateResponse)
        self.assertTemplateUsed(response, "custom_admin/password_change_done.html")
        self.assertContains(
            response, "Hello from a custom password change done template"
        )

    def test_custom_admin_site_view(self):
        self.client.force_login(self.superuser)
        response = self.client.get(reverse("admin2:my_view"))
        self.assertEqual(response.content, b"Django is a magical pony!")

    def test_pwd_change_custom_template(self):
        self.client.force_login(self.superuser)
        su = User.objects.get(username="super")
        response = self.client.get(
            reverse("admin4:auth_user_password_change", args=(su.pk,))
        )
        self.assertEqual(response.status_code, 200)


def get_perm(Model, codename):
    """Return the permission object, for the Model"""
    ct = ContentType.objects.get_for_model(Model, for_concrete_model=False)
    return Permission.objects.get(content_type=ct, codename=codename)


@override_settings(
    ROOT_URLCONF="admin_views.urls",
    # Test with the admin's documented list of required context processors.
    TEMPLATES=[
        {
            "BACKEND": "django.template.backends.django.DjangoTemplates",
            "APP_DIRS": True,
            "OPTIONS": {
                "context_processors": [
                    "django.template.context_processors.request",
                    "django.contrib.auth.context_processors.auth",
                    "django.contrib.messages.context_processors.messages",
                ],
            },
        }
    ],
)
class AdminViewPermissionsTest(TestCase):
    """Tests for Admin Views Permissions."""

    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="super", password="secret", email="super@example.com"
        )
        cls.viewuser = User.objects.create_user(
            username="viewuser", password="secret", is_staff=True
        )
        cls.adduser = User.objects.create_user(
            username="adduser", password="secret", is_staff=True
        )
        cls.changeuser = User.objects.create_user(
            username="changeuser", password="secret", is_staff=True
        )
        cls.deleteuser = User.objects.create_user(
            username="deleteuser", password="secret", is_staff=True
        )
        cls.joepublicuser = User.objects.create_user(
            username="joepublic", password="secret"
        )
        cls.nostaffuser = User.objects.create_user(
            username="nostaff", password="secret"
        )
        cls.s1 = Section.objects.create(name="Test section")
        cls.a1 = Article.objects.create(
            content="<p>Middle content</p>",
            date=datetime.datetime(2008, 3, 18, 11, 54, 58),
            section=cls.s1,
            another_section=cls.s1,
        )
        cls.a2 = Article.objects.create(
            content="<p>Oldest content</p>",
            date=datetime.datetime(2000, 3, 18, 11, 54, 58),
            section=cls.s1,
        )
        cls.a3 = Article.objects.create(
            content="<p>Newest content</p>",
            date=datetime.datetime(2009, 3, 18, 11, 54, 58),
            section=cls.s1,
        )
        cls.p1 = PrePopulatedPost.objects.create(
            title="A Long Title", published=True, slug="a-long-title"
        )

        # Setup permissions, for our users who can add, change, and delete.
        opts = Article._meta

        # User who can view Articles
        cls.viewuser.user_permissions.add(
            get_perm(Article, get_permission_codename("view", opts))
        )
        # User who can add Articles
        cls.adduser.user_permissions.add(
            get_perm(Article, get_permission_codename("add", opts))
        )
        # User who can change Articles
        cls.changeuser.user_permissions.add(
            get_perm(Article, get_permission_codename("change", opts))
        )
        cls.nostaffuser.user_permissions.add(
            get_perm(Article, get_permission_codename("change", opts))
        )

        # User who can delete Articles
        cls.deleteuser.user_permissions.add(
            get_perm(Article, get_permission_codename("delete", opts))
        )
        cls.deleteuser.user_permissions.add(
            get_perm(Section, get_permission_codename("delete", Section._meta))
        )

        # login POST dicts
        cls.index_url = reverse("admin:index")
        cls.super_login = {
            REDIRECT_FIELD_NAME: cls.index_url,
            "username": "super",
            "password": "secret",
        }
        cls.super_email_login = {
            REDIRECT_FIELD_NAME: cls.index_url,
            "username": "super@example.com",
            "password": "secret",
        }
        cls.super_email_bad_login = {
            REDIRECT_FIELD_NAME: cls.index_url,
            "username": "super@example.com",
            "password": "notsecret",
        }
        cls.adduser_login = {
            REDIRECT_FIELD_NAME: cls.index_url,
            "username": "adduser",
            "password": "secret",
        }
        cls.changeuser_login = {
            REDIRECT_FIELD_NAME: cls.index_url,
            "username": "changeuser",
            "password": "secret",
        }
        cls.deleteuser_login = {
            REDIRECT_FIELD_NAME: cls.index_url,
            "username": "deleteuser",
            "password": "secret",
        }
        cls.nostaff_login = {
            REDIRECT_FIELD_NAME: reverse("has_permission_admin:index"),
            "username": "nostaff",
            "password": "secret",
        }
        cls.joepublic_login = {
            REDIRECT_FIELD_NAME: cls.index_url,
            "username": "joepublic",
            "password": "secret",
        }
        cls.viewuser_login = {
            REDIRECT_FIELD_NAME: cls.index_url,
            "username": "viewuser",
            "password": "secret",
        }
        cls.no_username_login = {
            REDIRECT_FIELD_NAME: cls.index_url,
            "password": "secret",
        }

    def test_login(self):
        """
        Make sure only staff members can log in.

        Successful posts to the login page will redirect to the original url.
        Unsuccessful attempts will continue to render the login page with
        a 200 status code.
        """
        login_url = "%s?next=%s" % (reverse("admin:login"), reverse("admin:index"))
        # Super User
        response = self.client.get(self.index_url)
        self.assertRedirects(response, login_url)
        login = self.client.post(login_url, self.super_login)
        self.assertRedirects(login, self.index_url)
        self.assertFalse(login.context)
        self.client.post(reverse("admin:logout"))

        # Test if user enters email address
        response = self.client.get(self.index_url)
        self.assertEqual(response.status_code, 302)
        login = self.client.post(login_url, self.super_email_login)
        self.assertContains(login, ERROR_MESSAGE)
        # only correct passwords get a username hint
        login = self.client.post(login_url, self.super_email_bad_login)
        self.assertContains(login, ERROR_MESSAGE)
        new_user = User(username="jondoe", password="secret", email="super@example.com")
        new_user.save()
        # check to ensure if there are multiple email addresses a user doesn't get a 500
        login = self.client.post(login_url, self.super_email_login)
        self.assertContains(login, ERROR_MESSAGE)

        # View User
        response = self.client.get(self.index_url)
        self.assertEqual(response.status_code, 302)
        login = self.client.post(login_url, self.viewuser_login)
        self.assertRedirects(login, self.index_url)
        self.assertFalse(login.context)
        self.client.post(reverse("admin:logout"))

        # Add User
        response = self.client.get(self.index_url)
        self.assertEqual(response.status_code, 302)
        login = self.client.post(login_url, self.adduser_login)
        self.assertRedirects(login, self.index_url)
        self.assertFalse(login.context)
        self.client.post(reverse("admin:logout"))

        # Change User
        response = self.client.get(self.index_url)
        self.assertEqual(response.status_code, 302)
        login = self.client.post(login_url, self.changeuser_login)
        self.assertRedirects(login, self.index_url)
        self.assertFalse(login.context)
        self.client.post(reverse("admin:logout"))

        # Delete User
        response = self.client.get(self.index_url)
        self.assertEqual(response.status_code, 302)
        login = self.client.post(login_url, self.deleteuser_login)
        self.assertRedirects(login, self.index_url)
        self.assertFalse(login.context)
        self.client.post(reverse("admin:logout"))

        # Regular User should not be able to login.
        response = self.client.get(self.index_url)
        self.assertEqual(response.status_code, 302)
        login = self.client.post(login_url, self.joepublic_login)
        self.assertContains(login, ERROR_MESSAGE)

        # Requests without username should not return 500 errors.
        response = self.client.get(self.index_url)
        self.assertEqual(response.status_code, 302)
        login = self.client.post(login_url, self.no_username_login)
        self.assertEqual(login.status_code, 200)
        self.assertFormError(
            login.context["form"], "username", ["This field is required."]
        )

    def test_login_redirect_for_direct_get(self):
        """
        Login redirect should be to the admin index page when going directly to
        /admin/login/.
        """
        response = self.client.get(reverse("admin:login"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context[REDIRECT_FIELD_NAME], reverse("admin:index"))

    def test_login_has_permission(self):
        # Regular User should not be able to login.
        response = self.client.get(reverse("has_permission_admin:index"))
        self.assertEqual(response.status_code, 302)
        login = self.client.post(
            reverse("has_permission_admin:login"), self.joepublic_login
        )
        self.assertContains(login, "permission denied")

        # User with permissions should be able to login.
        response = self.client.get(reverse("has_permission_admin:index"))
        self.assertEqual(response.status_code, 302)
        login = self.client.post(
            reverse("has_permission_admin:login"), self.nostaff_login
        )
        self.assertRedirects(login, reverse("has_permission_admin:index"))
        self.assertFalse(login.context)
        self.client.post(reverse("has_permission_admin:logout"))

        # Staff should be able to login.
        response = self.client.get(reverse("has_permission_admin:index"))
        self.assertEqual(response.status_code, 302)
        login = self.client.post(
            reverse("has_permission_admin:login"),
            {
                REDIRECT_FIELD_NAME: reverse("has_permission_admin:index"),
                "username": "deleteuser",
                "password": "secret",
            },
        )
        self.assertRedirects(login, reverse("has_permission_admin:index"))
        self.assertFalse(login.context)
        self.client.post(reverse("has_permission_admin:logout"))

    def test_login_successfully_redirects_to_original_URL(self):
        response = self.client.get(self.index_url)
        self.assertEqual(response.status_code, 302)
        query_string = "the-answer=42"
        redirect_url = "%s?%s" % (self.index_url, query_string)
        new_next = {REDIRECT_FIELD_NAME: redirect_url}
        post_data = self.super_login.copy()
        post_data.pop(REDIRECT_FIELD_NAME)
        login = self.client.post(
            "%s?%s" % (reverse("admin:login"), urlencode(new_next)), post_data
        )
        self.assertRedirects(login, redirect_url)

    def test_double_login_is_not_allowed(self):
        """Regression test for #19327"""
        login_url = "%s?next=%s" % (reverse("admin:login"), reverse("admin:index"))

        response = self.client.get(self.index_url)
        self.assertEqual(response.status_code, 302)

        # Establish a valid admin session
        login = self.client.post(login_url, self.super_login)
        self.assertRedirects(login, self.index_url)
        self.assertFalse(login.context)

        # Logging in with non-admin user fails
        login = self.client.post(login_url, self.joepublic_login)
        self.assertContains(login, ERROR_MESSAGE)

        # Establish a valid admin session
        login = self.client.post(login_url, self.super_login)
        self.assertRedirects(login, self.index_url)
        self.assertFalse(login.context)

        # Logging in with admin user while already logged in
        login = self.client.post(login_url, self.super_login)
        self.assertRedirects(login, self.index_url)
        self.assertFalse(login.context)
        self.client.post(reverse("admin:logout"))

    def test_login_page_notice_for_non_staff_users(self):
        """
        A logged-in non-staff user trying to access the admin index should be
        presented with the login page and a hint indicating that the current
        user doesn't have access to it.
        """
        hint_template = "You are authenticated as {}"

        # Anonymous user should not be shown the hint
        response = self.client.get(self.index_url, follow=True)
        self.assertContains(response, "login-form")
        self.assertNotContains(response, hint_template.format(""), status_code=200)

        # Non-staff user should be shown the hint
        self.client.force_login(self.nostaffuser)
        response = self.client.get(self.index_url, follow=True)
        self.assertContains(response, "login-form")
        self.assertContains(
            response, hint_template.format(self.nostaffuser.username), status_code=200
        )

    def test_add_view(self):
        """Test add view restricts access and actually adds items."""
        add_dict = {
            "title": "Døm ikke",
            "content": "<p>great article</p>",
            "date_0": "2008-03-18",
            "date_1": "10:54:39",
            "section": self.s1.pk,
        }
        # Change User should not have access to add articles
        self.client.force_login(self.changeuser)
        # make sure the view removes test cookie
        self.assertIs(self.client.session.test_cookie_worked(), False)
        response = self.client.get(reverse("admin:admin_views_article_add"))
        self.assertEqual(response.status_code, 403)
        # Try POST just to make sure
        post = self.client.post(reverse("admin:admin_views_article_add"), add_dict)
        self.assertEqual(post.status_code, 403)
        self.assertEqual(Article.objects.count(), 3)
        self.client.post(reverse("admin:logout"))

        # View User should not have access to add articles
        self.client.force_login(self.viewuser)
        response = self.client.get(reverse("admin:admin_views_article_add"))
        self.assertEqual(response.status_code, 403)
        # Try POST just to make sure
        post = self.client.post(reverse("admin:admin_views_article_add"), add_dict)
        self.assertEqual(post.status_code, 403)
        self.assertEqual(Article.objects.count(), 3)
        # Now give the user permission to add but not change.
        self.viewuser.user_permissions.add(
            get_perm(Article, get_permission_codename("add", Article._meta))
        )
        response = self.client.get(reverse("admin:admin_views_article_add"))
        self.assertEqual(response.context["title"], "Add article")
        self.assertContains(response, "<title>Add article | Django site admin</title>")
        self.assertContains(
            response, '<input type="submit" value="Save and view" name="_continue">'
        )
        post = self.client.post(
            reverse("admin:admin_views_article_add"), add_dict, follow=False
        )
        self.assertEqual(post.status_code, 302)
        self.assertEqual(Article.objects.count(), 4)
        article = Article.objects.latest("pk")
        response = self.client.get(
            reverse("admin:admin_views_article_change", args=(article.pk,))
        )
        self.assertContains(
            response,
            '<li class="success">The article “Døm ikke” was added successfully.</li>',
        )
        article.delete()
        self.client.post(reverse("admin:logout"))

        # Add user may login and POST to add view, then redirect to admin root
        self.client.force_login(self.adduser)
        addpage = self.client.get(reverse("admin:admin_views_article_add"))
        change_list_link = '&rsaquo; <a href="%s">Articles</a>' % reverse(
            "admin:admin_views_article_changelist"
        )
        self.assertNotContains(
            addpage,
            change_list_link,
            msg_prefix=(
                "User restricted to add permission is given link to change list view "
                "in breadcrumbs."
            ),
        )
        post = self.client.post(reverse("admin:admin_views_article_add"), add_dict)
        self.assertRedirects(post, self.index_url)
        self.assertEqual(Article.objects.count(), 4)
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(mail.outbox[0].subject, "Greetings from a created object")
        self.client.post(reverse("admin:logout"))

        # The addition was logged correctly
        addition_log = LogEntry.objects.all()[0]
        new_article = Article.objects.last()
        article_ct = ContentType.objects.get_for_model(Article)
        self.assertEqual(addition_log.user_id, self.adduser.pk)
        self.assertEqual(addition_log.content_type_id, article_ct.pk)
        self.assertEqual(addition_log.object_id, str(new_article.pk))
        self.assertEqual(addition_log.object_repr, "Døm ikke")
        self.assertEqual(addition_log.action_flag, ADDITION)
        self.assertEqual(addition_log.get_change_message(), "Added.")

        # Super can add too, but is redirected to the change list view
        self.client.force_login(self.superuser)
        addpage = self.client.get(reverse("admin:admin_views_article_add"))
        self.assertContains(
            addpage,
            change_list_link,
            msg_prefix=(
                "Unrestricted user is not given link to change list view in "
                "breadcrumbs."
            ),
        )
        post = self.client.post(reverse("admin:admin_views_article_add"), add_dict)
        self.assertRedirects(post, reverse("admin:admin_views_article_changelist"))
        self.assertEqual(Article.objects.count(), 5)
        self.client.post(reverse("admin:logout"))

        # 8509 - if a normal user is already logged in, it is possible
        # to change user into the superuser without error
        self.client.force_login(self.joepublicuser)
        # Check and make sure that if user expires, data still persists
        self.client.force_login(self.superuser)
        # make sure the view removes test cookie
        self.assertIs(self.client.session.test_cookie_worked(), False)

    @mock.patch("django.contrib.admin.options.InlineModelAdmin.has_change_permission")
    def test_add_view_with_view_only_inlines(self, has_change_permission):
        """User with add permission to a section but view-only for inlines."""
        self.viewuser.user_permissions.add(
            get_perm(Section, get_permission_codename("add", Section._meta))
        )
        self.client.force_login(self.viewuser)
        # Valid POST creates a new section.
        data = {
            "name": "New obj",
            "article_set-TOTAL_FORMS": 0,
            "article_set-INITIAL_FORMS": 0,
        }
        response = self.client.post(reverse("admin:admin_views_section_add"), data)
        self.assertRedirects(response, reverse("admin:index"))
        self.assertEqual(Section.objects.latest("id").name, data["name"])
        # InlineModelAdmin.has_change_permission()'s obj argument is always
        # None during object add.
        self.assertEqual(
            [obj for (request, obj), _ in has_change_permission.call_args_list],
            [None, None],
        )

    def test_change_view(self):
        """Change view should restrict access and allow users to edit items."""
        change_dict = {
            "title": "Ikke fordømt",
            "content": "<p>edited article</p>",
            "date_0": "2008-03-18",
            "date_1": "10:54:39",
            "section": self.s1.pk,
        }
        article_change_url = reverse(
            "admin:admin_views_article_change", args=(self.a1.pk,)
        )
        article_changelist_url = reverse("admin:admin_views_article_changelist")

        # add user should not be able to view the list of article or change any of them
        self.client.force_login(self.adduser)
        response = self.client.get(article_changelist_url)
        self.assertEqual(response.status_code, 403)
        response = self.client.get(article_change_url)
        self.assertEqual(response.status_code, 403)
        post = self.client.post(article_change_url, change_dict)
        self.assertEqual(post.status_code, 403)
        self.client.post(reverse("admin:logout"))

        # view user can view articles but not make changes.
        self.client.force_login(self.viewuser)
        response = self.client.get(article_changelist_url)
        self.assertContains(
            response,
            "<title>Select article to view | Django site admin</title>",
        )
        self.assertContains(response, "<h1>Select article to view</h1>")
        self.assertEqual(response.context["title"], "Select article to view")
        response = self.client.get(article_change_url)
        self.assertContains(response, "<title>View article | Django site admin</title>")
        self.assertContains(response, "<h1>View article</h1>")
        self.assertContains(response, "<label>Extra form field:</label>")
        self.assertContains(
            response,
            '<a href="/test_admin/admin/admin_views/article/" class="closelink">Close'
            "</a>",
        )
        self.assertEqual(response.context["title"], "View article")
        post = self.client.post(article_change_url, change_dict)
        self.assertEqual(post.status_code, 403)
        self.assertEqual(
            Article.objects.get(pk=self.a1.pk).content, "<p>Middle content</p>"
        )
        self.client.post(reverse("admin:logout"))

        # change user can view all items and edit them
        self.client.force_login(self.changeuser)
        response = self.client.get(article_changelist_url)
        self.assertEqual(response.context["title"], "Select article to change")
        self.assertContains(
            response,
            "<title>Select article to change | Django site admin</title>",
        )
        self.assertContains(response, "<h1>Select article to change</h1>")
        response = self.client.get(article_change_url)
        self.assertEqual(response.context["title"], "Change article")
        self.assertContains(
            response,
            "<title>Change article | Django site admin</title>",
        )
        self.assertContains(response, "<h1>Change article</h1>")
        post = self.client.post(article_change_url, change_dict)
        self.assertRedirects(post, article_changelist_url)
        self.assertEqual(
            Article.objects.get(pk=self.a1.pk).content, "<p>edited article</p>"
        )

        # one error in form should produce singular error message, multiple
        # errors plural.
        change_dict["title"] = ""
        post = self.client.post(article_change_url, change_dict)
        self.assertContains(
            post,
            "Please correct the error below.",
            msg_prefix=(
                "Singular error message not found in response to post with one error"
            ),
        )

        change_dict["content"] = ""
        post = self.client.post(article_change_url, change_dict)
        self.assertContains(
            post,
            "Please correct the errors below.",
            msg_prefix=(
                "Plural error message not found in response to post with multiple "
                "errors"
            ),
        )
        self.client.post(reverse("admin:logout"))

        # Test redirection when using row-level change permissions. Refs #11513.
        r1 = RowLevelChangePermissionModel.objects.create(id=1, name="odd id")
        r2 = RowLevelChangePermissionModel.objects.create(id=2, name="even id")
        r3 = RowLevelChangePermissionModel.objects.create(id=3, name="odd id mult 3")
        r6 = RowLevelChangePermissionModel.objects.create(id=6, name="even id mult 3")
        change_url_1 = reverse(
            "admin:admin_views_rowlevelchangepermissionmodel_change", args=(r1.pk,)
        )
        change_url_2 = reverse(
            "admin:admin_views_rowlevelchangepermissionmodel_change", args=(r2.pk,)
        )
        change_url_3 = reverse(
            "admin:admin_views_rowlevelchangepermissionmodel_change", args=(r3.pk,)
        )
        change_url_6 = reverse(
            "admin:admin_views_rowlevelchangepermissionmodel_change", args=(r6.pk,)
        )
        logins = [
            self.superuser,
            self.viewuser,
            self.adduser,
            self.changeuser,
            self.deleteuser,
        ]
        for login_user in logins:
            with self.subTest(login_user.username):
                self.client.force_login(login_user)
                response = self.client.get(change_url_1)
                self.assertEqual(response.status_code, 403)
                response = self.client.post(change_url_1, {"name": "changed"})
                self.assertEqual(
                    RowLevelChangePermissionModel.objects.get(id=1).name, "odd id"
                )
                self.assertEqual(response.status_code, 403)
                response = self.client.get(change_url_2)
                self.assertEqual(response.status_code, 200)
                response = self.client.post(change_url_2, {"name": "changed"})
                self.assertEqual(
                    RowLevelChangePermissionModel.objects.get(id=2).name, "changed"
                )
                self.assertRedirects(response, self.index_url)
                response = self.client.get(change_url_3)
                self.assertEqual(response.status_code, 200)
                response = self.client.post(change_url_3, {"name": "changed"})
                self.assertEqual(response.status_code, 403)
                self.assertEqual(
                    RowLevelChangePermissionModel.objects.get(id=3).name,
                    "odd id mult 3",
                )
                response = self.client.get(change_url_6)
                self.assertEqual(response.status_code, 200)
                response = self.client.post(change_url_6, {"name": "changed"})
                self.assertEqual(
                    RowLevelChangePermissionModel.objects.get(id=6).name, "changed"
                )
                self.assertRedirects(response, self.index_url)

                self.client.post(reverse("admin:logout"))

        for login_user in [self.joepublicuser, self.nostaffuser]:
            with self.subTest(login_user.username):
                self.client.force_login(login_user)
                response = self.client.get(change_url_1, follow=True)
                self.assertContains(response, "login-form")
                response = self.client.post(
                    change_url_1, {"name": "changed"}, follow=True
                )
                self.assertEqual(
                    RowLevelChangePermissionModel.objects.get(id=1).name, "odd id"
                )
                self.assertContains(response, "login-form")
                response = self.client.get(change_url_2, follow=True)
                self.assertContains(response, "login-form")
                response = self.client.post(
                    change_url_2, {"name": "changed again"}, follow=True
                )
                self.assertEqual(
                    RowLevelChangePermissionModel.objects.get(id=2).name, "changed"
                )
                self.assertContains(response, "login-form")
                self.client.post(reverse("admin:logout"))

    def test_change_view_without_object_change_permission(self):
        """
        The object should be read-only if the user has permission to view it
        and change objects of that type but not to change the current object.
        """
        change_url = reverse("admin9:admin_views_article_change", args=(self.a1.pk,))
        self.client.force_login(self.viewuser)
        response = self.client.get(change_url)
        self.assertEqual(response.context["title"], "View article")
        self.assertContains(response, "<title>View article | Django site admin</title>")
        self.assertContains(response, "<h1>View article</h1>")
        self.assertContains(
            response,
            '<a href="/test_admin/admin9/admin_views/article/" class="closelink">Close'
            "</a>",
        )

    def test_change_view_save_as_new(self):
        """
        'Save as new' should raise PermissionDenied for users without the 'add'
        permission.
        """
        change_dict_save_as_new = {
            "_saveasnew": "Save as new",
            "title": "Ikke fordømt",
            "content": "<p>edited article</p>",
            "date_0": "2008-03-18",
            "date_1": "10:54:39",
            "section": self.s1.pk,
        }
        article_change_url = reverse(
            "admin:admin_views_article_change", args=(self.a1.pk,)
        )

        # Add user can perform "Save as new".
        article_count = Article.objects.count()
        self.client.force_login(self.adduser)
        post = self.client.post(article_change_url, change_dict_save_as_new)
        self.assertRedirects(post, self.index_url)
        self.assertEqual(Article.objects.count(), article_count + 1)
        self.client.logout()

        # Change user cannot perform "Save as new" (no 'add' permission).
        article_count = Article.objects.count()
        self.client.force_login(self.changeuser)
        post = self.client.post(article_change_url, change_dict_save_as_new)
        self.assertEqual(post.status_code, 403)
        self.assertEqual(Article.objects.count(), article_count)

        # User with both add and change permissions should be redirected to the
        # change page for the newly created object.
        article_count = Article.objects.count()
        self.client.force_login(self.superuser)
        post = self.client.post(article_change_url, change_dict_save_as_new)
        self.assertEqual(Article.objects.count(), article_count + 1)
        new_article = Article.objects.latest("id")
        self.assertRedirects(
            post, reverse("admin:admin_views_article_change", args=(new_article.pk,))
        )

    def test_change_view_with_view_only_inlines(self):
        """
        User with change permission to a section but view-only for inlines.
        """
        self.viewuser.user_permissions.add(
            get_perm(Section, get_permission_codename("change", Section._meta))
        )
        self.client.force_login(self.viewuser)
        # GET shows inlines.
        response = self.client.get(
            reverse("admin:admin_views_section_change", args=(self.s1.pk,))
        )
        self.assertEqual(len(response.context["inline_admin_formsets"]), 1)
        formset = response.context["inline_admin_formsets"][0]
        self.assertEqual(len(formset.forms), 3)
        # Valid POST changes the name.
        data = {
            "name": "Can edit name with view-only inlines",
            "article_set-TOTAL_FORMS": 3,
            "article_set-INITIAL_FORMS": 3,
        }
        response = self.client.post(
            reverse("admin:admin_views_section_change", args=(self.s1.pk,)), data
        )
        self.assertRedirects(response, reverse("admin:admin_views_section_changelist"))
        self.assertEqual(Section.objects.get(pk=self.s1.pk).name, data["name"])
        # Invalid POST reshows inlines.
        del data["name"]
        response = self.client.post(
            reverse("admin:admin_views_section_change", args=(self.s1.pk,)), data
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["inline_admin_formsets"]), 1)
        formset = response.context["inline_admin_formsets"][0]
        self.assertEqual(len(formset.forms), 3)

    def test_change_view_with_view_only_last_inline(self):
        self.viewuser.user_permissions.add(
            get_perm(Section, get_permission_codename("view", Section._meta))
        )
        self.client.force_login(self.viewuser)
        response = self.client.get(
            reverse("admin:admin_views_section_change", args=(self.s1.pk,))
        )
        self.assertEqual(len(response.context["inline_admin_formsets"]), 1)
        formset = response.context["inline_admin_formsets"][0]
        self.assertEqual(len(formset.forms), 3)
        # The last inline is not marked as empty.
        self.assertContains(response, 'id="article_set-2"')

    def test_change_view_with_view_and_add_inlines(self):
        """User has view and add permissions on the inline model."""
        self.viewuser.user_permissions.add(
            get_perm(Section, get_permission_codename("change", Section._meta))
        )
        self.viewuser.user_permissions.add(
            get_perm(Article, get_permission_codename("add", Article._meta))
        )
        self.client.force_login(self.viewuser)
        # GET shows inlines.
        response = self.client.get(
            reverse("admin:admin_views_section_change", args=(self.s1.pk,))
        )
        self.assertEqual(len(response.context["inline_admin_formsets"]), 1)
        formset = response.context["inline_admin_formsets"][0]
        self.assertEqual(len(formset.forms), 6)
        # Valid POST creates a new article.
        data = {
            "name": "Can edit name with view-only inlines",
            "article_set-TOTAL_FORMS": 6,
            "article_set-INITIAL_FORMS": 3,
            "article_set-3-id": [""],
            "article_set-3-title": ["A title"],
            "article_set-3-content": ["Added content"],
            "article_set-3-date_0": ["2008-3-18"],
            "article_set-3-date_1": ["11:54:58"],
            "article_set-3-section": [str(self.s1.pk)],
        }
        response = self.client.post(
            reverse("admin:admin_views_section_change", args=(self.s1.pk,)), data
        )
        self.assertRedirects(response, reverse("admin:admin_views_section_changelist"))
        self.assertEqual(Section.objects.get(pk=self.s1.pk).name, data["name"])
        self.assertEqual(Article.objects.count(), 4)
        # Invalid POST reshows inlines.
        del data["name"]
        response = self.client.post(
            reverse("admin:admin_views_section_change", args=(self.s1.pk,)), data
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["inline_admin_formsets"]), 1)
        formset = response.context["inline_admin_formsets"][0]
        self.assertEqual(len(formset.forms), 6)

    def test_change_view_with_view_and_delete_inlines(self):
        """User has view and delete permissions on the inline model."""
        self.viewuser.user_permissions.add(
            get_perm(Section, get_permission_codename("change", Section._meta))
        )
        self.client.force_login(self.viewuser)
        data = {
            "name": "Name is required.",
            "article_set-TOTAL_FORMS": 6,
            "article_set-INITIAL_FORMS": 3,
            "article_set-0-id": [str(self.a1.pk)],
            "article_set-0-DELETE": ["on"],
        }
        # Inline POST details are ignored without delete permission.
        response = self.client.post(
            reverse("admin:admin_views_section_change", args=(self.s1.pk,)), data
        )
        self.assertRedirects(response, reverse("admin:admin_views_section_changelist"))
        self.assertEqual(Article.objects.count(), 3)
        # Deletion successful when delete permission is added.
        self.viewuser.user_permissions.add(
            get_perm(Article, get_permission_codename("delete", Article._meta))
        )
        data = {
            "name": "Name is required.",
            "article_set-TOTAL_FORMS": 6,
            "article_set-INITIAL_FORMS": 3,
            "article_set-0-id": [str(self.a1.pk)],
            "article_set-0-DELETE": ["on"],
        }
        response = self.client.post(
            reverse("admin:admin_views_section_change", args=(self.s1.pk,)), data
        )
        self.assertRedirects(response, reverse("admin:admin_views_section_changelist"))
        self.assertEqual(Article.objects.count(), 2)

    def test_delete_view(self):
        """Delete view should restrict access and actually delete items."""
        delete_dict = {"post": "yes"}
        delete_url = reverse("admin:admin_views_article_delete", args=(self.a1.pk,))

        # add user should not be able to delete articles
        self.client.force_login(self.adduser)
        response = self.client.get(delete_url)
        self.assertEqual(response.status_code, 403)
        post = self.client.post(delete_url, delete_dict)
        self.assertEqual(post.status_code, 403)
        self.assertEqual(Article.objects.count(), 3)
        self.client.logout()

        # view user should not be able to delete articles
        self.client.force_login(self.viewuser)
        response = self.client.get(delete_url)
        self.assertEqual(response.status_code, 403)
        post = self.client.post(delete_url, delete_dict)
        self.assertEqual(post.status_code, 403)
        self.assertEqual(Article.objects.count(), 3)
        self.client.logout()

        # Delete user can delete
        self.client.force_login(self.deleteuser)
        response = self.client.get(
            reverse("admin:admin_views_section_delete", args=(self.s1.pk,))
        )
        self.assertContains(response, "<h1>Delete</h1>")
        self.assertContains(response, "<h2>Summary</h2>")
        self.assertContains(response, "<li>Articles: 3</li>")
        # test response contains link to related Article
        self.assertContains(response, "admin_views/article/%s/" % self.a1.pk)

        response = self.client.get(delete_url)
        self.assertContains(response, "admin_views/article/%s/" % self.a1.pk)
        self.assertContains(response, "<h2>Summary</h2>")
        self.assertContains(response, "<li>Articles: 1</li>")
        post = self.client.post(delete_url, delete_dict)
        self.assertRedirects(post, self.index_url)
        self.assertEqual(Article.objects.count(), 2)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Greetings from a deleted object")
        article_ct = ContentType.objects.get_for_model(Article)
        logged = LogEntry.objects.get(content_type=article_ct, action_flag=DELETION)
        self.assertEqual(logged.object_id, str(self.a1.pk))

    def test_delete_view_with_no_default_permissions(self):
        """
        The delete view allows users to delete collected objects without a
        'delete' permission (ReadOnlyPizza.Meta.default_permissions is empty).
        """
        pizza = ReadOnlyPizza.objects.create(name="Double Cheese")
        delete_url = reverse("admin:admin_views_readonlypizza_delete", args=(pizza.pk,))
        self.client.force_login(self.adduser)
        response = self.client.get(delete_url)
        self.assertContains(response, "admin_views/readonlypizza/%s/" % pizza.pk)
        self.assertContains(response, "<h2>Summary</h2>")
        self.assertContains(response, "<li>Read only pizzas: 1</li>")
        post = self.client.post(delete_url, {"post": "yes"})
        self.assertRedirects(
            post, reverse("admin:admin_views_readonlypizza_changelist")
        )
        self.assertEqual(ReadOnlyPizza.objects.count(), 0)

    def test_delete_view_nonexistent_obj(self):
        self.client.force_login(self.deleteuser)
        url = reverse("admin:admin_views_article_delete", args=("nonexistent",))
        response = self.client.get(url, follow=True)
        self.assertRedirects(response, reverse("admin:index"))
        self.assertEqual(
            [m.message for m in response.context["messages"]],
            ["article with ID “nonexistent” doesn’t exist. Perhaps it was deleted?"],
        )

    def test_history_view(self):
        """History view should restrict access."""
        # add user should not be able to view the list of article or change any of them
        self.client.force_login(self.adduser)
        response = self.client.get(
            reverse("admin:admin_views_article_history", args=(self.a1.pk,))
        )
        self.assertEqual(response.status_code, 403)
        self.client.post(reverse("admin:logout"))

        # view user can view all items
        self.client.force_login(self.viewuser)
        response = self.client.get(
            reverse("admin:admin_views_article_history", args=(self.a1.pk,))
        )
        self.assertEqual(response.status_code, 200)
        self.client.post(reverse("admin:logout"))

        # change user can view all items and edit them
        self.client.force_login(self.changeuser)
        response = self.client.get(
            reverse("admin:admin_views_article_history", args=(self.a1.pk,))
        )
        self.assertEqual(response.status_code, 200)

        # Test redirection when using row-level change permissions. Refs #11513.
        rl1 = RowLevelChangePermissionModel.objects.create(id=1, name="odd id")
        rl2 = RowLevelChangePermissionModel.objects.create(id=2, name="even id")
        logins = [
            self.superuser,
            self.viewuser,
            self.adduser,
            self.changeuser,
            self.deleteuser,
        ]
        for login_user in logins:
            with self.subTest(login_user.username):
                self.client.force_login(login_user)
                url = reverse(
                    "admin:admin_views_rowlevelchangepermissionmodel_history",
                    args=(rl1.pk,),
                )
                response = self.client.get(url)
                self.assertEqual(response.status_code, 403)

                url = reverse(
                    "admin:admin_views_rowlevelchangepermissionmodel_history",
                    args=(rl2.pk,),
                )
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)

                self.client.post(reverse("admin:logout"))

        for login_user in [self.joepublicuser, self.nostaffuser]:
            with self.subTest(login_user.username):
                self.client.force_login(login_user)
                url = reverse(
                    "admin:admin_views_rowlevelchangepermissionmodel_history",
                    args=(rl1.pk,),
                )
                response = self.client.get(url, follow=True)
                self.assertContains(response, "login-form")
                url = reverse(
                    "admin:admin_views_rowlevelchangepermissionmodel_history",
                    args=(rl2.pk,),
                )
                response = self.client.get(url, follow=True)
                self.assertContains(response, "login-form")

                self.client.post(reverse("admin:logout"))

    def test_history_view_bad_url(self):
        self.client.force_login(self.changeuser)
        response = self.client.get(
            reverse("admin:admin_views_article_history", args=("foo",)), follow=True
        )
        self.assertRedirects(response, reverse("admin:index"))
        self.assertEqual(
            [m.message for m in response.context["messages"]],
            ["article with ID “foo” doesn’t exist. Perhaps it was deleted?"],
        )

    def test_conditionally_show_add_section_link(self):
        """
        The foreign key widget should only show the "add related" button if the
        user has permission to add that related item.
        """
        self.client.force_login(self.adduser)
        # The user can't add sections yet, so they shouldn't see the "add section" link.
        url = reverse("admin:admin_views_article_add")
        add_link_text = "add_id_section"
        response = self.client.get(url)
        self.assertNotContains(response, add_link_text)
        # Allow the user to add sections too. Now they can see the "add section" link.
        user = User.objects.get(username="adduser")
        perm = get_perm(Section, get_permission_codename("add", Section._meta))
        user.user_permissions.add(perm)
        response = self.client.get(url)
        self.assertContains(response, add_link_text)

    def test_conditionally_show_change_section_link(self):
        """
        The foreign key widget should only show the "change related" button if
        the user has permission to change that related item.
        """

        def get_change_related(response):
            return (
                response.context["adminform"]
                .form.fields["section"]
                .widget.can_change_related
            )

        self.client.force_login(self.adduser)
        # The user can't change sections yet, so they shouldn't see the
        # "change section" link.
        url = reverse("admin:admin_views_article_add")
        change_link_text = "change_id_section"
        response = self.client.get(url)
        self.assertFalse(get_change_related(response))
        self.assertNotContains(response, change_link_text)
        # Allow the user to change sections too. Now they can see the
        # "change section" link.
        user = User.objects.get(username="adduser")
        perm = get_perm(Section, get_permission_codename("change", Section._meta))
        user.user_permissions.add(perm)
        response = self.client.get(url)
        self.assertTrue(get_change_related(response))
        self.assertContains(response, change_link_text)

    def test_conditionally_show_delete_section_link(self):
        """
        The foreign key widget should only show the "delete related" button if
        the user has permission to delete that related item.
        """

        def get_delete_related(response):
            return (
                response.context["adminform"]
                .form.fields["sub_section"]
                .widget.can_delete_related
            )

        self.client.force_login(self.adduser)
        # The user can't delete sections yet, so they shouldn't see the
        # "delete section" link.
        url = reverse("admin:admin_views_article_add")
        delete_link_text = "delete_id_sub_section"
        response = self.client.get(url)
        self.assertFalse(get_delete_related(response))
        self.assertNotContains(response, delete_link_text)
        # Allow the user to delete sections too. Now they can see the
        # "delete section" link.
        user = User.objects.get(username="adduser")
        perm = get_perm(Section, get_permission_codename("delete", Section._meta))
        user.user_permissions.add(perm)
        response = self.client.get(url)
        self.assertTrue(get_delete_related(response))
        self.assertContains(response, delete_link_text)

    def test_disabled_permissions_when_logged_in(self):
        self.client.force_login(self.superuser)
        superuser = User.objects.get(username="super")
        superuser.is_active = False
        superuser.save()

        response = self.client.get(self.index_url, follow=True)
        self.assertContains(response, 'id="login-form"')
        self.assertNotContains(response, "Log out")

        response = self.client.get(reverse("secure_view"), follow=True)
        self.assertContains(response, 'id="login-form"')

    def test_disabled_staff_permissions_when_logged_in(self):
        self.client.force_login(self.superuser)
        superuser = User.objects.get(username="super")
        superuser.is_staff = False
        superuser.save()

        response = self.client.get(self.index_url, follow=True)
        self.assertContains(response, 'id="login-form"')
        self.assertNotContains(response, "Log out")

        response = self.client.get(reverse("secure_view"), follow=True)
        self.assertContains(response, 'id="login-form"')

    def test_app_list_permissions(self):
        """
        If a user has no module perms, the app list returns a 404.
        """
        opts = Article._meta
        change_user = User.objects.get(username="changeuser")
        permission = get_perm(Article, get_permission_codename("change", opts))

        self.client.force_login(self.changeuser)

        # the user has no module permissions
        change_user.user_permissions.remove(permission)
        response = self.client.get(reverse("admin:app_list", args=("admin_views",)))
        self.assertEqual(response.status_code, 404)

        # the user now has module permissions
        change_user.user_permissions.add(permission)
        response = self.client.get(reverse("admin:app_list", args=("admin_views",)))
        self.assertEqual(response.status_code, 200)

    def test_shortcut_view_only_available_to_staff(self):
        """
        Only admin users should be able to use the admin shortcut view.
        """
        model_ctype = ContentType.objects.get_for_model(ModelWithStringPrimaryKey)
        obj = ModelWithStringPrimaryKey.objects.create(string_pk="foo")
        shortcut_url = reverse("admin:view_on_site", args=(model_ctype.pk, obj.pk))

        # Not logged in: we should see the login page.
        response = self.client.get(shortcut_url, follow=True)
        self.assertTemplateUsed(response, "admin/login.html")

        # Logged in? Redirect.
        self.client.force_login(self.superuser)
        response = self.client.get(shortcut_url, follow=False)
        # Can't use self.assertRedirects() because User.get_absolute_url() is silly.
        self.assertEqual(response.status_code, 302)
        # Domain may depend on contrib.sites tests also run
        self.assertRegex(response.url, "http://(testserver|example.com)/dummy/foo/")

    def test_has_module_permission(self):
        """
        has_module_permission() returns True for all users who
        have any permission for that module (add, change, or delete), so that
        the module is displayed on the admin index page.
        """
        self.client.force_login(self.superuser)
        response = self.client.get(self.index_url)
        self.assertContains(response, "admin_views")
        self.assertContains(response, "Articles")
        self.client.logout()

        self.client.force_login(self.viewuser)
        response = self.client.get(self.index_url)
        self.assertContains(response, "admin_views")
        self.assertContains(response, "Articles")
        self.client.logout()

        self.client.force_login(self.adduser)
        response = self.client.get(self.index_url)
        self.assertContains(response, "admin_views")
        self.assertContains(response, "Articles")
        self.client.logout()

        self.client.force_login(self.changeuser)
        response = self.client.get(self.index_url)
        self.assertContains(response, "admin_views")
        self.assertContains(response, "Articles")
        self.client.logout()

        self.client.force_login(self.deleteuser)
        response = self.client.get(self.index_url)
        self.assertContains(response, "admin_views")
        self.assertContains(response, "Articles")

    def test_overriding_has_module_permission(self):
        """
        If has_module_permission() always returns False, the module shouldn't
        be displayed on the admin index page for any users.
        """
        articles = Article._meta.verbose_name_plural.title()
        sections = Section._meta.verbose_name_plural.title()
        index_url = reverse("admin7:index")

        self.client.force_login(self.superuser)
        response = self.client.get(index_url)
        self.assertContains(response, sections)
        self.assertNotContains(response, articles)
        self.client.logout()

        self.client.force_login(self.viewuser)
        response = self.client.get(index_url)
        self.assertNotContains(response, "admin_views")
        self.assertNotContains(response, articles)
        self.client.logout()

        self.client.force_login(self.adduser)
        response = self.client.get(index_url)
        self.assertNotContains(response, "admin_views")
        self.assertNotContains(response, articles)
        self.client.logout()

        self.client.force_login(self.changeuser)
        response = self.client.get(index_url)
        self.assertNotContains(response, "admin_views")
        self.assertNotContains(response, articles)
        self.client.logout()

        self.client.force_login(self.deleteuser)
        response = self.client.get(index_url)
        self.assertNotContains(response, articles)

        # The app list displays Sections but not Articles as the latter has
        # ModelAdmin.has_module_permission() = False.
        self.client.force_login(self.superuser)
        response = self.client.get(reverse("admin7:app_list", args=("admin_views",)))
        self.assertContains(response, sections)
        self.assertNotContains(response, articles)

    def test_post_save_message_no_forbidden_links_visible(self):
        """
        Post-save message shouldn't contain a link to the change form if the
        user doesn't have the change permission.
        """
        self.client.force_login(self.adduser)
        # Emulate Article creation for user with add-only permission.
        post_data = {
            "title": "Fun & games",
            "content": "Some content",
            "date_0": "2015-10-31",
            "date_1": "16:35:00",
            "_save": "Save",
        }
        response = self.client.post(
            reverse("admin:admin_views_article_add"), post_data, follow=True
        )
        self.assertContains(
            response,
            '<li class="success">The article “Fun &amp; games” was added successfully.'
            "</li>",
            html=True,
        )


@override_settings(
    ROOT_URLCONF="admin_views.urls",
    TEMPLATES=[
        {
            "BACKEND": "django.template.backends.django.DjangoTemplates",
            "APP_DIRS": True,
            "OPTIONS": {
                "context_processors": [
                    "django.template.context_processors.request",
                    "django.contrib.auth.context_processors.auth",
                    "django.contrib.messages.context_processors.messages",
                ],
            },
        }
    ],
)
class AdminViewProxyModelPermissionsTests(TestCase):
    """Tests for proxy models permissions in the admin."""

    @classmethod
    def setUpTestData(cls):
        cls.viewuser = User.objects.create_user(
            username="viewuser", password="secret", is_staff=True
        )
        cls.adduser = User.objects.create_user(
            username="adduser", password="secret", is_staff=True
        )
        cls.changeuser = User.objects.create_user(
            username="changeuser", password="secret", is_staff=True
        )
        cls.deleteuser = User.objects.create_user(
            username="deleteuser", password="secret", is_staff=True
        )
        # Setup permissions.
        opts = UserProxy._meta
        cls.viewuser.user_permissions.add(
            get_perm(UserProxy, get_permission_codename("view", opts))
        )
        cls.adduser.user_permissions.add(
            get_perm(UserProxy, get_permission_codename("add", opts))
        )
        cls.changeuser.user_permissions.add(
            get_perm(UserProxy, get_permission_codename("change", opts))
        )
        cls.deleteuser.user_permissions.add(
            get_perm(UserProxy, get_permission_codename("delete", opts))
        )
        # UserProxy instances.
        cls.user_proxy = UserProxy.objects.create(
            username="user_proxy", password="secret"
        )

    def test_add(self):
        self.client.force_login(self.adduser)
        url = reverse("admin:admin_views_userproxy_add")
        data = {
            "username": "can_add",
            "password": "secret",
            "date_joined_0": "2019-01-15",
            "date_joined_1": "16:59:10",
        }
        response = self.client.post(url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(UserProxy.objects.filter(username="can_add").exists())

    def test_view(self):
        self.client.force_login(self.viewuser)
        response = self.client.get(reverse("admin:admin_views_userproxy_changelist"))
        self.assertContains(response, "<h1>Select user proxy to view</h1>")
        response = self.client.get(
            reverse("admin:admin_views_userproxy_change", args=(self.user_proxy.pk,))
        )
        self.assertContains(response, "<h1>View user proxy</h1>")
        self.assertContains(response, '<div class="readonly">user_proxy</div>')

    def test_change(self):
        self.client.force_login(self.changeuser)
        data = {
            "password": self.user_proxy.password,
            "username": self.user_proxy.username,
            "date_joined_0": self.user_proxy.date_joined.strftime("%Y-%m-%d"),
            "date_joined_1": self.user_proxy.date_joined.strftime("%H:%M:%S"),
            "first_name": "first_name",
        }
        url = reverse("admin:admin_views_userproxy_change", args=(self.user_proxy.pk,))
        response = self.client.post(url, data)
        self.assertRedirects(
            response, reverse("admin:admin_views_userproxy_changelist")
        )
        self.assertEqual(
            UserProxy.objects.get(pk=self.user_proxy.pk).first_name, "first_name"
        )

    def test_delete(self):
        self.client.force_login(self.deleteuser)
        url = reverse("admin:admin_views_userproxy_delete", args=(self.user_proxy.pk,))
        response = self.client.post(url, {"post": "yes"}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(UserProxy.objects.filter(pk=self.user_proxy.pk).exists())


@override_settings(ROOT_URLCONF="admin_views.urls")
class AdminViewsNoUrlTest(TestCase):
    """Regression test for #17333"""

    @classmethod
    def setUpTestData(cls):
        # User who can change Reports
        cls.changeuser = User.objects.create_user(
            username="changeuser", password="secret", is_staff=True
        )
        cls.changeuser.user_permissions.add(
            get_perm(Report, get_permission_codename("change", Report._meta))
        )

    def test_no_standard_modeladmin_urls(self):
        """Admin index views don't break when user's ModelAdmin removes standard urls"""
        self.client.force_login(self.changeuser)
        r = self.client.get(reverse("admin:index"))
        # we shouldn't get a 500 error caused by a NoReverseMatch
        self.assertEqual(r.status_code, 200)
        self.client.post(reverse("admin:logout"))


@skipUnlessDBFeature("can_defer_constraint_checks")
@override_settings(ROOT_URLCONF="admin_views.urls")
class AdminViewDeletedObjectsTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="super", password="secret", email="super@example.com"
        )
        cls.deleteuser = User.objects.create_user(
            username="deleteuser", password="secret", is_staff=True
        )
        cls.s1 = Section.objects.create(name="Test section")
        cls.a1 = Article.objects.create(
            content="<p>Middle content</p>",
            date=datetime.datetime(2008, 3, 18, 11, 54, 58),
            section=cls.s1,
        )
        cls.a2 = Article.objects.create(
            content="<p>Oldest content</p>",
            date=datetime.datetime(2000, 3, 18, 11, 54, 58),
            section=cls.s1,
        )
        cls.a3 = Article.objects.create(
            content="<p>Newest content</p>",
            date=datetime.datetime(2009, 3, 18, 11, 54, 58),
            section=cls.s1,
        )
        cls.p1 = PrePopulatedPost.objects.create(
            title="A Long Title", published=True, slug="a-long-title"
        )

        cls.v1 = Villain.objects.create(name="Adam")
        cls.v2 = Villain.objects.create(name="Sue")
        cls.sv1 = SuperVillain.objects.create(name="Bob")
        cls.pl1 = Plot.objects.create(
            name="World Domination", team_leader=cls.v1, contact=cls.v2
        )
        cls.pl2 = Plot.objects.create(
            name="World Peace", team_leader=cls.v2, contact=cls.v2
        )
        cls.pl3 = Plot.objects.create(
            name="Corn Conspiracy", team_leader=cls.v1, contact=cls.v1
        )
        cls.pd1 = PlotDetails.objects.create(details="almost finished", plot=cls.pl1)
        cls.sh1 = SecretHideout.objects.create(
            location="underground bunker", villain=cls.v1
        )
        cls.sh2 = SecretHideout.objects.create(
            location="floating castle", villain=cls.sv1
        )
        cls.ssh1 = SuperSecretHideout.objects.create(
            location="super floating castle!", supervillain=cls.sv1
        )
        cls.cy1 = CyclicOne.objects.create(pk=1, name="I am recursive", two_id=1)
        cls.cy2 = CyclicTwo.objects.create(pk=1, name="I am recursive too", one_id=1)

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_nesting(self):
        """
        Objects should be nested to display the relationships that
        cause them to be scheduled for deletion.
        """
        pattern = re.compile(
            r'<li>Plot: <a href="%s">World Domination</a>\s*<ul>\s*'
            r'<li>Plot details: <a href="%s">almost finished</a>'
            % (
                reverse("admin:admin_views_plot_change", args=(self.pl1.pk,)),
                reverse("admin:admin_views_plotdetails_change", args=(self.pd1.pk,)),
            )
        )
        response = self.client.get(
            reverse("admin:admin_views_villain_delete", args=(self.v1.pk,))
        )
        self.assertRegex(response.content.decode(), pattern)

    def test_cyclic(self):
        """
        Cyclic relationships should still cause each object to only be
        listed once.
        """
        one = '<li>Cyclic one: <a href="%s">I am recursive</a>' % (
            reverse("admin:admin_views_cyclicone_change", args=(self.cy1.pk,)),
        )
        two = '<li>Cyclic two: <a href="%s">I am recursive too</a>' % (
            reverse("admin:admin_views_cyclictwo_change", args=(self.cy2.pk,)),
        )
        response = self.client.get(
            reverse("admin:admin_views_cyclicone_delete", args=(self.cy1.pk,))
        )

        self.assertContains(response, one, 1)
        self.assertContains(response, two, 1)

    def test_perms_needed(self):
        self.client.logout()
        delete_user = User.objects.get(username="deleteuser")
        delete_user.user_permissions.add(
            get_perm(Plot, get_permission_codename("delete", Plot._meta))
        )

        self.client.force_login(self.deleteuser)
        response = self.client.get(
            reverse("admin:admin_views_plot_delete", args=(self.pl1.pk,))
        )
        self.assertContains(
            response,
            "your account doesn't have permission to delete the following types of "
            "objects",
        )
        self.assertContains(response, "<li>plot details</li>")

    def test_protected(self):
        q = Question.objects.create(question="Why?")
        a1 = Answer.objects.create(question=q, answer="Because.")
        a2 = Answer.objects.create(question=q, answer="Yes.")

        response = self.client.get(
            reverse("admin:admin_views_question_delete", args=(q.pk,))
        )
        self.assertContains(
            response, "would require deleting the following protected related objects"
        )
        self.assertContains(
            response,
            '<li>Answer: <a href="%s">Because.</a></li>'
            % reverse("admin:admin_views_answer_change", args=(a1.pk,)),
        )
        self.assertContains(
            response,
            '<li>Answer: <a href="%s">Yes.</a></li>'
            % reverse("admin:admin_views_answer_change", args=(a2.pk,)),
        )

    def test_post_delete_protected(self):
        """
        A POST request to delete protected objects should display the page
        which says the deletion is prohibited.
        """
        q = Question.objects.create(question="Why?")
        Answer.objects.create(question=q, answer="Because.")

        response = self.client.post(
            reverse("admin:admin_views_question_delete", args=(q.pk,)), {"post": "yes"}
        )
        self.assertEqual(Question.objects.count(), 1)
        self.assertContains(
            response, "would require deleting the following protected related objects"
        )

    def test_restricted(self):
        album = Album.objects.create(title="Amaryllis")
        song = Song.objects.create(album=album, name="Unity")
        response = self.client.get(
            reverse("admin:admin_views_album_delete", args=(album.pk,))
        )
        self.assertContains(
            response,
            "would require deleting the following protected related objects",
        )
        self.assertContains(
            response,
            '<li>Song: <a href="%s">Unity</a></li>'
            % reverse("admin:admin_views_song_change", args=(song.pk,)),
        )

    def test_post_delete_restricted(self):
        album = Album.objects.create(title="Amaryllis")
        Song.objects.create(album=album, name="Unity")
        response = self.client.post(
            reverse("admin:admin_views_album_delete", args=(album.pk,)),
            {"post": "yes"},
        )
        self.assertEqual(Album.objects.count(), 1)
        self.assertContains(
            response,
            "would require deleting the following protected related objects",
        )

    def test_not_registered(self):
        should_contain = """<li>Secret hideout: underground bunker"""
        response = self.client.get(
            reverse("admin:admin_views_villain_delete", args=(self.v1.pk,))
        )
        self.assertContains(response, should_contain, 1)

    def test_multiple_fkeys_to_same_model(self):
        """
        If a deleted object has two relationships from another model,
        both of those should be followed in looking for related
        objects to delete.
        """
        should_contain = '<li>Plot: <a href="%s">World Domination</a>' % reverse(
            "admin:admin_views_plot_change", args=(self.pl1.pk,)
        )
        response = self.client.get(
            reverse("admin:admin_views_villain_delete", args=(self.v1.pk,))
        )
        self.assertContains(response, should_contain)
        response = self.client.get(
            reverse("admin:admin_views_villain_delete", args=(self.v2.pk,))
        )
        self.assertContains(response, should_contain)

    def test_multiple_fkeys_to_same_instance(self):
        """
        If a deleted object has two relationships pointing to it from
        another object, the other object should still only be listed
        once.
        """
        should_contain = '<li>Plot: <a href="%s">World Peace</a></li>' % reverse(
            "admin:admin_views_plot_change", args=(self.pl2.pk,)
        )
        response = self.client.get(
            reverse("admin:admin_views_villain_delete", args=(self.v2.pk,))
        )
        self.assertContains(response, should_contain, 1)

    def test_inheritance(self):
        """
        In the case of an inherited model, if either the child or
        parent-model instance is deleted, both instances are listed
        for deletion, as well as any relationships they have.
        """
        should_contain = [
            '<li>Villain: <a href="%s">Bob</a>'
            % reverse("admin:admin_views_villain_change", args=(self.sv1.pk,)),
            '<li>Super villain: <a href="%s">Bob</a>'
            % reverse("admin:admin_views_supervillain_change", args=(self.sv1.pk,)),
            "<li>Secret hideout: floating castle",
            "<li>Super secret hideout: super floating castle!",
        ]
        response = self.client.get(
            reverse("admin:admin_views_villain_delete", args=(self.sv1.pk,))
        )
        for should in should_contain:
            self.assertContains(response, should, 1)
        response = self.client.get(
            reverse("admin:admin_views_supervillain_delete", args=(self.sv1.pk,))
        )
        for should in should_contain:
            self.assertContains(response, should, 1)

    def test_generic_relations(self):
        """
        If a deleted object has GenericForeignKeys pointing to it,
        those objects should be listed for deletion.
        """
        plot = self.pl3
        tag = FunkyTag.objects.create(content_object=plot, name="hott")
        should_contain = '<li>Funky tag: <a href="%s">hott' % reverse(
            "admin:admin_views_funkytag_change", args=(tag.id,)
        )
        response = self.client.get(
            reverse("admin:admin_views_plot_delete", args=(plot.pk,))
        )
        self.assertContains(response, should_contain)

    def test_generic_relations_with_related_query_name(self):
        """
        If a deleted object has GenericForeignKey with
        GenericRelation(related_query_name='...') pointing to it, those objects
        should be listed for deletion.
        """
        bookmark = Bookmark.objects.create(name="djangoproject")
        tag = FunkyTag.objects.create(content_object=bookmark, name="django")
        tag_url = reverse("admin:admin_views_funkytag_change", args=(tag.id,))
        should_contain = '<li>Funky tag: <a href="%s">django' % tag_url
        response = self.client.get(
            reverse("admin:admin_views_bookmark_delete", args=(bookmark.pk,))
        )
        self.assertContains(response, should_contain)

    def test_delete_view_uses_get_deleted_objects(self):
        """The delete view uses ModelAdmin.get_deleted_objects()."""
        book = Book.objects.create(name="Test Book")
        response = self.client.get(
            reverse("admin2:admin_views_book_delete", args=(book.pk,))
        )
        # BookAdmin.get_deleted_objects() returns custom text.
        self.assertContains(response, "a deletable object")


@override_settings(ROOT_URLCONF="admin_views.urls")
class TestGenericRelations(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="super", password="secret", email="super@example.com"
        )
        cls.v1 = Villain.objects.create(name="Adam")
        cls.pl3 = Plot.objects.create(
            name="Corn Conspiracy", team_leader=cls.v1, contact=cls.v1
        )

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_generic_content_object_in_list_display(self):
        FunkyTag.objects.create(content_object=self.pl3, name="hott")
        response = self.client.get(reverse("admin:admin_views_funkytag_changelist"))
        self.assertContains(response, "%s</td>" % self.pl3)


@override_settings(ROOT_URLCONF="admin_views.urls")
class AdminViewStringPrimaryKeyTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="super", password="secret", email="super@example.com"
        )
        cls.s1 = Section.objects.create(name="Test section")
        cls.a1 = Article.objects.create(
            content="<p>Middle content</p>",
            date=datetime.datetime(2008, 3, 18, 11, 54, 58),
            section=cls.s1,
        )
        cls.a2 = Article.objects.create(
            content="<p>Oldest content</p>",
            date=datetime.datetime(2000, 3, 18, 11, 54, 58),
            section=cls.s1,
        )
        cls.a3 = Article.objects.create(
            content="<p>Newest content</p>",
            date=datetime.datetime(2009, 3, 18, 11, 54, 58),
            section=cls.s1,
        )
        cls.p1 = PrePopulatedPost.objects.create(
            title="A Long Title", published=True, slug="a-long-title"
        )
        cls.pk = (
            "abcdefghijklmnopqrstuvwxyz ABCDEFGHIJKLMNOPQRSTUVWXYZ 1234567890 "
            r"""-_.!~*'() ;/?:@&=+$, <>#%" {}|\^[]`"""
        )
        cls.m1 = ModelWithStringPrimaryKey.objects.create(string_pk=cls.pk)
        user_pk = cls.superuser.pk
        LogEntry.objects.log_actions(
            user_pk,
            [cls.m1],
            2,
            change_message="Changed something",
            single_object=True,
        )
        LogEntry.objects.log_actions(
            user_pk,
            [cls.m1],
            1,
            change_message="Added something",
            single_object=True,
        )
        LogEntry.objects.log_actions(
            user_pk,
            [cls.m1],
            3,
            change_message="Deleted something",
            single_object=True,
        )

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_get_history_view(self):
        """
        Retrieving the history for an object using urlencoded form of primary
        key should work.
        Refs #12349, #18550.
        """
        response = self.client.get(
            reverse(
                "admin:admin_views_modelwithstringprimarykey_history", args=(self.pk,)
            )
        )
        self.assertContains(response, escape(self.pk))
        self.assertContains(response, "Changed something")

    def test_get_change_view(self):
        "Retrieving the object using urlencoded form of primary key should work"
        response = self.client.get(
            reverse(
                "admin:admin_views_modelwithstringprimarykey_change", args=(self.pk,)
            )
        )
        self.assertContains(response, escape(self.pk))

    def test_changelist_to_changeform_link(self):
        """
        Link to the changeform of the object in changelist should use reverse()
        and be quoted.
        """
        response = self.client.get(
            reverse("admin:admin_views_modelwithstringprimarykey_changelist")
        )
        # this URL now comes through reverse(), thus url quoting and iri_to_uri encoding
        pk_final_url = escape(iri_to_uri(quote(self.pk)))
        change_url = reverse(
            "admin:admin_views_modelwithstringprimarykey_change", args=("__fk__",)
        ).replace("__fk__", pk_final_url)
        should_contain = '<th class="field-__str__"><a href="%s">%s</a></th>' % (
            change_url,
            escape(self.pk),
        )
        self.assertContains(response, should_contain)

    def test_recentactions_link(self):
        """
        The link from the recent actions list referring to the changeform of
        the object should be quoted.
        """
        response = self.client.get(reverse("admin:index"))
        link = reverse(
            "admin:admin_views_modelwithstringprimarykey_change", args=(quote(self.pk),)
        )
        should_contain = """<a href="%s">%s</a>""" % (escape(link), escape(self.pk))
        self.assertContains(response, should_contain)

    def test_recentactions_description(self):
        response = self.client.get(reverse("admin:index"))
        for operation in ["Added", "Changed", "Deleted"]:
            with self.subTest(operation):
                self.assertContains(
                    response, f'<span class="visually-hidden">{operation}:'
                )

    def test_deleteconfirmation_link(self):
        """
        The link from the delete confirmation page referring back to the
        changeform of the object should be quoted.
        """
        url = reverse(
            "admin:admin_views_modelwithstringprimarykey_delete", args=(quote(self.pk),)
        )
        response = self.client.get(url)
        # this URL now comes through reverse(), thus url quoting and iri_to_uri encoding
        change_url = reverse(
            "admin:admin_views_modelwithstringprimarykey_change", args=("__fk__",)
        ).replace("__fk__", escape(iri_to_uri(quote(self.pk))))
        should_contain = '<a href="%s">%s</a>' % (change_url, escape(self.pk))
        self.assertContains(response, should_contain)

    def test_url_conflicts_with_add(self):
        "A model with a primary key that ends with add or is `add` should be visible"
        add_model = ModelWithStringPrimaryKey.objects.create(
            pk="i have something to add"
        )
        add_model.save()
        response = self.client.get(
            reverse(
                "admin:admin_views_modelwithstringprimarykey_change",
                args=(quote(add_model.pk),),
            )
        )
        should_contain = """<h1>Change model with string primary key</h1>"""
        self.assertContains(response, should_contain)

        add_model2 = ModelWithStringPrimaryKey.objects.create(pk="add")
        add_url = reverse("admin:admin_views_modelwithstringprimarykey_add")
        change_url = reverse(
            "admin:admin_views_modelwithstringprimarykey_change",
            args=(quote(add_model2.pk),),
        )
        self.assertNotEqual(add_url, change_url)

    def test_url_conflicts_with_delete(self):
        "A model with a primary key that ends with delete should be visible"
        delete_model = ModelWithStringPrimaryKey(pk="delete")
        delete_model.save()
        response = self.client.get(
            reverse(
                "admin:admin_views_modelwithstringprimarykey_change",
                args=(quote(delete_model.pk),),
            )
        )
        should_contain = """<h1>Change model with string primary key</h1>"""
        self.assertContains(response, should_contain)

    def test_url_conflicts_with_history(self):
        "A model with a primary key that ends with history should be visible"
        history_model = ModelWithStringPrimaryKey(pk="history")
        history_model.save()
        response = self.client.get(
            reverse(
                "admin:admin_views_modelwithstringprimarykey_change",
                args=(quote(history_model.pk),),
            )
        )
        should_contain = """<h1>Change model with string primary key</h1>"""
        self.assertContains(response, should_contain)

    def test_shortcut_view_with_escaping(self):
        "'View on site should' work properly with char fields"
        model = ModelWithStringPrimaryKey(pk="abc_123")
        model.save()
        response = self.client.get(
            reverse(
                "admin:admin_views_modelwithstringprimarykey_change",
                args=(quote(model.pk),),
            )
        )
        should_contain = '/%s/" class="viewsitelink">' % model.pk
        self.assertContains(response, should_contain)

    def test_change_view_history_link(self):
        """Object history button link should work and contain the pk value quoted."""
        url = reverse(
            "admin:%s_modelwithstringprimarykey_change"
            % ModelWithStringPrimaryKey._meta.app_label,
            args=(quote(self.pk),),
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        expected_link = reverse(
            "admin:%s_modelwithstringprimarykey_history"
            % ModelWithStringPrimaryKey._meta.app_label,
            args=(quote(self.pk),),
        )
        self.assertContains(
            response, '<a href="%s" class="historylink"' % escape(expected_link)
        )

    def test_redirect_on_add_view_continue_button(self):
        """As soon as an object is added using "Save and continue editing"
        button, the user should be redirected to the object's change_view.

        In case primary key is a string containing some special characters
        like slash or underscore, these characters must be escaped (see #22266)
        """
        response = self.client.post(
            reverse("admin:admin_views_modelwithstringprimarykey_add"),
            {
                "string_pk": "123/history",
                "_continue": "1",  # Save and continue editing
            },
        )

        self.assertEqual(response.status_code, 302)  # temporary redirect
        self.assertIn("/123_2Fhistory/", response.headers["location"])  # PK is quoted


@override_settings(ROOT_URLCONF="admin_views.urls")
class SecureViewTests(TestCase):
    """
    Test behavior of a view protected by the staff_member_required decorator.
    """

    def test_secure_view_shows_login_if_not_logged_in(self):
        secure_url = reverse("secure_view")
        response = self.client.get(secure_url)
        self.assertRedirects(
            response, "%s?next=%s" % (reverse("admin:login"), secure_url)
        )
        response = self.client.get(secure_url, follow=True)
        self.assertTemplateUsed(response, "admin/login.html")
        self.assertEqual(response.context[REDIRECT_FIELD_NAME], secure_url)

    def test_staff_member_required_decorator_works_with_argument(self):
        """
        Staff_member_required decorator works with an argument
        (redirect_field_name).
        """
        secure_url = "/test_admin/admin/secure-view2/"
        response = self.client.get(secure_url)
        self.assertRedirects(
            response, "%s?myfield=%s" % (reverse("admin:login"), secure_url)
        )


@override_settings(ROOT_URLCONF="admin_views.urls")
class AdminViewUnicodeTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="super", password="secret", email="super@example.com"
        )
        cls.b1 = Book.objects.create(name="Lærdommer")
        cls.p1 = Promo.objects.create(name="<Promo for Lærdommer>", book=cls.b1)
        cls.chap1 = Chapter.objects.create(
            title="Norske bostaver æøå skaper problemer",
            content="<p>Svært frustrerende med UnicodeDecodeErro</p>",
            book=cls.b1,
        )
        cls.chap2 = Chapter.objects.create(
            title="Kjærlighet",
            content="<p>La kjærligheten til de lidende seire.</p>",
            book=cls.b1,
        )
        cls.chap3 = Chapter.objects.create(
            title="Kjærlighet", content="<p>Noe innhold</p>", book=cls.b1
        )
        cls.chap4 = ChapterXtra1.objects.create(
            chap=cls.chap1, xtra="<Xtra(1) Norske bostaver æøå skaper problemer>"
        )
        cls.chap5 = ChapterXtra1.objects.create(
            chap=cls.chap2, xtra="<Xtra(1) Kjærlighet>"
        )
        cls.chap6 = ChapterXtra1.objects.create(
            chap=cls.chap3, xtra="<Xtra(1) Kjærlighet>"
        )
        cls.chap7 = ChapterXtra2.objects.create(
            chap=cls.chap1, xtra="<Xtra(2) Norske bostaver æøå skaper problemer>"
        )
        cls.chap8 = ChapterXtra2.objects.create(
            chap=cls.chap2, xtra="<Xtra(2) Kjærlighet>"
        )
        cls.chap9 = ChapterXtra2.objects.create(
            chap=cls.chap3, xtra="<Xtra(2) Kjærlighet>"
        )

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_unicode_edit(self):
        """
        A test to ensure that POST on edit_view handles non-ASCII characters.
        """
        post_data = {
            "name": "Test lærdommer",
            # inline data
            "chapter_set-TOTAL_FORMS": "6",
            "chapter_set-INITIAL_FORMS": "3",
            "chapter_set-MAX_NUM_FORMS": "0",
            "chapter_set-0-id": self.chap1.pk,
            "chapter_set-0-title": "Norske bostaver æøå skaper problemer",
            "chapter_set-0-content": (
                "&lt;p&gt;Svært frustrerende med UnicodeDecodeError&lt;/p&gt;"
            ),
            "chapter_set-1-id": self.chap2.id,
            "chapter_set-1-title": "Kjærlighet.",
            "chapter_set-1-content": (
                "&lt;p&gt;La kjærligheten til de lidende seire.&lt;/p&gt;"
            ),
            "chapter_set-2-id": self.chap3.id,
            "chapter_set-2-title": "Need a title.",
            "chapter_set-2-content": "&lt;p&gt;Newest content&lt;/p&gt;",
            "chapter_set-3-id": "",
            "chapter_set-3-title": "",
            "chapter_set-3-content": "",
            "chapter_set-4-id": "",
            "chapter_set-4-title": "",
            "chapter_set-4-content": "",
            "chapter_set-5-id": "",
            "chapter_set-5-title": "",
            "chapter_set-5-content": "",
        }

        response = self.client.post(
            reverse("admin:admin_views_book_change", args=(self.b1.pk,)), post_data
        )
        self.assertEqual(response.status_code, 302)  # redirect somewhere

    def test_unicode_delete(self):
        """
        The delete_view handles non-ASCII characters
        """
        delete_dict = {"post": "yes"}
        delete_url = reverse("admin:admin_views_book_delete", args=(self.b1.pk,))
        response = self.client.get(delete_url)
        self.assertEqual(response.status_code, 200)
        response = self.client.post(delete_url, delete_dict)
        self.assertRedirects(response, reverse("admin:admin_views_book_changelist"))


@override_settings(ROOT_URLCONF="admin_views.urls")
class AdminViewListEditable(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="super", password="secret", email="super@example.com"
        )
        cls.s1 = Section.objects.create(name="Test section")
        cls.a1 = Article.objects.create(
            content="<p>Middle content</p>",
            date=datetime.datetime(2008, 3, 18, 11, 54, 58),
            section=cls.s1,
        )
        cls.a2 = Article.objects.create(
            content="<p>Oldest content</p>",
            date=datetime.datetime(2000, 3, 18, 11, 54, 58),
            section=cls.s1,
        )
        cls.a3 = Article.objects.create(
            content="<p>Newest content</p>",
            date=datetime.datetime(2009, 3, 18, 11, 54, 58),
            section=cls.s1,
        )
        cls.p1 = PrePopulatedPost.objects.create(
            title="A Long Title", published=True, slug="a-long-title"
        )
        cls.per1 = Person.objects.create(name="John Mauchly", gender=1, alive=True)
        cls.per2 = Person.objects.create(name="Grace Hopper", gender=1, alive=False)
        cls.per3 = Person.objects.create(name="Guido van Rossum", gender=1, alive=True)

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_inheritance(self):
        Podcast.objects.create(
            name="This Week in Django", release_date=datetime.date.today()
        )
        response = self.client.get(reverse("admin:admin_views_podcast_changelist"))
        self.assertEqual(response.status_code, 200)

    def test_inheritance_2(self):
        Vodcast.objects.create(name="This Week in Django", released=True)
        response = self.client.get(reverse("admin:admin_views_vodcast_changelist"))
        self.assertEqual(response.status_code, 200)

    def test_custom_pk(self):
        Language.objects.create(iso="en", name="English", english_name="English")
        response = self.client.get(reverse("admin:admin_views_language_changelist"))
        self.assertEqual(response.status_code, 200)

    def test_changelist_input_html(self):
        response = self.client.get(reverse("admin:admin_views_person_changelist"))
        # 2 inputs per object(the field and the hidden id field) = 6
        # 4 management hidden fields = 4
        # 4 action inputs (3 regular checkboxes, 1 checkbox to select all)
        # main form submit button = 1
        # search field and search submit button = 2
        # CSRF field = 2
        # field to track 'select all' across paginated views = 1
        # 6 + 4 + 4 + 1 + 2 + 2 + 1 = 20 inputs
        self.assertContains(response, "<input", count=21)
        # 1 select per object = 3 selects
        self.assertContains(response, "<select", count=4)

    def test_post_messages(self):
        # Ticket 12707: Saving inline editable should not show admin
        # action warnings
        data = {
            "form-TOTAL_FORMS": "3",
            "form-INITIAL_FORMS": "3",
            "form-MAX_NUM_FORMS": "0",
            "form-0-gender": "1",
            "form-0-id": str(self.per1.pk),
            "form-1-gender": "2",
            "form-1-id": str(self.per2.pk),
            "form-2-alive": "checked",
            "form-2-gender": "1",
            "form-2-id": str(self.per3.pk),
            "_save": "Save",
        }
        response = self.client.post(
            reverse("admin:admin_views_person_changelist"), data, follow=True
        )
        self.assertEqual(len(response.context["messages"]), 1)

    def test_post_submission(self):
        data = {
            "form-TOTAL_FORMS": "3",
            "form-INITIAL_FORMS": "3",
            "form-MAX_NUM_FORMS": "0",
            "form-0-gender": "1",
            "form-0-id": str(self.per1.pk),
            "form-1-gender": "2",
            "form-1-id": str(self.per2.pk),
            "form-2-alive": "checked",
            "form-2-gender": "1",
            "form-2-id": str(self.per3.pk),
            "_save": "Save",
        }
        self.client.post(reverse("admin:admin_views_person_changelist"), data)

        self.assertIs(Person.objects.get(name="John Mauchly").alive, False)
        self.assertEqual(Person.objects.get(name="Grace Hopper").gender, 2)

        # test a filtered page
        data = {
            "form-TOTAL_FORMS": "2",
            "form-INITIAL_FORMS": "2",
            "form-MAX_NUM_FORMS": "0",
            "form-0-id": str(self.per1.pk),
            "form-0-gender": "1",
            "form-0-alive": "checked",
            "form-1-id": str(self.per3.pk),
            "form-1-gender": "1",
            "form-1-alive": "checked",
            "_save": "Save",
        }
        self.client.post(
            reverse("admin:admin_views_person_changelist") + "?gender__exact=1", data
        )

        self.assertIs(Person.objects.get(name="John Mauchly").alive, True)

        # test a searched page
        data = {
            "form-TOTAL_FORMS": "1",
            "form-INITIAL_FORMS": "1",
            "form-MAX_NUM_FORMS": "0",
            "form-0-id": str(self.per1.pk),
            "form-0-gender": "1",
            "_save": "Save",
        }
        self.client.post(
            reverse("admin:admin_views_person_changelist") + "?q=john", data
        )

        self.assertIs(Person.objects.get(name="John Mauchly").alive, False)

    def test_non_field_errors(self):
        """
        Non-field errors are displayed for each of the forms in the
        changelist's formset.
        """
        fd1 = FoodDelivery.objects.create(
            reference="123", driver="bill", restaurant="thai"
        )
        fd2 = FoodDelivery.objects.create(
            reference="456", driver="bill", restaurant="india"
        )
        fd3 = FoodDelivery.objects.create(
            reference="789", driver="bill", restaurant="pizza"
        )

        data = {
            "form-TOTAL_FORMS": "3",
            "form-INITIAL_FORMS": "3",
            "form-MAX_NUM_FORMS": "0",
            "form-0-id": str(fd1.id),
            "form-0-reference": "123",
            "form-0-driver": "bill",
            "form-0-restaurant": "thai",
            # Same data as above: Forbidden because of unique_together!
            "form-1-id": str(fd2.id),
            "form-1-reference": "456",
            "form-1-driver": "bill",
            "form-1-restaurant": "thai",
            "form-2-id": str(fd3.id),
            "form-2-reference": "789",
            "form-2-driver": "bill",
            "form-2-restaurant": "pizza",
            "_save": "Save",
        }
        response = self.client.post(
            reverse("admin:admin_views_fooddelivery_changelist"), data
        )
        self.assertContains(
            response,
            '<tr><td colspan="4"><ul class="errorlist nonfield"><li>Food delivery '
            "with this Driver and Restaurant already exists.</li></ul></td></tr>",
            1,
            html=True,
        )

        data = {
            "form-TOTAL_FORMS": "3",
            "form-INITIAL_FORMS": "3",
            "form-MAX_NUM_FORMS": "0",
            "form-0-id": str(fd1.id),
            "form-0-reference": "123",
            "form-0-driver": "bill",
            "form-0-restaurant": "thai",
            # Same data as above: Forbidden because of unique_together!
            "form-1-id": str(fd2.id),
            "form-1-reference": "456",
            "form-1-driver": "bill",
            "form-1-restaurant": "thai",
            # Same data also.
            "form-2-id": str(fd3.id),
            "form-2-reference": "789",
            "form-2-driver": "bill",
            "form-2-restaurant": "thai",
            "_save": "Save",
        }
        response = self.client.post(
            reverse("admin:admin_views_fooddelivery_changelist"), data
        )
        self.assertContains(
            response,
            '<tr><td colspan="4"><ul class="errorlist nonfield"><li>Food delivery '
            "with this Driver and Restaurant already exists.</li></ul></td></tr>",
            2,
            html=True,
        )

    def test_non_form_errors(self):
        # test if non-form errors are handled; ticket #12716
        data = {
            "form-TOTAL_FORMS": "1",
            "form-INITIAL_FORMS": "1",
            "form-MAX_NUM_FORMS": "0",
            "form-0-id": str(self.per2.pk),
            "form-0-alive": "1",
            "form-0-gender": "2",
            # The form processing understands this as a list_editable "Save"
            # and not an action "Go".
            "_save": "Save",
        }
        response = self.client.post(
            reverse("admin:admin_views_person_changelist"), data
        )
        self.assertContains(response, "Grace is not a Zombie")

    def test_non_form_errors_is_errorlist(self):
        # test if non-form errors are correctly handled; ticket #12878
        data = {
            "form-TOTAL_FORMS": "1",
            "form-INITIAL_FORMS": "1",
            "form-MAX_NUM_FORMS": "0",
            "form-0-id": str(self.per2.pk),
            "form-0-alive": "1",
            "form-0-gender": "2",
            "_save": "Save",
        }
        response = self.client.post(
            reverse("admin:admin_views_person_changelist"), data
        )
        non_form_errors = response.context["cl"].formset.non_form_errors()
        self.assertIsInstance(non_form_errors, ErrorList)
        self.assertEqual(
            str(non_form_errors),
            str(ErrorList(["Grace is not a Zombie"], error_class="nonform")),
        )

    def test_list_editable_ordering(self):
        collector = Collector.objects.create(id=1, name="Frederick Clegg")

        Category.objects.create(id=1, order=1, collector=collector)
        Category.objects.create(id=2, order=2, collector=collector)
        Category.objects.create(id=3, order=0, collector=collector)
        Category.objects.create(id=4, order=0, collector=collector)

        # NB: The order values must be changed so that the items are reordered.
        data = {
            "form-TOTAL_FORMS": "4",
            "form-INITIAL_FORMS": "4",
            "form-MAX_NUM_FORMS": "0",
            "form-0-order": "14",
            "form-0-id": "1",
            "form-0-collector": "1",
            "form-1-order": "13",
            "form-1-id": "2",
            "form-1-collector": "1",
            "form-2-order": "1",
            "form-2-id": "3",
            "form-2-collector": "1",
            "form-3-order": "0",
            "form-3-id": "4",
            "form-3-collector": "1",
            # The form processing understands this as a list_editable "Save"
            # and not an action "Go".
            "_save": "Save",
        }
        response = self.client.post(
            reverse("admin:admin_views_category_changelist"), data
        )
        # Successful post will redirect
        self.assertEqual(response.status_code, 302)

        # The order values have been applied to the right objects
        self.assertEqual(Category.objects.get(id=1).order, 14)
        self.assertEqual(Category.objects.get(id=2).order, 13)
        self.assertEqual(Category.objects.get(id=3).order, 1)
        self.assertEqual(Category.objects.get(id=4).order, 0)

    def test_list_editable_pagination(self):
        """
        Pagination works for list_editable items.
        """
        UnorderedObject.objects.create(id=1, name="Unordered object #1")
        UnorderedObject.objects.create(id=2, name="Unordered object #2")
        UnorderedObject.objects.create(id=3, name="Unordered object #3")
        response = self.client.get(
            reverse("admin:admin_views_unorderedobject_changelist")
        )
        self.assertContains(response, "Unordered object #3")
        self.assertContains(response, "Unordered object #2")
        self.assertNotContains(response, "Unordered object #1")
        response = self.client.get(
            reverse("admin:admin_views_unorderedobject_changelist") + "?p=2"
        )
        self.assertNotContains(response, "Unordered object #3")
        self.assertNotContains(response, "Unordered object #2")
        self.assertContains(response, "Unordered object #1")

    def test_list_editable_action_submit(self):
        # List editable changes should not be executed if the action "Go" button is
        # used to submit the form.
        data = {
            "form-TOTAL_FORMS": "3",
            "form-INITIAL_FORMS": "3",
            "form-MAX_NUM_FORMS": "0",
            "form-0-gender": "1",
            "form-0-id": "1",
            "form-1-gender": "2",
            "form-1-id": "2",
            "form-2-alive": "checked",
            "form-2-gender": "1",
            "form-2-id": "3",
            "index": "0",
            "_selected_action": ["3"],
            "action": ["", "delete_selected"],
        }
        self.client.post(reverse("admin:admin_views_person_changelist"), data)

        self.assertIs(Person.objects.get(name="John Mauchly").alive, True)
        self.assertEqual(Person.objects.get(name="Grace Hopper").gender, 1)

    def test_list_editable_action_choices(self):
        # List editable changes should be executed if the "Save" button is
        # used to submit the form - any action choices should be ignored.
        data = {
            "form-TOTAL_FORMS": "3",
            "form-INITIAL_FORMS": "3",
            "form-MAX_NUM_FORMS": "0",
            "form-0-gender": "1",
            "form-0-id": str(self.per1.pk),
            "form-1-gender": "2",
            "form-1-id": str(self.per2.pk),
            "form-2-alive": "checked",
            "form-2-gender": "1",
            "form-2-id": str(self.per3.pk),
            "_save": "Save",
            "_selected_action": ["1"],
            "action": ["", "delete_selected"],
        }
        self.client.post(reverse("admin:admin_views_person_changelist"), data)

        self.assertIs(Person.objects.get(name="John Mauchly").alive, False)
        self.assertEqual(Person.objects.get(name="Grace Hopper").gender, 2)

    def test_list_editable_popup(self):
        """
        Fields should not be list-editable in popups.
        """
        response = self.client.get(reverse("admin:admin_views_person_changelist"))
        self.assertNotEqual(response.context["cl"].list_editable, ())
        response = self.client.get(
            reverse("admin:admin_views_person_changelist") + "?%s" % IS_POPUP_VAR
        )
        self.assertEqual(response.context["cl"].list_editable, ())

    def test_pk_hidden_fields(self):
        """
        hidden pk fields aren't displayed in the table body and their
        corresponding human-readable value is displayed instead. The hidden pk
        fields are displayed but separately (not in the table) and only once.
        """
        story1 = Story.objects.create(
            title="The adventures of Guido", content="Once upon a time in Djangoland..."
        )
        story2 = Story.objects.create(
            title="Crouching Tiger, Hidden Python",
            content="The Python was sneaking into...",
        )
        response = self.client.get(reverse("admin:admin_views_story_changelist"))
        # Only one hidden field, in a separate place than the table.
        self.assertContains(response, 'id="id_form-0-id"', 1)
        self.assertContains(response, 'id="id_form-1-id"', 1)
        self.assertContains(
            response,
            '<div class="hiddenfields">\n'
            '<input type="hidden" name="form-0-id" value="%d" id="id_form-0-id">'
            '<input type="hidden" name="form-1-id" value="%d" id="id_form-1-id">\n'
            "</div>" % (story2.id, story1.id),
            html=True,
        )
        self.assertContains(response, '<td class="field-id">%d</td>' % story1.id, 1)
        self.assertContains(response, '<td class="field-id">%d</td>' % story2.id, 1)

    def test_pk_hidden_fields_with_list_display_links(self):
        """Similarly as test_pk_hidden_fields, but when the hidden pk fields are
        referenced in list_display_links.
        Refs #12475.
        """
        story1 = OtherStory.objects.create(
            title="The adventures of Guido",
            content="Once upon a time in Djangoland...",
        )
        story2 = OtherStory.objects.create(
            title="Crouching Tiger, Hidden Python",
            content="The Python was sneaking into...",
        )
        link1 = reverse("admin:admin_views_otherstory_change", args=(story1.pk,))
        link2 = reverse("admin:admin_views_otherstory_change", args=(story2.pk,))
        response = self.client.get(reverse("admin:admin_views_otherstory_changelist"))
        # Only one hidden field, in a separate place than the table.
        self.assertContains(response, 'id="id_form-0-id"', 1)
        self.assertContains(response, 'id="id_form-1-id"', 1)
        self.assertContains(
            response,
            '<div class="hiddenfields">\n'
            '<input type="hidden" name="form-0-id" value="%d" id="id_form-0-id">'
            '<input type="hidden" name="form-1-id" value="%d" id="id_form-1-id">\n'
            "</div>" % (story2.id, story1.id),
            html=True,
        )
        self.assertContains(
            response,
            '<th class="field-id"><a href="%s">%d</a></th>' % (link1, story1.id),
            1,
        )
        self.assertContains(
            response,
            '<th class="field-id"><a href="%s">%d</a></th>' % (link2, story2.id),
            1,
        )


@override_settings(ROOT_URLCONF="admin_views.urls")
class AdminSearchTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="super", password="secret", email="super@example.com"
        )
        cls.joepublicuser = User.objects.create_user(
            username="joepublic", password="secret"
        )
        cls.s1 = Section.objects.create(name="Test section")
        cls.a1 = Article.objects.create(
            content="<p>Middle content</p>",
            date=datetime.datetime(2008, 3, 18, 11, 54, 58),
            section=cls.s1,
        )
        cls.a2 = Article.objects.create(
            content="<p>Oldest content</p>",
            date=datetime.datetime(2000, 3, 18, 11, 54, 58),
            section=cls.s1,
        )
        cls.a3 = Article.objects.create(
            content="<p>Newest content</p>",
            date=datetime.datetime(2009, 3, 18, 11, 54, 58),
            section=cls.s1,
        )
        cls.p1 = PrePopulatedPost.objects.create(
            title="A Long Title", published=True, slug="a-long-title"
        )

        cls.per1 = Person.objects.create(name="John Mauchly", gender=1, alive=True)
        cls.per2 = Person.objects.create(name="Grace Hopper", gender=1, alive=False)
        cls.per3 = Person.objects.create(name="Guido van Rossum", gender=1, alive=True)
        Person.objects.create(name="John Doe", gender=1)
        Person.objects.create(name='John O"Hara', gender=1)
        Person.objects.create(name="John O'Hara", gender=1)

        cls.t1 = Recommender.objects.create()
        cls.t2 = Recommendation.objects.create(the_recommender=cls.t1)
        cls.t3 = Recommender.objects.create()
        cls.t4 = Recommendation.objects.create(the_recommender=cls.t3)

        cls.tt1 = TitleTranslation.objects.create(title=cls.t1, text="Bar")
        cls.tt2 = TitleTranslation.objects.create(title=cls.t2, text="Foo")
        cls.tt3 = TitleTranslation.objects.create(title=cls.t3, text="Few")
        cls.tt4 = TitleTranslation.objects.create(title=cls.t4, text="Bas")

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_search_on_sibling_models(self):
        "A search that mentions sibling models"
        response = self.client.get(
            reverse("admin:admin_views_recommendation_changelist") + "?q=bar"
        )
        # confirm the search returned 1 object
        self.assertContains(response, "\n1 recommendation\n")

    def test_with_fk_to_field(self):
        """
        The to_field GET parameter is preserved when a search is performed.
        Refs #10918.
        """
        response = self.client.get(
            reverse("admin:auth_user_changelist") + "?q=joe&%s=id" % TO_FIELD_VAR
        )
        self.assertContains(response, "\n1 user\n")
        self.assertContains(
            response,
            '<input type="hidden" name="%s" value="id">' % TO_FIELD_VAR,
            html=True,
        )

    def test_exact_matches(self):
        response = self.client.get(
            reverse("admin:admin_views_recommendation_changelist") + "?q=bar"
        )
        # confirm the search returned one object
        self.assertContains(response, "\n1 recommendation\n")

        response = self.client.get(
            reverse("admin:admin_views_recommendation_changelist") + "?q=ba"
        )
        # confirm the search returned zero objects
        self.assertContains(response, "\n0 recommendations\n")

    def test_beginning_matches(self):
        response = self.client.get(
            reverse("admin:admin_views_person_changelist") + "?q=Gui"
        )
        # confirm the search returned one object
        self.assertContains(response, "\n1 person\n")
        self.assertContains(response, "Guido")

        response = self.client.get(
            reverse("admin:admin_views_person_changelist") + "?q=uido"
        )
        # confirm the search returned zero objects
        self.assertContains(response, "\n0 persons\n")
        self.assertNotContains(response, "Guido")

    def test_pluggable_search(self):
        PluggableSearchPerson.objects.create(name="Bob", age=10)
        PluggableSearchPerson.objects.create(name="Amy", age=20)

        response = self.client.get(
            reverse("admin:admin_views_pluggablesearchperson_changelist") + "?q=Bob"
        )
        # confirm the search returned one object
        self.assertContains(response, "\n1 pluggable search person\n")
        self.assertContains(response, "Bob")

        response = self.client.get(
            reverse("admin:admin_views_pluggablesearchperson_changelist") + "?q=20"
        )
        # confirm the search returned one object
        self.assertContains(response, "\n1 pluggable search person\n")
        self.assertContains(response, "Amy")

    def test_reset_link(self):
        """
        Test presence of reset link in search bar ("1 result (_x total_)").
        """
        #   1 query for session + 1 for fetching user
        # + 1 for filtered result + 1 for filtered count
        # + 1 for total count
        with self.assertNumQueries(5):
            response = self.client.get(
                reverse("admin:admin_views_person_changelist") + "?q=Gui"
            )
        self.assertContains(
            response,
            """<span class="small quiet">1 result (<a href="?">6 total</a>)</span>""",
            html=True,
        )

    def test_no_total_count(self):
        """
        #8408 -- "Show all" should be displayed instead of the total count if
        ModelAdmin.show_full_result_count is False.
        """
        #   1 query for session + 1 for fetching user
        # + 1 for filtered result + 1 for filtered count
        with self.assertNumQueries(4):
            response = self.client.get(
                reverse("admin:admin_views_recommendation_changelist") + "?q=bar"
            )
        self.assertContains(
            response,
            """<span class="small quiet">1 result (<a href="?">Show all</a>)</span>""",
            html=True,
        )
        self.assertTrue(response.context["cl"].show_admin_actions)

    def test_search_with_spaces(self):
        url = reverse("admin:admin_views_person_changelist") + "?q=%s"
        tests = [
            ('"John Doe"', 1),
            ("'John Doe'", 1),
            ("John Doe", 0),
            ('"John Doe" John', 1),
            ("'John Doe' John", 1),
            ("John Doe John", 0),
            ('"John Do"', 1),
            ("'John Do'", 1),
            ("'John O'Hara'", 0),
            ("'John O\\'Hara'", 1),
            ('"John O"Hara"', 0),
            ('"John O\\"Hara"', 1),
        ]
        for search, hits in tests:
            with self.subTest(search=search):
                response = self.client.get(url % search)
                self.assertContains(response, "\n%s person" % hits)


@override_settings(ROOT_URLCONF="admin_views.urls")
class AdminInheritedInlinesTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="super", password="secret", email="super@example.com"
        )

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_inline(self):
        """
        Inline models which inherit from a common parent are correctly handled.
        """
        foo_user = "foo username"
        bar_user = "bar username"

        name_re = re.compile(b'name="(.*?)"')

        # test the add case
        response = self.client.get(reverse("admin:admin_views_persona_add"))
        names = name_re.findall(response.content)
        names.remove(b"csrfmiddlewaretoken")
        # make sure we have no duplicate HTML names
        self.assertEqual(len(names), len(set(names)))

        # test the add case
        post_data = {
            "name": "Test Name",
            # inline data
            "accounts-TOTAL_FORMS": "1",
            "accounts-INITIAL_FORMS": "0",
            "accounts-MAX_NUM_FORMS": "0",
            "accounts-0-username": foo_user,
            "accounts-2-TOTAL_FORMS": "1",
            "accounts-2-INITIAL_FORMS": "0",
            "accounts-2-MAX_NUM_FORMS": "0",
            "accounts-2-0-username": bar_user,
        }

        response = self.client.post(reverse("admin:admin_views_persona_add"), post_data)
        self.assertEqual(response.status_code, 302)  # redirect somewhere
        self.assertEqual(Persona.objects.count(), 1)
        self.assertEqual(FooAccount.objects.count(), 1)
        self.assertEqual(BarAccount.objects.count(), 1)
        self.assertEqual(FooAccount.objects.all()[0].username, foo_user)
        self.assertEqual(BarAccount.objects.all()[0].username, bar_user)
        self.assertEqual(Persona.objects.all()[0].accounts.count(), 2)

        persona_id = Persona.objects.all()[0].id
        foo_id = FooAccount.objects.all()[0].id
        bar_id = BarAccount.objects.all()[0].id

        # test the edit case

        response = self.client.get(
            reverse("admin:admin_views_persona_change", args=(persona_id,))
        )
        names = name_re.findall(response.content)
        names.remove(b"csrfmiddlewaretoken")
        # make sure we have no duplicate HTML names
        self.assertEqual(len(names), len(set(names)))

        post_data = {
            "name": "Test Name",
            "accounts-TOTAL_FORMS": "2",
            "accounts-INITIAL_FORMS": "1",
            "accounts-MAX_NUM_FORMS": "0",
            "accounts-0-username": "%s-1" % foo_user,
            "accounts-0-account_ptr": str(foo_id),
            "accounts-0-persona": str(persona_id),
            "accounts-2-TOTAL_FORMS": "2",
            "accounts-2-INITIAL_FORMS": "1",
            "accounts-2-MAX_NUM_FORMS": "0",
            "accounts-2-0-username": "%s-1" % bar_user,
            "accounts-2-0-account_ptr": str(bar_id),
            "accounts-2-0-persona": str(persona_id),
        }
        response = self.client.post(
            reverse("admin:admin_views_persona_change", args=(persona_id,)), post_data
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Persona.objects.count(), 1)
        self.assertEqual(FooAccount.objects.count(), 1)
        self.assertEqual(BarAccount.objects.count(), 1)
        self.assertEqual(FooAccount.objects.all()[0].username, "%s-1" % foo_user)
        self.assertEqual(BarAccount.objects.all()[0].username, "%s-1" % bar_user)
        self.assertEqual(Persona.objects.all()[0].accounts.count(), 2)


@override_settings(ROOT_URLCONF="admin_views.urls")
class TestCustomChangeList(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="super", password="secret", email="super@example.com"
        )

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_custom_changelist(self):
        """
        Validate that a custom ChangeList class can be used (#9749)
        """
        # Insert some data
        post_data = {"name": "First Gadget"}
        response = self.client.post(reverse("admin:admin_views_gadget_add"), post_data)
        self.assertEqual(response.status_code, 302)  # redirect somewhere
        # Hit the page once to get messages out of the queue message list
        response = self.client.get(reverse("admin:admin_views_gadget_changelist"))
        # Data is still not visible on the page
        response = self.client.get(reverse("admin:admin_views_gadget_changelist"))
        self.assertNotContains(response, "First Gadget")


@override_settings(ROOT_URLCONF="admin_views.urls")
class TestInlineNotEditable(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="super", password="secret", email="super@example.com"
        )

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_GET_parent_add(self):
        """
        InlineModelAdmin broken?
        """
        response = self.client.get(reverse("admin:admin_views_parent_add"))
        self.assertEqual(response.status_code, 200)


@override_settings(ROOT_URLCONF="admin_views.urls")
class AdminCustomQuerysetTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="super", password="secret", email="super@example.com"
        )
        cls.pks = [EmptyModel.objects.create().id for i in range(3)]

    def setUp(self):
        self.client.force_login(self.superuser)
        self.super_login = {
            REDIRECT_FIELD_NAME: reverse("admin:index"),
            "username": "super",
            "password": "secret",
        }

    def test_changelist_view(self):
        response = self.client.get(reverse("admin:admin_views_emptymodel_changelist"))
        for i in self.pks:
            if i > 1:
                self.assertContains(response, "Primary key = %s" % i)
            else:
                self.assertNotContains(response, "Primary key = %s" % i)

    def test_changelist_view_count_queries(self):
        # create 2 Person objects
        Person.objects.create(name="person1", gender=1)
        Person.objects.create(name="person2", gender=2)
        changelist_url = reverse("admin:admin_views_person_changelist")

        # 5 queries are expected: 1 for the session, 1 for the user,
        # 2 for the counts and 1 for the objects on the page
        with self.assertNumQueries(5):
            resp = self.client.get(changelist_url)
            self.assertEqual(resp.context["selection_note"], "0 of 2 selected")
            self.assertEqual(resp.context["selection_note_all"], "All 2 selected")
        with self.assertNumQueries(5):
            extra = {"q": "not_in_name"}
            resp = self.client.get(changelist_url, extra)
            self.assertEqual(resp.context["selection_note"], "0 of 0 selected")
            self.assertEqual(resp.context["selection_note_all"], "All 0 selected")
        with self.assertNumQueries(5):
            extra = {"q": "person"}
            resp = self.client.get(changelist_url, extra)
            self.assertEqual(resp.context["selection_note"], "0 of 2 selected")
            self.assertEqual(resp.context["selection_note_all"], "All 2 selected")
        with self.assertNumQueries(5):
            extra = {"gender__exact": "1"}
            resp = self.client.get(changelist_url, extra)
            self.assertEqual(resp.context["selection_note"], "0 of 1 selected")
            self.assertEqual(resp.context["selection_note_all"], "1 selected")

    def test_change_view(self):
        for i in self.pks:
            url = reverse("admin:admin_views_emptymodel_change", args=(i,))
            response = self.client.get(url, follow=True)
            if i > 1:
                self.assertEqual(response.status_code, 200)
            else:
                self.assertRedirects(response, reverse("admin:index"))
                self.assertEqual(
                    [m.message for m in response.context["messages"]],
                    ["empty model with ID “1” doesn’t exist. Perhaps it was deleted?"],
                )

    def test_add_model_modeladmin_defer_qs(self):
        # Test for #14529. defer() is used in ModelAdmin.get_queryset()

        # model has __str__ method
        self.assertEqual(CoverLetter.objects.count(), 0)
        # Emulate model instance creation via the admin
        post_data = {
            "author": "Candidate, Best",
            "_save": "Save",
        }
        response = self.client.post(
            reverse("admin:admin_views_coverletter_add"), post_data, follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(CoverLetter.objects.count(), 1)
        # Message should contain non-ugly model verbose name
        pk = CoverLetter.objects.all()[0].pk
        self.assertContains(
            response,
            '<li class="success">The cover letter “<a href="%s">'
            "Candidate, Best</a>” was added successfully.</li>"
            % reverse("admin:admin_views_coverletter_change", args=(pk,)),
            html=True,
        )

        # model has no __str__ method
        self.assertEqual(ShortMessage.objects.count(), 0)
        # Emulate model instance creation via the admin
        post_data = {
            "content": "What's this SMS thing?",
            "_save": "Save",
        }
        response = self.client.post(
            reverse("admin:admin_views_shortmessage_add"), post_data, follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ShortMessage.objects.count(), 1)
        # Message should contain non-ugly model verbose name
        sm = ShortMessage.objects.all()[0]
        self.assertContains(
            response,
            '<li class="success">The short message “<a href="%s">'
            "%s</a>” was added successfully.</li>"
            % (reverse("admin:admin_views_shortmessage_change", args=(sm.pk,)), sm),
            html=True,
        )

    def test_add_model_modeladmin_only_qs(self):
        # Test for #14529. only() is used in ModelAdmin.get_queryset()

        # model has __str__ method
        self.assertEqual(Telegram.objects.count(), 0)
        # Emulate model instance creation via the admin
        post_data = {
            "title": "Urgent telegram",
            "_save": "Save",
        }
        response = self.client.post(
            reverse("admin:admin_views_telegram_add"), post_data, follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Telegram.objects.count(), 1)
        # Message should contain non-ugly model verbose name
        pk = Telegram.objects.all()[0].pk
        self.assertContains(
            response,
            '<li class="success">The telegram “<a href="%s">'
            "Urgent telegram</a>” was added successfully.</li>"
            % reverse("admin:admin_views_telegram_change", args=(pk,)),
            html=True,
        )

        # model has no __str__ method
        self.assertEqual(Paper.objects.count(), 0)
        # Emulate model instance creation via the admin
        post_data = {
            "title": "My Modified Paper Title",
            "_save": "Save",
        }
        response = self.client.post(
            reverse("admin:admin_views_paper_add"), post_data, follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Paper.objects.count(), 1)
        # Message should contain non-ugly model verbose name
        p = Paper.objects.all()[0]
        self.assertContains(
            response,
            '<li class="success">The paper “<a href="%s">'
            "%s</a>” was added successfully.</li>"
            % (reverse("admin:admin_views_paper_change", args=(p.pk,)), p),
            html=True,
        )

    def test_edit_model_modeladmin_defer_qs(self):
        # Test for #14529. defer() is used in ModelAdmin.get_queryset()

        # model has __str__ method
        cl = CoverLetter.objects.create(author="John Doe")
        self.assertEqual(CoverLetter.objects.count(), 1)
        response = self.client.get(
            reverse("admin:admin_views_coverletter_change", args=(cl.pk,))
        )
        self.assertEqual(response.status_code, 200)
        # Emulate model instance edit via the admin
        post_data = {
            "author": "John Doe II",
            "_save": "Save",
        }
        url = reverse("admin:admin_views_coverletter_change", args=(cl.pk,))
        response = self.client.post(url, post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(CoverLetter.objects.count(), 1)
        # Message should contain non-ugly model verbose name. Instance
        # representation is set by model's __str__()
        self.assertContains(
            response,
            '<li class="success">The cover letter “<a href="%s">'
            "John Doe II</a>” was changed successfully.</li>"
            % reverse("admin:admin_views_coverletter_change", args=(cl.pk,)),
            html=True,
        )

        # model has no __str__ method
        sm = ShortMessage.objects.create(content="This is expensive")
        self.assertEqual(ShortMessage.objects.count(), 1)
        response = self.client.get(
            reverse("admin:admin_views_shortmessage_change", args=(sm.pk,))
        )
        self.assertEqual(response.status_code, 200)
        # Emulate model instance edit via the admin
        post_data = {
            "content": "Too expensive",
            "_save": "Save",
        }
        url = reverse("admin:admin_views_shortmessage_change", args=(sm.pk,))
        response = self.client.post(url, post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ShortMessage.objects.count(), 1)
        # Message should contain non-ugly model verbose name. The ugly(!)
        # instance representation is set by __str__().
        self.assertContains(
            response,
            '<li class="success">The short message “<a href="%s">'
            "%s</a>” was changed successfully.</li>"
            % (reverse("admin:admin_views_shortmessage_change", args=(sm.pk,)), sm),
            html=True,
        )

    def test_edit_model_modeladmin_only_qs(self):
        # Test for #14529. only() is used in ModelAdmin.get_queryset()

        # model has __str__ method
        t = Telegram.objects.create(title="First Telegram")
        self.assertEqual(Telegram.objects.count(), 1)
        response = self.client.get(
            reverse("admin:admin_views_telegram_change", args=(t.pk,))
        )
        self.assertEqual(response.status_code, 200)
        # Emulate model instance edit via the admin
        post_data = {
            "title": "Telegram without typo",
            "_save": "Save",
        }
        response = self.client.post(
            reverse("admin:admin_views_telegram_change", args=(t.pk,)),
            post_data,
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Telegram.objects.count(), 1)
        # Message should contain non-ugly model verbose name. The instance
        # representation is set by model's __str__()
        self.assertContains(
            response,
            '<li class="success">The telegram “<a href="%s">'
            "Telegram without typo</a>” was changed successfully.</li>"
            % reverse("admin:admin_views_telegram_change", args=(t.pk,)),
            html=True,
        )

        # model has no __str__ method
        p = Paper.objects.create(title="My Paper Title")
        self.assertEqual(Paper.objects.count(), 1)
        response = self.client.get(
            reverse("admin:admin_views_paper_change", args=(p.pk,))
        )
        self.assertEqual(response.status_code, 200)
        # Emulate model instance edit via the admin
        post_data = {
            "title": "My Modified Paper Title",
            "_save": "Save",
        }
        response = self.client.post(
            reverse("admin:admin_views_paper_change", args=(p.pk,)),
            post_data,
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Paper.objects.count(), 1)
        # Message should contain non-ugly model verbose name. The ugly(!)
        # instance representation is set by __str__().
        self.assertContains(
            response,
            '<li class="success">The paper “<a href="%s">'
            "%s</a>” was changed successfully.</li>"
            % (reverse("admin:admin_views_paper_change", args=(p.pk,)), p),
            html=True,
        )

    def test_history_view_custom_qs(self):
        """
        Custom querysets are considered for the admin history view.
        """
        self.client.post(reverse("admin:login"), self.super_login)
        FilteredManager.objects.create(pk=1)
        FilteredManager.objects.create(pk=2)
        response = self.client.get(
            reverse("admin:admin_views_filteredmanager_changelist")
        )
        self.assertContains(response, "PK=1")
        self.assertContains(response, "PK=2")
        self.assertEqual(
            self.client.get(
                reverse("admin:admin_views_filteredmanager_history", args=(1,))
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(
                reverse("admin:admin_views_filteredmanager_history", args=(2,))
            ).status_code,
            200,
        )


@override_settings(ROOT_URLCONF="admin_views.urls")
class AdminInlineFileUploadTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="super", password="secret", email="super@example.com"
        )
        file1 = tempfile.NamedTemporaryFile(suffix=".file1")
        file1.write(b"a" * (2**21))
        filename = file1.name
        file1.close()
        cls.gallery = Gallery.objects.create(name="Test Gallery")
        cls.picture = Picture.objects.create(
            name="Test Picture",
            image=filename,
            gallery=cls.gallery,
        )

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_form_has_multipart_enctype(self):
        response = self.client.get(
            reverse("admin:admin_views_gallery_change", args=(self.gallery.id,))
        )
        self.assertIs(response.context["has_file_field"], True)
        self.assertContains(response, MULTIPART_ENCTYPE)

    def test_inline_file_upload_edit_validation_error_post(self):
        """
        Inline file uploads correctly display prior data (#10002).
        """
        post_data = {
            "name": "Test Gallery",
            "pictures-TOTAL_FORMS": "2",
            "pictures-INITIAL_FORMS": "1",
            "pictures-MAX_NUM_FORMS": "0",
            "pictures-0-id": str(self.picture.id),
            "pictures-0-gallery": str(self.gallery.id),
            "pictures-0-name": "Test Picture",
            "pictures-0-image": "",
            "pictures-1-id": "",
            "pictures-1-gallery": str(self.gallery.id),
            "pictures-1-name": "Test Picture 2",
            "pictures-1-image": "",
        }
        response = self.client.post(
            reverse("admin:admin_views_gallery_change", args=(self.gallery.id,)),
            post_data,
        )
        self.assertContains(response, b"Currently")


@override_settings(ROOT_URLCONF="admin_views.urls")
class AdminInlineTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="super", password="secret", email="super@example.com"
        )
        cls.collector = Collector.objects.create(pk=1, name="John Fowles")

    def setUp(self):
        self.post_data = {
            "name": "Test Name",
            "widget_set-TOTAL_FORMS": "3",
            "widget_set-INITIAL_FORMS": "0",
            "widget_set-MAX_NUM_FORMS": "0",
            "widget_set-0-id": "",
            "widget_set-0-owner": "1",
            "widget_set-0-name": "",
            "widget_set-1-id": "",
            "widget_set-1-owner": "1",
            "widget_set-1-name": "",
            "widget_set-2-id": "",
            "widget_set-2-owner": "1",
            "widget_set-2-name": "",
            "doohickey_set-TOTAL_FORMS": "3",
            "doohickey_set-INITIAL_FORMS": "0",
            "doohickey_set-MAX_NUM_FORMS": "0",
            "doohickey_set-0-owner": "1",
            "doohickey_set-0-code": "",
            "doohickey_set-0-name": "",
            "doohickey_set-1-owner": "1",
            "doohickey_set-1-code": "",
            "doohickey_set-1-name": "",
            "doohickey_set-2-owner": "1",
            "doohickey_set-2-code": "",
            "doohickey_set-2-name": "",
            "grommet_set-TOTAL_FORMS": "3",
            "grommet_set-INITIAL_FORMS": "0",
            "grommet_set-MAX_NUM_FORMS": "0",
            "grommet_set-0-code": "",
            "grommet_set-0-owner": "1",
            "grommet_set-0-name": "",
            "grommet_set-1-code": "",
            "grommet_set-1-owner": "1",
            "grommet_set-1-name": "",
            "grommet_set-2-code": "",
            "grommet_set-2-owner": "1",
            "grommet_set-2-name": "",
            "whatsit_set-TOTAL_FORMS": "3",
            "whatsit_set-INITIAL_FORMS": "0",
            "whatsit_set-MAX_NUM_FORMS": "0",
            "whatsit_set-0-owner": "1",
            "whatsit_set-0-index": "",
            "whatsit_set-0-name": "",
            "whatsit_set-1-owner": "1",
            "whatsit_set-1-index": "",
            "whatsit_set-1-name": "",
            "whatsit_set-2-owner": "1",
            "whatsit_set-2-index": "",
            "whatsit_set-2-name": "",
            "fancydoodad_set-TOTAL_FORMS": "3",
            "fancydoodad_set-INITIAL_FORMS": "0",
            "fancydoodad_set-MAX_NUM_FORMS": "0",
            "fancydoodad_set-0-doodad_ptr": "",
            "fancydoodad_set-0-owner": "1",
            "fancydoodad_set-0-name": "",
            "fancydoodad_set-0-expensive": "on",
            "fancydoodad_set-1-doodad_ptr": "",
            "fancydoodad_set-1-owner": "1",
            "fancydoodad_set-1-name": "",
            "fancydoodad_set-1-expensive": "on",
            "fancydoodad_set-2-doodad_ptr": "",
            "fancydoodad_set-2-owner": "1",
            "fancydoodad_set-2-name": "",
            "fancydoodad_set-2-expensive": "on",
            "category_set-TOTAL_FORMS": "3",
            "category_set-INITIAL_FORMS": "0",
            "category_set-MAX_NUM_FORMS": "0",
            "category_set-0-order": "",
            "category_set-0-id": "",
            "category_set-0-collector": "1",
            "category_set-1-order": "",
            "category_set-1-id": "",
            "category_set-1-collector": "1",
            "category_set-2-order": "",
            "category_set-2-id": "",
            "category_set-2-collector": "1",
        }

        self.client.force_login(self.superuser)

    def test_simple_inline(self):
        "A simple model can be saved as inlines"
        # First add a new inline
        self.post_data["widget_set-0-name"] = "Widget 1"
        collector_url = reverse(
            "admin:admin_views_collector_change", args=(self.collector.pk,)
        )
        response = self.client.post(collector_url, self.post_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Widget.objects.count(), 1)
        self.assertEqual(Widget.objects.all()[0].name, "Widget 1")
        widget_id = Widget.objects.all()[0].id

        # The PK link exists on the rendered form
        response = self.client.get(collector_url)
        self.assertContains(response, 'name="widget_set-0-id"')

        # No file or image fields, no enctype on the forms
        self.assertIs(response.context["has_file_field"], False)
        self.assertNotContains(response, MULTIPART_ENCTYPE)

        # Now resave that inline
        self.post_data["widget_set-INITIAL_FORMS"] = "1"
        self.post_data["widget_set-0-id"] = str(widget_id)
        self.post_data["widget_set-0-name"] = "Widget 1"
        response = self.client.post(collector_url, self.post_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Widget.objects.count(), 1)
        self.assertEqual(Widget.objects.all()[0].name, "Widget 1")

        # Now modify that inline
        self.post_data["widget_set-INITIAL_FORMS"] = "1"
        self.post_data["widget_set-0-id"] = str(widget_id)
        self.post_data["widget_set-0-name"] = "Widget 1 Updated"
        response = self.client.post(collector_url, self.post_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Widget.objects.count(), 1)
        self.assertEqual(Widget.objects.all()[0].name, "Widget 1 Updated")

    def test_explicit_autofield_inline(self):
        """
        A model with an explicit autofield primary key can be saved as inlines.
        """
        # First add a new inline
        self.post_data["grommet_set-0-name"] = "Grommet 1"
        collector_url = reverse(
            "admin:admin_views_collector_change", args=(self.collector.pk,)
        )
        response = self.client.post(collector_url, self.post_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Grommet.objects.count(), 1)
        self.assertEqual(Grommet.objects.all()[0].name, "Grommet 1")

        # The PK link exists on the rendered form
        response = self.client.get(collector_url)
        self.assertContains(response, 'name="grommet_set-0-code"')

        # Now resave that inline
        self.post_data["grommet_set-INITIAL_FORMS"] = "1"
        self.post_data["grommet_set-0-code"] = str(Grommet.objects.all()[0].code)
        self.post_data["grommet_set-0-name"] = "Grommet 1"
        response = self.client.post(collector_url, self.post_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Grommet.objects.count(), 1)
        self.assertEqual(Grommet.objects.all()[0].name, "Grommet 1")

        # Now modify that inline
        self.post_data["grommet_set-INITIAL_FORMS"] = "1"
        self.post_data["grommet_set-0-code"] = str(Grommet.objects.all()[0].code)
        self.post_data["grommet_set-0-name"] = "Grommet 1 Updated"
        response = self.client.post(collector_url, self.post_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Grommet.objects.count(), 1)
        self.assertEqual(Grommet.objects.all()[0].name, "Grommet 1 Updated")

    def test_char_pk_inline(self):
        "A model with a character PK can be saved as inlines. Regression for #10992"
        # First add a new inline
        self.post_data["doohickey_set-0-code"] = "DH1"
        self.post_data["doohickey_set-0-name"] = "Doohickey 1"
        collector_url = reverse(
            "admin:admin_views_collector_change", args=(self.collector.pk,)
        )
        response = self.client.post(collector_url, self.post_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(DooHickey.objects.count(), 1)
        self.assertEqual(DooHickey.objects.all()[0].name, "Doohickey 1")

        # The PK link exists on the rendered form
        response = self.client.get(collector_url)
        self.assertContains(response, 'name="doohickey_set-0-code"')

        # Now resave that inline
        self.post_data["doohickey_set-INITIAL_FORMS"] = "1"
        self.post_data["doohickey_set-0-code"] = "DH1"
        self.post_data["doohickey_set-0-name"] = "Doohickey 1"
        response = self.client.post(collector_url, self.post_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(DooHickey.objects.count(), 1)
        self.assertEqual(DooHickey.objects.all()[0].name, "Doohickey 1")

        # Now modify that inline
        self.post_data["doohickey_set-INITIAL_FORMS"] = "1"
        self.post_data["doohickey_set-0-code"] = "DH1"
        self.post_data["doohickey_set-0-name"] = "Doohickey 1 Updated"
        response = self.client.post(collector_url, self.post_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(DooHickey.objects.count(), 1)
        self.assertEqual(DooHickey.objects.all()[0].name, "Doohickey 1 Updated")

    def test_integer_pk_inline(self):
        "A model with an integer PK can be saved as inlines. Regression for #10992"
        # First add a new inline
        self.post_data["whatsit_set-0-index"] = "42"
        self.post_data["whatsit_set-0-name"] = "Whatsit 1"
        collector_url = reverse(
            "admin:admin_views_collector_change", args=(self.collector.pk,)
        )
        response = self.client.post(collector_url, self.post_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Whatsit.objects.count(), 1)
        self.assertEqual(Whatsit.objects.all()[0].name, "Whatsit 1")

        # The PK link exists on the rendered form
        response = self.client.get(collector_url)
        self.assertContains(response, 'name="whatsit_set-0-index"')

        # Now resave that inline
        self.post_data["whatsit_set-INITIAL_FORMS"] = "1"
        self.post_data["whatsit_set-0-index"] = "42"
        self.post_data["whatsit_set-0-name"] = "Whatsit 1"
        response = self.client.post(collector_url, self.post_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Whatsit.objects.count(), 1)
        self.assertEqual(Whatsit.objects.all()[0].name, "Whatsit 1")

        # Now modify that inline
        self.post_data["whatsit_set-INITIAL_FORMS"] = "1"
        self.post_data["whatsit_set-0-index"] = "42"
        self.post_data["whatsit_set-0-name"] = "Whatsit 1 Updated"
        response = self.client.post(collector_url, self.post_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Whatsit.objects.count(), 1)
        self.assertEqual(Whatsit.objects.all()[0].name, "Whatsit 1 Updated")

    def test_inherited_inline(self):
        "An inherited model can be saved as inlines. Regression for #11042"
        # First add a new inline
        self.post_data["fancydoodad_set-0-name"] = "Fancy Doodad 1"
        collector_url = reverse(
            "admin:admin_views_collector_change", args=(self.collector.pk,)
        )
        response = self.client.post(collector_url, self.post_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(FancyDoodad.objects.count(), 1)
        self.assertEqual(FancyDoodad.objects.all()[0].name, "Fancy Doodad 1")
        doodad_pk = FancyDoodad.objects.all()[0].pk

        # The PK link exists on the rendered form
        response = self.client.get(collector_url)
        self.assertContains(response, 'name="fancydoodad_set-0-doodad_ptr"')

        # Now resave that inline
        self.post_data["fancydoodad_set-INITIAL_FORMS"] = "1"
        self.post_data["fancydoodad_set-0-doodad_ptr"] = str(doodad_pk)
        self.post_data["fancydoodad_set-0-name"] = "Fancy Doodad 1"
        response = self.client.post(collector_url, self.post_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(FancyDoodad.objects.count(), 1)
        self.assertEqual(FancyDoodad.objects.all()[0].name, "Fancy Doodad 1")

        # Now modify that inline
        self.post_data["fancydoodad_set-INITIAL_FORMS"] = "1"
        self.post_data["fancydoodad_set-0-doodad_ptr"] = str(doodad_pk)
        self.post_data["fancydoodad_set-0-name"] = "Fancy Doodad 1 Updated"
        response = self.client.post(collector_url, self.post_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(FancyDoodad.objects.count(), 1)
        self.assertEqual(FancyDoodad.objects.all()[0].name, "Fancy Doodad 1 Updated")

    def test_ordered_inline(self):
        """
        An inline with an editable ordering fields is updated correctly.
        """
        # Create some objects with an initial ordering
        Category.objects.create(id=1, order=1, collector=self.collector)
        Category.objects.create(id=2, order=2, collector=self.collector)
        Category.objects.create(id=3, order=0, collector=self.collector)
        Category.objects.create(id=4, order=0, collector=self.collector)

        # NB: The order values must be changed so that the items are reordered.
        self.post_data.update(
            {
                "name": "Frederick Clegg",
                "category_set-TOTAL_FORMS": "7",
                "category_set-INITIAL_FORMS": "4",
                "category_set-MAX_NUM_FORMS": "0",
                "category_set-0-order": "14",
                "category_set-0-id": "1",
                "category_set-0-collector": "1",
                "category_set-1-order": "13",
                "category_set-1-id": "2",
                "category_set-1-collector": "1",
                "category_set-2-order": "1",
                "category_set-2-id": "3",
                "category_set-2-collector": "1",
                "category_set-3-order": "0",
                "category_set-3-id": "4",
                "category_set-3-collector": "1",
                "category_set-4-order": "",
                "category_set-4-id": "",
                "category_set-4-collector": "1",
                "category_set-5-order": "",
                "category_set-5-id": "",
                "category_set-5-collector": "1",
                "category_set-6-order": "",
                "category_set-6-id": "",
                "category_set-6-collector": "1",
            }
        )
        collector_url = reverse(
            "admin:admin_views_collector_change", args=(self.collector.pk,)
        )
        response = self.client.post(collector_url, self.post_data)
        # Successful post will redirect
        self.assertEqual(response.status_code, 302)

        # The order values have been applied to the right objects
        self.assertEqual(self.collector.category_set.count(), 4)
        self.assertEqual(Category.objects.get(id=1).order, 14)
        self.assertEqual(Category.objects.get(id=2).order, 13)
        self.assertEqual(Category.objects.get(id=3).order, 1)
        self.assertEqual(Category.objects.get(id=4).order, 0)


@override_settings(ROOT_URLCONF="admin_views.urls")
class NeverCacheTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="super", password="secret", email="super@example.com"
        )
        cls.s1 = Section.objects.create(name="Test section")

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_admin_index(self):
        "Check the never-cache status of the main index"
        response = self.client.get(reverse("admin:index"))
        self.assertEqual(get_max_age(response), 0)

    def test_app_index(self):
        "Check the never-cache status of an application index"
        response = self.client.get(reverse("admin:app_list", args=("admin_views",)))
        self.assertEqual(get_max_age(response), 0)

    def test_model_index(self):
        "Check the never-cache status of a model index"
        response = self.client.get(reverse("admin:admin_views_fabric_changelist"))
        self.assertEqual(get_max_age(response), 0)

    def test_model_add(self):
        "Check the never-cache status of a model add page"
        response = self.client.get(reverse("admin:admin_views_fabric_add"))
        self.assertEqual(get_max_age(response), 0)

    def test_model_view(self):
        "Check the never-cache status of a model edit page"
        response = self.client.get(
            reverse("admin:admin_views_section_change", args=(self.s1.pk,))
        )
        self.assertEqual(get_max_age(response), 0)

    def test_model_history(self):
        "Check the never-cache status of a model history page"
        response = self.client.get(
            reverse("admin:admin_views_section_history", args=(self.s1.pk,))
        )
        self.assertEqual(get_max_age(response), 0)

    def test_model_delete(self):
        "Check the never-cache status of a model delete page"
        response = self.client.get(
            reverse("admin:admin_views_section_delete", args=(self.s1.pk,))
        )
        self.assertEqual(get_max_age(response), 0)

    def test_login(self):
        "Check the never-cache status of login views"
        self.client.logout()
        response = self.client.get(reverse("admin:index"))
        self.assertEqual(get_max_age(response), 0)

    def test_logout(self):
        "Check the never-cache status of logout view"
        response = self.client.post(reverse("admin:logout"))
        self.assertEqual(get_max_age(response), 0)

    def test_password_change(self):
        "Check the never-cache status of the password change view"
        self.client.logout()
        response = self.client.get(reverse("admin:password_change"))
        self.assertIsNone(get_max_age(response))

    def test_password_change_done(self):
        "Check the never-cache status of the password change done view"
        response = self.client.get(reverse("admin:password_change_done"))
        self.assertIsNone(get_max_age(response))

    def test_JS_i18n(self):
        "Check the never-cache status of the JavaScript i18n view"
        response = self.client.get(reverse("admin:jsi18n"))
        self.assertIsNone(get_max_age(response))


@override_settings(ROOT_URLCONF="admin_views.urls")
class PrePopulatedTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="super", password="secret", email="super@example.com"
        )
        cls.p1 = PrePopulatedPost.objects.create(
            title="A Long Title", published=True, slug="a-long-title"
        )

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_prepopulated_on(self):
        response = self.client.get(reverse("admin:admin_views_prepopulatedpost_add"))
        self.assertContains(response, "&quot;id&quot;: &quot;#id_slug&quot;")
        self.assertContains(
            response, "&quot;dependency_ids&quot;: [&quot;#id_title&quot;]"
        )
        self.assertContains(
            response,
            "&quot;id&quot;: &quot;#id_prepopulatedsubpost_set-0-subslug&quot;",
        )

    def test_prepopulated_off(self):
        response = self.client.get(
            reverse("admin:admin_views_prepopulatedpost_change", args=(self.p1.pk,))
        )
        self.assertContains(response, "A Long Title")
        self.assertNotContains(response, "&quot;id&quot;: &quot;#id_slug&quot;")
        self.assertNotContains(
            response, "&quot;dependency_ids&quot;: [&quot;#id_title&quot;]"
        )
        self.assertNotContains(
            response,
            "&quot;id&quot;: &quot;#id_prepopulatedsubpost_set-0-subslug&quot;",
        )

    @override_settings(USE_THOUSAND_SEPARATOR=True)
    def test_prepopulated_maxlength_localized(self):
        """
        Regression test for #15938: if USE_THOUSAND_SEPARATOR is set, make sure
        that maxLength (in the JavaScript) is rendered without separators.
        """
        response = self.client.get(
            reverse("admin:admin_views_prepopulatedpostlargeslug_add")
        )
        self.assertContains(response, "&quot;maxLength&quot;: 1000")  # instead of 1,000

    def test_view_only_add_form(self):
        """
        PrePopulatedPostReadOnlyAdmin.prepopulated_fields includes 'slug'
        which is present in the add view, even if the
        ModelAdmin.has_change_permission() returns False.
        """
        response = self.client.get(reverse("admin7:admin_views_prepopulatedpost_add"))
        self.assertContains(response, "data-prepopulated-fields=")
        self.assertContains(response, "&quot;id&quot;: &quot;#id_slug&quot;")

    def test_view_only_change_form(self):
        """
        PrePopulatedPostReadOnlyAdmin.prepopulated_fields includes 'slug'. That
        doesn't break a view-only change view.
        """
        response = self.client.get(
            reverse("admin7:admin_views_prepopulatedpost_change", args=(self.p1.pk,))
        )
        self.assertContains(response, 'data-prepopulated-fields="[]"')
        self.assertContains(response, '<div class="readonly">%s</div>' % self.p1.slug)


def _clean_sidebar_state(driver):
    driver.execute_script("localStorage.removeItem('django.admin.navSidebarIsOpen')")


@override_settings(ROOT_URLCONF="admin_views.urls")
class SeleniumTests(AdminSeleniumTestCase):
    available_apps = ["admin_views"] + AdminSeleniumTestCase.available_apps

    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="super", password="secret", email="super@example.com"
        )
        self.p1 = PrePopulatedPost.objects.create(
            title="A Long Title", published=True, slug="a-long-title"
        )

    @screenshot_cases(["desktop_size", "mobile_size", "rtl", "dark", "high_contrast"])
    def test_login_button_centered(self):
        from selenium.webdriver.common.by import By

        self.selenium.get(self.live_server_url + reverse("admin:login"))
        button = self.selenium.find_element(By.CSS_SELECTOR, ".submit-row input")
        offset_left = button.get_property("offsetLeft")
        offset_right = button.get_property("offsetParent").get_property(
            "offsetWidth"
        ) - (offset_left + button.get_property("offsetWidth"))
        # Use assertAlmostEqual to avoid pixel rounding errors.
        self.assertAlmostEqual(offset_left, offset_right, delta=3)
        self.take_screenshot("login")

    def test_prepopulated_fields(self):
        """
        The JavaScript-automated prepopulated fields work with the main form
        and with stacked and tabular inlines.
        Refs #13068, #9264, #9983, #9784.
        """
        from selenium.webdriver import ActionChains
        from selenium.webdriver.common.by import By

        self.admin_login(
            username="super", password="secret", login_url=reverse("admin:index")
        )
        self.selenium.get(
            self.live_server_url + reverse("admin:admin_views_mainprepopulated_add")
        )
        self.wait_for(".select2")

        # Main form ----------------------------------------------------------
        self.selenium.find_element(By.ID, "id_pubdate").send_keys("2012-02-18")
        status = self.selenium.find_element(By.ID, "id_status")
        ActionChains(self.selenium).move_to_element(status).click(status).perform()
        self.select_option("#id_status", "option two")
        self.selenium.find_element(By.ID, "id_name").send_keys(
            " the mAin nÀMë and it's awεšomeıııİ"
        )
        slug1 = self.selenium.find_element(By.ID, "id_slug1").get_attribute("value")
        slug2 = self.selenium.find_element(By.ID, "id_slug2").get_attribute("value")
        slug3 = self.selenium.find_element(By.ID, "id_slug3").get_attribute("value")
        self.assertEqual(slug1, "the-main-name-and-its-awesomeiiii-2012-02-18")
        self.assertEqual(slug2, "option-two-the-main-name-and-its-awesomeiiii")
        self.assertEqual(
            slug3, "the-main-n\xe0m\xeb-and-its-aw\u03b5\u0161ome\u0131\u0131\u0131i"
        )

        # Stacked inlines with fieldsets -------------------------------------
        # Initial inline
        self.selenium.find_element(
            By.ID, "id_relatedprepopulated_set-0-pubdate"
        ).send_keys("2011-12-17")
        status = self.selenium.find_element(
            By.ID, "id_relatedprepopulated_set-0-status"
        )
        ActionChains(self.selenium).move_to_element(status).click(status).perform()
        self.select_option("#id_relatedprepopulated_set-0-status", "option one")
        self.selenium.find_element(
            By.ID, "id_relatedprepopulated_set-0-name"
        ).send_keys(" here is a sŤāÇkeð   inline !  ")
        slug1 = self.selenium.find_element(
            By.ID, "id_relatedprepopulated_set-0-slug1"
        ).get_attribute("value")
        slug2 = self.selenium.find_element(
            By.ID, "id_relatedprepopulated_set-0-slug2"
        ).get_attribute("value")
        self.assertEqual(slug1, "here-is-a-stacked-inline-2011-12-17")
        self.assertEqual(slug2, "option-one-here-is-a-stacked-inline")
        initial_select2_inputs = self.selenium.find_elements(
            By.CLASS_NAME, "select2-selection"
        )
        # Inline formsets have empty/invisible forms.
        # Only the 4 visible select2 inputs are initialized.
        num_initial_select2_inputs = len(initial_select2_inputs)
        self.assertEqual(num_initial_select2_inputs, 4)

        # Add an inline
        self.selenium.find_elements(By.LINK_TEXT, "Add another Related prepopulated")[
            0
        ].click()
        self.assertEqual(
            len(self.selenium.find_elements(By.CLASS_NAME, "select2-selection")),
            num_initial_select2_inputs + 2,
        )
        self.selenium.find_element(
            By.ID, "id_relatedprepopulated_set-1-pubdate"
        ).send_keys("1999-01-25")
        status = self.selenium.find_element(
            By.ID, "id_relatedprepopulated_set-1-status"
        )
        ActionChains(self.selenium).move_to_element(status).click(status).perform()
        self.select_option("#id_relatedprepopulated_set-1-status", "option two")
        self.selenium.find_element(
            By.ID, "id_relatedprepopulated_set-1-name"
        ).send_keys(
            " now you haVe anöther   sŤāÇkeð  inline with a very ... "
            "loooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooog "
            "text... "
        )
        slug1 = self.selenium.find_element(
            By.ID, "id_relatedprepopulated_set-1-slug1"
        ).get_attribute("value")
        slug2 = self.selenium.find_element(
            By.ID, "id_relatedprepopulated_set-1-slug2"
        ).get_attribute("value")
        # 50 characters maximum for slug1 field
        self.assertEqual(slug1, "now-you-have-another-stacked-inline-with-a-very-lo")
        # 60 characters maximum for slug2 field
        self.assertEqual(
            slug2, "option-two-now-you-have-another-stacked-inline-with-a-very-l"
        )

        # Tabular inlines ----------------------------------------------------
        # Initial inline
        status = self.selenium.find_element(
            By.ID, "id_relatedprepopulated_set-2-0-status"
        )
        ActionChains(self.selenium).move_to_element(status).click(status).perform()
        self.selenium.find_element(
            By.ID, "id_relatedprepopulated_set-2-0-pubdate"
        ).send_keys("1234-12-07")
        self.select_option("#id_relatedprepopulated_set-2-0-status", "option two")
        self.selenium.find_element(
            By.ID, "id_relatedprepopulated_set-2-0-name"
        ).send_keys("And now, with a tÃbűlaŘ inline !!!")
        slug1 = self.selenium.find_element(
            By.ID, "id_relatedprepopulated_set-2-0-slug1"
        ).get_attribute("value")
        slug2 = self.selenium.find_element(
            By.ID, "id_relatedprepopulated_set-2-0-slug2"
        ).get_attribute("value")
        self.assertEqual(slug1, "and-now-with-a-tabular-inline-1234-12-07")
        self.assertEqual(slug2, "option-two-and-now-with-a-tabular-inline")

        # Add an inline
        # Button may be outside the browser frame.
        element = self.selenium.find_elements(
            By.LINK_TEXT, "Add another Related prepopulated"
        )[1]
        self.selenium.execute_script("window.scrollTo(0, %s);" % element.location["y"])
        element.click()
        self.assertEqual(
            len(self.selenium.find_elements(By.CLASS_NAME, "select2-selection")),
            num_initial_select2_inputs + 4,
        )
        self.selenium.find_element(
            By.ID, "id_relatedprepopulated_set-2-1-pubdate"
        ).send_keys("1981-08-22")
        status = self.selenium.find_element(
            By.ID, "id_relatedprepopulated_set-2-1-status"
        )
        ActionChains(self.selenium).move_to_element(status).click(status).perform()
        self.select_option("#id_relatedprepopulated_set-2-1-status", "option one")
        self.selenium.find_element(
            By.ID, "id_relatedprepopulated_set-2-1-name"
        ).send_keys(r'tÃbűlaŘ inline with ignored ;"&*^\%$#@-/`~ characters')
        slug1 = self.selenium.find_element(
            By.ID, "id_relatedprepopulated_set-2-1-slug1"
        ).get_attribute("value")
        slug2 = self.selenium.find_element(
            By.ID, "id_relatedprepopulated_set-2-1-slug2"
        ).get_attribute("value")
        self.assertEqual(slug1, "tabular-inline-with-ignored-characters-1981-08-22")
        self.assertEqual(slug2, "option-one-tabular-inline-with-ignored-characters")
        # Add an inline without an initial inline.
        # The button is outside of the browser frame.
        self.selenium.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        self.selenium.find_elements(By.LINK_TEXT, "Add another Related prepopulated")[
            2
        ].click()
        self.assertEqual(
            len(self.selenium.find_elements(By.CLASS_NAME, "select2-selection")),
            num_initial_select2_inputs + 6,
        )
        # Stacked Inlines without fieldsets ----------------------------------
        # Initial inline.
        row_id = "id_relatedprepopulated_set-4-0-"
        self.selenium.find_element(By.ID, f"{row_id}pubdate").send_keys("2011-12-12")
        status = self.selenium.find_element(By.ID, f"{row_id}status")
        ActionChains(self.selenium).move_to_element(status).click(status).perform()
        self.select_option(f"#{row_id}status", "option one")
        self.selenium.find_element(By.ID, f"{row_id}name").send_keys(
            " sŤāÇkeð  inline !  "
        )
        slug1 = self.selenium.find_element(By.ID, f"{row_id}slug1").get_attribute(
            "value"
        )
        slug2 = self.selenium.find_element(By.ID, f"{row_id}slug2").get_attribute(
            "value"
        )
        self.assertEqual(slug1, "stacked-inline-2011-12-12")
        self.assertEqual(slug2, "option-one")
        # Add inline.
        self.selenium.find_elements(
            By.LINK_TEXT,
            "Add another Related prepopulated",
        )[3].click()
        row_id = "id_relatedprepopulated_set-4-1-"
        self.selenium.find_element(By.ID, f"{row_id}pubdate").send_keys("1999-01-20")
        status = self.selenium.find_element(By.ID, f"{row_id}status")
        ActionChains(self.selenium).move_to_element(status).click(status).perform()
        self.select_option(f"#{row_id}status", "option two")
        self.selenium.find_element(By.ID, f"{row_id}name").send_keys(
            " now you haVe anöther   sŤāÇkeð  inline with a very loooong "
        )
        slug1 = self.selenium.find_element(By.ID, f"{row_id}slug1").get_attribute(
            "value"
        )
        slug2 = self.selenium.find_element(By.ID, f"{row_id}slug2").get_attribute(
            "value"
        )
        self.assertEqual(slug1, "now-you-have-another-stacked-inline-with-a-very-lo")
        self.assertEqual(slug2, "option-two")

        # Save and check that everything is properly stored in the database
        with self.wait_page_loaded():
            self.selenium.find_element(By.XPATH, '//input[@value="Save"]').click()
        self.assertEqual(MainPrepopulated.objects.count(), 1)
        MainPrepopulated.objects.get(
            name=" the mAin nÀMë and it's awεšomeıııİ",
            pubdate="2012-02-18",
            status="option two",
            slug1="the-main-name-and-its-awesomeiiii-2012-02-18",
            slug2="option-two-the-main-name-and-its-awesomeiiii",
            slug3="the-main-nàmë-and-its-awεšomeıııi",
        )
        self.assertEqual(RelatedPrepopulated.objects.count(), 6)
        RelatedPrepopulated.objects.get(
            name=" here is a sŤāÇkeð   inline !  ",
            pubdate="2011-12-17",
            status="option one",
            slug1="here-is-a-stacked-inline-2011-12-17",
            slug2="option-one-here-is-a-stacked-inline",
        )
        RelatedPrepopulated.objects.get(
            # 75 characters in name field
            name=(
                " now you haVe anöther   sŤāÇkeð  inline with a very ... "
                "loooooooooooooooooo"
            ),
            pubdate="1999-01-25",
            status="option two",
            slug1="now-you-have-another-stacked-inline-with-a-very-lo",
            slug2="option-two-now-you-have-another-stacked-inline-with-a-very-l",
        )
        RelatedPrepopulated.objects.get(
            name="And now, with a tÃbűlaŘ inline !!!",
            pubdate="1234-12-07",
            status="option two",
            slug1="and-now-with-a-tabular-inline-1234-12-07",
            slug2="option-two-and-now-with-a-tabular-inline",
        )
        RelatedPrepopulated.objects.get(
            name=r'tÃbűlaŘ inline with ignored ;"&*^\%$#@-/`~ characters',
            pubdate="1981-08-22",
            status="option one",
            slug1="tabular-inline-with-ignored-characters-1981-08-22",
            slug2="option-one-tabular-inline-with-ignored-characters",
        )

    def test_populate_existing_object(self):
        """
        The prepopulation works for existing objects too, as long as
        the original field is empty (#19082).
        """
        from selenium.webdriver.common.by import By

        # Slugs are empty to start with.
        item = MainPrepopulated.objects.create(
            name=" this is the mAin nÀMë",
            pubdate="2012-02-18",
            status="option two",
            slug1="",
            slug2="",
        )
        self.admin_login(
            username="super", password="secret", login_url=reverse("admin:index")
        )

        object_url = self.live_server_url + reverse(
            "admin:admin_views_mainprepopulated_change", args=(item.id,)
        )

        self.selenium.get(object_url)
        self.selenium.find_element(By.ID, "id_name").send_keys(" the best")

        # The slugs got prepopulated since they were originally empty
        slug1 = self.selenium.find_element(By.ID, "id_slug1").get_attribute("value")
        slug2 = self.selenium.find_element(By.ID, "id_slug2").get_attribute("value")
        self.assertEqual(slug1, "this-is-the-main-name-the-best-2012-02-18")
        self.assertEqual(slug2, "option-two-this-is-the-main-name-the-best")

        # Save the object
        with self.wait_page_loaded():
            self.selenium.find_element(By.XPATH, '//input[@value="Save"]').click()

        self.selenium.get(object_url)
        self.selenium.find_element(By.ID, "id_name").send_keys(" hello")

        # The slugs got prepopulated didn't change since they were originally not empty
        slug1 = self.selenium.find_element(By.ID, "id_slug1").get_attribute("value")
        slug2 = self.selenium.find_element(By.ID, "id_slug2").get_attribute("value")
        self.assertEqual(slug1, "this-is-the-main-name-the-best-2012-02-18")
        self.assertEqual(slug2, "option-two-this-is-the-main-name-the-best")

    @screenshot_cases(["desktop_size", "mobile_size", "dark", "high_contrast"])
    def test_collapsible_fieldset(self):
        """
        The 'collapse' class in fieldsets definition allows to
        show/hide the appropriate field section.
        """
        from selenium.webdriver.common.by import By

        self.admin_login(
            username="super", password="secret", login_url=reverse("admin:index")
        )
        self.selenium.get(
            self.live_server_url + reverse("admin:admin_views_article_add")
        )
        self.assertFalse(self.selenium.find_element(By.ID, "id_title").is_displayed())
        self.take_screenshot("collapsed")
        self.selenium.find_elements(By.TAG_NAME, "summary")[0].click()
        self.assertTrue(self.selenium.find_element(By.ID, "id_title").is_displayed())
        self.take_screenshot("expanded")

    @screenshot_cases(["desktop_size", "mobile_size", "rtl", "dark", "high_contrast"])
    def test_selectbox_height_collapsible_fieldset(self):
        from selenium.webdriver.common.by import By

        self.admin_login(
            username="super",
            password="secret",
            login_url=reverse("admin7:index"),
        )
        url = self.live_server_url + reverse("admin7:admin_views_pizza_add")
        self.selenium.get(url)
        self.selenium.find_elements(By.TAG_NAME, "summary")[0].click()
        from_filter_box = self.selenium.find_element(By.ID, "id_toppings_filter")
        from_box = self.selenium.find_element(By.ID, "id_toppings_from")
        to_filter_box = self.selenium.find_element(By.ID, "id_toppings_filter_selected")
        to_box = self.selenium.find_element(By.ID, "id_toppings_to")
        self.assertEqual(
            (
                to_filter_box.get_property("offsetHeight")
                + to_box.get_property("offsetHeight")
            ),
            (
                from_filter_box.get_property("offsetHeight")
                + from_box.get_property("offsetHeight")
            ),
        )
        self.take_screenshot("selectbox-collapsible")

    @screenshot_cases(["desktop_size", "mobile_size", "rtl", "dark", "high_contrast"])
    def test_selectbox_height_not_collapsible_fieldset(self):
        from selenium.webdriver.common.by import By

        self.admin_login(
            username="super",
            password="secret",
            login_url=reverse("admin7:index"),
        )
        url = self.live_server_url + reverse("admin7:admin_views_question_add")
        self.selenium.get(url)
        from_filter_box = self.selenium.find_element(
            By.ID, "id_related_questions_filter"
        )
        from_box = self.selenium.find_element(By.ID, "id_related_questions_from")
        to_filter_box = self.selenium.find_element(
            By.ID, "id_related_questions_filter_selected"
        )
        to_box = self.selenium.find_element(By.ID, "id_related_questions_to")
        self.assertEqual(
            (
                to_filter_box.get_property("offsetHeight")
                + to_box.get_property("offsetHeight")
            ),
            (
                from_filter_box.get_property("offsetHeight")
                + from_box.get_property("offsetHeight")
            ),
        )
        self.take_screenshot("selectbox-non-collapsible")

    @screenshot_cases(["desktop_size", "mobile_size", "rtl", "dark", "high_contrast"])
    def test_selectbox_selected_rows(self):
        from selenium.webdriver import ActionChains
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys

        self.admin_login(
            username="super", password="secret", login_url=reverse("admin:index")
        )
        # Create a new user to ensure that no extra permissions have been set.
        user = User.objects.create_user(username="new", password="newuser")
        url = self.live_server_url + reverse("admin:auth_user_change", args=[user.id])
        self.selenium.get(url)

        # Scroll to the User permissions section.
        user_permissions = self.selenium.find_element(
            By.CSS_SELECTOR, "#id_user_permissions_from"
        )
        ActionChains(self.selenium).move_to_element(user_permissions).perform()
        self.take_screenshot("selectbox-available-perms-none-selected")

        # Select multiple permissions from the "Available" list.
        ct = ContentType.objects.get_for_model(Permission)
        perms = list(Permission.objects.filter(content_type=ct))
        for perm in perms:
            elem = self.selenium.find_element(
                By.CSS_SELECTOR, f"#id_user_permissions_from option[value='{perm.id}']"
            )
            ActionChains(self.selenium).key_down(Keys.CONTROL).click(elem).key_up(
                Keys.CONTROL
            ).perform()

        # Move focus to other element.
        self.selenium.find_element(
            By.CSS_SELECTOR, "#id_user_permissions_input"
        ).click()
        self.take_screenshot("selectbox-available-perms-some-selected")

        # Move permissions to the "Chosen" list, but none is selected yet.
        self.selenium.find_element(
            By.CSS_SELECTOR, "#id_user_permissions_add_link"
        ).click()
        self.take_screenshot("selectbox-chosen-perms-none-selected")

        # Select some permissions from the "Chosen" list.
        for perm in [perms[0], perms[-1]]:
            elem = self.selenium.find_element(
                By.CSS_SELECTOR, f"#id_user_permissions_to option[value='{perm.id}']"
            )
            ActionChains(self.selenium).key_down(Keys.CONTROL).click(elem).key_up(
                Keys.CONTROL
            ).perform()

        # Move focus to other element.
        self.selenium.find_element(
            By.CSS_SELECTOR, "#id_user_permissions_selected_input"
        ).click()
        self.take_screenshot("selectbox-chosen-perms-some-selected")

    @screenshot_cases(["desktop_size", "mobile_size", "rtl", "dark", "high_contrast"])
    def test_first_field_focus(self):
        """JavaScript-assisted auto-focus on first usable form field."""
        from selenium.webdriver.common.by import By

        # First form field has a single widget
        self.admin_login(
            username="super", password="secret", login_url=reverse("admin:index")
        )
        with self.wait_page_loaded():
            self.selenium.get(
                self.live_server_url + reverse("admin:admin_views_picture_add")
            )
        self.assertEqual(
            self.selenium.switch_to.active_element,
            self.selenium.find_element(By.ID, "id_name"),
        )
        self.take_screenshot("focus-single-widget")

        # First form field has a MultiWidget
        with self.wait_page_loaded():
            self.selenium.get(
                self.live_server_url + reverse("admin:admin_views_reservation_add")
            )
        self.assertEqual(
            self.selenium.switch_to.active_element,
            self.selenium.find_element(By.ID, "id_start_date_0"),
        )
        self.take_screenshot("focus-multi-widget")

    def test_cancel_delete_confirmation(self):
        "Cancelling the deletion of an object takes the user back one page."
        from selenium.webdriver.common.by import By

        pizza = Pizza.objects.create(name="Double Cheese")
        url = reverse("admin:admin_views_pizza_change", args=(pizza.id,))
        full_url = self.live_server_url + url
        self.admin_login(
            username="super", password="secret", login_url=reverse("admin:index")
        )
        self.selenium.get(full_url)
        self.selenium.find_element(By.CLASS_NAME, "deletelink").click()
        # Click 'cancel' on the delete page.
        self.selenium.find_element(By.CLASS_NAME, "cancel-link").click()
        # Wait until we're back on the change page.
        self.wait_for_text("#content h1", "Change pizza")
        self.assertEqual(self.selenium.current_url, full_url)
        self.assertEqual(Pizza.objects.count(), 1)

    def test_cancel_delete_related_confirmation(self):
        """
        Cancelling the deletion of an object with relations takes the user back
        one page.
        """
        from selenium.webdriver.common.by import By

        pizza = Pizza.objects.create(name="Double Cheese")
        topping1 = Topping.objects.create(name="Cheddar")
        topping2 = Topping.objects.create(name="Mozzarella")
        pizza.toppings.add(topping1, topping2)
        url = reverse("admin:admin_views_pizza_change", args=(pizza.id,))
        full_url = self.live_server_url + url
        self.admin_login(
            username="super", password="secret", login_url=reverse("admin:index")
        )
        self.selenium.get(full_url)
        self.selenium.find_element(By.CLASS_NAME, "deletelink").click()
        # Click 'cancel' on the delete page.
        self.selenium.find_element(By.CLASS_NAME, "cancel-link").click()
        # Wait until we're back on the change page.
        self.wait_for_text("#content h1", "Change pizza")
        self.assertEqual(self.selenium.current_url, full_url)
        self.assertEqual(Pizza.objects.count(), 1)
        self.assertEqual(Topping.objects.count(), 2)

    def test_list_editable_popups(self):
        """
        list_editable foreign keys have add/change popups.
        """
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import Select

        s1 = Section.objects.create(name="Test section")
        Article.objects.create(
            title="foo",
            content="<p>Middle content</p>",
            date=datetime.datetime(2008, 3, 18, 11, 54, 58),
            section=s1,
        )
        self.admin_login(
            username="super", password="secret", login_url=reverse("admin:index")
        )
        self.selenium.get(
            self.live_server_url + reverse("admin:admin_views_article_changelist")
        )
        # Change popup
        self.selenium.find_element(By.ID, "change_id_form-0-section").click()
        self.wait_for_and_switch_to_popup()
        self.wait_for_text("#content h1", "Change section")
        name_input = self.selenium.find_element(By.ID, "id_name")
        name_input.clear()
        name_input.send_keys("<i>edited section</i>")
        self.selenium.find_element(By.XPATH, '//input[@value="Save"]').click()
        self.wait_until(lambda d: len(d.window_handles) == 1, 1)
        self.selenium.switch_to.window(self.selenium.window_handles[0])
        # Hide sidebar.
        toggle_button = self.selenium.find_element(
            By.CSS_SELECTOR, "#toggle-nav-sidebar"
        )
        toggle_button.click()
        self.addCleanup(_clean_sidebar_state, self.selenium)
        select = Select(self.selenium.find_element(By.ID, "id_form-0-section"))
        self.assertEqual(select.first_selected_option.text, "<i>edited section</i>")
        # Rendered select2 input.
        select2_display = self.selenium.find_element(
            By.CLASS_NAME, "select2-selection__rendered"
        )
        # Clear button (×\n) is included in text.
        self.assertEqual(select2_display.text, "×\n<i>edited section</i>")

        # Add popup
        self.selenium.find_element(By.ID, "add_id_form-0-section").click()
        self.wait_for_and_switch_to_popup()
        self.wait_for_text("#content h1", "Add section")
        self.selenium.find_element(By.ID, "id_name").send_keys("new section")
        self.selenium.find_element(By.XPATH, '//input[@value="Save"]').click()
        self.wait_until(lambda d: len(d.window_handles) == 1, 1)
        self.selenium.switch_to.window(self.selenium.window_handles[0])
        select = Select(self.selenium.find_element(By.ID, "id_form-0-section"))
        self.assertEqual(select.first_selected_option.text, "new section")
        select2_display = self.selenium.find_element(
            By.CLASS_NAME, "select2-selection__rendered"
        )
        # Clear button (×\n) is included in text.
        self.assertEqual(select2_display.text, "×\nnew section")

    def test_inline_uuid_pk_edit_with_popup(self):
        from selenium.webdriver import ActionChains
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import Select

        parent = ParentWithUUIDPK.objects.create(title="test")
        related_with_parent = RelatedWithUUIDPKModel.objects.create(parent=parent)
        self.admin_login(
            username="super", password="secret", login_url=reverse("admin:index")
        )
        change_url = reverse(
            "admin:admin_views_relatedwithuuidpkmodel_change",
            args=(related_with_parent.id,),
        )
        with self.wait_page_loaded():
            self.selenium.get(self.live_server_url + change_url)
        change_parent = self.selenium.find_element(By.ID, "change_id_parent")
        ActionChains(self.selenium).move_to_element(change_parent).click().perform()
        self.wait_for_and_switch_to_popup()
        self.selenium.find_element(By.XPATH, '//input[@value="Save"]').click()
        self.selenium.switch_to.window(self.selenium.window_handles[0])
        select = Select(self.selenium.find_element(By.ID, "id_parent"))
        self.assertEqual(select.first_selected_option.text, str(parent.id))
        self.assertEqual(
            select.first_selected_option.get_attribute("value"), str(parent.id)
        )

    def test_inline_uuid_pk_add_with_popup(self):
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import Select

        self.admin_login(
            username="super", password="secret", login_url=reverse("admin:index")
        )
        self.selenium.get(
            self.live_server_url
            + reverse("admin:admin_views_relatedwithuuidpkmodel_add")
        )
        self.selenium.find_element(By.ID, "add_id_parent").click()
        self.wait_for_and_switch_to_popup()
        self.selenium.find_element(By.ID, "id_title").send_keys("test")
        self.selenium.find_element(By.XPATH, '//input[@value="Save"]').click()
        self.wait_until(lambda d: len(d.window_handles) == 1, 1)
        self.selenium.switch_to.window(self.selenium.window_handles[0])
        select = Select(self.selenium.find_element(By.ID, "id_parent"))
        uuid_id = str(ParentWithUUIDPK.objects.first().id)
        self.assertEqual(select.first_selected_option.text, uuid_id)
        self.assertEqual(select.first_selected_option.get_attribute("value"), uuid_id)

    def test_inline_uuid_pk_delete_with_popup(self):
        from selenium.webdriver import ActionChains
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import Select

        parent = ParentWithUUIDPK.objects.create(title="test")
        related_with_parent = RelatedWithUUIDPKModel.objects.create(parent=parent)
        self.admin_login(
            username="super", password="secret", login_url=reverse("admin:index")
        )
        change_url = reverse(
            "admin:admin_views_relatedwithuuidpkmodel_change",
            args=(related_with_parent.id,),
        )
        with self.wait_page_loaded():
            self.selenium.get(self.live_server_url + change_url)
        delete_parent = self.selenium.find_element(By.ID, "delete_id_parent")
        ActionChains(self.selenium).move_to_element(delete_parent).click().perform()
        self.wait_for_and_switch_to_popup()
        self.selenium.find_element(By.XPATH, '//input[@value="Yes, I’m sure"]').click()
        self.selenium.switch_to.window(self.selenium.window_handles[0])
        select = Select(self.selenium.find_element(By.ID, "id_parent"))
        self.assertEqual(ParentWithUUIDPK.objects.count(), 0)
        self.assertEqual(select.first_selected_option.text, "---------")
        self.assertEqual(select.first_selected_option.get_attribute("value"), "")

    def test_inline_with_popup_cancel_delete(self):
        """Clicking ""No, take me back" on a delete popup closes the window."""
        from selenium.webdriver import ActionChains
        from selenium.webdriver.common.by import By

        parent = ParentWithUUIDPK.objects.create(title="test")
        related_with_parent = RelatedWithUUIDPKModel.objects.create(parent=parent)
        self.admin_login(
            username="super", password="secret", login_url=reverse("admin:index")
        )
        change_url = reverse(
            "admin:admin_views_relatedwithuuidpkmodel_change",
            args=(related_with_parent.id,),
        )
        with self.wait_page_loaded():
            self.selenium.get(self.live_server_url + change_url)
        delete_parent = self.selenium.find_element(By.ID, "delete_id_parent")
        ActionChains(self.selenium).move_to_element(delete_parent).click().perform()
        self.wait_for_and_switch_to_popup()
        self.selenium.find_element(By.XPATH, '//a[text()="No, take me back"]').click()
        self.selenium.switch_to.window(self.selenium.window_handles[0])
        self.assertEqual(len(self.selenium.window_handles), 1)

    def test_list_editable_raw_id_fields(self):
        from selenium.webdriver.common.by import By

        parent = ParentWithUUIDPK.objects.create(title="test")
        parent2 = ParentWithUUIDPK.objects.create(title="test2")
        RelatedWithUUIDPKModel.objects.create(parent=parent)
        self.admin_login(
            username="super", password="secret", login_url=reverse("admin:index")
        )
        change_url = reverse(
            "admin:admin_views_relatedwithuuidpkmodel_changelist",
            current_app=site2.name,
        )
        self.selenium.get(self.live_server_url + change_url)
        self.selenium.find_element(By.ID, "lookup_id_form-0-parent").click()
        self.wait_for_and_switch_to_popup()
        # Select "parent2" in the popup.
        self.selenium.find_element(By.LINK_TEXT, str(parent2.pk)).click()
        self.selenium.switch_to.window(self.selenium.window_handles[0])
        # The newly selected pk should appear in the raw id input.
        value = self.selenium.find_element(By.ID, "id_form-0-parent").get_attribute(
            "value"
        )
        self.assertEqual(value, str(parent2.pk))

    def test_input_element_font(self):
        """
        Browsers' default stylesheets override the font of inputs. The admin
        adds additional CSS to handle this.
        """
        from selenium.webdriver.common.by import By

        self.selenium.get(self.live_server_url + reverse("admin:login"))
        element = self.selenium.find_element(By.ID, "id_username")
        # Some browsers quotes the fonts, some don't.
        fonts = [
            font.strip().strip('"')
            for font in element.value_of_css_property("font-family").split(",")
        ]
        self.assertEqual(
            fonts,
            [
                "Segoe UI",
                "system-ui",
                "Roboto",
                "Helvetica Neue",
                "Arial",
                "sans-serif",
                "Apple Color Emoji",
                "Segoe UI Emoji",
                "Segoe UI Symbol",
                "Noto Color Emoji",
            ],
        )

    def test_search_input_filtered_page(self):
        from selenium.webdriver.common.by import By

        Person.objects.create(name="Guido van Rossum", gender=1, alive=True)
        Person.objects.create(name="Grace Hopper", gender=1, alive=False)
        self.admin_login(
            username="super", password="secret", login_url=reverse("admin:index")
        )
        person_url = reverse("admin:admin_views_person_changelist") + "?q=Gui"
        self.selenium.get(self.live_server_url + person_url)
        # Hide sidebar.
        toggle_button = self.selenium.find_element(
            By.CSS_SELECTOR, "#toggle-nav-sidebar"
        )
        toggle_button.click()
        self.addCleanup(_clean_sidebar_state, self.selenium)
        self.assertGreater(
            self.selenium.find_element(By.ID, "searchbar").rect["width"],
            50,
        )

    def test_related_popup_index(self):
        """
        Create a chain of 'self' related objects via popups.
        """
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import Select

        self.admin_login(
            username="super", password="secret", login_url=reverse("admin:index")
        )
        add_url = reverse("admin:admin_views_box_add", current_app=site.name)
        self.selenium.get(self.live_server_url + add_url)

        base_window = self.selenium.current_window_handle
        self.selenium.find_element(By.ID, "add_id_next_box").click()
        self.wait_for_and_switch_to_popup()

        popup_window_test = self.selenium.current_window_handle
        self.selenium.find_element(By.ID, "id_title").send_keys("test")
        self.selenium.find_element(By.ID, "add_id_next_box").click()
        self.wait_for_and_switch_to_popup(num_windows=3)

        popup_window_test2 = self.selenium.current_window_handle
        self.selenium.find_element(By.ID, "id_title").send_keys("test2")
        self.selenium.find_element(By.ID, "add_id_next_box").click()
        self.wait_for_and_switch_to_popup(num_windows=4)

        self.selenium.find_element(By.ID, "id_title").send_keys("test3")
        self.selenium.find_element(By.XPATH, '//input[@value="Save"]').click()
        self.selenium.switch_to.window(popup_window_test2)
        select = Select(self.selenium.find_element(By.ID, "id_next_box"))
        next_box_id = str(Box.objects.get(title="test3").id)
        self.assertEqual(
            select.first_selected_option.get_attribute("value"), next_box_id
        )

        self.selenium.find_element(By.XPATH, '//input[@value="Save"]').click()
        self.selenium.switch_to.window(popup_window_test)
        select = Select(self.selenium.find_element(By.ID, "id_next_box"))
        next_box_id = str(Box.objects.get(title="test2").id)
        self.assertEqual(
            select.first_selected_option.get_attribute("value"), next_box_id
        )

        self.selenium.find_element(By.XPATH, '//input[@value="Save"]').click()
        self.selenium.switch_to.window(base_window)
        select = Select(self.selenium.find_element(By.ID, "id_next_box"))
        next_box_id = str(Box.objects.get(title="test").id)
        self.assertEqual(
            select.first_selected_option.get_attribute("value"), next_box_id
        )

    def test_related_popup_incorrect_close(self):
        """
        Cleanup child popups when closing a parent popup.
        """
        from selenium.webdriver.common.by import By

        self.admin_login(
            username="super", password="secret", login_url=reverse("admin:index")
        )
        add_url = reverse("admin:admin_views_box_add", current_app=site.name)
        self.selenium.get(self.live_server_url + add_url)

        self.selenium.find_element(By.ID, "add_id_next_box").click()
        self.wait_for_and_switch_to_popup()

        test_window = self.selenium.current_window_handle
        self.selenium.find_element(By.ID, "id_title").send_keys("test")
        self.selenium.find_element(By.ID, "add_id_next_box").click()
        self.wait_for_and_switch_to_popup(num_windows=3)

        test2_window = self.selenium.current_window_handle
        self.selenium.find_element(By.ID, "id_title").send_keys("test2")
        self.selenium.find_element(By.ID, "add_id_next_box").click()
        self.wait_for_and_switch_to_popup(num_windows=4)
        self.assertEqual(len(self.selenium.window_handles), 4)

        self.selenium.switch_to.window(test2_window)
        self.selenium.find_element(By.XPATH, '//input[@value="Save"]').click()
        self.wait_until(lambda d: len(d.window_handles) == 2, 1)
        self.assertEqual(len(self.selenium.window_handles), 2)

        # Close final popup to clean up test.
        self.selenium.switch_to.window(test_window)
        self.selenium.find_element(By.XPATH, '//input[@value="Save"]').click()
        self.wait_until(lambda d: len(d.window_handles) == 1, 1)
        self.selenium.switch_to.window(self.selenium.window_handles[-1])

    def test_hidden_fields_small_window(self):
        from selenium.webdriver.common.by import By

        self.admin_login(
            username="super",
            password="secret",
            login_url=reverse("admin:index"),
        )
        self.selenium.get(self.live_server_url + reverse("admin:admin_views_story_add"))
        field_title = self.selenium.find_element(By.CLASS_NAME, "field-title")
        with self.small_screen_size():
            self.assertIs(field_title.is_displayed(), False)
        with self.mobile_size():
            self.assertIs(field_title.is_displayed(), False)

    def test_updating_related_objects_updates_fk_selects_except_autocompletes(self):
        from selenium.webdriver import ActionChains
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import Select

        born_country_select_id = "id_born_country"
        living_country_select_id = "id_living_country"
        living_country_select2_textbox_id = "select2-id_living_country-container"
        favorite_country_to_vacation_select_id = "id_favorite_country_to_vacation"
        continent_select_id = "id_continent"

        def _get_HTML_inside_element_by_id(id_):
            return self.selenium.find_element(By.ID, id_).get_attribute("innerHTML")

        def _get_text_inside_element_by_selector(selector):
            return self.selenium.find_element(By.CSS_SELECTOR, selector).get_attribute(
                "innerText"
            )

        self.admin_login(
            username="super", password="secret", login_url=reverse("admin:index")
        )
        add_url = reverse("admin:admin_views_traveler_add")
        self.selenium.get(self.live_server_url + add_url)

        # Add new Country from the born_country select.
        self.selenium.find_element(By.ID, f"add_{born_country_select_id}").click()
        self.wait_for_and_switch_to_popup()
        self.selenium.find_element(By.ID, "id_name").send_keys("Argentina")
        continent_select = Select(
            self.selenium.find_element(By.ID, continent_select_id)
        )
        continent_select.select_by_visible_text("South America")
        self.selenium.find_element(By.CSS_SELECTOR, '[type="submit"]').click()
        self.wait_until(lambda d: len(d.window_handles) == 1, 1)
        self.selenium.switch_to.window(self.selenium.window_handles[0])

        self.assertHTMLEqual(
            _get_HTML_inside_element_by_id(born_country_select_id),
            """
            <option value="" selected="">---------</option>
            <option value="1" selected="">Argentina</option>
            """,
        )
        # Argentina isn't added to the living_country select nor selected by
        # the select2 widget.
        self.assertEqual(
            _get_text_inside_element_by_selector(f"#{living_country_select_id}"), ""
        )
        self.assertEqual(
            _get_text_inside_element_by_selector(
                f"#{living_country_select2_textbox_id}"
            ),
            "",
        )
        # Argentina won't appear because favorite_country_to_vacation field has
        # limit_choices_to.
        self.assertHTMLEqual(
            _get_HTML_inside_element_by_id(favorite_country_to_vacation_select_id),
            '<option value="" selected="">---------</option>',
        )

        # Add new Country from the living_country select.
        element = self.selenium.find_element(By.ID, f"add_{living_country_select_id}")
        ActionChains(self.selenium).move_to_element(element).click(element).perform()
        self.wait_for_and_switch_to_popup()
        self.selenium.find_element(By.ID, "id_name").send_keys("Spain")
        continent_select = Select(
            self.selenium.find_element(By.ID, continent_select_id)
        )
        continent_select.select_by_visible_text("Europe")
        self.selenium.find_element(By.CSS_SELECTOR, '[type="submit"]').click()
        self.wait_until(lambda d: len(d.window_handles) == 1, 1)
        self.selenium.switch_to.window(self.selenium.window_handles[0])

        self.assertHTMLEqual(
            _get_HTML_inside_element_by_id(born_country_select_id),
            """
            <option value="" selected="">---------</option>
            <option value="1" selected="">Argentina</option>
            <option value="2">Spain</option>
            """,
        )

        # Spain is added to the living_country select and it's also selected by
        # the select2 widget.
        self.assertEqual(
            _get_text_inside_element_by_selector(f"#{living_country_select_id} option"),
            "Spain",
        )
        self.assertEqual(
            _get_text_inside_element_by_selector(
                f"#{living_country_select2_textbox_id}"
            ),
            "Spain",
        )
        # Spain won't appear because favorite_country_to_vacation field has
        # limit_choices_to.
        self.assertHTMLEqual(
            _get_HTML_inside_element_by_id(favorite_country_to_vacation_select_id),
            '<option value="" selected="">---------</option>',
        )

        # Edit second Country created from living_country select.
        favorite_select = Select(
            self.selenium.find_element(By.ID, living_country_select_id)
        )
        favorite_select.select_by_visible_text("Spain")
        self.selenium.find_element(By.ID, f"change_{living_country_select_id}").click()
        self.wait_for_and_switch_to_popup()
        favorite_name_input = self.selenium.find_element(By.ID, "id_name")
        favorite_name_input.clear()
        favorite_name_input.send_keys("Italy")
        self.selenium.find_element(By.CSS_SELECTOR, '[type="submit"]').click()
        self.wait_until(lambda d: len(d.window_handles) == 1, 1)
        self.selenium.switch_to.window(self.selenium.window_handles[0])

        self.assertHTMLEqual(
            _get_HTML_inside_element_by_id(born_country_select_id),
            """
            <option value="" selected="">---------</option>
            <option value="1" selected="">Argentina</option>
            <option value="2">Italy</option>
            """,
        )
        # Italy is added to the living_country select and it's also selected by
        # the select2 widget.
        self.assertEqual(
            _get_text_inside_element_by_selector(f"#{living_country_select_id} option"),
            "Italy",
        )
        self.assertEqual(
            _get_text_inside_element_by_selector(
                f"#{living_country_select2_textbox_id}"
            ),
            "Italy",
        )
        # favorite_country_to_vacation field has no options.
        self.assertHTMLEqual(
            _get_HTML_inside_element_by_id(favorite_country_to_vacation_select_id),
            '<option value="" selected="">---------</option>',
        )

        # Add a new Asian country.
        self.selenium.find_element(
            By.ID, f"add_{favorite_country_to_vacation_select_id}"
        ).click()
        self.wait_for_and_switch_to_popup()
        favorite_name_input = self.selenium.find_element(By.ID, "id_name")
        favorite_name_input.send_keys("Qatar")
        continent_select = Select(
            self.selenium.find_element(By.ID, continent_select_id)
        )
        continent_select.select_by_visible_text("Asia")
        self.selenium.find_element(By.CSS_SELECTOR, '[type="submit"]').click()
        self.wait_until(lambda d: len(d.window_handles) == 1, 1)
        self.selenium.switch_to.window(self.selenium.window_handles[0])

        # Submit the new Traveler.
        with self.wait_page_loaded():
            self.selenium.find_element(By.CSS_SELECTOR, '[name="_save"]').click()
        traveler = Traveler.objects.get()
        self.assertEqual(traveler.born_country.name, "Argentina")
        self.assertEqual(traveler.living_country.name, "Italy")
        self.assertEqual(traveler.favorite_country_to_vacation.name, "Qatar")

    def test_redirect_on_add_view_add_another_button(self):
        from selenium.webdriver.common.by import By

        self.admin_login(
            username="super", password="secret", login_url=reverse("admin:index")
        )
        add_url = reverse("admin7:admin_views_section_add")
        self.selenium.get(self.live_server_url + add_url)
        name_input = self.selenium.find_element(By.ID, "id_name")
        name_input.send_keys("Test section 1")
        self.selenium.find_element(
            By.XPATH, '//input[@value="Save and add another"]'
        ).click()
        self.assertEqual(Section.objects.count(), 1)
        name_input = self.selenium.find_element(By.ID, "id_name")
        name_input.send_keys("Test section 2")
        self.selenium.find_element(
            By.XPATH, '//input[@value="Save and add another"]'
        ).click()
        self.assertEqual(Section.objects.count(), 2)

    def test_redirect_on_add_view_continue_button(self):
        from selenium.webdriver.common.by import By

        self.admin_login(
            username="super", password="secret", login_url=reverse("admin:index")
        )
        add_url = reverse("admin7:admin_views_section_add")
        self.selenium.get(self.live_server_url + add_url)
        name_input = self.selenium.find_element(By.ID, "id_name")
        name_input.send_keys("Test section 1")
        self.selenium.find_element(
            By.XPATH, '//input[@value="Save and continue editing"]'
        ).click()
        self.assertEqual(Section.objects.count(), 1)
        name_input = self.selenium.find_element(By.ID, "id_name")
        name_input_value = name_input.get_attribute("value")
        self.assertEqual(name_input_value, "Test section 1")


@override_settings(ROOT_URLCONF="admin_views.urls")
class ReadonlyTest(AdminFieldExtractionMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="super", password="secret", email="super@example.com"
        )

    def setUp(self):
        self.client.force_login(self.superuser)

    @ignore_warnings(category=RemovedInDjango60Warning)
    def test_readonly_get(self):
        response = self.client.get(reverse("admin:admin_views_post_add"))
        self.assertNotContains(response, 'name="posted"')
        # 3 fields + 2 submit buttons + 5 inline management form fields, + 2
        # hidden fields for inlines + 1 field for the inline + 2 empty form
        # + 1 logout form.
        self.assertContains(response, "<input", count=17)
        self.assertContains(response, formats.localize(datetime.date.today()))
        self.assertContains(response, "<label>Awesomeness level:</label>")
        self.assertContains(response, "Very awesome.")
        self.assertContains(response, "Unknown coolness.")
        self.assertContains(response, "foo")

        # Multiline text in a readonly field gets <br> tags
        self.assertContains(response, "Multiline<br>test<br>string")
        self.assertContains(
            response,
            '<div class="readonly">Multiline<br>html<br>content</div>',
            html=True,
        )
        self.assertContains(response, "InlineMultiline<br>test<br>string")

        self.assertContains(
            response,
            formats.localize(datetime.date.today() - datetime.timedelta(days=7)),
        )

        self.assertContains(response, '<div class="form-row field-coolness">')
        self.assertContains(response, '<div class="form-row field-awesomeness_level">')
        self.assertContains(response, '<div class="form-row field-posted">')
        self.assertContains(response, '<div class="form-row field-value">')
        self.assertContains(response, '<div class="form-row">')
        self.assertContains(response, '<div class="help"', 3)
        self.assertContains(
            response,
            '<div class="help" id="id_title_helptext"><div>Some help text for the '
            "title (with Unicode ŠĐĆŽćžšđ)</div></div>",
            html=True,
        )
        self.assertContains(
            response,
            '<div class="help" id="id_content_helptext"><div>Some help text for the '
            "content (with Unicode ŠĐĆŽćžšđ)</div></div>",
            html=True,
        )
        self.assertContains(
            response,
            '<div class="help"><div>Some help text for the date (with Unicode ŠĐĆŽćžšđ)'
            "</div></div>",
            html=True,
        )

        p = Post.objects.create(
            title="I worked on readonly_fields", content="Its good stuff"
        )
        response = self.client.get(
            reverse("admin:admin_views_post_change", args=(p.pk,))
        )
        self.assertContains(response, "%d amount of cool" % p.pk)

    @ignore_warnings(category=RemovedInDjango60Warning)
    def test_readonly_text_field(self):
        p = Post.objects.create(
            title="Readonly test",
            content="test",
            readonly_content="test\r\n\r\ntest\r\n\r\ntest\r\n\r\ntest",
        )
        Link.objects.create(
            url="http://www.djangoproject.com",
            post=p,
            readonly_link_content="test\r\nlink",
        )
        response = self.client.get(
            reverse("admin:admin_views_post_change", args=(p.pk,))
        )
        # Checking readonly field.
        self.assertContains(response, "test<br><br>test<br><br>test<br><br>test")
        # Checking readonly field in inline.
        self.assertContains(response, "test<br>link")

    @ignore_warnings(category=RemovedInDjango60Warning)
    def test_readonly_post(self):
        data = {
            "title": "Django Got Readonly Fields",
            "content": "This is an incredible development.",
            "link_set-TOTAL_FORMS": "1",
            "link_set-INITIAL_FORMS": "0",
            "link_set-MAX_NUM_FORMS": "0",
        }
        response = self.client.post(reverse("admin:admin_views_post_add"), data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Post.objects.count(), 1)
        p = Post.objects.get()
        self.assertEqual(p.posted, datetime.date.today())

        data["posted"] = "10-8-1990"  # some date that's not today
        response = self.client.post(reverse("admin:admin_views_post_add"), data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Post.objects.count(), 2)
        p = Post.objects.order_by("-id")[0]
        self.assertEqual(p.posted, datetime.date.today())

    def test_readonly_manytomany(self):
        "Regression test for #13004"
        response = self.client.get(reverse("admin:admin_views_pizza_add"))
        self.assertEqual(response.status_code, 200)

    def test_user_password_change_limited_queryset(self):
        su = User.objects.filter(is_superuser=True)[0]
        response = self.client.get(
            reverse("admin2:auth_user_password_change", args=(su.pk,))
        )
        self.assertEqual(response.status_code, 404)

    def test_change_form_renders_correct_null_choice_value(self):
        """
        Regression test for #17911.
        """
        choice = Choice.objects.create(choice=None)
        response = self.client.get(
            reverse("admin:admin_views_choice_change", args=(choice.pk,))
        )
        self.assertContains(
            response, '<div class="readonly">No opinion</div>', html=True
        )

    def _test_readonly_foreignkey_links(self, admin_site):
        """
        ForeignKey readonly fields render as links if the target model is
        registered in admin.
        """
        chapter = Chapter.objects.create(
            title="Chapter 1",
            content="content",
            book=Book.objects.create(name="Book 1"),
        )
        language = Language.objects.create(iso="_40", name="Test")
        obj = ReadOnlyRelatedField.objects.create(
            chapter=chapter,
            language=language,
            user=self.superuser,
        )
        response = self.client.get(
            reverse(
                f"{admin_site}:admin_views_readonlyrelatedfield_change", args=(obj.pk,)
            ),
        )
        # Related ForeignKey object registered in admin.
        user_url = reverse(f"{admin_site}:auth_user_change", args=(self.superuser.pk,))
        self.assertContains(
            response,
            '<div class="readonly"><a href="%s">super</a></div>' % user_url,
            html=True,
        )
        # Related ForeignKey with the string primary key registered in admin.
        language_url = reverse(
            f"{admin_site}:admin_views_language_change",
            args=(quote(language.pk),),
        )
        self.assertContains(
            response,
            '<div class="readonly"><a href="%s">_40</a></div>' % language_url,
            html=True,
        )
        # Related ForeignKey object not registered in admin.
        self.assertContains(
            response, '<div class="readonly">Chapter 1</div>', html=True
        )

    def test_readonly_foreignkey_links_default_admin_site(self):
        self._test_readonly_foreignkey_links("admin")

    def test_readonly_foreignkey_links_custom_admin_site(self):
        self._test_readonly_foreignkey_links("namespaced_admin")

    def test_readonly_manytomany_backwards_ref(self):
        """
        Regression test for #16433 - backwards references for related objects
        broke if the related field is read-only due to the help_text attribute
        """
        topping = Topping.objects.create(name="Salami")
        pizza = Pizza.objects.create(name="Americano")
        pizza.toppings.add(topping)
        response = self.client.get(reverse("admin:admin_views_topping_add"))
        self.assertEqual(response.status_code, 200)

    def test_readonly_manytomany_forwards_ref(self):
        topping = Topping.objects.create(name="Salami")
        pizza = Pizza.objects.create(name="Americano")
        pizza.toppings.add(topping)
        response = self.client.get(
            reverse("admin:admin_views_pizza_change", args=(pizza.pk,))
        )
        self.assertContains(response, "<label>Toppings:</label>", html=True)
        self.assertContains(response, '<div class="readonly">Salami</div>', html=True)

    def test_readonly_onetoone_backwards_ref(self):
        """
        Can reference a reverse OneToOneField in ModelAdmin.readonly_fields.
        """
        v1 = Villain.objects.create(name="Adam")
        pl = Plot.objects.create(name="Test Plot", team_leader=v1, contact=v1)
        pd = PlotDetails.objects.create(details="Brand New Plot", plot=pl)

        response = self.client.get(
            reverse("admin:admin_views_plotproxy_change", args=(pl.pk,))
        )
        field = self.get_admin_readonly_field(response, "plotdetails")
        pd_url = reverse("admin:admin_views_plotdetails_change", args=(pd.pk,))
        self.assertEqual(field.contents(), '<a href="%s">Brand New Plot</a>' % pd_url)

        # The reverse relation also works if the OneToOneField is null.
        pd.plot = None
        pd.save()

        response = self.client.get(
            reverse("admin:admin_views_plotproxy_change", args=(pl.pk,))
        )
        field = self.get_admin_readonly_field(response, "plotdetails")
        self.assertEqual(field.contents(), "-")  # default empty value

    @skipUnlessDBFeature("supports_stored_generated_columns")
    def test_readonly_unsaved_generated_field(self):
        response = self.client.get(reverse("admin:admin_views_square_add"))
        self.assertContains(response, '<div class="readonly">-</div>')

    @ignore_warnings(category=RemovedInDjango60Warning)
    def test_readonly_field_overrides(self):
        """
        Regression test for #22087 - ModelForm Meta overrides are ignored by
        AdminReadonlyField
        """
        p = FieldOverridePost.objects.create(title="Test Post", content="Test Content")
        response = self.client.get(
            reverse("admin:admin_views_fieldoverridepost_change", args=(p.pk,))
        )
        self.assertContains(
            response,
            '<div class="help"><div>Overridden help text for the date</div></div>',
            html=True,
        )
        self.assertContains(
            response,
            '<label for="id_public">Overridden public label:</label>',
            html=True,
        )
        self.assertNotContains(
            response, "Some help text for the date (with Unicode ŠĐĆŽćžšđ)"
        )

    def test_correct_autoescaping(self):
        """
        Make sure that non-field readonly elements are properly autoescaped (#24461)
        """
        section = Section.objects.create(name="<a>evil</a>")
        response = self.client.get(
            reverse("admin:admin_views_section_change", args=(section.pk,))
        )
        self.assertNotContains(response, "<a>evil</a>", status_code=200)
        self.assertContains(response, "&lt;a&gt;evil&lt;/a&gt;", status_code=200)

    def test_label_suffix_translated(self):
        pizza = Pizza.objects.create(name="Americano")
        url = reverse("admin:admin_views_pizza_change", args=(pizza.pk,))
        with self.settings(LANGUAGE_CODE="fr"):
            response = self.client.get(url)
        self.assertContains(response, "<label>Toppings\u00A0:</label>", html=True)


@override_settings(ROOT_URLCONF="admin_views.urls")
class LimitChoicesToInAdminTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="super", password="secret", email="super@example.com"
        )

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_limit_choices_to_as_callable(self):
        """Test for ticket 2445 changes to admin."""
        threepwood = Character.objects.create(
            username="threepwood",
            last_action=datetime.datetime.today() + datetime.timedelta(days=1),
        )
        marley = Character.objects.create(
            username="marley",
            last_action=datetime.datetime.today() - datetime.timedelta(days=1),
        )
        response = self.client.get(reverse("admin:admin_views_stumpjoke_add"))
        # The allowed option should appear twice; the limited option should not appear.
        self.assertContains(response, threepwood.username, count=2)
        self.assertNotContains(response, marley.username)


@override_settings(ROOT_URLCONF="admin_views.urls")
class RawIdFieldsTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="super", password="secret", email="super@example.com"
        )

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_limit_choices_to(self):
        """Regression test for 14880"""
        actor = Actor.objects.create(name="Palin", age=27)
        Inquisition.objects.create(expected=True, leader=actor, country="England")
        Inquisition.objects.create(expected=False, leader=actor, country="Spain")
        response = self.client.get(reverse("admin:admin_views_sketch_add"))
        # Find the link
        m = re.search(
            rb'<a href="([^"]*)"[^>]* id="lookup_id_inquisition"', response.content
        )
        self.assertTrue(m)  # Got a match
        popup_url = m[1].decode().replace("&amp;", "&")

        # Handle relative links
        popup_url = urljoin(response.request["PATH_INFO"], popup_url)
        # Get the popup and verify the correct objects show up in the resulting
        # page. This step also tests integers, strings and booleans in the
        # lookup query string; in model we define inquisition field to have a
        # limit_choices_to option that includes a filter on a string field
        # (inquisition__actor__name), a filter on an integer field
        # (inquisition__actor__age), and a filter on a boolean field
        # (inquisition__expected).
        response2 = self.client.get(popup_url)
        self.assertContains(response2, "Spain")
        self.assertNotContains(response2, "England")

    def test_limit_choices_to_isnull_false(self):
        """Regression test for 20182"""
        Actor.objects.create(name="Palin", age=27)
        Actor.objects.create(name="Kilbraken", age=50, title="Judge")
        response = self.client.get(reverse("admin:admin_views_sketch_add"))
        # Find the link
        m = re.search(
            rb'<a href="([^"]*)"[^>]* id="lookup_id_defendant0"', response.content
        )
        self.assertTrue(m)  # Got a match
        popup_url = m[1].decode().replace("&amp;", "&")

        # Handle relative links
        popup_url = urljoin(response.request["PATH_INFO"], popup_url)
        # Get the popup and verify the correct objects show up in the resulting
        # page. This step tests field__isnull=0 gets parsed correctly from the
        # lookup query string; in model we define defendant0 field to have a
        # limit_choices_to option that includes "actor__title__isnull=False".
        response2 = self.client.get(popup_url)
        self.assertContains(response2, "Kilbraken")
        self.assertNotContains(response2, "Palin")

    def test_limit_choices_to_isnull_true(self):
        """Regression test for 20182"""
        Actor.objects.create(name="Palin", age=27)
        Actor.objects.create(name="Kilbraken", age=50, title="Judge")
        response = self.client.get(reverse("admin:admin_views_sketch_add"))
        # Find the link
        m = re.search(
            rb'<a href="([^"]*)"[^>]* id="lookup_id_defendant1"', response.content
        )
        self.assertTrue(m)  # Got a match
        popup_url = m[1].decode().replace("&amp;", "&")

        # Handle relative links
        popup_url = urljoin(response.request["PATH_INFO"], popup_url)
        # Get the popup and verify the correct objects show up in the resulting
        # page. This step tests field__isnull=1 gets parsed correctly from the
        # lookup query string; in model we define defendant1 field to have a
        # limit_choices_to option that includes "actor__title__isnull=True".
        response2 = self.client.get(popup_url)
        self.assertNotContains(response2, "Kilbraken")
        self.assertContains(response2, "Palin")

    def test_list_display_method_same_name_as_reverse_accessor(self):
        """
        Should be able to use a ModelAdmin method in list_display that has the
        same name as a reverse model field ("sketch" in this case).
        """
        actor = Actor.objects.create(name="Palin", age=27)
        Inquisition.objects.create(expected=True, leader=actor, country="England")
        response = self.client.get(reverse("admin:admin_views_inquisition_changelist"))
        self.assertContains(response, "list-display-sketch")


@override_settings(ROOT_URLCONF="admin_views.urls")
class UserAdminTest(TestCase):
    """
    Tests user CRUD functionality.
    """

    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="super", password="secret", email="super@example.com"
        )
        cls.adduser = User.objects.create_user(
            username="adduser", password="secret", is_staff=True
        )
        cls.changeuser = User.objects.create_user(
            username="changeuser", password="secret", is_staff=True
        )
        cls.s1 = Section.objects.create(name="Test section")
        cls.a1 = Article.objects.create(
            content="<p>Middle content</p>",
            date=datetime.datetime(2008, 3, 18, 11, 54, 58),
            section=cls.s1,
        )
        cls.a2 = Article.objects.create(
            content="<p>Oldest content</p>",
            date=datetime.datetime(2000, 3, 18, 11, 54, 58),
            section=cls.s1,
        )
        cls.a3 = Article.objects.create(
            content="<p>Newest content</p>",
            date=datetime.datetime(2009, 3, 18, 11, 54, 58),
            section=cls.s1,
        )
        cls.p1 = PrePopulatedPost.objects.create(
            title="A Long Title", published=True, slug="a-long-title"
        )

        cls.per1 = Person.objects.create(name="John Mauchly", gender=1, alive=True)
        cls.per2 = Person.objects.create(name="Grace Hopper", gender=1, alive=False)
        cls.per3 = Person.objects.create(name="Guido van Rossum", gender=1, alive=True)

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_save_button(self):
        user_count = User.objects.count()
        response = self.client.post(
            reverse("admin:auth_user_add"),
            {
                "username": "newuser",
                "password1": "newpassword",
                "password2": "newpassword",
            },
        )
        new_user = User.objects.get(username="newuser")
        self.assertRedirects(
            response, reverse("admin:auth_user_change", args=(new_user.pk,))
        )
        self.assertEqual(User.objects.count(), user_count + 1)
        self.assertTrue(new_user.has_usable_password())

    def test_save_continue_editing_button(self):
        user_count = User.objects.count()
        response = self.client.post(
            reverse("admin:auth_user_add"),
            {
                "username": "newuser",
                "password1": "newpassword",
                "password2": "newpassword",
                "_continue": "1",
            },
        )
        new_user = User.objects.get(username="newuser")
        new_user_url = reverse("admin:auth_user_change", args=(new_user.pk,))
        self.assertRedirects(response, new_user_url, fetch_redirect_response=False)
        self.assertEqual(User.objects.count(), user_count + 1)
        self.assertTrue(new_user.has_usable_password())
        response = self.client.get(new_user_url)
        self.assertContains(
            response,
            '<li class="success">The user “<a href="%s">'
            "%s</a>” was added successfully. You may edit it again below.</li>"
            % (new_user_url, new_user),
            html=True,
        )

    def test_password_mismatch(self):
        response = self.client.post(
            reverse("admin:auth_user_add"),
            {
                "username": "newuser",
                "password1": "newpassword",
                "password2": "mismatch",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context["adminform"], "password1", [])
        self.assertFormError(
            response.context["adminform"],
            "password2",
            ["The two password fields didn’t match."],
        )

    def test_user_fk_add_popup(self):
        """
        User addition through a FK popup should return the appropriate
        JavaScript response.
        """
        response = self.client.get(reverse("admin:admin_views_album_add"))
        self.assertContains(response, reverse("admin:auth_user_add"))
        self.assertContains(
            response,
            'class="related-widget-wrapper-link add-related" id="add_id_owner"',
        )
        response = self.client.get(
            reverse("admin:auth_user_add") + "?%s=1" % IS_POPUP_VAR
        )
        self.assertNotContains(response, 'name="_continue"')
        self.assertNotContains(response, 'name="_addanother"')
        data = {
            "username": "newuser",
            "password1": "newpassword",
            "password2": "newpassword",
            IS_POPUP_VAR: "1",
            "_save": "1",
        }
        response = self.client.post(
            reverse("admin:auth_user_add") + "?%s=1" % IS_POPUP_VAR, data, follow=True
        )
        self.assertContains(response, "&quot;obj&quot;: &quot;newuser&quot;")

    def test_user_fk_change_popup(self):
        """
        User change through a FK popup should return the appropriate JavaScript
        response.
        """
        response = self.client.get(reverse("admin:admin_views_album_add"))
        self.assertContains(
            response, reverse("admin:auth_user_change", args=("__fk__",))
        )
        self.assertContains(
            response,
            'class="related-widget-wrapper-link change-related" id="change_id_owner"',
        )
        user = User.objects.get(username="changeuser")
        url = (
            reverse("admin:auth_user_change", args=(user.pk,)) + "?%s=1" % IS_POPUP_VAR
        )
        response = self.client.get(url)
        self.assertNotContains(response, 'name="_continue"')
        self.assertNotContains(response, 'name="_addanother"')
        data = {
            "username": "newuser",
            "password1": "newpassword",
            "password2": "newpassword",
            "last_login_0": "2007-05-30",
            "last_login_1": "13:20:10",
            "date_joined_0": "2007-05-30",
            "date_joined_1": "13:20:10",
            IS_POPUP_VAR: "1",
            "_save": "1",
        }
        response = self.client.post(url, data, follow=True)
        self.assertContains(response, "&quot;obj&quot;: &quot;newuser&quot;")
        self.assertContains(response, "&quot;action&quot;: &quot;change&quot;")

    def test_user_fk_delete_popup(self):
        """
        User deletion through a FK popup should return the appropriate
        JavaScript response.
        """
        response = self.client.get(reverse("admin:admin_views_album_add"))
        self.assertContains(
            response, reverse("admin:auth_user_delete", args=("__fk__",))
        )
        self.assertContains(
            response,
            'class="related-widget-wrapper-link change-related" id="change_id_owner"',
        )
        user = User.objects.get(username="changeuser")
        url = (
            reverse("admin:auth_user_delete", args=(user.pk,)) + "?%s=1" % IS_POPUP_VAR
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = {
            "post": "yes",
            IS_POPUP_VAR: "1",
        }
        response = self.client.post(url, data, follow=True)
        self.assertContains(response, "&quot;action&quot;: &quot;delete&quot;")

    def test_save_add_another_button(self):
        user_count = User.objects.count()
        response = self.client.post(
            reverse("admin:auth_user_add"),
            {
                "username": "newuser",
                "password1": "newpassword",
                "password2": "newpassword",
                "_addanother": "1",
            },
        )
        new_user = User.objects.order_by("-id")[0]
        self.assertRedirects(response, reverse("admin:auth_user_add"))
        self.assertEqual(User.objects.count(), user_count + 1)
        self.assertTrue(new_user.has_usable_password())

    def test_user_permission_performance(self):
        u = User.objects.all()[0]

        # Don't depend on a warm cache, see #17377.
        ContentType.objects.clear_cache()

        expected_num_queries = 8 if connection.features.uses_savepoints else 6
        with self.assertNumQueries(expected_num_queries):
            response = self.client.get(reverse("admin:auth_user_change", args=(u.pk,)))
            self.assertEqual(response.status_code, 200)

    def test_form_url_present_in_context(self):
        u = User.objects.all()[0]
        response = self.client.get(
            reverse("admin3:auth_user_password_change", args=(u.pk,))
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["form_url"], "pony")


@override_settings(ROOT_URLCONF="admin_views.urls")
class GroupAdminTest(TestCase):
    """
    Tests group CRUD functionality.
    """

    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="super", password="secret", email="super@example.com"
        )

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_save_button(self):
        group_count = Group.objects.count()
        response = self.client.post(
            reverse("admin:auth_group_add"),
            {
                "name": "newgroup",
            },
        )

        Group.objects.order_by("-id")[0]
        self.assertRedirects(response, reverse("admin:auth_group_changelist"))
        self.assertEqual(Group.objects.count(), group_count + 1)

    def test_group_permission_performance(self):
        g = Group.objects.create(name="test_group")

        # Ensure no queries are skipped due to cached content type for Group.
        ContentType.objects.clear_cache()

        expected_num_queries = 6 if connection.features.uses_savepoints else 4
        with self.assertNumQueries(expected_num_queries):
            response = self.client.get(reverse("admin:auth_group_change", args=(g.pk,)))
            self.assertEqual(response.status_code, 200)


@override_settings(ROOT_URLCONF="admin_views.urls")
class CSSTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="super", password="secret", email="super@example.com"
        )
        cls.s1 = Section.objects.create(name="Test section")
        cls.a1 = Article.objects.create(
            content="<p>Middle content</p>",
            date=datetime.datetime(2008, 3, 18, 11, 54, 58),
            section=cls.s1,
        )
        cls.a2 = Article.objects.create(
            content="<p>Oldest content</p>",
            date=datetime.datetime(2000, 3, 18, 11, 54, 58),
            section=cls.s1,
        )
        cls.a3 = Article.objects.create(
            content="<p>Newest content</p>",
            date=datetime.datetime(2009, 3, 18, 11, 54, 58),
            section=cls.s1,
        )
        cls.p1 = PrePopulatedPost.objects.create(
            title="A Long Title", published=True, slug="a-long-title"
        )

    def setUp(self):
        self.client.force_login(self.superuser)

    @ignore_warnings(category=RemovedInDjango60Warning)
    def test_field_prefix_css_classes(self):
        """
        Fields have a CSS class name with a 'field-' prefix.
        """
        response = self.client.get(reverse("admin:admin_views_post_add"))

        # The main form
        self.assertContains(response, 'class="form-row field-title"')
        self.assertContains(response, 'class="form-row field-content"')
        self.assertContains(response, 'class="form-row field-public"')
        self.assertContains(response, 'class="form-row field-awesomeness_level"')
        self.assertContains(response, 'class="form-row field-coolness"')
        self.assertContains(response, 'class="form-row field-value"')
        self.assertContains(response, 'class="form-row"')  # The lambda function

        # The tabular inline
        self.assertContains(response, '<td class="field-url">')
        self.assertContains(response, '<td class="field-posted">')

    def test_index_css_classes(self):
        """
        CSS class names are used for each app and model on the admin index
        pages (#17050).
        """
        # General index page
        response = self.client.get(reverse("admin:index"))
        self.assertContains(response, '<div class="app-admin_views module')
        self.assertContains(
            response,
            '<thead class="visually-hidden"><tr><th scope="col">Model name</th>'
            '<th scope="col">Add link</th><th scope="col">Change or view list link</th>'
            "</tr></thead>",
            html=True,
        )
        self.assertContains(response, '<tr class="model-actor">')
        self.assertContains(response, '<tr class="model-album">')

        # App index page
        response = self.client.get(reverse("admin:app_list", args=("admin_views",)))
        self.assertContains(response, '<div class="app-admin_views module')
        self.assertContains(
            response,
            '<thead class="visually-hidden"><tr><th scope="col">Model name</th>'
            '<th scope="col">Add link</th><th scope="col">Change or view list link</th>'
            "</tr></thead>",
            html=True,
        )
        self.assertContains(response, '<tr class="model-actor">')
        self.assertContains(response, '<tr class="model-album">')

    def test_app_model_in_form_body_class(self):
        """
        Ensure app and model tag are correctly read by change_form template
        """
        response = self.client.get(reverse("admin:admin_views_section_add"))
        self.assertContains(response, '<body class=" app-admin_views model-section ')

    def test_app_model_in_list_body_class(self):
        """
        Ensure app and model tag are correctly read by change_list template
        """
        response = self.client.get(reverse("admin:admin_views_section_changelist"))
        self.assertContains(response, '<body class=" app-admin_views model-section ')

    def test_app_model_in_delete_confirmation_body_class(self):
        """
        Ensure app and model tag are correctly read by delete_confirmation
        template
        """
        response = self.client.get(
            reverse("admin:admin_views_section_delete", args=(self.s1.pk,))
        )
        self.assertContains(response, '<body class=" app-admin_views model-section ')

    def test_app_model_in_app_index_body_class(self):
        """
        Ensure app and model tag are correctly read by app_index template
        """
        response = self.client.get(reverse("admin:app_list", args=("admin_views",)))
        self.assertContains(response, '<body class=" dashboard app-admin_views')

    def test_app_model_in_delete_selected_confirmation_body_class(self):
        """
        Ensure app and model tag are correctly read by
        delete_selected_confirmation template
        """
        action_data = {
            ACTION_CHECKBOX_NAME: [self.s1.pk],
            "action": "delete_selected",
            "index": 0,
        }
        response = self.client.post(
            reverse("admin:admin_views_section_changelist"), action_data
        )
        self.assertContains(response, '<body class=" app-admin_views model-section ')

    def test_changelist_field_classes(self):
        """
        Cells of the change list table should contain the field name in their
        class attribute.
        """
        Podcast.objects.create(name="Django Dose", release_date=datetime.date.today())
        response = self.client.get(reverse("admin:admin_views_podcast_changelist"))
        self.assertContains(response, '<th class="field-name">')
        self.assertContains(response, '<td class="field-release_date nowrap">')
        self.assertContains(response, '<td class="action-checkbox">')


try:
    import docutils
except ImportError:
    docutils = None


@unittest.skipUnless(docutils, "no docutils installed.")
@override_settings(ROOT_URLCONF="admin_views.urls")
@modify_settings(
    INSTALLED_APPS={"append": ["django.contrib.admindocs", "django.contrib.flatpages"]}
)
class AdminDocsTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="super", password="secret", email="super@example.com"
        )

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_tags(self):
        response = self.client.get(reverse("django-admindocs-tags"))

        # The builtin tag group exists
        self.assertContains(response, "<h2>Built-in tags</h2>", count=2, html=True)

        # A builtin tag exists in both the index and detail
        self.assertContains(
            response, '<h3 id="built_in-autoescape">autoescape</h3>', html=True
        )
        self.assertContains(
            response,
            '<li><a href="#built_in-autoescape">autoescape</a></li>',
            html=True,
        )

        # An app tag exists in both the index and detail
        self.assertContains(
            response, '<h3 id="flatpages-get_flatpages">get_flatpages</h3>', html=True
        )
        self.assertContains(
            response,
            '<li><a href="#flatpages-get_flatpages">get_flatpages</a></li>',
            html=True,
        )

        # The admin list tag group exists
        self.assertContains(response, "<h2>admin_list</h2>", count=2, html=True)

        # An admin list tag exists in both the index and detail
        self.assertContains(
            response, '<h3 id="admin_list-admin_actions">admin_actions</h3>', html=True
        )
        self.assertContains(
            response,
            '<li><a href="#admin_list-admin_actions">admin_actions</a></li>',
            html=True,
        )

    def test_filters(self):
        response = self.client.get(reverse("django-admindocs-filters"))

        # The builtin filter group exists
        self.assertContains(response, "<h2>Built-in filters</h2>", count=2, html=True)

        # A builtin filter exists in both the index and detail
        self.assertContains(response, '<h3 id="built_in-add">add</h3>', html=True)
        self.assertContains(
            response, '<li><a href="#built_in-add">add</a></li>', html=True
        )

    def test_index_headers(self):
        response = self.client.get(reverse("django-admindocs-docroot"))
        self.assertContains(response, "<h1>Documentation</h1>")
        self.assertContains(response, '<h2><a href="tags/">Tags</a></h2>')
        self.assertContains(response, '<h2><a href="filters/">Filters</a></h2>')
        self.assertContains(response, '<h2><a href="models/">Models</a></h2>')
        self.assertContains(response, '<h2><a href="views/">Views</a></h2>')
        self.assertContains(
            response, '<h2><a href="bookmarklets/">Bookmarklets</a></h2>'
        )


@override_settings(
    ROOT_URLCONF="admin_views.urls",
    TEMPLATES=[
        {
            "BACKEND": "django.template.backends.django.DjangoTemplates",
            "APP_DIRS": True,
            "OPTIONS": {
                "context_processors": [
                    "django.template.context_processors.request",
                    "django.contrib.auth.context_processors.auth",
                    "django.contrib.messages.context_processors.messages",
                ],
            },
        }
    ],
)
class ValidXHTMLTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="super", password="secret", email="super@example.com"
        )

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_lang_name_present(self):
        with translation.override(None):
            response = self.client.get(reverse("admin:app_list", args=("admin_views",)))
            self.assertNotContains(response, ' lang=""')
            self.assertNotContains(response, ' xml:lang=""')


@override_settings(ROOT_URLCONF="admin_views.urls", USE_THOUSAND_SEPARATOR=True)
class DateHierarchyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="super", password="secret", email="super@example.com"
        )

    def setUp(self):
        self.client.force_login(self.superuser)

    def assert_non_localized_year(self, response, year):
        """
        The year is not localized with USE_THOUSAND_SEPARATOR (#15234).
        """
        self.assertNotContains(response, formats.number_format(year))

    def assert_contains_year_link(self, response, date):
        self.assertContains(response, '?release_date__year=%d"' % date.year)

    def assert_contains_month_link(self, response, date):
        self.assertContains(
            response,
            '?release_date__month=%d&amp;release_date__year=%d"'
            % (date.month, date.year),
        )

    def assert_contains_day_link(self, response, date):
        self.assertContains(
            response,
            "?release_date__day=%d&amp;"
            'release_date__month=%d&amp;release_date__year=%d"'
            % (date.day, date.month, date.year),
        )

    def test_empty(self):
        """
        No date hierarchy links display with empty changelist.
        """
        response = self.client.get(reverse("admin:admin_views_podcast_changelist"))
        self.assertNotContains(response, "release_date__year=")
        self.assertNotContains(response, "release_date__month=")
        self.assertNotContains(response, "release_date__day=")

    def test_single(self):
        """
        Single day-level date hierarchy appears for single object.
        """
        DATE = datetime.date(2000, 6, 30)
        Podcast.objects.create(release_date=DATE)
        url = reverse("admin:admin_views_podcast_changelist")
        response = self.client.get(url)
        self.assert_contains_day_link(response, DATE)
        self.assert_non_localized_year(response, 2000)

    def test_within_month(self):
        """
        day-level links appear for changelist within single month.
        """
        DATES = (
            datetime.date(2000, 6, 30),
            datetime.date(2000, 6, 15),
            datetime.date(2000, 6, 3),
        )
        for date in DATES:
            Podcast.objects.create(release_date=date)
        url = reverse("admin:admin_views_podcast_changelist")
        response = self.client.get(url)
        for date in DATES:
            self.assert_contains_day_link(response, date)
        self.assert_non_localized_year(response, 2000)

    def test_within_year(self):
        """
        month-level links appear for changelist within single year.
        """
        DATES = (
            datetime.date(2000, 1, 30),
            datetime.date(2000, 3, 15),
            datetime.date(2000, 5, 3),
        )
        for date in DATES:
            Podcast.objects.create(release_date=date)
        url = reverse("admin:admin_views_podcast_changelist")
        response = self.client.get(url)
        # no day-level links
        self.assertNotContains(response, "release_date__day=")
        for date in DATES:
            self.assert_contains_month_link(response, date)
        self.assert_non_localized_year(response, 2000)

    def test_multiple_years(self):
        """
        year-level links appear for year-spanning changelist.
        """
        DATES = (
            datetime.date(2001, 1, 30),
            datetime.date(2003, 3, 15),
            datetime.date(2005, 5, 3),
        )
        for date in DATES:
            Podcast.objects.create(release_date=date)
        response = self.client.get(reverse("admin:admin_views_podcast_changelist"))
        # no day/month-level links
        self.assertNotContains(response, "release_date__day=")
        self.assertNotContains(response, "release_date__month=")
        for date in DATES:
            self.assert_contains_year_link(response, date)

        # and make sure GET parameters still behave correctly
        for date in DATES:
            url = "%s?release_date__year=%d" % (
                reverse("admin:admin_views_podcast_changelist"),
                date.year,
            )
            response = self.client.get(url)
            self.assert_contains_month_link(response, date)
            self.assert_non_localized_year(response, 2000)
            self.assert_non_localized_year(response, 2003)
            self.assert_non_localized_year(response, 2005)

            url = "%s?release_date__year=%d&release_date__month=%d" % (
                reverse("admin:admin_views_podcast_changelist"),
                date.year,
                date.month,
            )
            response = self.client.get(url)
            self.assert_contains_day_link(response, date)
            self.assert_non_localized_year(response, 2000)
            self.assert_non_localized_year(response, 2003)
            self.assert_non_localized_year(response, 2005)

    def test_related_field(self):
        questions_data = (
            # (posted data, number of answers),
            (datetime.date(2001, 1, 30), 0),
            (datetime.date(2003, 3, 15), 1),
            (datetime.date(2005, 5, 3), 2),
        )
        for date, answer_count in questions_data:
            question = Question.objects.create(posted=date)
            for i in range(answer_count):
                question.answer_set.create()

        response = self.client.get(reverse("admin:admin_views_answer_changelist"))
        for date, answer_count in questions_data:
            link = '?question__posted__year=%d"' % date.year
            if answer_count > 0:
                self.assertContains(response, link)
            else:
                self.assertNotContains(response, link)


@override_settings(ROOT_URLCONF="admin_views.urls")
class AdminCustomSaveRelatedTests(TestCase):
    """
    One can easily customize the way related objects are saved.
    Refs #16115.
    """

    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="super", password="secret", email="super@example.com"
        )

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_should_be_able_to_edit_related_objects_on_add_view(self):
        post = {
            "child_set-TOTAL_FORMS": "3",
            "child_set-INITIAL_FORMS": "0",
            "name": "Josh Stone",
            "child_set-0-name": "Paul",
            "child_set-1-name": "Catherine",
        }
        self.client.post(reverse("admin:admin_views_parent_add"), post)
        self.assertEqual(1, Parent.objects.count())
        self.assertEqual(2, Child.objects.count())

        children_names = list(
            Child.objects.order_by("name").values_list("name", flat=True)
        )

        self.assertEqual("Josh Stone", Parent.objects.latest("id").name)
        self.assertEqual(["Catherine Stone", "Paul Stone"], children_names)

    def test_should_be_able_to_edit_related_objects_on_change_view(self):
        parent = Parent.objects.create(name="Josh Stone")
        paul = Child.objects.create(parent=parent, name="Paul")
        catherine = Child.objects.create(parent=parent, name="Catherine")
        post = {
            "child_set-TOTAL_FORMS": "5",
            "child_set-INITIAL_FORMS": "2",
            "name": "Josh Stone",
            "child_set-0-name": "Paul",
            "child_set-0-id": paul.id,
            "child_set-1-name": "Catherine",
            "child_set-1-id": catherine.id,
        }
        self.client.post(
            reverse("admin:admin_views_parent_change", args=(parent.id,)), post
        )

        children_names = list(
            Child.objects.order_by("name").values_list("name", flat=True)
        )

        self.assertEqual("Josh Stone", Parent.objects.latest("id").name)
        self.assertEqual(["Catherine Stone", "Paul Stone"], children_names)

    def test_should_be_able_to_edit_related_objects_on_changelist_view(self):
        parent = Parent.objects.create(name="Josh Rock")
        Child.objects.create(parent=parent, name="Paul")
        Child.objects.create(parent=parent, name="Catherine")
        post = {
            "form-TOTAL_FORMS": "1",
            "form-INITIAL_FORMS": "1",
            "form-MAX_NUM_FORMS": "0",
            "form-0-id": parent.id,
            "form-0-name": "Josh Stone",
            "_save": "Save",
        }

        self.client.post(reverse("admin:admin_views_parent_changelist"), post)
        children_names = list(
            Child.objects.order_by("name").values_list("name", flat=True)
        )

        self.assertEqual("Josh Stone", Parent.objects.latest("id").name)
        self.assertEqual(["Catherine Stone", "Paul Stone"], children_names)


@override_settings(ROOT_URLCONF="admin_views.urls")
class AdminViewLogoutTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="super", password="secret", email="super@example.com"
        )

    def test_logout(self):
        self.client.force_login(self.superuser)
        response = self.client.post(reverse("admin:logout"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "registration/logged_out.html")
        self.assertEqual(response.request["PATH_INFO"], reverse("admin:logout"))
        self.assertFalse(response.context["has_permission"])
        self.assertNotContains(
            response, "user-tools"
        )  # user-tools div shouldn't visible.

    def test_client_logout_url_can_be_used_to_login(self):
        response = self.client.post(reverse("admin:logout"))
        self.assertEqual(
            response.status_code, 302
        )  # we should be redirected to the login page.

        # follow the redirect and test results.
        response = self.client.post(reverse("admin:logout"), follow=True)
        self.assertContains(
            response,
            '<input type="hidden" name="next" value="%s">' % reverse("admin:index"),
        )
        self.assertTemplateUsed(response, "admin/login.html")
        self.assertEqual(response.request["PATH_INFO"], reverse("admin:login"))


@override_settings(ROOT_URLCONF="admin_views.urls")
class AdminUserMessageTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="super", password="secret", email="super@example.com"
        )

    def setUp(self):
        self.client.force_login(self.superuser)

    def send_message(self, level):
        """
        Helper that sends a post to the dummy test methods and asserts that a
        message with the level has appeared in the response.
        """
        action_data = {
            ACTION_CHECKBOX_NAME: [1],
            "action": "message_%s" % level,
            "index": 0,
        }

        response = self.client.post(
            reverse("admin:admin_views_usermessenger_changelist"),
            action_data,
            follow=True,
        )
        self.assertContains(
            response, '<li class="%s">Test %s</li>' % (level, level), html=True
        )

    @override_settings(MESSAGE_LEVEL=10)  # Set to DEBUG for this request
    def test_message_debug(self):
        self.send_message("debug")

    def test_message_info(self):
        self.send_message("info")

    def test_message_success(self):
        self.send_message("success")

    def test_message_warning(self):
        self.send_message("warning")

    def test_message_error(self):
        self.send_message("error")

    def test_message_extra_tags(self):
        action_data = {
            ACTION_CHECKBOX_NAME: [1],
            "action": "message_extra_tags",
            "index": 0,
        }

        response = self.client.post(
            reverse("admin:admin_views_usermessenger_changelist"),
            action_data,
            follow=True,
        )
        self.assertContains(
            response, '<li class="extra_tag info">Test tags</li>', html=True
        )


@override_settings(ROOT_URLCONF="admin_views.urls")
class AdminKeepChangeListFiltersTests(TestCase):
    admin_site = site

    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="super", password="secret", email="super@example.com"
        )
        cls.joepublicuser = User.objects.create_user(
            username="joepublic", password="secret"
        )

    def setUp(self):
        self.client.force_login(self.superuser)

    def assertURLEqual(self, url1, url2, msg_prefix=""):
        """
        Assert that two URLs are equal despite the ordering
        of their querystring. Refs #22360.
        """
        parsed_url1 = urlsplit(url1)
        path1 = parsed_url1.path
        parsed_qs1 = dict(parse_qsl(parsed_url1.query))

        parsed_url2 = urlsplit(url2)
        path2 = parsed_url2.path
        parsed_qs2 = dict(parse_qsl(parsed_url2.query))

        for parsed_qs in [parsed_qs1, parsed_qs2]:
            if "_changelist_filters" in parsed_qs:
                changelist_filters = parsed_qs["_changelist_filters"]
                parsed_filters = dict(parse_qsl(changelist_filters))
                parsed_qs["_changelist_filters"] = parsed_filters

        self.assertEqual(path1, path2)
        self.assertEqual(parsed_qs1, parsed_qs2)

    def test_assert_url_equal(self):
        # Test equality.
        change_user_url = reverse(
            "admin:auth_user_change", args=(self.joepublicuser.pk,)
        )
        self.assertURLEqual(
            "http://testserver{}?_changelist_filters="
            "is_staff__exact%3D0%26is_superuser__exact%3D0".format(change_user_url),
            "http://testserver{}?_changelist_filters="
            "is_staff__exact%3D0%26is_superuser__exact%3D0".format(change_user_url),
        )

        # Test inequality.
        with self.assertRaises(AssertionError):
            self.assertURLEqual(
                "http://testserver{}?_changelist_filters="
                "is_staff__exact%3D0%26is_superuser__exact%3D0".format(change_user_url),
                "http://testserver{}?_changelist_filters="
                "is_staff__exact%3D1%26is_superuser__exact%3D1".format(change_user_url),
            )

        # Ignore scheme and host.
        self.assertURLEqual(
            "http://testserver{}?_changelist_filters="
            "is_staff__exact%3D0%26is_superuser__exact%3D0".format(change_user_url),
            "{}?_changelist_filters="
            "is_staff__exact%3D0%26is_superuser__exact%3D0".format(change_user_url),
        )

        # Ignore ordering of querystring.
        self.assertURLEqual(
            "{}?is_staff__exact=0&is_superuser__exact=0".format(
                reverse("admin:auth_user_changelist")
            ),
            "{}?is_superuser__exact=0&is_staff__exact=0".format(
                reverse("admin:auth_user_changelist")
            ),
        )

        # Ignore ordering of _changelist_filters.
        self.assertURLEqual(
            "{}?_changelist_filters="
            "is_staff__exact%3D0%26is_superuser__exact%3D0".format(change_user_url),
            "{}?_changelist_filters="
            "is_superuser__exact%3D0%26is_staff__exact%3D0".format(change_user_url),
        )

    def get_changelist_filters(self):
        return {
            "is_superuser__exact": 0,
            "is_staff__exact": 0,
        }

    def get_changelist_filters_querystring(self):
        return urlencode(self.get_changelist_filters())

    def get_preserved_filters_querystring(self):
        return urlencode(
            {"_changelist_filters": self.get_changelist_filters_querystring()}
        )

    def get_sample_user_id(self):
        return self.joepublicuser.pk

    def get_changelist_url(self):
        return "%s?%s" % (
            reverse("admin:auth_user_changelist", current_app=self.admin_site.name),
            self.get_changelist_filters_querystring(),
        )

    def get_add_url(self, add_preserved_filters=True):
        url = reverse("admin:auth_user_add", current_app=self.admin_site.name)
        if add_preserved_filters:
            url = "%s?%s" % (url, self.get_preserved_filters_querystring())
        return url

    def get_change_url(self, user_id=None, add_preserved_filters=True):
        if user_id is None:
            user_id = self.get_sample_user_id()
        url = reverse(
            "admin:auth_user_change", args=(user_id,), current_app=self.admin_site.name
        )
        if add_preserved_filters:
            url = "%s?%s" % (url, self.get_preserved_filters_querystring())
        return url

    def get_history_url(self, user_id=None):
        if user_id is None:
            user_id = self.get_sample_user_id()
        return "%s?%s" % (
            reverse(
                "admin:auth_user_history",
                args=(user_id,),
                current_app=self.admin_site.name,
            ),
            self.get_preserved_filters_querystring(),
        )

    def get_delete_url(self, user_id=None):
        if user_id is None:
            user_id = self.get_sample_user_id()
        return "%s?%s" % (
            reverse(
                "admin:auth_user_delete",
                args=(user_id,),
                current_app=self.admin_site.name,
            ),
            self.get_preserved_filters_querystring(),
        )

    def test_changelist_view(self):
        response = self.client.get(self.get_changelist_url())
        self.assertEqual(response.status_code, 200)

        # Check the `change_view` link has the correct querystring.
        detail_link = re.search(
            '<a href="(.*?)">{}</a>'.format(self.joepublicuser.username),
            response.content.decode(),
        )
        self.assertURLEqual(detail_link[1], self.get_change_url())

    def test_change_view(self):
        # Get the `change_view`.
        response = self.client.get(self.get_change_url())
        self.assertEqual(response.status_code, 200)

        # Check the form action.
        form_action = re.search(
            '<form action="(.*?)" method="post" id="user_form" novalidate>',
            response.content.decode(),
        )
        self.assertURLEqual(
            form_action[1], "?%s" % self.get_preserved_filters_querystring()
        )

        # Check the history link.
        history_link = re.search(
            '<a href="(.*?)" class="historylink">History</a>', response.content.decode()
        )
        self.assertURLEqual(history_link[1], self.get_history_url())

        # Check the delete link.
        delete_link = re.search(
            '<a href="(.*?)" class="deletelink">Delete</a>', response.content.decode()
        )
        self.assertURLEqual(delete_link[1], self.get_delete_url())

        # Test redirect on "Save".
        post_data = {
            "username": "joepublic",
            "last_login_0": "2007-05-30",
            "last_login_1": "13:20:10",
            "date_joined_0": "2007-05-30",
            "date_joined_1": "13:20:10",
        }

        post_data["_save"] = 1
        response = self.client.post(self.get_change_url(), data=post_data)
        self.assertRedirects(response, self.get_changelist_url())
        post_data.pop("_save")

        # Test redirect on "Save and continue".
        post_data["_continue"] = 1
        response = self.client.post(self.get_change_url(), data=post_data)
        self.assertRedirects(response, self.get_change_url())
        post_data.pop("_continue")

        # Test redirect on "Save and add new".
        post_data["_addanother"] = 1
        response = self.client.post(self.get_change_url(), data=post_data)
        self.assertRedirects(response, self.get_add_url())
        post_data.pop("_addanother")

    def test_change_view_close_link(self):
        viewuser = User.objects.create_user(
            username="view", password="secret", is_staff=True
        )
        viewuser.user_permissions.add(
            get_perm(User, get_permission_codename("view", User._meta))
        )
        self.client.force_login(viewuser)
        response = self.client.get(self.get_change_url())
        close_link = re.search(
            '<a href="(.*?)" class="closelink">Close</a>', response.content.decode()
        )
        close_link = close_link[1].replace("&amp;", "&")
        self.assertURLEqual(close_link, self.get_changelist_url())

    def test_change_view_without_preserved_filters(self):
        response = self.client.get(self.get_change_url(add_preserved_filters=False))
        # The action attribute is omitted.
        self.assertContains(response, '<form method="post" id="user_form" novalidate>')

    def test_add_view(self):
        # Get the `add_view`.
        response = self.client.get(self.get_add_url())
        self.assertEqual(response.status_code, 200)

        # Check the form action.
        form_action = re.search(
            '<form action="(.*?)" method="post" id="user_form" novalidate>',
            response.content.decode(),
        )
        self.assertURLEqual(
            form_action[1], "?%s" % self.get_preserved_filters_querystring()
        )

        post_data = {
            "username": "dummy",
            "password1": "test",
            "password2": "test",
        }

        # Test redirect on "Save".
        post_data["_save"] = 1
        response = self.client.post(self.get_add_url(), data=post_data)
        self.assertRedirects(
            response, self.get_change_url(User.objects.get(username="dummy").pk)
        )
        post_data.pop("_save")

        # Test redirect on "Save and continue".
        post_data["username"] = "dummy2"
        post_data["_continue"] = 1
        response = self.client.post(self.get_add_url(), data=post_data)
        self.assertRedirects(
            response, self.get_change_url(User.objects.get(username="dummy2").pk)
        )
        post_data.pop("_continue")

        # Test redirect on "Save and add new".
        post_data["username"] = "dummy3"
        post_data["_addanother"] = 1
        response = self.client.post(self.get_add_url(), data=post_data)
        self.assertRedirects(response, self.get_add_url())
        post_data.pop("_addanother")

    def test_add_view_without_preserved_filters(self):
        response = self.client.get(self.get_add_url(add_preserved_filters=False))
        # The action attribute is omitted.
        self.assertContains(response, '<form method="post" id="user_form" novalidate>')

    def test_delete_view(self):
        # Test redirect on "Delete".
        response = self.client.post(self.get_delete_url(), {"post": "yes"})
        self.assertRedirects(response, self.get_changelist_url())

    def test_url_prefix(self):
        context = {
            "preserved_filters": self.get_preserved_filters_querystring(),
            "opts": User._meta,
        }
        prefixes = ("", "/prefix/", "/後台/")
        for prefix in prefixes:
            with self.subTest(prefix=prefix), override_script_prefix(prefix):
                url = reverse(
                    "admin:auth_user_changelist", current_app=self.admin_site.name
                )
                self.assertURLEqual(
                    self.get_changelist_url(),
                    add_preserved_filters(context, url),
                )


class NamespacedAdminKeepChangeListFiltersTests(AdminKeepChangeListFiltersTests):
    admin_site = site2


@override_settings(ROOT_URLCONF="admin_views.urls")
class TestLabelVisibility(TestCase):
    """#11277 -Labels of hidden fields in admin were not hidden."""

    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="super", password="secret", email="super@example.com"
        )

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_all_fields_visible(self):
        response = self.client.get(reverse("admin:admin_views_emptymodelvisible_add"))
        self.assert_fieldline_visible(response)
        self.assert_field_visible(response, "first")
        self.assert_field_visible(response, "second")

    def test_all_fields_hidden(self):
        response = self.client.get(reverse("admin:admin_views_emptymodelhidden_add"))
        self.assert_fieldline_hidden(response)
        self.assert_field_hidden(response, "first")
        self.assert_field_hidden(response, "second")

    def test_mixin(self):
        response = self.client.get(reverse("admin:admin_views_emptymodelmixin_add"))
        self.assert_fieldline_visible(response)
        self.assert_field_hidden(response, "first")
        self.assert_field_visible(response, "second")

    def assert_field_visible(self, response, field_name):
        self.assertContains(
            response, f'<div class="flex-container fieldBox field-{field_name}">'
        )

    def assert_field_hidden(self, response, field_name):
        self.assertContains(
            response, f'<div class="flex-container fieldBox field-{field_name} hidden">'
        )

    def assert_fieldline_visible(self, response):
        self.assertContains(response, '<div class="form-row field-first field-second">')

    def assert_fieldline_hidden(self, response):
        self.assertContains(response, '<div class="form-row hidden')


@override_settings(ROOT_URLCONF="admin_views.urls")
class AdminViewOnSiteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="super", password="secret", email="super@example.com"
        )

        cls.s1 = State.objects.create(name="New York")
        cls.s2 = State.objects.create(name="Illinois")
        cls.s3 = State.objects.create(name="California")
        cls.c1 = City.objects.create(state=cls.s1, name="New York")
        cls.c2 = City.objects.create(state=cls.s2, name="Chicago")
        cls.c3 = City.objects.create(state=cls.s3, name="San Francisco")
        cls.r1 = Restaurant.objects.create(city=cls.c1, name="Italian Pizza")
        cls.r2 = Restaurant.objects.create(city=cls.c1, name="Boulevard")
        cls.r3 = Restaurant.objects.create(city=cls.c2, name="Chinese Dinner")
        cls.r4 = Restaurant.objects.create(city=cls.c2, name="Angels")
        cls.r5 = Restaurant.objects.create(city=cls.c2, name="Take Away")
        cls.r6 = Restaurant.objects.create(city=cls.c3, name="The Unknown Restaurant")
        cls.w1 = Worker.objects.create(work_at=cls.r1, name="Mario", surname="Rossi")
        cls.w2 = Worker.objects.create(
            work_at=cls.r1, name="Antonio", surname="Bianchi"
        )
        cls.w3 = Worker.objects.create(work_at=cls.r1, name="John", surname="Doe")

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_add_view_form_and_formsets_run_validation(self):
        """
        Issue #20522
        Verifying that if the parent form fails validation, the inlines also
        run validation even if validation is contingent on parent form data.
        Also, assertFormError() and assertFormSetError() is usable for admin
        forms and formsets.
        """
        # The form validation should fail because 'some_required_info' is
        # not included on the parent form, and the family_name of the parent
        # does not match that of the child
        post_data = {
            "family_name": "Test1",
            "dependentchild_set-TOTAL_FORMS": "1",
            "dependentchild_set-INITIAL_FORMS": "0",
            "dependentchild_set-MAX_NUM_FORMS": "1",
            "dependentchild_set-0-id": "",
            "dependentchild_set-0-parent": "",
            "dependentchild_set-0-family_name": "Test2",
        }
        response = self.client.post(
            reverse("admin:admin_views_parentwithdependentchildren_add"), post_data
        )
        self.assertFormError(
            response.context["adminform"],
            "some_required_info",
            ["This field is required."],
        )
        self.assertFormError(response.context["adminform"], None, [])
        self.assertFormSetError(
            response.context["inline_admin_formset"],
            0,
            None,
            [
                "Children must share a family name with their parents in this "
                "contrived test case"
            ],
        )
        self.assertFormSetError(
            response.context["inline_admin_formset"], None, None, []
        )

    def test_change_view_form_and_formsets_run_validation(self):
        """
        Issue #20522
        Verifying that if the parent form fails validation, the inlines also
        run validation even if validation is contingent on parent form data
        """
        pwdc = ParentWithDependentChildren.objects.create(
            some_required_info=6, family_name="Test1"
        )
        # The form validation should fail because 'some_required_info' is
        # not included on the parent form, and the family_name of the parent
        # does not match that of the child
        post_data = {
            "family_name": "Test2",
            "dependentchild_set-TOTAL_FORMS": "1",
            "dependentchild_set-INITIAL_FORMS": "0",
            "dependentchild_set-MAX_NUM_FORMS": "1",
            "dependentchild_set-0-id": "",
            "dependentchild_set-0-parent": str(pwdc.id),
            "dependentchild_set-0-family_name": "Test1",
        }
        response = self.client.post(
            reverse(
                "admin:admin_views_parentwithdependentchildren_change", args=(pwdc.id,)
            ),
            post_data,
        )
        self.assertFormError(
            response.context["adminform"],
            "some_required_info",
            ["This field is required."],
        )
        self.assertFormSetError(
            response.context["inline_admin_formset"],
            0,
            None,
            [
                "Children must share a family name with their parents in this "
                "contrived test case"
            ],
        )

    def test_check(self):
        "The view_on_site value is either a boolean or a callable"
        try:
            admin = CityAdmin(City, AdminSite())
            CityAdmin.view_on_site = True
            self.assertEqual(admin.check(), [])
            CityAdmin.view_on_site = False
            self.assertEqual(admin.check(), [])
            CityAdmin.view_on_site = lambda obj: obj.get_absolute_url()
            self.assertEqual(admin.check(), [])
            CityAdmin.view_on_site = []
            self.assertEqual(
                admin.check(),
                [
                    Error(
                        "The value of 'view_on_site' must be a callable or a boolean "
                        "value.",
                        obj=CityAdmin,
                        id="admin.E025",
                    ),
                ],
            )
        finally:
            # Restore the original values for the benefit of other tests.
            CityAdmin.view_on_site = True

    def test_false(self):
        "The 'View on site' button is not displayed if view_on_site is False"
        response = self.client.get(
            reverse("admin:admin_views_restaurant_change", args=(self.r1.pk,))
        )
        content_type_pk = ContentType.objects.get_for_model(Restaurant).pk
        self.assertNotContains(
            response, reverse("admin:view_on_site", args=(content_type_pk, 1))
        )

    def test_true(self):
        "The default behavior is followed if view_on_site is True"
        response = self.client.get(
            reverse("admin:admin_views_city_change", args=(self.c1.pk,))
        )
        content_type_pk = ContentType.objects.get_for_model(City).pk
        self.assertContains(
            response, reverse("admin:view_on_site", args=(content_type_pk, self.c1.pk))
        )

    def test_callable(self):
        "The right link is displayed if view_on_site is a callable"
        response = self.client.get(
            reverse("admin:admin_views_worker_change", args=(self.w1.pk,))
        )
        self.assertContains(
            response, '"/worker/%s/%s/"' % (self.w1.surname, self.w1.name)
        )

    def test_missing_get_absolute_url(self):
        "None is returned if model doesn't have get_absolute_url"
        model_admin = ModelAdmin(Worker, None)
        self.assertIsNone(model_admin.get_view_on_site_url(Worker()))

    def test_custom_admin_site(self):
        model_admin = ModelAdmin(City, customadmin.site)
        content_type_pk = ContentType.objects.get_for_model(City).pk
        redirect_url = model_admin.get_view_on_site_url(self.c1)
        self.assertEqual(
            redirect_url,
            reverse(
                f"{customadmin.site.name}:view_on_site",
                kwargs={
                    "content_type_id": content_type_pk,
                    "object_id": self.c1.pk,
                },
            ),
        )


@override_settings(ROOT_URLCONF="admin_views.urls")
class InlineAdminViewOnSiteTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="super", password="secret", email="super@example.com"
        )

        cls.s1 = State.objects.create(name="New York")
        cls.s2 = State.objects.create(name="Illinois")
        cls.s3 = State.objects.create(name="California")
        cls.c1 = City.objects.create(state=cls.s1, name="New York")
        cls.c2 = City.objects.create(state=cls.s2, name="Chicago")
        cls.c3 = City.objects.create(state=cls.s3, name="San Francisco")
        cls.r1 = Restaurant.objects.create(city=cls.c1, name="Italian Pizza")
        cls.r2 = Restaurant.objects.create(city=cls.c1, name="Boulevard")
        cls.r3 = Restaurant.objects.create(city=cls.c2, name="Chinese Dinner")
        cls.r4 = Restaurant.objects.create(city=cls.c2, name="Angels")
        cls.r5 = Restaurant.objects.create(city=cls.c2, name="Take Away")
        cls.r6 = Restaurant.objects.create(city=cls.c3, name="The Unknown Restaurant")
        cls.w1 = Worker.objects.create(work_at=cls.r1, name="Mario", surname="Rossi")
        cls.w2 = Worker.objects.create(
            work_at=cls.r1, name="Antonio", surname="Bianchi"
        )
        cls.w3 = Worker.objects.create(work_at=cls.r1, name="John", surname="Doe")

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_false(self):
        "The 'View on site' button is not displayed if view_on_site is False"
        response = self.client.get(
            reverse("admin:admin_views_state_change", args=(self.s1.pk,))
        )
        content_type_pk = ContentType.objects.get_for_model(City).pk
        self.assertNotContains(
            response, reverse("admin:view_on_site", args=(content_type_pk, self.c1.pk))
        )

    def test_true(self):
        "The 'View on site' button is displayed if view_on_site is True"
        response = self.client.get(
            reverse("admin:admin_views_city_change", args=(self.c1.pk,))
        )
        content_type_pk = ContentType.objects.get_for_model(Restaurant).pk
        self.assertContains(
            response, reverse("admin:view_on_site", args=(content_type_pk, self.r1.pk))
        )

    def test_callable(self):
        "The right link is displayed if view_on_site is a callable"
        response = self.client.get(
            reverse("admin:admin_views_restaurant_change", args=(self.r1.pk,))
        )
        self.assertContains(
            response, '"/worker_inline/%s/%s/"' % (self.w1.surname, self.w1.name)
        )


@override_settings(ROOT_URLCONF="admin_views.urls")
class GetFormsetsWithInlinesArgumentTest(TestCase):
    """
    #23934 - When adding a new model instance in the admin, the 'obj' argument
    of get_formsets_with_inlines() should be None. When changing, it should be
    equal to the existing model instance.
    The GetFormsetsArgumentCheckingAdmin ModelAdmin throws an exception
    if obj is not None during add_view or obj is None during change_view.
    """

    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="super", password="secret", email="super@example.com"
        )

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_explicitly_provided_pk(self):
        post_data = {"name": "1"}
        response = self.client.post(
            reverse("admin:admin_views_explicitlyprovidedpk_add"), post_data
        )
        self.assertEqual(response.status_code, 302)

        post_data = {"name": "2"}
        response = self.client.post(
            reverse("admin:admin_views_explicitlyprovidedpk_change", args=(1,)),
            post_data,
        )
        self.assertEqual(response.status_code, 302)

    def test_implicitly_generated_pk(self):
        post_data = {"name": "1"}
        response = self.client.post(
            reverse("admin:admin_views_implicitlygeneratedpk_add"), post_data
        )
        self.assertEqual(response.status_code, 302)

        post_data = {"name": "2"}
        response = self.client.post(
            reverse("admin:admin_views_implicitlygeneratedpk_change", args=(1,)),
            post_data,
        )
        self.assertEqual(response.status_code, 302)


@override_settings(ROOT_URLCONF="admin_views.urls")
class AdminSiteFinalCatchAllPatternTests(TestCase):
    """
    Verifies the behaviour of the admin catch-all view.

    * Anonynous/non-staff users are redirected to login for all URLs, whether
      otherwise valid or not.
    * APPEND_SLASH is applied for staff if needed.
    * Otherwise Http404.
    * Catch-all view disabled via AdminSite.final_catch_all_view.
    """

    @classmethod
    def setUpTestData(cls):
        cls.staff_user = User.objects.create_user(
            username="staff",
            password="secret",
            email="staff@example.com",
            is_staff=True,
        )
        cls.non_staff_user = User.objects.create_user(
            username="user",
            password="secret",
            email="user@example.com",
            is_staff=False,
        )

    def test_unknown_url_redirects_login_if_not_authenticated(self):
        unknown_url = "/test_admin/admin/unknown/"
        response = self.client.get(unknown_url)
        self.assertRedirects(
            response, "%s?next=%s" % (reverse("admin:login"), unknown_url)
        )

    def test_unknown_url_404_if_authenticated(self):
        self.client.force_login(self.staff_user)
        unknown_url = "/test_admin/admin/unknown/"
        response = self.client.get(unknown_url)
        self.assertEqual(response.status_code, 404)

    def test_known_url_redirects_login_if_not_authenticated(self):
        known_url = reverse("admin:admin_views_article_changelist")
        response = self.client.get(known_url)
        self.assertRedirects(
            response, "%s?next=%s" % (reverse("admin:login"), known_url)
        )

    def test_known_url_missing_slash_redirects_login_if_not_authenticated(self):
        known_url = reverse("admin:admin_views_article_changelist")[:-1]
        response = self.client.get(known_url)
        # Redirects with the next URL also missing the slash.
        self.assertRedirects(
            response, "%s?next=%s" % (reverse("admin:login"), known_url)
        )

    def test_non_admin_url_shares_url_prefix(self):
        url = reverse("non_admin")[:-1]
        response = self.client.get(url)
        # Redirects with the next URL also missing the slash.
        self.assertRedirects(response, "%s?next=%s" % (reverse("admin:login"), url))

    def test_url_without_trailing_slash_if_not_authenticated(self):
        url = reverse("admin:article_extra_json")
        response = self.client.get(url)
        self.assertRedirects(response, "%s?next=%s" % (reverse("admin:login"), url))

    def test_unkown_url_without_trailing_slash_if_not_authenticated(self):
        url = reverse("admin:article_extra_json")[:-1]
        response = self.client.get(url)
        self.assertRedirects(response, "%s?next=%s" % (reverse("admin:login"), url))

    @override_settings(APPEND_SLASH=True)
    def test_missing_slash_append_slash_true_unknown_url(self):
        self.client.force_login(self.staff_user)
        unknown_url = "/test_admin/admin/unknown/"
        response = self.client.get(unknown_url[:-1])
        self.assertEqual(response.status_code, 404)

    @override_settings(APPEND_SLASH=True)
    def test_missing_slash_append_slash_true(self):
        self.client.force_login(self.staff_user)
        known_url = reverse("admin:admin_views_article_changelist")
        response = self.client.get(known_url[:-1])
        self.assertRedirects(
            response, known_url, status_code=301, target_status_code=403
        )

    @override_settings(APPEND_SLASH=True)
    def test_missing_slash_append_slash_true_query_string(self):
        self.client.force_login(self.staff_user)
        known_url = reverse("admin:admin_views_article_changelist")
        response = self.client.get("%s?id=1" % known_url[:-1])
        self.assertRedirects(
            response,
            f"{known_url}?id=1",
            status_code=301,
            fetch_redirect_response=False,
        )

    @override_settings(APPEND_SLASH=True)
    def test_missing_slash_append_slash_true_script_name(self):
        self.client.force_login(self.staff_user)
        known_url = reverse("admin:admin_views_article_changelist")
        response = self.client.get(known_url[:-1], SCRIPT_NAME="/prefix/")
        self.assertRedirects(
            response,
            "/prefix" + known_url,
            status_code=301,
            fetch_redirect_response=False,
        )

    @override_settings(APPEND_SLASH=True)
    def test_missing_slash_append_slash_true_script_name_query_string(self):
        self.client.force_login(self.staff_user)
        known_url = reverse("admin:admin_views_article_changelist")
        response = self.client.get("%s?id=1" % known_url[:-1], SCRIPT_NAME="/prefix/")
        self.assertRedirects(
            response,
            f"/prefix{known_url}?id=1",
            status_code=301,
            fetch_redirect_response=False,
        )

    @override_settings(APPEND_SLASH=True, FORCE_SCRIPT_NAME="/prefix/")
    def test_missing_slash_append_slash_true_force_script_name(self):
        self.client.force_login(self.staff_user)
        known_url = reverse("admin:admin_views_article_changelist")
        response = self.client.get(known_url[:-1])
        self.assertRedirects(
            response,
            "/prefix" + known_url,
            status_code=301,
            fetch_redirect_response=False,
        )

    @override_settings(APPEND_SLASH=True)
    def test_missing_slash_append_slash_true_non_staff_user(self):
        self.client.force_login(self.non_staff_user)
        known_url = reverse("admin:admin_views_article_changelist")
        response = self.client.get(known_url[:-1])
        self.assertRedirects(
            response,
            "/test_admin/admin/login/?next=/test_admin/admin/admin_views/article",
        )

    @override_settings(APPEND_SLASH=True)
    def test_missing_slash_append_slash_true_non_staff_user_query_string(self):
        self.client.force_login(self.non_staff_user)
        known_url = reverse("admin:admin_views_article_changelist")
        response = self.client.get("%s?id=1" % known_url[:-1])
        self.assertRedirects(
            response,
            "/test_admin/admin/login/?next=/test_admin/admin/admin_views/article"
            "%3Fid%3D1",
        )

    @override_settings(APPEND_SLASH=False)
    def test_missing_slash_append_slash_false(self):
        self.client.force_login(self.staff_user)
        known_url = reverse("admin:admin_views_article_changelist")
        response = self.client.get(known_url[:-1])
        self.assertEqual(response.status_code, 404)

    @override_settings(APPEND_SLASH=True)
    def test_single_model_no_append_slash(self):
        self.client.force_login(self.staff_user)
        known_url = reverse("admin9:admin_views_actor_changelist")
        response = self.client.get(known_url[:-1])
        self.assertEqual(response.status_code, 404)

    # Same tests above with final_catch_all_view=False.

    def test_unknown_url_404_if_not_authenticated_without_final_catch_all_view(self):
        unknown_url = "/test_admin/admin10/unknown/"
        response = self.client.get(unknown_url)
        self.assertEqual(response.status_code, 404)

    def test_unknown_url_404_if_authenticated_without_final_catch_all_view(self):
        self.client.force_login(self.staff_user)
        unknown_url = "/test_admin/admin10/unknown/"
        response = self.client.get(unknown_url)
        self.assertEqual(response.status_code, 404)

    def test_known_url_redirects_login_if_not_auth_without_final_catch_all_view(
        self,
    ):
        known_url = reverse("admin10:admin_views_article_changelist")
        response = self.client.get(known_url)
        self.assertRedirects(
            response, "%s?next=%s" % (reverse("admin10:login"), known_url)
        )

    def test_known_url_missing_slash_redirects_with_slash_if_not_auth_no_catch_all_view(
        self,
    ):
        known_url = reverse("admin10:admin_views_article_changelist")
        response = self.client.get(known_url[:-1])
        self.assertRedirects(
            response, known_url, status_code=301, fetch_redirect_response=False
        )

    def test_non_admin_url_shares_url_prefix_without_final_catch_all_view(self):
        url = reverse("non_admin10")
        response = self.client.get(url[:-1])
        self.assertRedirects(response, url, status_code=301)

    def test_url_no_trailing_slash_if_not_auth_without_final_catch_all_view(
        self,
    ):
        url = reverse("admin10:article_extra_json")
        response = self.client.get(url)
        self.assertRedirects(response, "%s?next=%s" % (reverse("admin10:login"), url))

    def test_unknown_url_no_trailing_slash_if_not_auth_without_final_catch_all_view(
        self,
    ):
        url = reverse("admin10:article_extra_json")[:-1]
        response = self.client.get(url)
        # Matches test_admin/admin10/admin_views/article/<path:object_id>/
        self.assertRedirects(
            response, url + "/", status_code=301, fetch_redirect_response=False
        )

    @override_settings(APPEND_SLASH=True)
    def test_missing_slash_append_slash_true_unknown_url_without_final_catch_all_view(
        self,
    ):
        self.client.force_login(self.staff_user)
        unknown_url = "/test_admin/admin10/unknown/"
        response = self.client.get(unknown_url[:-1])
        self.assertEqual(response.status_code, 404)

    @override_settings(APPEND_SLASH=True)
    def test_missing_slash_append_slash_true_without_final_catch_all_view(self):
        self.client.force_login(self.staff_user)
        known_url = reverse("admin10:admin_views_article_changelist")
        response = self.client.get(known_url[:-1])
        self.assertRedirects(
            response, known_url, status_code=301, target_status_code=403
        )

    @override_settings(APPEND_SLASH=True)
    def test_missing_slash_append_slash_true_query_without_final_catch_all_view(self):
        self.client.force_login(self.staff_user)
        known_url = reverse("admin10:admin_views_article_changelist")
        response = self.client.get("%s?id=1" % known_url[:-1])
        self.assertRedirects(
            response,
            f"{known_url}?id=1",
            status_code=301,
            fetch_redirect_response=False,
        )

    @override_settings(APPEND_SLASH=False)
    def test_missing_slash_append_slash_false_without_final_catch_all_view(self):
        self.client.force_login(self.staff_user)
        known_url = reverse("admin10:admin_views_article_changelist")
        response = self.client.get(known_url[:-1])
        self.assertEqual(response.status_code, 404)

    # Outside admin.

    def test_non_admin_url_404_if_not_authenticated(self):
        unknown_url = "/unknown/"
        response = self.client.get(unknown_url)
        # Does not redirect to the admin login.
        self.assertEqual(response.status_code, 404)
