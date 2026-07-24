import datetime
import json
from contextlib import contextmanager

from django.contrib import admin
from django.contrib.admin.exceptions import NotRegistered
from django.contrib.admin.tests import AdminPlaywrightTestCase
from django.contrib.admin.views.autocomplete import AutocompleteJsonView
from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.test import RequestFactory, override_settings
from django.urls import reverse, reverse_lazy

from .admin import AnswerAdmin, QuestionAdmin
from .models import (
    Answer,
    Author,
    Authorship,
    Bonus,
    Book,
    Employee,
    Manager,
    Parent,
    PKChild,
    Question,
    Toy,
    WorkHour,
)
from .tests import AdminViewBasicTestCase

PAGINATOR_SIZE = AutocompleteJsonView.paginate_by


class AuthorAdmin(admin.ModelAdmin):
    ordering = ["id"]
    search_fields = ["id"]


class AuthorshipInline(admin.TabularInline):
    model = Authorship
    autocomplete_fields = ["author"]


class BookAdmin(admin.ModelAdmin):
    inlines = [AuthorshipInline]


site = admin.AdminSite(name="autocomplete_admin")
site.register(Question, QuestionAdmin)
site.register(Answer, AnswerAdmin)
site.register(Author, AuthorAdmin)
site.register(Book, BookAdmin)
site.register(Employee, search_fields=["name"])
site.register(WorkHour, autocomplete_fields=["employee"])
site.register(Manager, search_fields=["name"])
site.register(Bonus, autocomplete_fields=["recipient"])
site.register(PKChild, search_fields=["name"])
site.register(Toy, autocomplete_fields=["child"])


@contextmanager
def model_admin(model, model_admin, admin_site=site):
    try:
        org_admin = admin_site.get_model_admin(model)
    except NotRegistered:
        org_admin = None
    else:
        admin_site.unregister(model)
    admin_site.register(model, model_admin)
    try:
        yield
    finally:
        if org_admin:
            admin_site._registry[model] = org_admin


