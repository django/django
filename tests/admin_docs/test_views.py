import sys
import unittest

from django.conf import settings
from django.contrib.admindocs import utils, views
from django.contrib.admindocs.views import get_return_data_type, simplify_regex
from django.contrib.sites.models import Site
from django.db import models
from django.db.models import fields
from django.test import SimpleTestCase, modify_settings, override_settings
from django.test.utils import captured_stderr
from django.urls import reverse

from .models import Company, Person
from .tests import AdminDocsTestCase, TestDataMixin


@unittest.skipUnless(utils.docutils_is_available, "no docutils installed.")
class AdminDocViewTests(TestDataMixin, AdminDocsTestCase):

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_index(self):
        response = self.client.get(reverse('django-admindocs-docroot'))
        self.assertContains(response, '<h1>Documentation</h1>', html=True)
        self.assertContains(response, '<h1 id="site-name"><a href="/admin/">Django administration</a></h1>')
        self.client.logout()
        response = self.client.get(reverse('django-admindocs-docroot'), follow=True)
        # Should display the login screen
        self.assertContains(response, '<input type="hidden" name="next" value="/admindocs/">', html=True)

    def test_bookmarklets(self):
        response = self.client.get(reverse('django-admindocs-bookmarklets'))
        self.assertContains(response, '/admindocs/views/')

    def test_templatetag_index(self):
        response = self.client.get(reverse('django-admindocs-tags'))
        self.assertContains(response, '<h3 id="built_in-extends">extends</h3>', html=True)

    def test_templatefilter_index(self):
        response = self.client.get(reverse('django-admindocs-filters'))
        self.assertContains(response, '<h3 id="built_in-first">first</h3>', html=True)

    def test_view_index(self):
        response = self.client.get(reverse('django-admindocs-views-index'))
        self.assertContains(
            response,
            '<h3><a href="/admindocs/views/django.contrib.admindocs.views.BaseAdminDocsView/">/admindocs/</a></h3>',
            html=True
        )
        self.assertContains(response, 'Views by namespace test')
        self.assertContains(response, 'Name: <code>test:func</code>.')
        self.assertContains(
            response,
            '<h3><a href="/admindocs/views/admin_docs.views.XViewCallableObject/">'
            '/xview/callable_object_without_xview/</a></h3>',
            html=True,
        )

    def test_view_index_with_method(self):
        """
        Views that are methods are listed correctly.
        """
        response = self.client.get(reverse('django-admindocs-views-index'))
        self.assertContains(
            response,
            '<h3><a href="/admindocs/views/django.contrib.admin.sites.AdminSite.index/">/admin/</a></h3>',
            html=True
        )

    def test_view_detail(self):
        url = reverse('django-admindocs-views-detail', args=['django.contrib.admindocs.views.BaseAdminDocsView'])
        response = self.client.get(url)
        # View docstring
        self.assertContains(response, 'Base view for admindocs views.')

    @override_settings(ROOT_URLCONF='admin_docs.namespace_urls')
    def test_namespaced_view_detail(self):
        url = reverse('django-admindocs-views-detail', args=['admin_docs.views.XViewClass'])
        response = self.client.get(url)
        self.assertContains(response, '<h1>admin_docs.views.XViewClass</h1>')

    def test_view_detail_illegal_import(self):
        url = reverse('django-admindocs-views-detail', args=['urlpatterns_reverse.nonimported_module.view'])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
        self.assertNotIn("urlpatterns_reverse.nonimported_module", sys.modules)

    def test_view_detail_as_method(self):
        """
        Views that are methods can be displayed.
        """
        url = reverse('django-admindocs-views-detail', args=['django.contrib.admin.sites.AdminSite.index'])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_model_index(self):
        response = self.client.get(reverse('django-admindocs-models-index'))
        self.assertContains(
            response,
            '<h2 id="app-auth">Authentication and Authorization (django.contrib.auth)</h2>',
            html=True
        )

    def test_template_detail(self):
        response = self.client.get(reverse('django-admindocs-templates', args=['admin_doc/template_detail.html']))
        self.assertContains(response, '<h1>Template: "admin_doc/template_detail.html"</h1>', html=True)

    def test_missing_docutils(self):
        utils.docutils_is_available = False
        try:
            response = self.client.get(reverse('django-admindocs-docroot'))
            self.assertContains(
                response,
                '<h3>The admin documentation system requires Python\'s '
                '<a href="http://docutils.sf.net/">docutils</a> library.</h3>',
                html=True
            )
            self.assertContains(response, '<h1 id="site-name"><a href="/admin/">Django administration</a></h1>')
        finally:
            utils.docutils_is_available = True

    @modify_settings(INSTALLED_APPS={'remove': 'django.contrib.sites'})
    @override_settings(SITE_ID=None)    # will restore SITE_ID after the test
    def test_no_sites_framework(self):
        """
        Without the sites framework, should not access SITE_ID or Site
        objects. Deleting settings is fine here as UserSettingsHolder is used.
        """
        Site.objects.all().delete()
        del settings.SITE_ID
        response = self.client.get(reverse('django-admindocs-views-index'))
        self.assertContains(response, 'View documentation')


