from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.admin.helpers import AdminForm, AdminReadonlyField
from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils.deprecation import RemovedInDjango70Warning

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
        from django.contrib.admin.sites import AdminSite

        model_admin = ArticleAdmin(Article, AdminSite())
        form = ArticleForm()
        admin_form = AdminForm(form, fieldsets, {}, model_admin=model_admin)
        self.assertEqual(
            repr(admin_form),
            "<AdminForm: form=ArticleForm fieldsets=(('My fields', "
            "{'classes': ['collapse'], "
            "'fields': ('url', 'title', 'content', 'sites')}),)>",
        )

    def test_adminform_no_model_admin_deprecation_warning(self):
        fieldsets = ((None, {"fields": ("title",)}),)
        form = ArticleForm()
        msg = (
            "Passing model_admin=None to AdminForm is deprecated. "
            "Provide a ModelAdmin instance instead."
        )
        with self.assertWarnsMessage(RemovedInDjango70Warning, msg):
            AdminForm(form, fieldsets, {})

    def test_adminform_no_model_admin_readonly_fields_no_crash(self):
        fieldsets = ((None, {"fields": ("title",)}),)
        form = ArticleForm()
        msg = (
            "Passing model_admin=None to AdminForm is deprecated. "
            "Provide a ModelAdmin instance instead."
        )
        with self.assertWarnsMessage(RemovedInDjango70Warning, msg):
            admin_form = AdminForm(form, fieldsets, {}, readonly_fields=("title",))
            for fieldset in admin_form:
                for fieldline in fieldset:
                    for field in fieldline:
                        pass

    def test_admin_readonly_field_no_model_admin_deprecation_warning(self):
        form = ArticleForm()
        msg = (
            "Passing model_admin=None to AdminReadonlyField is deprecated. "
            "Provide a ModelAdmin instance instead."
        )
        with self.assertWarnsMessage(RemovedInDjango70Warning, msg):
            readonly_field = AdminReadonlyField(form, "title", is_first=True)
        self.assertEqual(readonly_field.empty_value_display, "-")