class AutocompleteJsonViewTests(AdminViewBasicTestCase):
    as_view_args = {"admin_site": site}
    opts = {
        "app_label": Answer._meta.app_label,
        "model_name": Answer._meta.model_name,
        "field_name": "question",
    }
    factory = RequestFactory()
    url = reverse_lazy("autocomplete_admin:autocomplete")

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="user",
            password="secret",
            email="user@example.com",
            is_staff=True,
        )
        super().setUpTestData()

    def test_success(self):
        q = Question.objects.create(question="Is this a question?")
        request = self.factory.get(self.url, {"term": "is", **self.opts})
        request.user = self.superuser
        response = AutocompleteJsonView.as_view(**self.as_view_args)(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.text)
        self.assertEqual(
            data,
            {
                "results": [{"id": str(q.pk), "text": q.question}],
                "pagination": {"more": False},
            },
        )

    def test_custom_to_field(self):
        q = Question.objects.create(question="Is this a question?")
        request = self.factory.get(
            self.url,
            {"term": "is", **self.opts, "field_name": "question_with_to_field"},
        )
        request.user = self.superuser
        response = AutocompleteJsonView.as_view(**self.as_view_args)(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.text)
        self.assertEqual(
            data,
            {
                "results": [{"id": str(q.uuid), "text": q.question}],
                "pagination": {"more": False},
            },
        )

    def test_custom_to_field_permission_denied(self):
        Question.objects.create(question="Is this a question?")
        request = self.factory.get(
            self.url,
            {"term": "is", **self.opts, "field_name": "question_with_to_field"},
        )
        request.user = self.user
        with self.assertRaises(PermissionDenied):
            AutocompleteJsonView.as_view(**self.as_view_args)(request)

    def test_custom_to_field_custom_pk(self):
        q = Question.objects.create(question="Is this a question?")
        opts = {
            "app_label": Question._meta.app_label,
            "model_name": Question._meta.model_name,
            "field_name": "related_questions",
        }
        request = self.factory.get(self.url, {"term": "is", **opts})
        request.user = self.superuser
        response = AutocompleteJsonView.as_view(**self.as_view_args)(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.text)
        self.assertEqual(
            data,
            {
                "results": [{"id": str(q.big_id), "text": q.question}],
                "pagination": {"more": False},
            },
        )

    def test_to_field_resolution_with_mti(self):
        """
        to_field resolution should correctly resolve for target models using
        MTI. Tests for single and multi-level cases.
        """
        tests = [
            (Employee, WorkHour, "employee"),
            (Manager, Bonus, "recipient"),
        ]
        for Target, Remote, related_name in tests:
            with self.subTest(
                target_model=Target, remote_model=Remote, related_name=related_name
            ):
                o = Target.objects.create(
                    name="Frida Kahlo", gender=2, code="painter", alive=False
                )
                opts = {
                    "app_label": Remote._meta.app_label,
                    "model_name": Remote._meta.model_name,
                    "field_name": related_name,
                }
                request = self.factory.get(self.url, {"term": "frida", **opts})
                request.user = self.superuser
                response = AutocompleteJsonView.as_view(**self.as_view_args)(request)
                self.assertEqual(response.status_code, 200)
                data = json.loads(response.text)
                self.assertEqual(
                    data,
                    {
                        "results": [{"id": str(o.pk), "text": o.name}],
                        "pagination": {"more": False},
                    },
                )

    def test_to_field_resolution_with_fk_pk(self):
        p = Parent.objects.create(name="Bertie")
        c = PKChild.objects.create(parent=p, name="Anna")
        opts = {
            "app_label": Toy._meta.app_label,
            "model_name": Toy._meta.model_name,
            "field_name": "child",
        }
        request = self.factory.get(self.url, {"term": "anna", **opts})
        request.user = self.superuser
        response = AutocompleteJsonView.as_view(**self.as_view_args)(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.text)
        self.assertEqual(
            data,
            {
                "results": [{"id": str(c.pk), "text": c.name}],
                "pagination": {"more": False},
            },
        )

    def test_field_does_not_exist(self):
        request = self.factory.get(
            self.url, {"term": "is", **self.opts, "field_name": "does_not_exist"}
        )
        request.user = self.superuser
        with self.assertRaises(PermissionDenied):
            AutocompleteJsonView.as_view(**self.as_view_args)(request)

    def test_field_no_related_field(self):
        request = self.factory.get(
            self.url, {"term": "is", **self.opts, "field_name": "answer"}
        )
        request.user = self.superuser
        with self.assertRaises(PermissionDenied):
            AutocompleteJsonView.as_view(**self.as_view_args)(request)

    def test_field_does_not_allowed(self):
        request = self.factory.get(
            self.url, {"term": "is", **self.opts, "field_name": "related_questions"}
        )
        request.user = self.superuser
        with self.assertRaises(PermissionDenied):
            AutocompleteJsonView.as_view(**self.as_view_args)(request)

    def test_limit_choices_to(self):
        # Answer.question_with_to_field defines limit_choices_to to "those not
        # starting with 'not'".
        q = Question.objects.create(question="Is this a question?")
        Question.objects.create(question="Not a question.")
        request = self.factory.get(
            self.url,
            {"term": "is", **self.opts, "field_name": "question_with_to_field"},
        )
        request.user = self.superuser
        response = AutocompleteJsonView.as_view(**self.as_view_args)(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.text)
        self.assertEqual(
            data,
            {
                "results": [{"id": str(q.uuid), "text": q.question}],
                "pagination": {"more": False},
            },
        )

    def test_must_be_logged_in(self):
        response = self.client.get(self.url, {"term": "", **self.opts})
        self.assertEqual(response.status_code, 200)
        self.client.logout()
        response = self.client.get(self.url, {"term": "", **self.opts})
        self.assertEqual(response.status_code, 302)

    def test_has_view_or_change_permission_required(self):
        """
        Users require the change permission for the related model to the
        autocomplete view for it.
        """
        request = self.factory.get(self.url, {"term": "is", **self.opts})
        request.user = self.user
        with self.assertRaises(PermissionDenied):
            AutocompleteJsonView.as_view(**self.as_view_args)(request)
        for permission in ("view", "change"):
            with self.subTest(permission=permission):
                self.user.user_permissions.clear()
                p = Permission.objects.get(
                    content_type=ContentType.objects.get_for_model(Question),
                    codename="%s_question" % permission,
                )
                self.user.user_permissions.add(p)
                request.user = User.objects.get(pk=self.user.pk)
                response = AutocompleteJsonView.as_view(**self.as_view_args)(request)
                self.assertEqual(response.status_code, 200)

    def test_search_use_distinct(self):
        """
        Searching across model relations use QuerySet.distinct() to avoid
        duplicates.
        """
        q1 = Question.objects.create(question="question 1")
        q2 = Question.objects.create(question="question 2")
        q2.related_questions.add(q1)
        q3 = Question.objects.create(question="question 3")
        q3.related_questions.add(q1)
        request = self.factory.get(self.url, {"term": "question", **self.opts})
        request.user = self.superuser

        class DistinctQuestionAdmin(QuestionAdmin):
            search_fields = ["related_questions__question", "question"]

        with model_admin(Question, DistinctQuestionAdmin):
            response = AutocompleteJsonView.as_view(**self.as_view_args)(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.text)
        self.assertEqual(len(data["results"]), 3)

    def test_missing_search_fields(self):
        class EmptySearchAdmin(QuestionAdmin):
            search_fields = []

        with model_admin(Question, EmptySearchAdmin):
            msg = "EmptySearchAdmin must have search_fields for the autocomplete_view."
            with self.assertRaisesMessage(Http404, msg):
                site.autocomplete_view(
                    self.factory.get(self.url, {"term": "", **self.opts})
                )

    def test_get_paginator(self):
        """Search results are paginated."""

        class PKOrderingQuestionAdmin(QuestionAdmin):
            ordering = ["pk"]

        Question.objects.bulk_create(
            Question(question=str(i)) for i in range(PAGINATOR_SIZE + 10)
        )
        # The first page of results.
        request = self.factory.get(self.url, {"term": "", **self.opts})
        request.user = self.superuser
        with model_admin(Question, PKOrderingQuestionAdmin):
            response = AutocompleteJsonView.as_view(**self.as_view_args)(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.text)
        self.assertEqual(
            data,
            {
                "results": [
                    {"id": str(q.pk), "text": q.question}
                    for q in Question.objects.all()[:PAGINATOR_SIZE]
                ],
                "pagination": {"more": True},
            },
        )
        # The second page of results.
        request = self.factory.get(self.url, {"term": "", "page": "2", **self.opts})
        request.user = self.superuser
        with model_admin(Question, PKOrderingQuestionAdmin):
            response = AutocompleteJsonView.as_view(**self.as_view_args)(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.text)
        self.assertEqual(
            data,
            {
                "results": [
                    {"id": str(q.pk), "text": q.question}
                    for q in Question.objects.all()[PAGINATOR_SIZE:]
                ],
                "pagination": {"more": False},
            },
        )

    def test_serialize_result(self):
        class AutocompleteJsonSerializeResultView(AutocompleteJsonView):
            def serialize_result(self, obj, to_field_name):
                return {
                    **super().serialize_result(obj, to_field_name),
                    "posted": str(obj.posted),
                }

        Question.objects.create(question="Question 1", posted=datetime.date(2021, 8, 9))
        Question.objects.create(question="Question 2", posted=datetime.date(2021, 8, 7))
        request = self.factory.get(self.url, {"term": "question", **self.opts})
        request.user = self.superuser
        response = AutocompleteJsonSerializeResultView.as_view(**self.as_view_args)(
            request
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.text)
        self.assertEqual(
            data,
            {
                "results": [
                    {"id": str(q.pk), "text": q.question, "posted": str(q.posted)}
                    for q in Question.objects.order_by("-posted")
                ],
                "pagination": {"more": False},
            },
        )


