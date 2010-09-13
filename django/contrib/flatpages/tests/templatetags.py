import os
from django.conf import settings
from django.contrib.auth.models import AnonymousUser, User
from django.template import Template, Context, TemplateSyntaxError
from django.test import TestCase

class FlatpageTemplateTagTests(TestCase):
    fixtures = ['sample_flatpages']
    urls = 'django.contrib.flatpages.tests.urls'

    def setUp(self):
        self.old_MIDDLEWARE_CLASSES = settings.MIDDLEWARE_CLASSES
        flatpage_middleware_class = 'django.contrib.flatpages.middleware.FlatpageFallbackMiddleware'
        if flatpage_middleware_class not in settings.MIDDLEWARE_CLASSES:
            settings.MIDDLEWARE_CLASSES += (flatpage_middleware_class,)
        self.old_TEMPLATE_DIRS = settings.TEMPLATE_DIRS
        settings.TEMPLATE_DIRS = (
            os.path.join(
                os.path.dirname(__file__),
                'templates'
            ),
        )
        self.me = User.objects.create_user('testuser', 'test@example.com', 's3krit')

    def tearDown(self):
        settings.MIDDLEWARE_CLASSES = self.old_MIDDLEWARE_CLASSES
        settings.TEMPLATE_DIRS = self.old_TEMPLATE_DIRS

    def test_get_flatpages_tag(self):
        "The flatpage template tag retrives unregistered prefixed flatpages by default"
        out = Template(
                "{% load flatpages %}"
                "{% get_flatpages as flatpages %}"
                "{% for page in flatpages %}"
                "{{ page.title }},"
                "{% endfor %}"
            ).render(Context())
        self.assertEquals(out, "A Flatpage,A Nested Flatpage,")

    def test_get_flatpages_tag_for_anon_user(self):
        "The flatpage template tag retrives unregistered flatpages for an anonymous user"
        out = Template(
                "{% load flatpages %}"
                "{% get_flatpages for anonuser as flatpages %}"
                "{% for page in flatpages %}"
                "{{ page.title }},"
                "{% endfor %}"
            ).render(Context({
                'anonuser': AnonymousUser()
            }))
        self.assertEquals(out, "A Flatpage,A Nested Flatpage,")

    def test_get_flatpages_tag_for_user(self):
        "The flatpage template tag retrives all flatpages for an authenticated user"
        out = Template(
                "{% load flatpages %}"
                "{% get_flatpages for me as flatpages %}"
                "{% for page in flatpages %}"
                "{{ page.title }},"
                "{% endfor %}"
            ).render(Context({
                'me': self.me
            }))
        self.assertEquals(out, "A Flatpage,A Nested Flatpage,Sekrit Nested Flatpage,Sekrit Flatpage,")

    def test_get_flatpages_with_prefix(self):
        "The flatpage template tag retrives unregistered prefixed flatpages by default"
        out = Template(
                "{% load flatpages %}"
                "{% get_flatpages '/location/' as location_flatpages %}"
                "{% for page in location_flatpages %}"
                "{{ page.title }},"
                "{% endfor %}"
            ).render(Context())
        self.assertEquals(out, "A Nested Flatpage,")

    def test_get_flatpages_with_prefix_for_anon_user(self):
        "The flatpage template tag retrives unregistered prefixed flatpages for an anonymous user"
        out = Template(
                "{% load flatpages %}"
                "{% get_flatpages '/location/' for anonuser as location_flatpages %}"
                "{% for page in location_flatpages %}"
                "{{ page.title }},"
                "{% endfor %}"
            ).render(Context({
                'anonuser': AnonymousUser()
            }))
        self.assertEquals(out, "A Nested Flatpage,")

    def test_get_flatpages_with_prefix_for_user(self):
        "The flatpage template tag retrive prefixed flatpages for an authenticated user"
        out = Template(
                "{% load flatpages %}"
                "{% get_flatpages '/location/' for me as location_flatpages %}"
                "{% for page in location_flatpages %}"
                "{{ page.title }},"
                "{% endfor %}"
            ).render(Context({
                'me': self.me
            }))
        self.assertEquals(out, "A Nested Flatpage,Sekrit Nested Flatpage,")

    def test_get_flatpages_with_variable_prefix(self):
        "The prefix for the flatpage template tag can be a template variable"
        out = Template(
                "{% load flatpages %}"
                "{% get_flatpages location_prefix as location_flatpages %}"
                "{% for page in location_flatpages %}"
                "{{ page.title }},"
                "{% endfor %}"
            ).render(Context({
                'location_prefix': '/location/'
            }))
        self.assertEquals(out, "A Nested Flatpage,")

    def test_parsing_errors(self):
        "There are various ways that the flatpages template tag won't parse"
        render = lambda t: Template(t).render(Context())

        self.assertRaises(TemplateSyntaxError, render,
                          "{% load flatpages %}{% get_flatpages %}")
        self.assertRaises(TemplateSyntaxError, render,
                          "{% load flatpages %}{% get_flatpages as %}")
        self.assertRaises(TemplateSyntaxError, render,
                          "{% load flatpages %}{% get_flatpages cheesecake flatpages %}")
        self.assertRaises(TemplateSyntaxError, render,
                          "{% load flatpages %}{% get_flatpages as flatpages asdf%}")
        self.assertRaises(TemplateSyntaxError, render,
                          "{% load flatpages %}{% get_flatpages cheesecake user as flatpages %}")
        self.assertRaises(TemplateSyntaxError, render,
                          "{% load flatpages %}{% get_flatpages for user as flatpages asdf%}")
        self.assertRaises(TemplateSyntaxError, render,
                          "{% load flatpages %}{% get_flatpages prefix for user as flatpages asdf%}")

