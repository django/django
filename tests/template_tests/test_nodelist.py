from unittest import TestCase

from django.template import Context, Template
from django.template.base import VariableNode
from django.test import override_settings


class NodelistTest(TestCase):

    def test_for(self):
        template = Template('{% for i in 1 %}{{ a }}{% endfor %}')
        vars = template.nodelist.get_nodes_by_type(VariableNode)
        self.assertEqual(len(vars), 1)

    def test_if(self):
        template = Template('{% if x %}{{ a }}{% endif %}')
        vars = template.nodelist.get_nodes_by_type(VariableNode)
        self.assertEqual(len(vars), 1)

    def test_ifequal(self):
        template = Template('{% ifequal x y %}{{ a }}{% endifequal %}')
        vars = template.nodelist.get_nodes_by_type(VariableNode)
        self.assertEqual(len(vars), 1)

    def test_ifchanged(self):
        template = Template('{% ifchanged x %}{{ a }}{% endifchanged %}')
        vars = template.nodelist.get_nodes_by_type(VariableNode)
        self.assertEqual(len(vars), 1)


class ErrorIndexTest(TestCase):
    """
    Checks whether index of error is calculated correctly in
    template debugger in for loops. Refs ticket #5831
    """
    @override_settings(DEBUG=True)
    def test_correct_exception_index(self):
        tests = [
            ('{% load bad_tag %}{% for i in range %}{% badsimpletag %}{% endfor %}', (38, 56)),
            ('{% load bad_tag %}{% for i in range %}{% for j in range %}{% badsimpletag %}{% endfor %}{% endfor %}', (58, 76)),
            ('{% load bad_tag %}{% for i in range %}{% badsimpletag %}{% for j in range %}Hello{% endfor %}{% endfor %}', (38, 56)),
            ('{% load bad_tag %}{% for i in range %}{% for j in five %}{% badsimpletag %}{% endfor %}{% endfor %}', (38, 57)),
            ('{% load bad_tag %}{% for j in five %}{% badsimpletag %}{% endfor %}', (18, 37)),
        ]
        context = Context({
            'range': range(5),
            'five': 5,
        })
        for source, expected_error_source_index in tests:
            template = Template(source)
            try:
                template.render(context)
            except (RuntimeError, TypeError) as e:
                error_source_index = e.django_template_source[1]
                self.assertEqual(error_source_index,
                                 expected_error_source_index)
