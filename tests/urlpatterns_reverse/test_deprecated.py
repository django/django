import warnings

from django.conf.urls import url
from django.test import SimpleTestCase, override_settings
from django.urls import reverse

from .views import empty_view

urlpatterns = [
    url(r'^(?i)CaseInsensitive/(\w+)', empty_view, name="insensitive"),
    url(r'^(?i)test/2/?$', empty_view, name="test2"),
]


@override_settings(ROOT_URLCONF='urlpatterns_reverse.test_deprecated')
class URLPatternReverse(SimpleTestCase):

    def test_urlpattern_reverse(self):
        test_data = (
            ('insensitive', '/CaseInsensitive/fred', ['fred'], {}),
            ('test2', '/test/2', [], {}),
        )
        with warnings.catch_warnings(record=True) as warns:
            warnings.simplefilter('always')
            warnings.filterwarnings(
                'ignore', 'Flags not at the start',
                DeprecationWarning, module='django.urls.resolvers'
            )
            for i, (name, expected, args, kwargs) in enumerate(test_data):
                got = reverse(name, args=args, kwargs=kwargs)
                self.assertEqual(got, expected)
                msg = str(warns[i].message)
                self.assertEqual(msg, 'Using (?i) in url() patterns is deprecated.')
