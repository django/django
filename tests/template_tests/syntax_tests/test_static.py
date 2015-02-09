from django.conf import settings
from django.test import SimpleTestCase, override_settings
from django.utils.six.moves.urllib.parse import urljoin

from ..utils import setup


@override_settings(MEDIA_URL="/media/", STATIC_URL="/static/")
class StaticTagTests(SimpleTestCase):

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
