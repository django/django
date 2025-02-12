from django.http import QueryDict
from django.template import RequestContext
from django.test import RequestFactory, SimpleTestCase

from ..utils import setup


class QueryStringTagTests(SimpleTestCase):
    def setUp(self):
        self.request_factory = RequestFactory()

    @setup({"querystring_empty": "{% querystring %}"})
    def test_querystring_empty(self):
        request = self.request_factory.get("/")
        template = self.engine.get_template("querystring_empty")
        context = RequestContext(request)
        output = template.render(context)
        self.assertEqual(output, "")

    @setup({"test_querystring_remove_all_params": "{% querystring a=None %}"})
    def test_querystring_remove_all_params(self):
        non_empty_context = RequestContext(self.request_factory.get("/?a=b"))
        empty_context = RequestContext(self.request_factory.get("/"))
        template = self.engine.get_template("test_querystring_remove_all_params")
        for context, expected in [(non_empty_context, "?"), (empty_context, "")]:
            with self.subTest(expected=expected):
                self.assertEqual(template.render(context), expected)

    @setup({"querystring_non_empty": "{% querystring %}"})
    def test_querystring_non_empty(self):
        request = self.request_factory.get("/", {"a": "b"})
        template = self.engine.get_template("querystring_non_empty")
        context = RequestContext(request)
        output = template.render(context)
        self.assertEqual(output, "?a=b")

    @setup({"querystring_multiple": "{% querystring %}"})
    def test_querystring_multiple(self):
        request = self.request_factory.get("/", {"x": "y", "a": "b"})
        template = self.engine.get_template("querystring_multiple")
        context = RequestContext(request)
        output = template.render(context)
        self.assertEqual(output, "?x=y&amp;a=b")

    @setup({"querystring_replace": "{% querystring a=1 %}"})
    def test_querystring_replace(self):
        request = self.request_factory.get("/", {"x": "y", "a": "b"})
        template = self.engine.get_template("querystring_replace")
        context = RequestContext(request)
        output = template.render(context)
        self.assertEqual(output, "?x=y&amp;a=1")

    @setup({"querystring_add": "{% querystring test_new='something' %}"})
    def test_querystring_add(self):
        request = self.request_factory.get("/", {"a": "b"})
        template = self.engine.get_template("querystring_add")
        context = RequestContext(request)
        output = template.render(context)
        self.assertEqual(output, "?a=b&amp;test_new=something")

    @setup({"querystring_remove": "{% querystring test=None a=1 %}"})
    def test_querystring_remove(self):
        request = self.request_factory.get("/", {"test": "value", "a": "1"})
        template = self.engine.get_template("querystring_remove")
        context = RequestContext(request)
        output = template.render(context)
        self.assertEqual(output, "?a=1")

    @setup({"querystring_remove_nonexistent": "{% querystring nonexistent=None a=1 %}"})
    def test_querystring_remove_nonexistent(self):
        request = self.request_factory.get("/", {"x": "y", "a": "1"})
        template = self.engine.get_template("querystring_remove_nonexistent")
        context = RequestContext(request)
        output = template.render(context)
        self.assertEqual(output, "?x=y&amp;a=1")

    @setup({"querystring_list": "{% querystring a=my_list %}"})
    def test_querystring_add_list(self):
        request = self.request_factory.get("/")
        template = self.engine.get_template("querystring_list")
        context = RequestContext(request, {"my_list": [2, 3]})
        output = template.render(context)
        self.assertEqual(output, "?a=2&amp;a=3")

    @setup({"querystring_query_dict": "{% querystring request.GET a=2 %}"})
    def test_querystring_with_explicit_query_dict(self):
        request = self.request_factory.get("/", {"a": 1})
        output = self.engine.render_to_string(
            "querystring_query_dict", {"request": request}
        )
        self.assertEqual(output, "?a=2")

    @setup({"querystring_query_dict_no_request": "{% querystring my_query_dict a=2 %}"})
    def test_querystring_with_explicit_query_dict_and_no_request(self):
        context = {"my_query_dict": QueryDict("a=1&b=2")}
        output = self.engine.render_to_string(
            "querystring_query_dict_no_request", context
        )
        self.assertEqual(output, "?a=2&amp;b=2")

    @setup({"querystring_no_request_no_query_dict": "{% querystring %}"})
    def test_querystring_without_request_or_explicit_query_dict(self):
        msg = "'Context' object has no attribute 'request'"
        with self.assertRaisesMessage(AttributeError, msg):
            self.engine.render_to_string("querystring_no_request_no_query_dict")
