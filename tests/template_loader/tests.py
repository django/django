from django.template import TemplateDoesNotExist
from django.template.loader import (
    get_template, render_to_string, select_template,
)
from django.test import SimpleTestCase, override_settings
from django.test.client import RequestFactory


@override_settings(TEMPLATES=[{
    'BACKEND': 'django.template.backends.dummy.TemplateStrings',
    'APP_DIRS': True,
}, {
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'APP_DIRS': True,
    'OPTIONS': {
        'context_processors': [
            'django.template.context_processors.request',
        ],
    },
}])
class TemplateLoaderTests(SimpleTestCase):

    def test_get_template_first_engine(self):
        template = get_template("template_loader/hello.html")
        self.assertEqual(template.render(), "Hello! (template strings)\n")

    def test_get_template_second_engine(self):
        template = get_template("template_loader/goodbye.html")
        self.assertEqual(template.render(), "Goodbye! (Django templates)\n")

    def test_get_template_using_engine(self):
        template = get_template("template_loader/hello.html", using="django")
        self.assertEqual(template.render(), "Hello! (Django templates)\n")

    def test_get_template_not_found(self):
        with self.assertRaises(TemplateDoesNotExist):
            get_template("template_loader/unknown.html")

    def test_select_template_first_engine(self):
        template = select_template(["template_loader/unknown.html",
                                    "template_loader/hello.html"])
        self.assertEqual(template.render(), "Hello! (template strings)\n")

    def test_select_template_second_engine(self):
        template = select_template(["template_loader/unknown.html",
                                    "template_loader/goodbye.html"])
        self.assertEqual(template.render(), "Goodbye! (Django templates)\n")

    def test_select_template_using_engine(self):
        template = select_template(["template_loader/unknown.html",
                                    "template_loader/hello.html"], using="django")
        self.assertEqual(template.render(), "Hello! (Django templates)\n")

    def test_select_template_empty(self):
        with self.assertRaises(TemplateDoesNotExist):
            select_template([])

    def test_select_template_not_found(self):
        with self.assertRaises(TemplateDoesNotExist):
            select_template(["template_loader/unknown.html",
                             "template_loader/missing.html"])

    def test_select_template_tries_all_engines_before_names(self):
        template = select_template(["template_loader/goodbye.html",
                                    "template_loader/hello.html"])
        self.assertEqual(template.render(), "Goodbye! (Django templates)\n")

    def test_render_to_string_first_engine(self):
        content = render_to_string("template_loader/hello.html")
        self.assertEqual(content, "Hello! (template strings)\n")

    def test_render_to_string_second_engine(self):
        content = render_to_string("template_loader/goodbye.html")
        self.assertEqual(content, "Goodbye! (Django templates)\n")

    def test_render_to_string_with_request(self):
        request = RequestFactory().get('/foobar/')
        content = render_to_string("template_loader/request.html", request=request)
        self.assertEqual(content, "/foobar/\n")

    def test_render_to_string_using_engine(self):
        content = render_to_string("template_loader/hello.html", using="django")
        self.assertEqual(content, "Hello! (Django templates)\n")

    def test_render_to_string_not_found(self):
        with self.assertRaises(TemplateDoesNotExist):
            render_to_string("template_loader/unknown.html")

    def test_render_to_string_with_list_first_engine(self):
        content = render_to_string(["template_loader/unknown.html",
                                    "template_loader/hello.html"])
        self.assertEqual(content, "Hello! (template strings)\n")

    def test_render_to_string_with_list_second_engine(self):
        content = render_to_string(["template_loader/unknown.html",
                                    "template_loader/goodbye.html"])
        self.assertEqual(content, "Goodbye! (Django templates)\n")

    def test_render_to_string_with_list_using_engine(self):
        content = render_to_string(["template_loader/unknown.html",
                                    "template_loader/hello.html"], using="django")
        self.assertEqual(content, "Hello! (Django templates)\n")

    def test_render_to_string_with_list_empty(self):
        with self.assertRaises(TemplateDoesNotExist):
            render_to_string([])

    def test_render_to_string_with_list_not_found(self):
        with self.assertRaises(TemplateDoesNotExist):
            render_to_string(["template_loader/unknown.html",
                              "template_loader/missing.html"])

    def test_render_to_string_with_list_tries_all_engines_before_names(self):
        content = render_to_string(["template_loader/goodbye.html",
                                    "template_loader/hello.html"])
        self.assertEqual(content, "Goodbye! (Django templates)\n")
