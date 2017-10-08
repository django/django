from django.contrib.auth.models import AnonymousUser, User
from django.contrib.flatpages.models import FlatPage
from django.contrib.sites.models import Site
from django.template import Context, Template, TemplateSyntaxError
from django.test import TestCase


class FlatpageTemplateTagTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        # don't use the manager because we want to ensure the site exists
        # with pk=1, regardless of whether or not it already exists.
        cls.site1 = Site(pk=1, domain='example.com', name='example.com')
        cls.site1.save()
        cls.fp1 = FlatPage.objects.create(
            url='/flatpage/', title='A Flatpage', content="Isn't it flat!",
            enable_comments=False, template_name='', registration_required=False
        )
        cls.fp2 = FlatPage.objects.create(
            url='/location/flatpage/', title='A Nested Flatpage', content="Isn't it flat and deep!",
            enable_comments=False, template_name='', registration_required=False
        )
        cls.fp3 = FlatPage.objects.create(
            url='/sekrit/', title='Sekrit Flatpage', content="Isn't it sekrit!",
            enable_comments=False, template_name='', registration_required=True
        )
        cls.fp4 = FlatPage.objects.create(
            url='/location/sekrit/', title='Sekrit Nested Flatpage', content="Isn't it sekrit and deep!",
            enable_comments=False, template_name='', registration_required=True
        )
        cls.fp1.sites.add(cls.site1)
        cls.fp2.sites.add(cls.site1)
        cls.fp3.sites.add(cls.site1)
        cls.fp4.sites.add(cls.site1)

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
        def render(t):
            return Template(t).render(Context())

        msg = (
            "get_flatpages expects a syntax of get_flatpages "
            "['url_starts_with'] [for user] as context_name"
        )
        with self.assertRaisesMessage(TemplateSyntaxError, msg):
            render("{% load flatpages %}{% get_flatpages %}")
        with self.assertRaisesMessage(TemplateSyntaxError, msg):
            render("{% load flatpages %}{% get_flatpages as %}")
        with self.assertRaisesMessage(TemplateSyntaxError, msg):
            render("{% load flatpages %}{% get_flatpages cheesecake flatpages %}")
        with self.assertRaisesMessage(TemplateSyntaxError, msg):
            render("{% load flatpages %}{% get_flatpages as flatpages asdf %}")
        with self.assertRaisesMessage(TemplateSyntaxError, msg):
            render("{% load flatpages %}{% get_flatpages cheesecake user as flatpages %}")
        with self.assertRaisesMessage(TemplateSyntaxError, msg):
            render("{% load flatpages %}{% get_flatpages for user as flatpages asdf %}")
        with self.assertRaisesMessage(TemplateSyntaxError, msg):
            render("{% load flatpages %}{% get_flatpages prefix for user as flatpages asdf %}")
