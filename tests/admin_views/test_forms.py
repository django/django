from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.admin.helpers import AdminForm, AdminReadonlyField
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase, override_settings

from .admin import ArticleAdmin, ArticleForm
from .models import Article


# To verify that the login form rejects inactive users, use an authentication
# backend that allows them.
@override_settings(
    AUTHENTICATION_BACKENDS=["django.contrib.auth.backends.AllowAllUsersModelBackend"]
)
class AdminAuthenticationFormTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User.objects.create_user(
            username="inactive", password="password", is_active=False
        )

    def test_inactive_user(self):
        data = {
            "username": "inactive",
            "password": "password",
        }
        form = AdminAuthenticationForm(None, data)
        self.assertEqual(form.non_field_errors(), ["This account is inactive."])


class AdminFormTests(SimpleTestCase):
    def setUp(self):
        self.model_admin = ArticleAdmin(Article, AdminSite())

    def test_repr(self):
        fieldsets = (
            (
                "My fields",
                {
                    "classes": ["collapse"],
                    "fields": ("url", "title", "content", "sites"),
                },
            ),
        )
        form = ArticleForm()
        admin_form = AdminForm(form, fieldsets, {}, model_admin=self.model_admin)
        self.assertEqual(
            repr(admin_form),
            "<AdminForm: form=ArticleForm fieldsets=(('My fields', "
            "{'classes': ['collapse'], "
            "'fields': ('url', 'title', 'content', 'sites')}),)>",
        )

    def test_model_admin_is_required(self):
        fieldsets = ((None, {"fields": ("title",)}),)
        msg = "missing 1 required keyword-only argument: 'model_admin'"
        with self.assertRaisesMessage(TypeError, msg):
            AdminForm(ArticleForm(), fieldsets, {})

    def test_model_admin_reaches_readonly_fields(self):
        fieldsets = ((None, {"fields": ("title",)}),)
        self.model_admin.empty_value_display = "???"
        admin_form = AdminForm(
            ArticleForm(),
            fieldsets,
            {},
            readonly_fields=("title",),
            model_admin=self.model_admin,
        )
        readonly_fields = [
            field for fieldset in admin_form for line in fieldset for field in line
        ]
        self.assertEqual(
            [field.empty_value_display for field in readonly_fields], ["???"]
        )


class AdminReadonlyFieldTests(SimpleTestCase):
    def test_empty_value_display_from_model_admin(self):
        model_admin = ArticleAdmin(Article, AdminSite())
        model_admin.empty_value_display = "???"
        readonly_field = AdminReadonlyField(
            ArticleForm(), "title", is_first=True, model_admin=model_admin
        )
        self.assertEqual(readonly_field.empty_value_display, "???")
