from django.contrib.admin.options import IS_POPUP_VAR
from django.contrib.auth.models import User
from django.middleware.csp import get_nonce
from django.test import TestCase, modify_settings, override_settings
from django.urls import reverse
from django.utils.csp import CSP

from .models import Recipe


@modify_settings(
    MIDDLEWARE={"append": "django.middleware.csp.ContentSecurityPolicyMiddleware"}
)
@override_settings(
    ROOT_URLCONF="admin_views.urls",
    TEMPLATES=[
        {
            "BACKEND": "django.template.backends.django.DjangoTemplates",
            "APP_DIRS": True,
            "OPTIONS": {
                "context_processors": [
                    "django.template.context_processors.request",
                    "django.contrib.auth.context_processors.auth",
                    "django.contrib.messages.context_processors.messages",
                    "django.template.context_processors.csp",
                ],
            },
        },
    ],
    SECURE_CSP={
        "script-src": [CSP.NONCE],
    },
)
class AdminCSPNonceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="super", password="secret", email="super@example.com"
        )
        cls.recipe = Recipe.objects.create(rname="pizza")

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_base(self):
        response = self.client.get(reverse("admin:index"))
        expected_nonce = get_nonce(response.wsgi_request)
        self.assertContains(
            response,
            f'<script src="/static/admin/js/theme.js" nonce="{expected_nonce}">',
        )
        self.assertContains(
            response,
            '<script src="/static/admin/js/nav_sidebar.js"'
            f' nonce="{expected_nonce}" defer>',
        )

    def test_changeform(self):
        response = self.client.get(
            reverse("admin:admin_views_recipe_change", args=(self.recipe.pk,))
        )
        expected_nonce = get_nonce(response.wsgi_request)
        self.assertContains(
            response,
            f'<script src="/test_admin/admin/jsi18n/" nonce="{expected_nonce}">',
        )
        self.assertContains(
            response,
            '<script id="django-admin-prepopulated-fields-constants"'
            ' src="/static/admin/js/prepopulate_init.js"'
            f' data-prepopulated-fields="[]" nonce="{expected_nonce}"></script>',
            html=True,
        )

    def test_changelist(self):
        response = self.client.get(reverse("admin:admin_views_recipe_changelist"))
        expected_nonce = get_nonce(response.wsgi_request)
        self.assertContains(
            response,
            f'<script src="/test_admin/admin/jsi18n/" nonce="{expected_nonce}">',
        )
        self.assertContains(
            response,
            '<script src="/static/admin/js/filters.js"'
            f' nonce="{expected_nonce}" defer>',
        )

    def test_delete_confirmation(self):
        response = self.client.get(
            reverse("admin:admin_views_recipe_delete", args=(self.recipe.pk,))
        )
        expected_nonce = get_nonce(response.wsgi_request)
        self.assertContains(
            response,
            f'<script src="/static/admin/js/cancel.js" nonce="{expected_nonce}" async>',
        )

    def test_delete_selected_confirmation(self):
        post_data = {
            "action": "delete_selected",
            "selected_across": "0",
            "index": "0",
            "_selected_action": self.recipe.pk,
        }
        response = self.client.post(
            reverse("admin:admin_views_recipe_changelist"), post_data, follow=True
        )
        expected_nonce = get_nonce(response.wsgi_request)
        self.assertContains(
            response,
            f'<script src="/static/admin/js/cancel.js" nonce="{expected_nonce}" async>',
        )

    def test_popup_response(self):
        post_data = {"rname": "chicken", "_save": "Save", IS_POPUP_VAR: "1"}
        response = self.client.post(
            reverse("admin:admin_views_recipe_add") + "?%s=1" % IS_POPUP_VAR,
            post_data,
            follwo=True,
        )
        expected_nonce = get_nonce(response.wsgi_request)
        self.assertContains(response, f'nonce="{expected_nonce}"')


@override_settings(
    ROOT_URLCONF="admin_views.urls",
)
class AdminWithoutCSPNonceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="super", password="secret", email="super@example.com"
        )
        cls.recipe = Recipe.objects.create(rname="snow")

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_base(self):
        response = self.client.get(reverse("admin:index"))
        self.assertContains(response, '<script src="/static/admin/js/theme.js">')
        self.assertContains(
            response, '<script src="/static/admin/js/nav_sidebar.js" defer>'
        )

    def test_chaneform(self):
        response = self.client.get(
            reverse("admin:admin_views_recipe_change", args=(self.recipe.pk,))
        )
        self.assertContains(response, '<script src="/test_admin/admin/jsi18n/">')
        self.assertContains(
            response,
            '<script id="django-admin-prepopulated-fields-constants"'
            ' src="/static/admin/js/prepopulate_init.js"'
            ' data-prepopulated-fields="[]"></script>',
            html=True,
        )

    def test_changelist(self):
        response = self.client.get(reverse("admin:admin_views_recipe_changelist"))
        self.assertContains(response, '<script src="/test_admin/admin/jsi18n/">')
        self.assertContains(
            response, '<script src="/static/admin/js/filters.js" defer>'
        )

    def test_delete_confirmation(self):
        response = self.client.get(
            reverse("admin:admin_views_recipe_delete", args=(self.recipe.pk,))
        )
        self.assertContains(response, '<script src="/static/admin/js/cancel.js" async>')

    def test_delete_selected_confirmation(self):
        post_data = {
            "action": "delete_selected",
            "selected_across": "0",
            "index": "0",
            "_selected_action": self.recipe.pk,
        }
        response = self.client.post(
            reverse("admin:admin_views_recipe_changelist"), post_data, follow=True
        )
        self.assertContains(response, '<script src="/static/admin/js/cancel.js" async>')

    def test_popup_response(self):
        post_data = {"rname": "hamburger", "_save": "Save", IS_POPUP_VAR: "1"}
        response = self.client.post(
            reverse("admin:admin_views_recipe_add") + "?%s=1" % IS_POPUP_VAR,
            post_data,
            follwo=True,
        )
        self.assertNotContains(response, "nonce=")
