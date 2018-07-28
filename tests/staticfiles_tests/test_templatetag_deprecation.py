from urllib.parse import urljoin

from django.contrib.staticfiles import storage
from django.contrib.staticfiles.templatetags.staticfiles import static
from django.template import Context, Template
from django.test import SimpleTestCase, override_settings
from django.utils.deprecation import RemovedInDjango30Warning


class StaticTestStorage(storage.StaticFilesStorage):
    def url(self, name):
        return urljoin('https://example.com/assets/', name)


@override_settings(
    STATIC_URL='http://media.example.com/static/',
    INSTALLED_APPS=('django.contrib.staticfiles',),
    STATICFILES_STORAGE='staticfiles_tests.test_forms.StaticTestStorage',
)
class StaticDeprecationTests(SimpleTestCase):
    def test_templatetag_deprecated(self):
        msg = '{% load staticfiles %} is deprecated in favor of {% load static %}.'
        template = "{% load staticfiles %}{% static 'main.js' %}"
        with self.assertWarnsMessage(RemovedInDjango30Warning, msg):
            template = Template(template)
        rendered = template.render(Context())
        self.assertEqual(rendered, 'https://example.com/assets/main.js')

    def test_static_deprecated(self):
        msg = (
            'django.contrib.staticfiles.templatetags.static() is deprecated in '
            'favor of django.templatetags.static.static().'
        )
        with self.assertWarnsMessage(RemovedInDjango30Warning, msg):
            url = static('main.js')
        self.assertEqual(url, 'https://example.com/assets/main.js')