@override_settings(TEMPLATES=[{
    'NAME': 'ONE',
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'APP_DIRS': True,
}, {
    'NAME': 'TWO',
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'APP_DIRS': True,
}])
@unittest.skipUnless(utils.docutils_is_available, "no docutils installed.")
class AdminDocViewWithMultipleEngines(AdminDocViewTests):

    def test_templatefilter_index(self):
        # Overridden because non-trivial TEMPLATES settings aren't supported
        # but the page shouldn't crash (#24125).
        response = self.client.get(reverse('django-admindocs-filters'))
        self.assertContains(response, '<title>Template filters</title>', html=True)

    def test_templatetag_index(self):
        # Overridden because non-trivial TEMPLATES settings aren't supported
        # but the page shouldn't crash (#24125).
        response = self.client.get(reverse('django-admindocs-tags'))
        self.assertContains(response, '<title>Template tags</title>', html=True)


@unittest.skipUnless(utils.docutils_is_available, "no docutils installed.")
class TestModelDetailView(TestDataMixin, AdminDocsTestCase):

    def setUp(self):
        self.client.force_login(self.superuser)
        with captured_stderr() as self.docutils_stderr:
            self.response = self.client.get(reverse('django-admindocs-models-detail', args=['admin_docs', 'Person']))

    def test_method_excludes(self):
        """
        Methods that begin with strings defined in
        ``django.contrib.admindocs.views.MODEL_METHODS_EXCLUDE``
        shouldn't be displayed in the admin docs.
        """
        self.assertContains(self.response, "<td>get_full_name</td>")
        self.assertNotContains(self.response, "<td>_get_full_name</td>")
        self.assertNotContains(self.response, "<td>add_image</td>")
        self.assertNotContains(self.response, "<td>delete_image</td>")
        self.assertNotContains(self.response, "<td>set_status</td>")
        self.assertNotContains(self.response, "<td>save_changes</td>")

    def test_methods_with_arguments(self):
        """
        Methods that take arguments should also displayed.
        """
        self.assertContains(self.response, "<h3>Methods with arguments</h3>")
        self.assertContains(self.response, "<td>rename_company</td>")
        self.assertContains(self.response, "<td>dummy_function</td>")
        self.assertContains(self.response, "<td>suffix_company_name</td>")

    def test_methods_with_arguments_display_arguments(self):
        """
        Methods with arguments should have their arguments displayed.
        """
        self.assertContains(self.response, "<td>new_name</td>")

    def test_methods_with_arguments_display_arguments_default_value(self):
        """
        Methods with keyword arguments should have their arguments displayed.
        """
        self.assertContains(self.response, "<td>suffix=&#39;ltd&#39;</td>")

    def test_methods_with_multiple_arguments_display_arguments(self):
        """
        Methods with multiple arguments should have all their arguments
        displayed, but omitting 'self'.
        """
        self.assertContains(self.response, "<td>baz, rox, *some_args, **some_kwargs</td>")

    def test_instance_of_property_methods_are_displayed(self):
        """Model properties are displayed as fields."""
        self.assertContains(self.response, '<td>a_property</td>')

    def test_method_data_types(self):
        company = Company.objects.create(name="Django")
        person = Person.objects.create(first_name="Human", last_name="User", company=company)
        self.assertEqual(get_return_data_type(person.get_status_count.__name__), 'Integer')
        self.assertEqual(get_return_data_type(person.get_groups_list.__name__), 'List')

    def test_descriptions_render_correctly(self):
        """
        The ``description`` field should render correctly for each field type.
        """
        # help text in fields
        self.assertContains(self.response, "<td>first name - The person's first name</td>")
        self.assertContains(self.response, "<td>last name - The person's last name</td>")

        # method docstrings
        self.assertContains(self.response, "<p>Get the full name of the person</p>")

        link = '<a class="reference external" href="/admindocs/models/%s/">%s</a>'
        markup = '<p>the related %s object</p>'
        company_markup = markup % (link % ("admin_docs.company", "admin_docs.Company"))

        # foreign keys
        self.assertContains(self.response, company_markup)

        # foreign keys with help text
        self.assertContains(self.response, "%s\n - place of work" % company_markup)

        # many to many fields
        self.assertContains(
            self.response,
            "number of related %s objects" % (link % ("admin_docs.group", "admin_docs.Group"))
        )
        self.assertContains(
            self.response,
            "all related %s objects" % (link % ("admin_docs.group", "admin_docs.Group"))
        )

        # "raw" and "include" directives are disabled
        self.assertContains(self.response, '<p>&quot;raw&quot; directive disabled.</p>',)
        self.assertContains(self.response, '.. raw:: html\n    :file: admin_docs/evilfile.txt')
        self.assertContains(self.response, '<p>&quot;include&quot; directive disabled.</p>',)
        self.assertContains(self.response, '.. include:: admin_docs/evilfile.txt')
        out = self.docutils_stderr.getvalue()
        self.assertIn('"raw" directive disabled', out)
        self.assertIn('"include" directive disabled', out)

    def test_model_with_many_to_one(self):
        link = '<a class="reference external" href="/admindocs/models/%s/">%s</a>'
        response = self.client.get(
            reverse('django-admindocs-models-detail', args=['admin_docs', 'company'])
        )
        self.assertContains(
            response,
            "number of related %s objects" % (link % ("admin_docs.person", "admin_docs.Person"))
        )
        self.assertContains(
            response,
            "all related %s objects" % (link % ("admin_docs.person", "admin_docs.Person"))
        )

    def test_model_with_no_backward_relations_render_only_relevant_fields(self):
        """
        A model with ``related_name`` of `+` shouldn't show backward
        relationship links.
        """
        response = self.client.get(reverse('django-admindocs-models-detail', args=['admin_docs', 'family']))
        fields = response.context_data.get('fields')
        self.assertEqual(len(fields), 2)

    def test_model_docstring_renders_correctly(self):
        summary = (
            '<h2 class="subhead"><p>Stores information about a person, related to <a class="reference external" '
            'href="/admindocs/models/myapp.company/">myapp.Company</a>.</p></h2>'
        )
        subheading = '<p><strong>Notes</strong></p>'
        body = '<p>Use <tt class="docutils literal">save_changes()</tt> when saving this object.</p>'
        model_body = (
            '<dl class="docutils"><dt><tt class="'
            'docutils literal">company</tt></dt><dd>Field storing <a class="'
            'reference external" href="/admindocs/models/myapp.company/">'
            'myapp.Company</a> where the person works.</dd></dl>'
        )
        self.assertContains(self.response, 'DESCRIPTION')
        self.assertContains(self.response, summary, html=True)
        self.assertContains(self.response, subheading, html=True)
        self.assertContains(self.response, body, html=True)
        self.assertContains(self.response, model_body, html=True)

    def test_model_detail_title(self):
        self.assertContains(self.response, '<h1>admin_docs.Person</h1>', html=True)

    def test_app_not_found(self):
        response = self.client.get(reverse('django-admindocs-models-detail', args=['doesnotexist', 'Person']))
        self.assertEqual(response.context['exception'], "App 'doesnotexist' not found")
        self.assertEqual(response.status_code, 404)

    def test_model_not_found(self):
        response = self.client.get(reverse('django-admindocs-models-detail', args=['admin_docs', 'doesnotexist']))
        self.assertEqual(response.context['exception'], "Model 'doesnotexist' not found in app 'admin_docs'")
        self.assertEqual(response.status_code, 404)


