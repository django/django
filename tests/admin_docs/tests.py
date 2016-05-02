import sys
import unittest

from django.conf import settings
from django.contrib.admindocs import utils
from django.contrib.admindocs.views import get_return_data_type
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.test import TestCase, modify_settings, override_settings
from django.test.utils import captured_stderr
from django.urls import reverse

from .models import Company, Person


class TestDataMixin(object):

    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(username='super', password='secret', email='super@example.com')


@override_settings(ROOT_URLCONF='admin_docs.urls')
@modify_settings(INSTALLED_APPS={'append': 'django.contrib.admindocs'})
class AdminDocsTestCase(TestCase):
    pass


class MiscTests(AdminDocsTestCase):

    def setUp(self):
        superuser = User.objects.create_superuser('super', None, 'secret')
        self.client.force_login(superuser)

    @modify_settings(INSTALLED_APPS={'remove': 'django.contrib.sites'})
    @override_settings(SITE_ID=None)    # will restore SITE_ID after the test
    def test_no_sites_framework(self):
        """
        Without the sites framework, should not access SITE_ID or Site
        objects. Deleting settings is fine here as UserSettingsHolder is used.
        """
        Site.objects.all().delete()
        del settings.SITE_ID
        self.client.get('/admindocs/views/')  # should not raise


@unittest.skipUnless(utils.docutils_is_available, "no docutils installed.")
class AdminDocViewTests(TestDataMixin, AdminDocsTestCase):

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_index(self):
        self.client.logout()
        response = self.client.get(reverse('django-admindocs-docroot'), follow=True)
        # Should display the login screen
        self.assertContains(response, '<input type="hidden" name="next" value="/admindocs/" />', html=True)
        self.client.force_login(self.superuser)
        response = self.client.get(reverse('django-admindocs-docroot'))
        self.assertContains(response, '<h1>Documentation</h1>', html=True)
        self.assertContains(response, '<h1 id="site-name"><a href="/admin/">Django administration</a></h1>')

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

    def test_view_detail(self):
        url = reverse('django-admindocs-views-detail', args=['django.contrib.admindocs.views.BaseAdminDocsView'])
        response = self.client.get(url)
        # View docstring
        self.assertContains(response, 'Base view for admindocs views.')

    def test_view_detail_illegal_import(self):
        """
        #23601 - Ensure the view exists in the URLconf.
        """
        url = reverse('django-admindocs-views-detail', args=['urlpatterns_reverse.nonimported_module.view'])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
        self.assertNotIn("urlpatterns_reverse.nonimported_module", sys.modules)

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


class XViewMiddlewareTest(TestDataMixin, AdminDocsTestCase):

    def test_xview_func(self):
        user = User.objects.get(username='super')
        response = self.client.head('/xview/func/')
        self.assertNotIn('X-View', response)
        self.client.force_login(self.superuser)
        response = self.client.head('/xview/func/')
        self.assertIn('X-View', response)
        self.assertEqual(response['X-View'], 'admin_docs.views.xview')
        user.is_staff = False
        user.save()
        response = self.client.head('/xview/func/')
        self.assertNotIn('X-View', response)
        user.is_staff = True
        user.is_active = False
        user.save()
        response = self.client.head('/xview/func/')
        self.assertNotIn('X-View', response)

    def test_xview_class(self):
        user = User.objects.get(username='super')
        response = self.client.head('/xview/class/')
        self.assertNotIn('X-View', response)
        self.client.force_login(self.superuser)
        response = self.client.head('/xview/class/')
        self.assertIn('X-View', response)
        self.assertEqual(response['X-View'], 'admin_docs.views.XViewClass')
        user.is_staff = False
        user.save()
        response = self.client.head('/xview/class/')
        self.assertNotIn('X-View', response)
        user.is_staff = True
        user.is_active = False
        user.save()
        response = self.client.head('/xview/class/')
        self.assertNotIn('X-View', response)


@unittest.skipUnless(utils.docutils_is_available, "no docutils installed.")
class DefaultRoleTest(AdminDocsTestCase):

    def test_parse_rst(self):
        """
        ``django.contrib.admindocs.utils.parse_rst`` should use
        ``cmsreference`` as the default role.
        """
        markup = '<p><a class="reference external" href="/admindocs/%s">title</a></p>\n'
        self.assertEqual(utils.parse_rst('`title`', 'model'), markup % 'models/title/')
        self.assertEqual(utils.parse_rst('`title`', 'view'), markup % 'views/title/')
        self.assertEqual(utils.parse_rst('`title`', 'template'), markup % 'templates/title/')
        self.assertEqual(utils.parse_rst('`title`', 'filter'), markup % 'filters/#title')
        self.assertEqual(utils.parse_rst('`title`', 'tag'), markup % 'tags/#title')

    def test_publish_parts(self):
        """
        Django shouldn't break the default role for interpreted text
        when ``publish_parts`` is used directly, by setting it to
        ``cmsreference``. See #6681.
        """
        import docutils
        self.assertNotEqual(docutils.parsers.rst.roles.DEFAULT_INTERPRETED_ROLE, 'cmsreference')
        source = 'reST, `interpreted text`, default role.'
        markup = '<p>reST, <cite>interpreted text</cite>, default role.</p>\n'
        parts = docutils.core.publish_parts(source=source, writer_name="html4css1")
        self.assertEqual(parts['fragment'], markup)


