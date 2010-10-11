from django.template.loader import get_template_from_string
from django.template import VariableNode
from django.utils.unittest import TestCase


class NodelistTest(TestCase):

    def test_for(self):
        source = '{% for i in 1 %}{{ a }}{% endfor %}'
        template = get_template_from_string(source)
        vars = template.nodelist.get_nodes_by_type(VariableNode)
        self.assertEqual(len(vars), 1)

    def test_if(self):
        source = '{% if x %}{{ a }}{% endif %}'
        template = get_template_from_string(source)
        vars = template.nodelist.get_nodes_by_type(VariableNode)
        self.assertEqual(len(vars), 1)

    def test_ifequal(self):
        source = '{% ifequal x y %}{{ a }}{% endifequal %}'
        template = get_template_from_string(source)
        vars = template.nodelist.get_nodes_by_type(VariableNode)
        self.assertEqual(len(vars), 1)

    def test_ifchanged(self):
        source = '{% ifchanged x %}{{ a }}{% endifchanged %}'
        template = get_template_from_string(source)
        vars = template.nodelist.get_nodes_by_type(VariableNode)
        self.assertEqual(len(vars), 1)
