from django.http import QueryDict
from django.template import RequestContext
from django.template.base import TemplateSyntaxError
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

    @setup({"querystring_remove_dict": "{% querystring my_dict a=1 %}"})
    def test_querystring_remove_from_dict(self):
        request = self.request_factory.get("/", {"test": "value"})
        template = self.engine.get_template("querystring_remove_dict")
        context = RequestContext(request, {"my_dict": {"test": None}})
        output = template.render(context)
        self.assertEqual(output, "?a=1")

    @setup({"querystring_remove_nonexistent": "{% querystring nonexistent=None a=1 %}"})
    def test_querystring_remove_nonexistent(self):
        request = self.request_factory.get("/", {"x": "y", "a": "1"})
        template = self.engine.get_template("querystring_remove_nonexistent")
        context = RequestContext(request)
        output = template.render(context)
        self.assertEqual(output, "?x=y&amp;a=1")

    @setup({"querystring_same_arg": "{% querystring a=1 a=2 %}"})
    def test_querystring_same_arg(self):
        with self.assertRaises(TemplateSyntaxError):
            self.engine.render_to_string("querystring_same_arg", {})

    @setup({"querystring_variable": "{% querystring a=a %}"})
    def test_querystring_variable(self):
        request = self.request_factory.get("/")
        template = self.engine.get_template("querystring_variable")
        context = RequestContext(request, {"a": 1})
        output = template.render(context)
        self.assertEqual(output, "?a=1")

    @setup({"querystring_dict": "{% querystring my_dict %}"})
    def test_querystring_dict(self):
        context = {"my_dict": {"a": 1}}
        output = self.engine.render_to_string("querystring_dict", context)
        self.assertEqual(output, "?a=1")

    @setup({"querystring_dict_list": "{% querystring my_dict %}"})
    def test_querystring_dict_list_values(self):
        context = {"my_dict": {"a": [1, 2]}}
        output = self.engine.render_to_string("querystring_dict_list", context)
        self.assertEqual(output, "?a=1&amp;a=2")

    @setup({"querystring_non_string_dict_keys": "{% querystring my_dict %}"})
    def test_querystring_non_string_dict_keys(self):
        context = {"my_dict": {0: 1}}
        msg = "querystring received non-string dict key: 0"
        with self.assertRaisesMessage(TemplateSyntaxError, msg):
            self.engine.render_to_string("querystring_non_string_dict_keys", context)

    @setup({"querystring_non_dict_args": "{% querystring somevar %}"})
    def test_querystring_non_dict_args(self):
        context = {"somevar": 0}
        msg = "'int' object has no attribute 'items'"
        with self.assertRaisesMessage(AttributeError, msg):
            self.engine.render_to_string("querystring_non_dict_args", context)

    @setup(
        {
            "querystring_multiple_args_override": (
                "{% querystring my_dict my_query_dict x=3 %}"
            )
        }
    )
    def test_querystring_multiple_args_override(self):
        context = {"my_dict": {"x": 0}, "my_query_dict": QueryDict("a=1&b=2")}
        output = self.engine.render_to_string(
            "querystring_multiple_args_override", context
        )
        self.assertEqual(output, "?x=3&amp;a=1&amp;b=2")

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