@unittest.skipUnless(utils.docutils_is_available, "no docutils installed.")
class TestModelDetailView(TestDataMixin, AdminDocsTestCase):
    """
    Tests that various details render correctly
    """

    def setUp(self):
        self.client.force_login(self.superuser)
        with captured_stderr() as self.docutils_stderr:
            self.response = self.client.get(reverse('django-admindocs-models-detail', args=['admin_docs', 'Person']))

    def test_method_excludes(self):
        """
        Methods that begin with strings defined in
        ``django.contrib.admindocs.views.MODEL_METHODS_EXCLUDE``
        should not get displayed in the admin docs.
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

    def test_method_data_types(self):
        """
        We should be able to get a basic idea of the type returned
        by a method
        """
        company = Company.objects.create(name="Django")
        person = Person.objects.create(first_name="Human", last_name="User", company=company)
        self.assertEqual(get_return_data_type(person.get_status_count.__name__), 'Integer')
        self.assertEqual(get_return_data_type(person.get_groups_list.__name__), 'List')

    def test_descriptions_render_correctly(self):
        """
        The ``description`` field should render correctly for each type of field
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
        A model with ``related_name`` of `+` should not show backward relationship
        links in admin docs
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


@unittest.skipUnless(utils.docutils_is_available, "no docutils installed.")
class TestUtils(AdminDocsTestCase):
    """
    This __doc__ output is required for testing. I copied this example from
    `admindocs` documentation. (TITLE)

    Display an individual :model:`myapp.MyModel`.

    **Context**

    ``RequestContext``

    ``mymodel``
        An instance of :model:`myapp.MyModel`.

    **Template:**

    :template:`myapp/my_template.html` (DESCRIPTION)

    some_metadata: some data
    """

    def setUp(self):
        self.docstring = self.__doc__

    def test_trim_docstring(self):
        trim_docstring_output = utils.trim_docstring(self.docstring)
        trimmed_docstring = (
            'This __doc__ output is required for testing. I copied this '
            'example from\n`admindocs` documentation. (TITLE)\n\n'
            'Display an individual :model:`myapp.MyModel`.\n\n'
            '**Context**\n\n``RequestContext``\n\n``mymodel``\n'
            '    An instance of :model:`myapp.MyModel`.\n\n'
            '**Template:**\n\n:template:`myapp/my_template.html` '
            '(DESCRIPTION)\n\nsome_metadata: some data'
        )
        self.assertEqual(trim_docstring_output, trimmed_docstring)

    def test_parse_docstring(self):
        title, description, metadata = utils.parse_docstring(self.docstring)
        docstring_title = (
            'This __doc__ output is required for testing. I copied this example from\n'
            '`admindocs` documentation. (TITLE)'
        )
        docstring_description = (
            'Display an individual :model:`myapp.MyModel`.\n\n'
            '**Context**\n\n``RequestContext``\n\n``mymodel``\n'
            '    An instance of :model:`myapp.MyModel`.\n\n'
            '**Template:**\n\n:template:`myapp/my_template.html` '
            '(DESCRIPTION)'
        )
        self.assertEqual(title, docstring_title)
        self.assertEqual(description, docstring_description)
        self.assertEqual(metadata, {'some_metadata': 'some data'})

    def test_title_output(self):
        title, description, metadata = utils.parse_docstring(self.docstring)
        title_output = utils.parse_rst(title, 'model', 'model:admindocs')
        self.assertIn('TITLE', title_output)

        title_rendered = (
            '<p>This __doc__ output is required for testing. I copied this '
            'example from\n<a class="reference external" '
            'href="/admindocs/models/admindocs/">admindocs</a> documentation. '
            '(TITLE)</p>\n'
        )
        self.assertHTMLEqual(title_output, title_rendered)

    def test_description_output(self):
        title, description, metadata = utils.parse_docstring(self.docstring)
        description_output = utils.parse_rst(description, 'model', 'model:admindocs')

        description_rendered = (
            '<p>Display an individual <a class="reference external" '
            'href="/admindocs/models/myapp.mymodel/">myapp.MyModel</a>.</p>\n'
            '<p><strong>Context</strong></p>\n<p><tt class="docutils literal">'
            'RequestContext</tt></p>\n<dl class="docutils">\n<dt><tt class="'
            'docutils literal">mymodel</tt></dt>\n<dd>An instance of <a class="'
            'reference external" href="/admindocs/models/myapp.mymodel/">'
            'myapp.MyModel</a>.</dd>\n</dl>\n<p><strong>Template:</strong></p>'
            '\n<p><a class="reference external" href="/admindocs/templates/'
            'myapp/my_template.html/">myapp/my_template.html</a> (DESCRIPTION)'
            '</p>\n'
        )
        self.assertHTMLEqual(description_output, description_rendered)

    def test_initial_header_level(self):
        header = 'should be h3...\n\nHeader\n------\n'
        output = utils.parse_rst(header, 'header')
        self.assertIn('<h3>Header</h3>', output)
