import json

from django.contrib import admin
from django.contrib.admin.tests import AdminSeleniumTestCase
from django.contrib.admin.views.autocomplete import AutocompleteJsonView
from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType
from django.http import Http404
from django.test import RequestFactory, override_settings
from django.urls import reverse, reverse_lazy

from .admin import AnswerAdmin, QuestionAdmin
from .models import Answer, Author, Authorship, Book, Question
from .tests import AdminViewBasicTestCase

PAGINATOR_SIZE = AutocompleteJsonView.paginate_by


class AuthorAdmin(admin.ModelAdmin):
    ordering = ['id']
    search_fields = ['id']


class AuthorshipInline(admin.TabularInline):
    model = Authorship
    autocomplete_fields = ['author']


class BookAdmin(admin.ModelAdmin):
    inlines = [AuthorshipInline]


site = admin.AdminSite(name='autocomplete_admin')
site.register(Question, QuestionAdmin)
site.register(Answer, AnswerAdmin)
site.register(Author, AuthorAdmin)
site.register(Book, BookAdmin)


class AutocompleteJsonViewTests(AdminViewBasicTestCase):
    as_view_args = {'model_admin': QuestionAdmin(Question, site)}
    factory = RequestFactory()
    url = reverse_lazy('autocomplete_admin:admin_views_question_autocomplete')

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='user', password='secret',
            email='user@example.com', is_staff=True,
        )
        super().setUpTestData()

    def test_success(self):
        q = Question.objects.create(question='Is this a question?')
        request = self.factory.get(self.url, {'term': 'is'})
        request.user = self.superuser
        response = AutocompleteJsonView.as_view(**self.as_view_args)(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(data, {
            'results': [{'id': str(q.pk), 'text': q.question}],
            'pagination': {'more': False},
        })

    def test_must_be_logged_in(self):
        response = self.client.get(self.url, {'term': ''})
        self.assertEqual(response.status_code, 200)
        self.client.logout()
        response = self.client.get(self.url, {'term': ''})
        self.assertEqual(response.status_code, 302)

    def test_has_change_permission_required(self):
        """
        Users require the change permission for the related model to the
        autocomplete view for it.
        """
        request = self.factory.get(self.url, {'term': 'is'})
        self.user.is_staff = True
        self.user.save()
        request.user = self.user
        response = AutocompleteJsonView.as_view(**self.as_view_args)(request)
        self.assertEqual(response.status_code, 403)
        self.assertJSONEqual(response.content.decode('utf-8'), {'error': '403 Forbidden'})
        # Add the change permission and retry.
        p = Permission.objects.get(
            content_type=ContentType.objects.get_for_model(Question),
            codename='change_question',
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
        q1 = Question.objects.create(question='question 1')
        q2 = Question.objects.create(question='question 2')
        q2.related_questions.add(q1)
        q3 = Question.objects.create(question='question 3')
        q3.related_questions.add(q1)
        request = self.factory.get(self.url, {'term': 'question'})
        request.user = self.superuser

        class DistinctQuestionAdmin(QuestionAdmin):
            search_fields = ['related_questions__question', 'question']

        model_admin = DistinctQuestionAdmin(Question, site)
        response = AutocompleteJsonView.as_view(model_admin=model_admin)(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(len(data['results']), 3)

    def test_missing_search_fields(self):
        class EmptySearchAdmin(QuestionAdmin):
            search_fields = []

        model_admin = EmptySearchAdmin(Question, site)
        msg = 'EmptySearchAdmin must have search_fields for the autocomplete_view.'
        with self.assertRaisesMessage(Http404, msg):
            model_admin.autocomplete_view(self.factory.get(self.url))

    def test_get_paginator(self):
        """Search results are paginated."""
        Question.objects.bulk_create(Question(question=str(i)) for i in range(PAGINATOR_SIZE + 10))
        model_admin = QuestionAdmin(Question, site)
        model_admin.ordering = ['pk']
        # The first page of results.
        request = self.factory.get(self.url, {'term': ''})
        request.user = self.superuser
        response = AutocompleteJsonView.as_view(model_admin=model_admin)(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(data, {
            'results': [{'id': str(q.pk), 'text': q.question} for q in Question.objects.all()[:PAGINATOR_SIZE]],
            'pagination': {'more': True},
        })
        # The second page of results.
        request = self.factory.get(self.url, {'term': '', 'page': '2'})
        request.user = self.superuser
        response = AutocompleteJsonView.as_view(model_admin=model_admin)(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(data, {
            'results': [{'id': str(q.pk), 'text': q.question} for q in Question.objects.all()[PAGINATOR_SIZE:]],
            'pagination': {'more': False},
        })


@override_settings(ROOT_URLCONF='admin_views.urls')
class SeleniumTests(AdminSeleniumTestCase):
    available_apps = ['admin_views'] + AdminSeleniumTestCase.available_apps

    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username='super', password='secret', email='super@example.com',
        )
        self.admin_login(username='super', password='secret', login_url=reverse('autocomplete_admin:index'))

    def test_select(self):
        from selenium.webdriver.common.keys import Keys
        from selenium.webdriver.support.ui import Select
        self.selenium.get(self.live_server_url + reverse('autocomplete_admin:admin_views_answer_add'))
        elem = self.selenium.find_element_by_css_selector('.select2-selection')
        elem.click()  # Open the autocomplete dropdown.
        results = self.selenium.find_element_by_css_selector('.select2-results')
        self.assertTrue(results.is_displayed())
        option = self.selenium.find_element_by_css_selector('.select2-results__option')
        self.assertEqual(option.text, 'No results found')
        elem.click()  # Close the autocomplete dropdown.
        q1 = Question.objects.create(question='Who am I?')
        Question.objects.bulk_create(Question(question=str(i)) for i in range(PAGINATOR_SIZE + 10))
        elem.click()  # Reopen the dropdown now that some objects exist.
        result_container = self.selenium.find_element_by_css_selector('.select2-results')
        self.assertTrue(result_container.is_displayed())
        results = result_container.find_elements_by_css_selector('.select2-results__option')
        # PAGINATOR_SIZE results and "Loading more results".
        self.assertEqual(len(results), PAGINATOR_SIZE + 1)
        search = self.selenium.find_element_by_css_selector('.select2-search__field')
        # Load next page of results by scrolling to the bottom of the list.
        for _ in range(len(results)):
            search.send_keys(Keys.ARROW_DOWN)
        results = result_container.find_elements_by_css_selector('.select2-results__option')
        # All objects and "Loading more results".
        self.assertEqual(len(results), PAGINATOR_SIZE + 11)
        # Limit the results with the search field.
        search.send_keys('Who')
        results = result_container.find_elements_by_css_selector('.select2-results__option')
        self.assertEqual(len(results), 1)
        # Select the result.
        search.send_keys(Keys.RETURN)
        select = Select(self.selenium.find_element_by_id('id_question'))
        self.assertEqual(select.first_selected_option.get_attribute('value'), str(q1.pk))

    def test_select_multiple(self):
        from selenium.webdriver.common.keys import Keys
        from selenium.webdriver.support.ui import Select
        self.selenium.get(self.live_server_url + reverse('autocomplete_admin:admin_views_question_add'))
        elem = self.selenium.find_element_by_css_selector('.select2-selection')
        elem.click()  # Open the autocomplete dropdown.
        results = self.selenium.find_element_by_css_selector('.select2-results')
        self.assertTrue(results.is_displayed())
        option = self.selenium.find_element_by_css_selector('.select2-results__option')
        self.assertEqual(option.text, 'No results found')
        elem.click()  # Close the autocomplete dropdown.
        Question.objects.create(question='Who am I?')
        Question.objects.bulk_create(Question(question=str(i)) for i in range(PAGINATOR_SIZE + 10))
        elem.click()  # Reopen the dropdown now that some objects exist.
        result_container = self.selenium.find_element_by_css_selector('.select2-results')
        self.assertTrue(result_container.is_displayed())
        results = result_container.find_elements_by_css_selector('.select2-results__option')
        self.assertEqual(len(results), PAGINATOR_SIZE + 1)
        search = self.selenium.find_element_by_css_selector('.select2-search__field')
        # Load next page of results by scrolling to the bottom of the list.
        for _ in range(len(results)):
            search.send_keys(Keys.ARROW_DOWN)
        results = result_container.find_elements_by_css_selector('.select2-results__option')
        self.assertEqual(len(results), 31)
        # Limit the results with the search field.
        search.send_keys('Who')
        results = result_container.find_elements_by_css_selector('.select2-results__option')
        self.assertEqual(len(results), 1)
        # Select the result.
        search.send_keys(Keys.RETURN)
        # Reopen the dropdown and add the first result to the selection.
        elem.click()
        search.send_keys(Keys.ARROW_DOWN)
        search.send_keys(Keys.RETURN)
        select = Select(self.selenium.find_element_by_id('id_related_questions'))
        self.assertEqual(len(select.all_selected_options), 2)

    def test_inline_add_another_widgets(self):
        def assertNoResults(row):
            elem = row.find_element_by_css_selector('.select2-selection')
            elem.click()  # Open the autocomplete dropdown.
            results = self.selenium.find_element_by_css_selector('.select2-results')
            self.assertTrue(results.is_displayed())
            option = self.selenium.find_element_by_css_selector('.select2-results__option')
            self.assertEqual(option.text, 'No results found')

        # Autocomplete works in rows present when the page loads.
        self.selenium.get(self.live_server_url + reverse('autocomplete_admin:admin_views_book_add'))
        rows = self.selenium.find_elements_by_css_selector('.dynamic-authorship_set')
        self.assertEqual(len(rows), 3)
        assertNoResults(rows[0])
        # Autocomplete works in rows added using the "Add another" button.
        self.selenium.find_element_by_link_text('Add another Authorship').click()
        rows = self.selenium.find_elements_by_css_selector('.dynamic-authorship_set')
        self.assertEqual(len(rows), 4)
        assertNoResults(rows[-1])
