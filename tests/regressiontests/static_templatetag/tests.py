from django.template import Template
from django.test import TestCase

class StaticTemplatetagTest(TestCase):

    def test_staticfile_does_not_exist(self):
        t=Template('{% load staticfiles %}{% static "file/does/not.exist" %}')
        self.assertEqual(t.render(), '')
