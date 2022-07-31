from urllib.parse import urljoin

from django.contrib.staticfiles import storage
from django.forms import Media
from django.templatetags.static import static
from django.test import SimpleTestCase, override_settings


class StaticTestStorage(storage.StaticFilesStorage):
    def url(self, name):
        return urljoin("https://example.com/assets/", name)


@override_settings(
    STATIC_URL="http://media.example.com/static/",
    INSTALLED_APPS=("django.contrib.staticfiles",),
    STATICFILES_STORAGE="staticfiles_tests.test_forms.StaticTestStorage",
)
class StaticFilesFormsMediaTestCase(SimpleTestCase):
    def test_absolute_url(self):
        m = Media(
            css={"all": ("path/to/css1", "/path/to/css2")},
            js=(
                "/path/to/js1",
                "http://media.other.com/path/to/js2",
                "https://secure.other.com/path/to/js3",
                static("relative/path/to/js4"),
            ),
        )
        self.assertEqual(
            str(m),
            '<link href="https://example.com/assets/path/to/css1" media="all" '
            'rel="stylesheet">\n'
            '<link href="/path/to/css2" media="all" rel="stylesheet">\n'
            '<script src="/path/to/js1"></script>\n'
            '<script src="http://media.other.com/path/to/js2"></script>\n'
            '<script src="https://secure.other.com/path/to/js3"></script>\n'
            '<script src="https://example.com/assets/relative/path/to/js4"></script>',
        )
