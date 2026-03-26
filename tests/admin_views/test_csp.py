from django.contrib.auth.models import User
from django.test import TestCase, modify_settings, override_settings
from django.urls import reverse

CSP_TEMPLATES = [
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
    }
]

csp_settings = override_settings(
    TEMPLATES=CSP_TEMPLATES,
)
csp_middleware = modify_settings(
    MIDDLEWARE={"append": "django.middleware.csp.ContentSecurityPolicyMiddleware"}
)


@override_settings(ROOT_URLCONF="admin_views.urls")
class AdminCspNonceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="super", password="secret", email="super@example.com"
        )

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_no_nonce_without_csp_context_processor(self):
        response = self.client.get(reverse("admin:index"))
        self.assertNotContains(response, 'nonce="')

    @csp_settings
    @csp_middleware
    def test_index_base_scripts_have_nonce(self):
        response = self.client.get(reverse("admin:index"))
        content = response.content.decode()
        self.assertRegex(content, r'<script src="[^"]*theme\.js"[^>]*nonce="[^"]+"')
        self.assertRegex(
            content, r'<script src="[^"]*nav_sidebar\.js"[^>]*nonce="[^"]+"'
        )

    @csp_settings
    @csp_middleware
    def test_index_base_links_have_nonce(self):
        response = self.client.get(reverse("admin:index"))
        content = response.content.decode()
        self.assertRegex(content, r'<link[^>]+base\.css"[^>]*nonce="[^"]+"')
        self.assertRegex(content, r'<link[^>]+dashboard\.css"[^>]*nonce="[^"]+"')

    @csp_settings
    @csp_middleware
    def test_change_form_scripts_have_nonce(self):
        response = self.client.get(
            reverse("admin:auth_user_change", args=[self.superuser.pk])
        )
        content = response.content.decode()
        self.assertRegex(
            content, r'<script[^>]*src="[^"]*change_form\.js"[^>]*nonce="[^"]+"'
        )

    @csp_settings
    @csp_middleware
    def test_change_form_links_have_nonce(self):
        response = self.client.get(
            reverse("admin:auth_user_change", args=[self.superuser.pk])
        )
        self.assertRegex(
            response.content.decode(), r'<link[^>]+forms\.css"[^>]*nonce="[^"]+"'
        )

    @csp_settings
    @csp_middleware
    def test_change_list_scripts_have_nonce(self):
        response = self.client.get(reverse("admin:auth_user_changelist"))
        self.assertRegex(
            response.content.decode(),
            r'<script src="[^"]*filters\.js"[^>]*nonce="[^"]+"',
        )

    @csp_settings
    @csp_middleware
    def test_change_list_links_have_nonce(self):
        response = self.client.get(reverse("admin:auth_user_changelist"))
        self.assertRegex(
            response.content.decode(), r'<link[^>]+changelists\.css"[^>]*nonce="[^"]+"'
        )

    @csp_settings
    @csp_middleware
    def test_delete_confirmation_script_has_nonce(self):
        response = self.client.get(
            reverse("admin:auth_user_delete", args=[self.superuser.pk])
        )
        self.assertRegex(
            response.content.decode(),
            r'<script src="[^"]*cancel\.js"[^>]*nonce="[^"]+"',
        )

    @csp_settings
    @csp_middleware
    def test_login_link_has_nonce(self):
        self.client.logout()
        response = self.client.get(reverse("admin:login"))
        self.assertRegex(
            response.content.decode(), r'<link[^>]+login\.css"[^>]*nonce="[^"]+"'
        )
