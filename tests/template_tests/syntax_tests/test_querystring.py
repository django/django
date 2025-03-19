from django.http import QueryDict
from django.template import RequestContext
from django.template.base import TemplateSyntaxError
from django.test import RequestFactory, SimpleTestCase

from ..utils import setup


class QueryStringTagTests(SimpleTestCase):

    request_factory = RequestFactory()

    def assertRenderEqual(self, template_name, context, expected):
        output = self.engine.render_to_string(template_name, context)
        self.assertEqual(output, expected)

    def assertTemplateSyntaxError(self, template_name, context, expected):
        with self.assertRaisesMessage(TemplateSyntaxError, expected):
            self.engine.render_to_string(template_name, context)

    @setup({"querystring_empty_get_params": "{% querystring %}"})
    def test_querystring_empty_get_params(self):
        context = RequestContext(self.request_factory.get("/"))
        self.assertRenderEqual("querystring_empty_get_params", context, expected="?")

    @setup({"querystring_remove_all_params": "{% querystring a=None %}"})
    def test_querystring_remove_all_params(self):
        non_empty_context = RequestContext(self.request_factory.get("/?a=b"))
        empty_context = RequestContext(self.request_factory.get("/"))
        for context in [non_empty_context, empty_context]:
            with self.subTest(context=context):
                self.assertRenderEqual("querystring_remove_all_params", context, "?")

    @setup(
        {
            "querystring_remove_all_params_custom_querydict": (
                "{% querystring my_query_dict my_dict a=None %}"
            )
        }
    )
    def test_querystring_remove_all_params_custom_querydict(self):
        context = {"my_query_dict": QueryDict("a=1&b=2"), "my_dict": {"b": None}}
        self.assertRenderEqual(
            "querystring_remove_all_params_custom_querydict", context, "?"
        )

    @setup({"querystring_non_empty_get_params": "{% querystring %}"})
    def test_querystring_non_empty_get_params(self):
        request = self.request_factory.get("/", {"a": "b"})
        context = RequestContext(request)
        self.assertRenderEqual(
            "querystring_non_empty_get_params", context, expected="?a=b"
        )

    @setup({"querystring_multiple": "{% querystring %}"})
    def test_querystring_multiple(self):
        request = self.request_factory.get("/", {"x": "y", "a": "b"})
        context = RequestContext(request)
        self.assertRenderEqual("querystring_multiple", context, expected="?x=y&amp;a=b")

    @setup({"querystring_empty_params": "{% querystring qd %}"})
    def test_querystring_empty_params(self):
        cases = [{}, QueryDict()]
        request = self.request_factory.get("/")
        qs = "?a=b"
        request_with_qs = self.request_factory.get(f"/{qs}")
        for param in cases:
            # Empty `query_dict` and nothing on `request.GET`.
            with self.subTest(param=param):
                context = RequestContext(request, {"qd": param})
                self.assertRenderEqual(
                    "querystring_empty_params", context, expected="?"
                )
            # Empty `query_dict` and a query string in `request.GET`.
            with self.subTest(param=param, qs=qs):
                context = RequestContext(request_with_qs, {"qd": param})
                expected = "?" if param is not None else qs
                self.assertRenderEqual("querystring_empty_params", context, expected)

    @setup({"querystring_replace": "{% querystring a=1 %}"})
    def test_querystring_replace(self):
        request = self.request_factory.get("/", {"x": "y", "a": "b"})
        context = RequestContext(request)
        self.assertRenderEqual("querystring_replace", context, expected="?x=y&amp;a=1")

    @setup({"querystring_add": "{% querystring test_new='something' %}"})
    def test_querystring_add(self):
        request = self.request_factory.get("/", {"a": "b"})
        context = RequestContext(request)
        self.assertRenderEqual(
            "querystring_add", context, expected="?a=b&amp;test_new=something"
        )

    @setup({"querystring_remove": "{% querystring test=None a=1 %}"})
    def test_querystring_remove(self):
        request = self.request_factory.get("/", {"test": "value", "a": "1"})
        context = RequestContext(request)
        self.assertRenderEqual("querystring_remove", context, expected="?a=1")

    @setup({"querystring_remove_nonexistent": "{% querystring nonexistent=None a=1 %}"})
    def test_querystring_remove_nonexistent(self):
        request = self.request_factory.get("/", {"x": "y", "a": "1"})
        context = RequestContext(request)
        self.assertRenderEqual(
            "querystring_remove_nonexistent", context, expected="?x=y&amp;a=1"
        )

    @setup({"querystring_remove_dict": "{% querystring my_dict a=1 %}"})
    def test_querystring_remove_from_dict(self):
        request = self.request_factory.get("/", {"test": "value"})
        context = RequestContext(request, {"my_dict": {"test": None}})
        self.assertRenderEqual("querystring_remove_dict", context, expected="?a=1")

    @setup({"querystring_variable": "{% querystring a=a %}"})
    def test_querystring_variable(self):
        request = self.request_factory.get("/")
        context = RequestContext(request, {"a": 1})
        self.assertRenderEqual("querystring_variable", context, expected="?a=1")

    @setup({"querystring_dict": "{% querystring my_dict %}"})
    def test_querystring_dict(self):
        context = {"my_dict": {"a": 1}}
        self.assertRenderEqual("querystring_dict", context, expected="?a=1")

    @setup({"querystring_dict_list": "{% querystring my_dict %}"})
    def test_querystring_dict_list_values(self):
        context = {"my_dict": {"a": [1, 2]}}
        self.assertRenderEqual(
            "querystring_dict_list", context, expected="?a=1&amp;a=2"
        )

    @setup(
        {
            "querystring_multiple_args_override": (
                "{% querystring my_dict my_query_dict x=3 y=None %}"
            )
        }
    )
    def test_querystring_multiple_args_override(self):
        context = {"my_dict": {"x": 0, "y": 42}, "my_query_dict": QueryDict("a=1&b=2")}
        self.assertRenderEqual(
            "querystring_multiple_args_override",
            context,
            expected="?x=3&amp;a=1&amp;b=2",
        )

    @setup({"querystring_request_get_ignored": "{% querystring my_mapping %}"})
    def test_querystring_request_get_ignored(self):
        cases = [({"y": "x"}, "?y=x"), ({}, "?")]
        request = self.request_factory.get("/", {"x": "y", "a": "b"})
        for param, expected in cases:
            with self.subTest(param=param):
                context = RequestContext(request, {"my_mapping": param})
                self.assertRenderEqual(
                    "querystring_request_get_ignored", context, expected=expected
                )

    @setup({"querystring_same_arg": "{% querystring a=1 a=2 %}"})
    def test_querystring_same_arg(self):
        msg = "'querystring' received multiple values for keyword argument 'a'"
        self.assertTemplateSyntaxError("querystring_same_arg", {}, msg)

    @setup({"querystring_non_mapping_args": "{% querystring somevar %}"})
    def test_querystring_non_mapping_args(self):
        cases = [None, 0, "", []]
        request = self.request_factory.get("/")
        msg = (
            "querystring requires mappings for positional arguments (got %r "
            "instead)."
        )
        for param in cases:
            with self.subTest(param=param):
                context = RequestContext(request, {"somevar": param})
                self.assertTemplateSyntaxError(
                    "querystring_non_mapping_args", context, msg % param
                )

    @setup({"querystring_non_string_dict_keys": "{% querystring my_dict %}"})
    def test_querystring_non_string_dict_keys(self):
        context = {"my_dict": {0: 1}}
        msg = "querystring requires strings for mapping keys (got 0 instead)."
        self.assertTemplateSyntaxError("querystring_non_string_dict_keys", context, msg)

    @setup({"querystring_list": "{% querystring a=my_list %}"})
    def test_querystring_add_list(self):
        request = self.request_factory.get("/")
        context = RequestContext(request, {"my_list": [2, 3]})
        self.assertRenderEqual("querystring_list", context, expected="?a=2&amp;a=3")

    @setup({"querystring_dict": "{% querystring a=my_dict %}"})
    def test_querystring_add_dict(self):
        request = self.request_factory.get("/")
        context = RequestContext(request, {"my_dict": {i: i * 2 for i in range(3)}})
        self.assertRenderEqual(
            "querystring_dict", context, expected="?a=0&amp;a=1&amp;a=2"
        )

    @setup({"querystring_query_dict": "{% querystring request.GET a=2 %}"})
    def test_querystring_with_explicit_query_dict(self):
        request = self.request_factory.get("/", {"a": 1})
        self.assertRenderEqual(
            "querystring_query_dict", {"request": request}, expected="?a=2"
        )

    @setup({"querystring_query_dict_no_request": "{% querystring my_query_dict a=2 %}"})
    def test_querystring_with_explicit_query_dict_and_no_request(self):
        context = {"my_query_dict": QueryDict("a=1&b=2")}
        self.assertRenderEqual(
            "querystring_query_dict_no_request", context, expected="?a=2&amp;b=2"
        )

    @setup({"querystring_no_request_no_query_dict": "{% querystring %}"})
    def test_querystring_without_request_or_explicit_query_dict(self):
        msg = "'Context' object has no attribute 'request'"
        with self.assertRaisesMessage(AttributeError, msg):
            self.engine.render_to_string("querystring_no_request_no_query_dict")
