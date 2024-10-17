from django.http import QueryDict
from django.template import RequestContext
from django.test import RequestFactory, SimpleTestCase

from ..utils import setup


class QueryStringTagTests(SimpleTestCase):
    request_factory = RequestFactory()

    def assertRenderEqual(self, template_name, request=None, expected="", **context):
        if request is None:
            request = self.request_factory.get("/")
        template = self.engine.get_template(template_name)
        context = RequestContext(request, context)
        output = template.render(context)
        self.assertEqual(output, expected)

    @setup({"test_querystring_empty_get_params": "{% querystring %}"})
    def test_querystring_empty_get_params(self):
        self.assertRenderEqual("test_querystring_empty_get_params", expected="")

    @setup({"test_querystring_non_empty_get_params": "{% querystring %}"})
    def test_querystring_non_empty_get_params(self):
        request = self.request_factory.get("/", {"a": "b"})
        self.assertRenderEqual(
            "test_querystring_non_empty_get_params", request, expected="?a=b"
        )

    @setup({"querystring_multiple": "{% querystring %}"})
    def test_querystring_multiple(self):
        request = self.request_factory.get("/", {"x": "y", "a": "b"})
        self.assertRenderEqual("querystring_multiple", request, expected="?x=y&amp;a=b")

    @setup({"test_querystring_empty_params": "{% querystring qd %}"})
    def test_querystring_empty_params(self):
        cases = [None, {}, QueryDict()]
        for param in cases:
            with self.subTest(param=param):
                self.assertRenderEqual(
                    "test_querystring_empty_params", qd=param, expected=""
                )

    @setup({"querystring_replace": "{% querystring a=1 %}"})
    def test_querystring_replace(self):
        request = self.request_factory.get("/", {"x": "y", "a": "b"})
        self.assertRenderEqual("querystring_replace", request, expected="?x=y&amp;a=1")

    @setup({"querystring_add": "{% querystring test_new='something' %}"})
    def test_querystring_add(self):
        request = self.request_factory.get("/", {"a": "b"})
        self.assertRenderEqual(
            "querystring_add", request, expected="?a=b&amp;test_new=something"
        )

    @setup({"querystring_remove": "{% querystring test=None a=1 %}"})
    def test_querystring_remove(self):
        request = self.request_factory.get("/", {"test": "value", "a": "1"})
        self.assertRenderEqual("querystring_remove", request, expected="?a=1")

    @setup({"querystring_remove_nonexistent": "{% querystring nonexistent=None a=1 %}"})
    def test_querystring_remove_nonexistent(self):
        request = self.request_factory.get("/", {"x": "y", "a": "1"})
        self.assertRenderEqual(
            "querystring_remove_nonexistent", request, expected="?x=y&amp;a=1"
        )

    @setup({"querystring_list": "{% querystring a=my_list %}"})
    def test_querystring_add_list(self):
        self.assertRenderEqual(
            "querystring_list", my_list=[2, 3], expected="?a=2&amp;a=3"
        )

    @setup({"querystring_dict": "{% querystring a=my_dict %}"})
    def test_querystring_add_dict(self):
        self.assertRenderEqual(
            "querystring_dict",
            my_dict={i: i * 2 for i in range(3)},
            expected="?a=0&amp;a=1&amp;a=2",
        )

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