class CustomField(models.Field):
    description = "A custom field type"


class DescriptionLackingField(models.Field):
    pass


class TestFieldType(unittest.TestCase):
    def test_field_name(self):
        with self.assertRaises(AttributeError):
            views.get_readable_field_data_type("NotAField")

    def test_builtin_fields(self):
        self.assertEqual(
            views.get_readable_field_data_type(fields.BooleanField()),
            'Boolean (Either True or False)'
        )

    def test_custom_fields(self):
        self.assertEqual(views.get_readable_field_data_type(CustomField()), 'A custom field type')
        self.assertEqual(
            views.get_readable_field_data_type(DescriptionLackingField()),
            'Field of type: DescriptionLackingField'
        )


class AdminDocViewFunctionsTests(SimpleTestCase):

    def test_simplify_regex(self):
        tests = (
            (r'^a', '/a'),
            (r'^(?P<a>\w+)/b/(?P<c>\w+)/$', '/<a>/b/<c>/'),
            (r'^(?P<a>\w+)/b/(?P<c>\w+)$', '/<a>/b/<c>'),
            (r'^(?P<a>\w+)/b/(\w+)$', '/<a>/b/<var>'),
            (r'^(?P<a>\w+)/b/((x|y)\w+)$', '/<a>/b/<var>'),
            (r'^(?P<a>(x|y))/b/(?P<c>\w+)$', '/<a>/b/<c>'),
            (r'^(?P<a>(x|y))/b/(?P<c>\w+)ab', '/<a>/b/<c>ab'),
            (r'^(?P<a>(x|y)(\(|\)))/b/(?P<c>\w+)ab', '/<a>/b/<c>ab'),
            (r'^a/?$', '/a/'),
        )
        for pattern, output in tests:
            with self.subTest(pattern=pattern):
                self.assertEqual(simplify_regex(pattern), output)