@override_settings(ROOT_URLCONF="admin_views.urls")
class PlaywrightTests(AdminPlaywrightTestCase):
    available_apps = ["admin_views"] + AdminPlaywrightTestCase.available_apps

    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="super",
            password="secret",
            email="super@example.com",
        )
        self.admin_login(
            username="super",
            password="secret",
            login_url=reverse("autocomplete_admin:index"),
        )

    def test_select(self):
        self.page.goto(
            self.live_server_url + reverse("autocomplete_admin:admin_views_answer_add")
        )
        elem = self.page.locator(".select2-selection")
        with self.page.expect_response(lambda r: "autocomplete" in r.url):
            elem.click()  # Open the autocomplete dropdown.
        results = self.page.locator(".select2-results")
        self.expect(results).to_be_visible()
        option = self.page.locator(".select2-results__option")
        self.expect(option).to_have_text("No results found")
        elem.click()  # Close the autocomplete dropdown.
        q1 = Question.objects.create(question="Who am I?")
        Question.objects.bulk_create(
            Question(question=str(i)) for i in range(PAGINATOR_SIZE + 10)
        )
        with self.page.expect_response(lambda r: "autocomplete" in r.url):
            elem.click()  # Reopen the dropdown now that some objects exist.
        result_container = self.page.locator(".select2-results")
        self.expect(result_container).to_be_visible()
        # PAGINATOR_SIZE results and "Loading more results".
        self.expect(result_container.locator(".select2-results__option")).to_have_count(
            PAGINATOR_SIZE + 1
        )
        search = self.page.locator(".select2-search__field")
        # Load next page of results by scrolling to the bottom of the list.
        for _ in range(PAGINATOR_SIZE + 1):
            search.press("ArrowDown")
        # All objects are now loaded.
        self.expect(result_container.locator(".select2-results__option")).to_have_count(
            PAGINATOR_SIZE + 11
        )
        # Limit the results with the search field.
        with self.page.expect_response(lambda r: "autocomplete" in r.url):
            search.press_sequentially("Who")
            # Ajax request is delayed.
            self.expect(result_container).to_be_visible()
            self.expect(
                result_container.locator(".select2-results__option")
            ).to_have_count(PAGINATOR_SIZE + 12)
        self.expect(result_container).to_be_visible()
        self.expect(result_container.locator(".select2-results__option")).to_have_count(
            1
        )
        # Select the result.
        search.press("Enter")
        select = self.page.locator("#id_question")
        self.expect(select).to_have_value(str(q1.pk))

    def test_select_multiple(self):
        self.page.goto(
            self.live_server_url
            + reverse("autocomplete_admin:admin_views_question_add")
        )
        elem = self.page.locator(".select2-selection")
        with self.page.expect_response(lambda r: "autocomplete" in r.url):
            elem.click()  # Open the autocomplete dropdown.
        results = self.page.locator(".select2-results")
        self.expect(results).to_be_visible()
        option = self.page.locator(".select2-results__option")
        self.expect(option).to_have_text("No results found")
        elem.click()  # Close the autocomplete dropdown.
        Question.objects.create(question="Who am I?")
        Question.objects.bulk_create(
            Question(question=str(i)) for i in range(PAGINATOR_SIZE + 10)
        )
        with self.page.expect_response(lambda r: "autocomplete" in r.url):
            elem.click()  # Reopen the dropdown now that some objects exist.
        result_container = self.page.locator(".select2-results")
        self.expect(result_container).to_be_visible()
        self.expect(result_container.locator(".select2-results__option")).to_have_count(
            PAGINATOR_SIZE + 1
        )
        search = self.page.locator(".select2-search__field")
        # Load next page of results by scrolling to the bottom of the list.
        for _ in range(PAGINATOR_SIZE + 1):
            search.press("ArrowDown")
        self.expect(result_container.locator(".select2-results__option")).to_have_count(
            PAGINATOR_SIZE + 11
        )
        # Limit the results with the search field.
        with self.page.expect_response(lambda r: "autocomplete" in r.url):
            search.press_sequentially("Who")
            # Ajax request is delayed.
            self.expect(result_container).to_be_visible()
            self.expect(
                result_container.locator(".select2-results__option")
            ).to_have_count(PAGINATOR_SIZE + 12)
        self.expect(result_container).to_be_visible()
        self.expect(result_container.locator(".select2-results__option")).to_have_count(
            1
        )
        # Select the result.
        search.press("Enter")
        self.expect(self.page.locator(".select2-results")).to_be_hidden()
        # Reopen the dropdown.
        with self.page.expect_response(lambda r: "autocomplete" in r.url):
            elem.click()
        result_container = self.page.locator(".select2-results")
        self.expect(result_container).to_be_visible()
        # Add the first result to the selection.
        search.press("ArrowDown")
        search.press("Enter")
        self.expect(
            self.page.locator("#id_related_questions option:checked")
        ).to_have_count(2)

    def test_inline_add_another_widgets(self):
        def assertNoResults(row):
            elem = row.locator(".select2-selection")
            with self.page.expect_response(lambda r: "autocomplete" in r.url):
                elem.click()  # Open the autocomplete dropdown.
            results = self.page.locator(".select2-results")
            self.expect(results).to_be_visible()
            option = self.page.locator(".select2-results__option")
            self.expect(option).to_have_text("No results found")

        # Autocomplete works in rows present when the page loads.
        self.page.goto(
            self.live_server_url + reverse("autocomplete_admin:admin_views_book_add")
        )
        rows = self.page.locator(".dynamic-authorship_set")
        self.expect(rows).to_have_count(3)
        assertNoResults(rows.nth(0))
        # Autocomplete works in rows added using the "Add another" button.
        self.page.get_by_role("button", name="Add another Authorship").click()
        rows = self.page.locator(".dynamic-authorship_set")
        self.expect(rows).to_have_count(4)
        assertNoResults(rows.last)
