from django.contrib.auth.models import AnonymousUser, User
from django.template import Context, Template, TemplateSyntaxError
from django.test import TestCase, modify_settings, override_settings

from .settings import FLATPAGES_TEMPLATES


@modify_settings(INSTALLED_APPS={'append': 'django.contrib.flatpages'})
@override_settings(
    MIDDLEWARE_CLASSES=(
        'django.middleware.common.CommonMiddleware',
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.middleware.csrf.CsrfViewMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'django.contrib.messages.middleware.MessageMiddleware',
        'django.contrib.flatpages.middleware.FlatpageFallbackMiddleware',
    ),
    ROOT_URLCONF='flatpages_tests.urls',
    TEMPLATES=FLATPAGES_TEMPLATES,
    SITE_ID=1,
)
class FlatpageTemplateTagTests(TestCase):
    fixtures = ['sample_flatpages']

    def test_get_flatpages_tag(self):
        "The flatpage template tag retrieves unregistered prefixed flatpages by default"
        out = Template(
            "{% load flatpages %}"
            "{% get_flatpages as flatpages %}"
            "{% for page in flatpages %}"
            "{{ page.title }},"
            "{% endfor %}"
        ).render(Context())
        self.assertEqual(out, "A Flatpage,A Nested Flatpage,")

    def test_get_flatpages_tag_for_anon_user(self):
        "The flatpage template tag retrieves unregistered flatpages for an anonymous user"
        out = Template(
            "{% load flatpages %}"
            "{% get_flatpages for anonuser as flatpages %}"
            "{% for page in flatpages %}"
            "{{ page.title }},"
            "{% endfor %}"
        ).render(Context({
            'anonuser': AnonymousUser()
        }))
        self.assertEqual(out, "A Flatpage,A Nested Flatpage,")

    def test_get_flatpages_tag_for_user(self):
        "The flatpage template tag retrieves all flatpages for an authenticated user"
        me = User.objects.create_user('testuser', 'test@example.com', 's3krit')
        out = Template(
            "{% load flatpages %}"
            "{% get_flatpages for me as flatpages %}"
            "{% for page in flatpages %}"
            "{{ page.title }},"
            "{% endfor %}"
        ).render(Context({
            'me': me
        }))
        self.assertEqual(out, "A Flatpage,A Nested Flatpage,Sekrit Nested Flatpage,Sekrit Flatpage,")

    def test_get_flatpages_with_prefix(self):
        "The flatpage template tag retrieves unregistered prefixed flatpages by default"
        out = Template(
            "{% load flatpages %}"
            "{% get_flatpages '/location/' as location_flatpages %}"
            "{% for page in location_flatpages %}"
            "{{ page.title }},"
            "{% endfor %}"
        ).render(Context())
        self.assertEqual(out, "A Nested Flatpage,")

    def test_get_flatpages_with_prefix_for_anon_user(self):
        "The flatpage template tag retrieves unregistered prefixed flatpages for an anonymous user"
        out = Template(
            "{% load flatpages %}"
            "{% get_flatpages '/location/' for anonuser as location_flatpages %}"
            "{% for page in location_flatpages %}"
            "{{ page.title }},"
            "{% endfor %}"
        ).render(Context({
            'anonuser': AnonymousUser()
        }))
        self.assertEqual(out, "A Nested Flatpage,")

    def test_get_flatpages_with_prefix_for_user(self):
        "The flatpage template tag retrieve prefixed flatpages for an authenticated user"
        me = User.objects.create_user('testuser', 'test@example.com', 's3krit')
        out = Template(
            "{% load flatpages %}"
            "{% get_flatpages '/location/' for me as location_flatpages %}"
            "{% for page in location_flatpages %}"
            "{{ page.title }},"
            "{% endfor %}"
        ).render(Context({
            'me': me
        }))
        self.assertEqual(out, "A Nested Flatpage,Sekrit Nested Flatpage,")

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
        self.assertEqual(out, "A Nested Flatpage,")

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
                          "{% load flatpages %}{% get_flatpages as flatpages asdf %}")
        self.assertRaises(TemplateSyntaxError, render,
                          "{% load flatpages %}{% get_flatpages cheesecake user as flatpages %}")
        self.assertRaises(TemplateSyntaxError, render,
                          "{% load flatpages %}{% get_flatpages for user as flatpages asdf %}")
        self.assertRaises(TemplateSyntaxError, render,
                          "{% load flatpages %}{% get_flatpages prefix for user as flatpages asdf %}")
