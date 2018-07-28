from django.test import SimpleTestCase
from django.urls.resolvers import RegexPattern, RoutePattern
from django.utils.translation import gettext_lazy as _


class RegexPatternTests(SimpleTestCase):

    def test_str(self):
        self.assertEqual(str(RegexPattern(_('^translated/$'))), '^translated/$')


class RoutePatternTests(SimpleTestCase):

    def test_str(self):
        self.assertEqual(str(RoutePattern(_('translated/'))), 'translated/')
