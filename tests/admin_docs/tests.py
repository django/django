import sys
import unittest

from django.conf import settings
from django.contrib.sites.models import Site
from django.contrib.admindocs import utils
from django.contrib.admindocs.views import get_return_data_type
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import TestCase, modify_settings, override_settings

from .models import Person, Company


class MiscTests(TestCase):
    urls = 'admin_docs.urls'

    def setUp(self):
        User.objects.create_superuser('super', None, 'secret')
        self.client.login(username='super', password='secret')

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


@override_settings(PASSWORD_HASHERS=('django.contrib.auth.hashers.SHA1PasswordHasher',))
@unittest.skipUnless(utils.docutils_is_available, "no docutils installed.")
class AdminDocViewTests(TestCase):
    fixtures = ['data.xml']
    urls = 'admin_docs.urls'

    def setUp(self):
        self.client.login(username='super', password='secret')

    def test_index(self):
        self.client.logout()
        response = self.client.get(reverse('django-admindocs-docroot'), follow=True)
        # Should display the login screen
        self.assertContains(response,
            '<input type="hidden" name="next" value="/admindocs/" />', html=True)
        self.client.login(username='super', password='secret')
        response = self.client.get(reverse('django-admindocs-docroot'))
        self.assertContains(response, '<h1>Documentation</h1>', html=True)
        self.assertContains(response,
                            '<h1 id="site-name"><a href="/admin/">Django '
                            'administration</a></h1>')

    def test_bookmarklets(self):
        response = self.client.get(reverse('django-admindocs-bookmarklets'))
        self.assertContains(response, 'http://testserver/admin/doc/views/')

    def test_templatetag_index(self):
        response = self.client.get(reverse('django-admindocs-tags'))
        self.assertContains(response, '<h3 id="built_in-extends">extends</h3>', html=True)

    def test_templatefilter_index(self):
        response = self.client.get(reverse('django-admindocs-filters'))
        self.assertContains(response, '<h3 id="built_in-first">first</h3>', html=True)

    def test_view_index(self):
        response = self.client.get(reverse('django-admindocs-views-index'))
        self.assertContains(response,
            '<h3><a href="/admindocs/views/django.contrib.admindocs.views.BaseAdminDocsView/">/admindocs/</a></h3>',
            html=True)
        self.assertContains(response, 'Views by namespace test')
        self.assertContains(response, 'Name: <code>test:func</code>.')

    def test_view_detail(self):
        response = self.client.get(
            reverse('django-admindocs-views-detail',
                    args=['django.contrib.admindocs.views.BaseAdminDocsView']))
        # View docstring
        self.assertContains(response, 'Base view for admindocs views.')

    def test_view_detail_illegal_import(self):
        """
        #23601 - Ensure the view exists in the URLconf.
        """
        response = self.client.get(
            reverse('django-admindocs-views-detail',
                    args=['urlpatterns_reverse.nonimported_module.view']))
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
        response = self.client.get(reverse('django-admindocs-templates',
            args=['admin_doc/template_detail.html']))
        self.assertContains(response,
            '<h1>Template: "admin_doc/template_detail.html"</h1>', html=True)

    def test_missing_docutils(self):
        utils.docutils_is_available = False
        try:
            response = self.client.get(reverse('django-admindocs-docroot'))
            self.assertContains(response,
                '<h3>The admin documentation system requires Python\'s '
                '<a href="http://docutils.sf.net/">docutils</a> library.</h3>',
                html=True)
            self.assertContains(response,
                                '<h1 id="site-name"><a href="/admin/">Django '
                                'administration</a></h1>')
        finally:
            utils.docutils_is_available = True


