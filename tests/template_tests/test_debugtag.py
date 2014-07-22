# -*- coding: utf-8 -*-
from django.test import TestCase
from django.template import Template, Context
from django.utils.safestring import SafeData
from django.utils import six

from .models import Article

class DebugTests(TestCase):
    def test_debug_tag(self):
        Article.objects.create(name="清風")
        c1 = Context({"objs": Article.objects.all()})
        t1 = Template('{% debug %} {{ objs }}')
        self.assertIsInstance(t1.render(c1), six.text_type)
        self.assertIsInstance(t1.render(c1), SafeData)
