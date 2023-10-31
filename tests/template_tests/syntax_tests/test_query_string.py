from django.http import QueryDict
from django.template import RequestContext
from django.test import RequestFactory, SimpleTestCase

from ..utils import setup


class QueryStringTagTests(SimpleTestCase):
    def setUp(self):
        self.request_factory = RequestFactory()

    @setup({"query_string_empty": "{% query_string %}"})
    def test_query_string_empty(self):
        request = self.request_factory.get("/")
        template = self.engine.get_template("query_string_empty")
        context = RequestContext(request)
        output = template.render(context)
        self.assertEqual(output, "")

    @setup({"query_string_non_empty": "{% query_string %}"})
    def test_query_string_non_empty(self):
        request = self.request_factory.get("/", {"a": "b"})
        template = self.engine.get_template("query_string_non_empty")
        context = RequestContext(request)
        output = template.render(context)
        self.assertEqual(output, "?a=b")

    @setup({"query_string_multiple": "{% query_string %}"})
    def test_query_string_multiple(self):
        request = self.request_factory.get("/", {"x": "y", "a": "b"})
        template = self.engine.get_template("query_string_multiple")
        context = RequestContext(request)
        output = template.render(context)
        self.assertEqual(output, "?x=y&amp;a=b")

    @setup({"query_string_replace": "{% query_string a=1 %}"})
    def test_query_string_replace(self):
        request = self.request_factory.get("/", {"x": "y", "a": "b"})
        template = self.engine.get_template("query_string_replace")
        context = RequestContext(request)
        output = template.render(context)
        self.assertEqual(output, "?x=y&amp;a=1")

    @setup({"query_string_add": "{% query_string test_new='something' %}"})
    def test_query_string_add(self):
        request = self.request_factory.get("/", {"a": "b"})
        template = self.engine.get_template("query_string_add")
        context = RequestContext(request)
        output = template.render(context)
        self.assertEqual(output, "?a=b&amp;test_new=something")

    @setup({"query_string_remove": "{% query_string test=None a=1 %}"})
    def test_query_string_remove(self):
        request = self.request_factory.get("/", {"test": "value", "a": "1"})
        template = self.engine.get_template("query_string_remove")
        context = RequestContext(request)
        output = template.render(context)
        self.assertEqual(output, "?a=1")

    @setup(
        {"query_string_remove_nonexistent": "{% query_string nonexistent=None a=1 %}"}
    )
    def test_query_string_remove_nonexistent(self):
        request = self.request_factory.get("/", {"x": "y", "a": "1"})
        template = self.engine.get_template("query_string_remove_nonexistent")
        context = RequestContext(request)
        output = template.render(context)
        self.assertEqual(output, "?x=y&amp;a=1")

    @setup({"query_string_list": "{% query_string a=my_list %}"})
    def test_query_string_add_list(self):
        request = self.request_factory.get("/")
        template = self.engine.get_template("query_string_list")
        context = RequestContext(request, {"my_list": [2, 3]})
        output = template.render(context)
        self.assertEqual(output, "?a=2&amp;a=3")

    @setup({"query_string_query_dict": "{% query_string request.GET a=2 %}"})
    def test_query_string_with_explicit_query_dict(self):
        request = self.request_factory.get("/", {"a": 1})
        output = self.engine.render_to_string(
            "query_string_query_dict", {"request": request}
        )
        self.assertEqual(output, "?a=2")

    @setup(
        {"query_string_query_dict_no_request": "{% query_string my_query_dict a=2 %}"}
    )
    def test_query_string_with_explicit_query_dict_and_no_request(self):
        context = {"my_query_dict": QueryDict("a=1&b=2")}
        output = self.engine.render_to_string(
            "query_string_query_dict_no_request", context
        )
        self.assertEqual(output, "?a=2&amp;b=2")

    @setup({"query_string_no_request_no_query_dict": "{% query_string %}"})
    def test_query_string_without_request_or_explicit_query_dict(self):
        msg = "'Context' object has no attribute 'request'"
        with self.assertRaisesMessage(AttributeError, msg):
            self.engine.render_to_string("query_string_no_request_no_query_dict")