@override_settings(PASSWORD_HASHERS=('django.contrib.auth.hashers.SHA1PasswordHasher',))
class XViewMiddlewareTest(TestCase):
    fixtures = ['data.xml']
    urls = 'admin_docs.urls'

    def test_xview_func(self):
        user = User.objects.get(username='super')
        response = self.client.head('/xview/func/')
        self.assertFalse('X-View' in response)
        self.client.login(username='super', password='secret')
        response = self.client.head('/xview/func/')
        self.assertTrue('X-View' in response)
        self.assertEqual(response['X-View'], 'admin_docs.views.xview')
        user.is_staff = False
        user.save()
        response = self.client.head('/xview/func/')
        self.assertFalse('X-View' in response)
        user.is_staff = True
        user.is_active = False
        user.save()
        response = self.client.head('/xview/func/')
        self.assertFalse('X-View' in response)

    def test_xview_class(self):
        user = User.objects.get(username='super')
        response = self.client.head('/xview/class/')
        self.assertFalse('X-View' in response)
        self.client.login(username='super', password='secret')
        response = self.client.head('/xview/class/')
        self.assertTrue('X-View' in response)
        self.assertEqual(response['X-View'], 'admin_docs.views.XViewClass')
        user.is_staff = False
        user.save()
        response = self.client.head('/xview/class/')
        self.assertFalse('X-View' in response)
        user.is_staff = True
        user.is_active = False
        user.save()
        response = self.client.head('/xview/class/')
        self.assertFalse('X-View' in response)


@unittest.skipUnless(utils.docutils_is_available, "no docutils installed.")
class DefaultRoleTest(TestCase):
    urls = 'admin_docs.urls'

    def test_parse_rst(self):
        """
        Tests that ``django.contrib.admindocs.utils.parse_rst`` uses
        ``cmsreference`` as the default role.
        """
        markup = ('<p><a class="reference external" href="/admindocs/%s">'
                  'title</a></p>\n')
        self.assertEqual(utils.parse_rst('`title`', 'model'),
                         markup % 'models/title/')
        self.assertEqual(utils.parse_rst('`title`', 'view'),
                         markup % 'views/title/')
        self.assertEqual(utils.parse_rst('`title`', 'template'),
                         markup % 'templates/title/')
        self.assertEqual(utils.parse_rst('`title`', 'filter'),
                         markup % 'filters/#title')
        self.assertEqual(utils.parse_rst('`title`', 'tag'),
                         markup % 'tags/#title')

    def test_publish_parts(self):
        """
        Tests that Django hasn't broken the default role for interpreted text
        when ``publish_parts`` is used directly, by setting it to
        ``cmsreference``. See #6681.
        """
        import docutils
        self.assertNotEqual(docutils.parsers.rst.roles.DEFAULT_INTERPRETED_ROLE,
                            'cmsreference')
        source = 'reST, `interpreted text`, default role.'
        markup = '<p>reST, <cite>interpreted text</cite>, default role.</p>\n'
        parts = docutils.core.publish_parts(source=source, writer_name="html4css1")
        self.assertEqual(parts['fragment'], markup)


@override_settings(PASSWORD_HASHERS=('django.contrib.auth.hashers.SHA1PasswordHasher',))
@unittest.skipUnless(utils.docutils_is_available, "no docutils installed.")
class TestModelDetailView(TestCase):
    """
    Tests that various details render correctly
    """

    fixtures = ['data.xml']
    urls = 'admin_docs.urls'

    def setUp(self):
        self.client.login(username='super', password='secret')
        self.response = self.client.get(
            reverse('django-admindocs-models-detail',
                    args=['admin_docs', 'person']))

    def test_method_excludes(self):
        """
        Test that methods that begin with strings defined in
        ``django.contrib.admindocs.views.MODEL_METHODS_EXCLUDE``
        do not get displayed in the admin docs
        """
        self.assertContains(self.response, "<td>get_full_name</td>")
        self.assertNotContains(self.response, "<td>_get_full_name</td>")
        self.assertNotContains(self.response, "<td>add_image</td>")
        self.assertNotContains(self.response, "<td>delete_image</td>")
        self.assertNotContains(self.response, "<td>set_status</td>")
        self.assertNotContains(self.response, "<td>save_changes</td>")

    def test_method_data_types(self):
        """
        We should be able to get a basic idea of the type returned
        by a method
        """
        company = Company.objects.create(name="Django")
        person = Person.objects.create(
            first_name="Human",
            last_name="User",
            company=company
        )

        self.assertEqual(
            get_return_data_type(person.get_status_count.__name__),
            'Integer'
        )

        self.assertEqual(
            get_return_data_type(person.get_groups_list.__name__),
            'List'
        )

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

    def test_model_with_no_backward_relations_render_only_relevant_fields(self):
        """
        A model with ``related_name`` of `+` should not show backward relationship
        links in admin docs
        """
        response = self.client.get(
            reverse('django-admindocs-models-detail',
                    args=['admin_docs', 'family']))

        fields = response.context_data.get('fields')
        self.assertEqual(len(fields), 2)
