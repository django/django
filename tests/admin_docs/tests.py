import unittest

from django.conf import settings
from django.contrib.sites.models import Site
from django.contrib.admindocs import utils
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import TestCase, modify_settings, override_settings


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

    def test_model_index(self):
        response = self.client.get(reverse('django-admindocs-models-index'))
        self.assertContains(response, '<h2 id="app-auth">Auth</h2>', html=True)

    def test_model_detail(self):
        response = self.client.get(reverse('django-admindocs-models-detail',
            args=['auth', 'user']))
        # Check for attribute, many-to-many field
        self.assertContains(response,
            '<tr><td>email</td><td>Email address</td><td>email address</td></tr>', html=True)
        self.assertContains(response,
            '<tr><td>user_permissions.all</td><td>List</td><td>'
            '<p>all related <a class="reference external" href="/admindocs/models/auth.permission/">'
            'auth.Permission</a> objects</p></td></tr>', html=True)

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
