from django.core.cache import cache
from django.template import Template, Context
from django.templatetags.cache import make_key
from django.utils.unittest import TestCase


class TestCache(TestCase):
    def setUp(self):
        self.vary_on = [1, {'a': 'b'}]
        self.cache_key = make_key('fragment', self.vary_on)

    @property
    def cache_value(self):
        return cache.get(self.cache_key)

    def test_cache_tag_makes_key_with_make_key(self):
        self.assertEqual(self.cache_value, None)
        raw_template = ('{% load cache %}' +
                        '{% cache 2 fragment vary_on.0 vary_on.1 %}OK' +
                        '{% endcache %}')
        template = Template(raw_template)
        context = Context({'vary_on': self.vary_on})
        html = template.render(context)
        self.assertEqual(self.cache_value, html)
