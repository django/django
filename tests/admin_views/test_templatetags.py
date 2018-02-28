import datetime

from django.contrib.admin import ModelAdmin
from django.contrib.admin.templatetags.admin_list import date_hierarchy
from django.contrib.admin.templatetags.admin_modify import submit_row
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase
from django.urls import reverse

from .admin import ArticleAdmin, site
from .models import Article, Question
from .tests import AdminViewBasicTestCase


class AdminTemplateTagsTest(AdminViewBasicTestCase):
    def test_submit_row(self):
        """
        submit_row template tag should pass whole context.
        """
        factory = RequestFactory()
        request = factory.get(reverse('admin:auth_user_change', args=[self.superuser.pk]))
        request.user = self.superuser
        admin = UserAdmin(User, site)
        extra_context = {'extra': True}
        response = admin.change_view(request, str(self.superuser.pk), extra_context=extra_context)
        template_context = submit_row(response.context_data)
        self.assertIs(template_context['extra'], True)
        self.assertIs(template_context['show_save'], True)

    def test_override_change_form_template_tags(self):
        """
        admin_modify template tags follow the standard search pattern
        admin/app_label/model/template.html.
        """
        factory = RequestFactory()
        article = Article.objects.all()[0]
        request = factory.get(reverse('admin:admin_views_article_change', args=[article.pk]))
        request.user = self.superuser
        admin = ArticleAdmin(Article, site)
        extra_context = {'show_publish': True, 'extra': True}
        response = admin.change_view(request, str(article.pk), extra_context=extra_context)
        response.render()
        self.assertIs(response.context_data['show_publish'], True)
        self.assertIs(response.context_data['extra'], True)
        content = str(response.content)
        self.assertIn('name="_save"', content)
        self.assertIn('name="_publish"', content)
        self.assertIn('override-change_form_object_tools', content)
        self.assertIn('override-prepopulated_fields_js', content)

    def test_override_change_list_template_tags(self):
        """
        admin_list template tags follow the standard search pattern
        admin/app_label/model/template.html.
        """
        factory = RequestFactory()
        request = factory.get(reverse('admin:admin_views_article_changelist'))
        request.user = self.superuser
        admin = ArticleAdmin(Article, site)
        admin.date_hierarchy = 'date'
        admin.search_fields = ('title', 'content')
        response = admin.changelist_view(request)
        response.render()
        content = str(response.content)
        self.assertIn('override-actions', content)
        self.assertIn('override-change_list_object_tools', content)
        self.assertIn('override-change_list_results', content)
        self.assertIn('override-date_hierarchy', content)
        self.assertIn('override-pagination', content)
        self.assertIn('override-search_form', content)


class DateHierarchyTests(TestCase):
    factory = RequestFactory()

    def test_choice_links(self):
        modeladmin = ModelAdmin(Question, site)
        modeladmin.date_hierarchy = 'posted'

        posted_dates = (
            datetime.date(2017, 10, 1),
            datetime.date(2017, 10, 1),
            datetime.date(2017, 12, 15),
            datetime.date(2017, 12, 15),
            datetime.date(2017, 12, 31),
            datetime.date(2018, 2, 1),
        )
        Question.objects.bulk_create(Question(question='q', posted=posted) for posted in posted_dates)

        tests = (
            ({}, [['year=2017'], ['year=2018']]),
            ({'year': 2016}, []),
            ({'year': 2017}, [['month=10', 'year=2017'], ['month=12', 'year=2017']]),
            ({'year': 2017, 'month': 9}, []),
            ({'year': 2017, 'month': 12}, [['day=15', 'month=12', 'year=2017'], ['day=31', 'month=12', 'year=2017']]),
        )
        for query, expected_choices in tests:
            with self.subTest(query=query):
                query = {'posted__%s' % q: val for q, val in query.items()}
                request = self.factory.get('/', query)
                changelist = modeladmin.get_changelist_instance(request)
                spec = date_hierarchy(changelist)
                choices = [choice['link'] for choice in spec['choices']]
                expected_choices = [
                    '&'.join('posted__%s' % c for c in choice) for choice in expected_choices
                ]
                expected_choices = [('?' + choice) if choice else '' for choice in expected_choices]
                self.assertEqual(choices, expected_choices)
