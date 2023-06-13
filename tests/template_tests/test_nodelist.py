from django.template import Context, Engine
from django.template.base import TextNode, VariableNode
from django.test import SimpleTestCase


class NodelistTest(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = Engine()
        super().setUpClass()

    def test_for(self):
        template = self.engine.from_string("{% for i in 1 %}{{ a }}{% endfor %}")
        vars = template.nodelist.get_nodes_by_type(VariableNode)
        self.assertEqual(len(vars), 1)

    def test_if(self):
        template = self.engine.from_string("{% if x %}{{ a }}{% endif %}")
        vars = template.nodelist.get_nodes_by_type(VariableNode)
        self.assertEqual(len(vars), 1)

    def test_ifchanged(self):
        template = self.engine.from_string("{% ifchanged x %}{{ a }}{% endifchanged %}")
        vars = template.nodelist.get_nodes_by_type(VariableNode)
        self.assertEqual(len(vars), 1)


class TextNodeTest(SimpleTestCase):
    def test_textnode_repr(self):
        engine = Engine()
        for temptext, reprtext in [
            ("Hello, world!", "<TextNode: 'Hello, world!'>"),
            ("One\ntwo.", "<TextNode: 'One\\ntwo.'>"),
        ]:
            template = engine.from_string(temptext)
            texts = template.nodelist.get_nodes_by_type(TextNode)
            self.assertEqual(repr(texts[0]), reprtext)


class ErrorIndexTest(SimpleTestCase):
    """
    Checks whether index of error is calculated correctly in
    template debugger in for loops. Refs ticket #5831
    """

    def test_correct_exception_index(self):
        tests = [
            (
                "{% load bad_tag %}{% for i in range %}{% badsimpletag %}{% endfor %}",
                (38, 56),
            ),
            (
                "{% load bad_tag %}{% for i in range %}{% for j in range %}"
                "{% badsimpletag %}{% endfor %}{% endfor %}",
                (58, 76),
            ),
            (
                "{% load bad_tag %}{% for i in range %}{% badsimpletag %}"
                "{% for j in range %}Hello{% endfor %}{% endfor %}",
                (38, 56),
            ),
            (
                "{% load bad_tag %}{% for i in range %}{% for j in five %}"
                "{% badsimpletag %}{% endfor %}{% endfor %}",
                (38, 57),
            ),
            (
                "{% load bad_tag %}{% for j in five %}{% badsimpletag %}{% endfor %}",
                (18, 37),
            ),
        ]
        context = Context(
            {
                "range": range(5),
                "five": 5,
            }
        )
        engine = Engine(
            debug=True, libraries={"bad_tag": "template_tests.templatetags.bad_tag"}
        )
        for source, expected_error_source_index in tests:
            template = engine.from_string(source)
            try:
                template.render(context)
            except (RuntimeError, TypeError) as e:
                debug = e.template_debug
                self.assertEqual(
                    (debug["start"], debug["end"]), expected_error_source_index
                )
