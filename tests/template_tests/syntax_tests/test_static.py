from urllib.parse import urljoin

from django.conf import settings
from django.template import TemplateSyntaxError
from django.test import SimpleTestCase, override_settings

from ..utils import setup


@override_settings(INSTALLED_APPS=[], MEDIA_URL='/media/', STATIC_URL='/static/')
class StaticTagTests(SimpleTestCase):
    libraries = {'static': 'django.templatetags.static'}

    @setup({'static-prefixtag01': '{% load static %}{% get_static_prefix %}'})
    def test_static_prefixtag01(self):
        output = self.engine.render_to_string('static-prefixtag01')
        self.assertEqual(output, settings.STATIC_URL)

    @setup({'static-prefixtag02': '{% load static %}'
                                  '{% get_static_prefix as static_prefix %}{{ static_prefix }}'})
    def test_static_prefixtag02(self):
        output = self.engine.render_to_string('static-prefixtag02')
        self.assertEqual(output, settings.STATIC_URL)

    @setup({'static-prefixtag03': '{% load static %}{% get_media_prefix %}'})
    def test_static_prefixtag03(self):
        output = self.engine.render_to_string('static-prefixtag03')
        self.assertEqual(output, settings.MEDIA_URL)

    @setup({'static-prefixtag04': '{% load static %}'
                                  '{% get_media_prefix as media_prefix %}{{ media_prefix }}'})
    def test_static_prefixtag04(self):
        output = self.engine.render_to_string('static-prefixtag04')
        self.assertEqual(output, settings.MEDIA_URL)

    @setup({'t': '{% load static %}{% get_media_prefix ad media_prefix %}{{ media_prefix }}'})
    def test_static_prefixtag_without_as(self):
        msg = "First argument in 'get_media_prefix' must be 'as'"
        with self.assertRaisesMessage(TemplateSyntaxError, msg):
            self.engine.render_to_string('t')

    @setup({'static-statictag01': '{% load static %}{% static "admin/base.css" %}'})
    def test_static_statictag01(self):
        output = self.engine.render_to_string('static-statictag01')
        self.assertEqual(output, urljoin(settings.STATIC_URL, 'admin/base.css'))

    @setup({'static-statictag02': '{% load static %}{% static base_css %}'})
    def test_static_statictag02(self):
        output = self.engine.render_to_string('static-statictag02', {'base_css': 'admin/base.css'})
        self.assertEqual(output, urljoin(settings.STATIC_URL, 'admin/base.css'))

    @setup({'static-statictag03': '{% load static %}{% static "admin/base.css" as foo %}{{ foo }}'})
    def test_static_statictag03(self):
        output = self.engine.render_to_string('static-statictag03')
        self.assertEqual(output, urljoin(settings.STATIC_URL, 'admin/base.css'))

    @setup({'static-statictag04': '{% load static %}{% static base_css as foo %}{{ foo }}'})
    def test_static_statictag04(self):
        output = self.engine.render_to_string('static-statictag04', {'base_css': 'admin/base.css'})
        self.assertEqual(output, urljoin(settings.STATIC_URL, 'admin/base.css'))

    @setup({'static-statictag05': '{% load static %}{% static "special?chars&quoted.html" %}'})
    def test_static_quotes_urls(self):
        output = self.engine.render_to_string('static-statictag05')
        self.assertEqual(output, urljoin(settings.STATIC_URL, '/static/special%3Fchars%26quoted.html'))

    @setup({'t': '{% load static %}{% static %}'})
    def test_static_statictag_without_path(self):
        msg = "'static' takes at least one argument (path to file)"
        with self.assertRaisesMessage(TemplateSyntaxError, msg):
            self.engine.render_to_string('t')


@override_settings(
    INSTALLED_APPS=['template_tests.apps.MyAdmin', 'template_tests.apps.MyAuth'],
    MEDIA_URL='/media/', STATIC_URL='/static/'
)
class SiteAssetsTagTests(SimpleTestCase):
    libraries = {'static': 'django.templatetags.static'}

    @setup({
        'siteassets01a': '{% load static %}{% site_assets %}',
        'siteassets01b': "{% load static %}{% site_assets 'myadmin, myauth' %}",
        'siteassets01c': "{% load static %}{% site_assets 'myadmin  myauth' %}",
    })
    def test_site_assets(self):
        expected_output = (
            '<link href="/static/css/admin.css" rel="stylesheet" type="text/css">\n'
            '<script src="https://code.jquery.com/jquery-3.1.1.js"></script>\n'
            '<script src="/static/js/admin.js"></script>\n'
            '<link href="/static/css/auth.css" rel="stylesheet" type="text/css">'
        )
        output = self.engine.render_to_string('siteassets01a')
        self.assertEqual(output, expected_output)
        output = self.engine.render_to_string('siteassets01b')
        self.assertEqual(output, expected_output)
        output = self.engine.render_to_string('siteassets01c')
        self.assertEqual(output, expected_output)

    @setup({'siteassets02': "{% load static %}{% site_assets '-myadmin' %}"})
    def test_site_assets_exclude(self):
        output = self.engine.render_to_string('siteassets02')
        self.assertEqual(
            output,
            '<link href="/static/css/auth.css" rel="stylesheet" type="text/css">\n'
            '<script src="https://code.jquery.com/jquery-3.1.1.js"></script>\n'
            '<script src="/static/js/admin.js"></script>'
        )
