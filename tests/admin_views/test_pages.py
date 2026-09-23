from unittest import mock

from django.apps import apps
from django.contrib import admin
from django.contrib.admin.exceptions import AlreadyRegistered, NotRegistered
from django.contrib.admin.sites import DefaultAdminSite
from django.contrib.auth.management import create_permissions
from django.contrib.auth.models import Group, Permission, User
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.http import HttpResponse
from django.test import Client, SimpleTestCase, TestCase, override_settings
from django.urls import path, reverse
from django.utils.module_loading import autodiscover_modules

from .models import Article

site = admin.AdminSite(name="pages")
other_site = admin.AdminSite(name="other_pages")


@admin.register_view(site=site)
class ReportsPage(admin.AdminPage):
    title = "Reports"
    path = "/reports/"
    url_name = "admin:reports"


@admin.register_view(site=site)
class PublicPage(admin.AdminPage):
    title = "Overview"
    path = "overview/"
    url_name = "overview"

    def has_permission(self, request):
        return self.admin_site.has_permission(request)

    def view(self, request):
        if request.method == "POST":
            return HttpResponse("Saved")
        return super().view(request)


other_site.register_view(ReportsPage)
urlpatterns = [path("admin/", site.urls), path("other/", other_site.urls)]


class RegistrationTests(SimpleTestCase):
    def test_registration(self):
        local_site = admin.AdminSite()
        local_site.register_view(ReportsPage)
        with self.assertRaises(AlreadyRegistered):
            local_site.register_view(ReportsPage)

        class Duplicate(ReportsPage):
            pass

        with self.assertRaises(AlreadyRegistered):
            local_site.register_view(Duplicate)
        local_site.unregister_view(ReportsPage)
        with self.assertRaises(NotRegistered):
            local_site.unregister_view(ReportsPage)
        with self.assertRaises(ValueError):
            local_site.register_view(object)

    def test_decorator(self):
        try:
            self.assertIs(admin.register_view(ReportsPage), ReportsPage)
        finally:
            admin.site.unregister_view(ReportsPage)

    def test_default_site(self):
        self.assertIs(ReportsPage().admin_site, admin.site)
        self.assertIs(ReportsPage(site=None).admin_site, admin.site)

    def test_explicit_site(self):
        self.assertIs(ReportsPage(site=other_site).admin_site, other_site)
        self.assertIs(ReportsPage(other_site).admin_site, other_site)
        self.assertIs(other_site._page_registry[ReportsPage].admin_site, other_site)
        with self.assertRaisesMessage(ValueError, "site must subclass AdminSite"):
            ReportsPage(site=object())

    def test_configured_default_site(self):
        default_site = DefaultAdminSite()
        config = apps.get_app_config("admin")
        with (
            mock.patch.object(
                config, "default_site", "admin_views.test_adminsite.CustomAdminSite"
            ),
            mock.patch("django.contrib.admin.sites.site", default_site),
        ):
            page = ReportsPage()
            admin.register_view()(ReportsPage)
            admin.register(Article)(admin.ModelAdmin)
            self.assertIs(page.admin_site, default_site)
            self.assertEqual(page.admin_site.site_title, "Custom title")
            self.assertIs(
                default_site._page_registry[ReportsPage].admin_site,
                default_site._wrapped,
            )
            self.assertIs(
                default_site.get_model_admin(Article).admin_site, default_site._wrapped
            )
            explicit_site = admin.AdminSite(name="explicit")
            self.assertIs(ReportsPage(site=explicit_site).admin_site, explicit_site)
            admin.register_view(site=explicit_site)(ReportsPage)
            admin.register(Article, site=explicit_site)(admin.ModelAdmin)
            self.assertIs(
                explicit_site._page_registry[ReportsPage].admin_site, explicit_site
            )
            self.assertIs(
                explicit_site.get_model_admin(Article).admin_site, explicit_site
            )

    def test_metadata(self):
        metadata = admin.ModelAdmin(Article, site).get_admin_page_meta()
        self.assertEqual(metadata.app_label, "admin_views")
        self.assertEqual(metadata.path, "article/")
        self.assertEqual(metadata.url_name, "admin_views_article_changelist")

    def test_invalid_configuration(self):
        for options in (
            {"app_label": "missing_app"},
            {"path": ""},
            {"path": "<int:pk>/"},
            {"title": None},
            {"required_permissions": "admin_views.view_reports"},
            {"required_permissions": ["invalid"]},
            {"url_name": "other:reports"},
            {"url_name": 123},
            {"required_permissions": ["admin_views." + "x" * 101]},
        ):
            with self.subTest(options=options):
                page = type("InvalidPage", (ReportsPage,), options)
                with self.assertRaises(ImproperlyConfigured):
                    admin.AdminSite().register_view(page)

    def test_model_url_conflicts(self):
        for options in ({"path": "article/"}, {"url_name": "index"}):
            with self.subTest(options=options):
                local_site = admin.AdminSite()
                local_site.register(Article)
                local_site.register_view(type("ConflictPage", (ReportsPage,), options))
                with self.assertRaisesMessage(ImproperlyConfigured, "conflicts"):
                    local_site.get_urls()

    def test_autodiscovery_rollback(self):
        local_site = admin.AdminSite()

        def broken_import(name):
            local_site.register_view(ReportsPage)
            raise RuntimeError("broken import")

        with mock.patch("django.utils.module_loading.import_module", broken_import):
            with mock.patch(
                "django.utils.module_loading.module_has_submodule", return_value=True
            ):
                with self.assertRaisesMessage(RuntimeError, "broken import"):
                    autodiscover_modules("admin", register_to=local_site)
        self.assertEqual(local_site._page_registry, {})


@override_settings(ROOT_URLCONF=__name__)
class PageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff = User.objects.create_user("staff", is_staff=True)
        cls.permission = Permission.objects.get(
            content_type__app_label="admin_views", codename="view_reportspage"
        )

    def setUp(self):
        self.client.force_login(self.staff)

    def test_permission_enforced_on_view_and_navigation(self):
        url = reverse("pages:reports")
        self.assertEqual(url, "/admin/admin_views/reports/")
        self.assertEqual(self.client.get(url).status_code, 403)
        self.assertNotContains(self.client.get(reverse("pages:index")), "Reports")
        self.staff.user_permissions.add(self.permission)
        response = self.client.get(url)
        self.assertContains(response, "Reports")
        self.assertContains(response, 'id="nav-sidebar"')
        self.assertContains(response, 'class="breadcrumbs"')
        self.assertContains(self.client.get(reverse("pages:index")), url)
        self.assertContains(
            self.client.get(
                reverse("pages:app_list", kwargs={"app_label": "admin_views"})
            ),
            "Reports",
        )
        self.assertIn("no-store", response.headers["Cache-Control"])

    def test_default_access_and_post(self):
        url = reverse("pages:overview")
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertContains(self.client.post(url), "Saved")
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.staff)
        self.assertEqual(csrf_client.post(url).status_code, 403)
        self.client.logout()
        self.assertRedirects(
            self.client.get(url), reverse("pages:login") + "?next=" + url
        )

    def test_nonstaff_and_inactive(self):
        for attribute in ("is_staff", "is_active"):
            with self.subTest(attribute=attribute):
                setattr(self.staff, attribute, False)
                self.staff.save()
                self.assertEqual(
                    self.client.get(reverse("pages:overview")).status_code, 302
                )
                setattr(self.staff, attribute, True)
                self.staff.save()

    def test_custom_site_links(self):
        self.staff.user_permissions.add(self.permission)
        response = self.client.get(reverse("other_pages:reports"))
        self.assertContains(response, 'href="/other/"')
        self.assertContains(response, 'href="/other/admin_views/"')

    def test_permissions_are_idempotent_and_survive_cleanup(self):
        create_permissions(apps.get_app_config("admin"), verbosity=0)
        self.assertEqual(
            Permission.objects.filter(
                content_type__app_label="admin_views", codename="view_reportspage"
            ).count(),
            1,
        )
        self.staff.user_permissions.add(self.permission)
        call_command("remove_stale_contenttypes", interactive=False, verbosity=0)
        self.assertTrue(
            self.staff.user_permissions.filter(pk=self.permission.pk).exists()
        )

    def test_custom_permission_hook(self):
        self.staff.user_permissions.add(self.permission)
        with mock.patch.object(ReportsPage, "has_permission", return_value=False):
            self.assertEqual(self.client.get(reverse("pages:reports")).status_code, 403)
            self.assertNotContains(self.client.get(reverse("pages:index")), "Reports")

    def test_reuse_existing_permission(self):
        count = Permission.objects.filter(
            content_type__app_label="auth", codename="view_user"
        ).count()
        with mock.patch.object(ReportsPage, "required_permissions", ["auth.view_user"]):
            create_permissions(apps.get_app_config("admin"), verbosity=0)
        self.assertEqual(
            Permission.objects.filter(
                content_type__app_label="auth", codename="view_user"
            ).count(),
            count,
        )

    def test_permission_creation_honors_router(self):
        with mock.patch(
            "django.contrib.auth.management.router.allow_migrate_model",
            return_value=False,
        ):
            with self.assertNumQueries(0):
                create_permissions(apps.get_app_config("admin"), verbosity=0)

    def test_group_permissions_and_superuser(self):
        group = Group.objects.create(name="Report readers")
        group.permissions.add(self.permission)
        self.staff.groups.add(group)
        self.assertEqual(self.client.get(reverse("pages:reports")).status_code, 200)
        self.staff.groups.clear()
        self.staff.is_superuser = True
        self.staff.save()
        self.assertEqual(self.client.get(reverse("pages:reports")).status_code, 200)

    def test_custom_template_and_context(self):
        templates = [
            {
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "APP_DIRS": False,
                "OPTIONS": {
                    "loaders": [
                        (
                            "django.template.loaders.locmem.Loader",
                            {
                                "reports.html": '{% extends "admin/page.html" %}'
                                "{% block content %}<p>Report content</p>{% endblock %}",
                            },
                        ),
                        "django.template.loaders.app_directories.Loader",
                    ],
                },
            }
        ]
        self.staff.user_permissions.add(self.permission)
        with self.settings(TEMPLATES=templates):
            with mock.patch.object(ReportsPage, "template_name", "reports.html"):
                response = self.client.get(reverse("pages:reports"))
        self.assertContains(response, "Report content")
        self.assertEqual(response.context["app_label"], "admin_views")
        self.assertEqual(response.context["title"], "Reports")

    def test_only_view_permission_created(self):
        permissions = Permission.objects.filter(
            content_type__app_label="admin_views",
            content_type__model="_admin_page_reportspage",
        )
        self.assertEqual(
            list(permissions.values_list("codename", "name")),
            [("view_reportspage", "Can view Reports")],
        )

    def test_additional_permissions_are_checked_not_created(self):
        self.staff.user_permissions.add(self.permission)
        with mock.patch.object(ReportsPage, "required_permissions", ["auth.view_user"]):
            self.assertEqual(self.client.get(reverse("pages:reports")).status_code, 403)
            self.staff.user_permissions.add(
                Permission.objects.get(
                    content_type__app_label="auth", codename="view_user"
                )
            )
            self.assertEqual(self.client.get(reverse("pages:reports")).status_code, 200)
        with mock.patch.object(
            ReportsPage, "required_permissions", ["admin_views.missing"]
        ):
            create_permissions(apps.get_app_config("admin"), verbosity=0)
        self.assertFalse(Permission.objects.filter(codename="missing").exists())

    def test_page_in_app_without_models(self):
        self.assertIsNone(apps.get_app_config("messages").models_module)
        local_site = admin.AdminSite()

        class MessageReport(admin.AdminPage):
            app_label = "messages"
            title = "Message report"
            path = "report/"

        local_site.register_view(MessageReport)
        create_permissions(apps.get_app_config("admin"), verbosity=0)
        self.assertEqual(
            list(
                Permission.objects.filter(
                    content_type__app_label="messages",
                    content_type__model="_admin_page_messagereport",
                ).values_list("codename", "name")
            ),
            [("view_messagereport", "Can view Message report")],
        )


class PagePermissionDatabaseTests(TestCase):
    databases = {"default", "other"}

    def test_database_alias(self):
        Permission.objects.using("other").filter(
            content_type__app_label="admin_views",
            content_type__model="_admin_page_reportspage",
        ).delete()
        with self.assertNumQueries(0, using="default"):
            create_permissions(apps.get_app_config("admin"), using="other", verbosity=0)
        self.assertEqual(
            list(
                Permission.objects.using("other")
                .filter(
                    content_type__app_label="admin_views",
                    content_type__model="_admin_page_reportspage",
                )
                .values_list("codename", "name")
            ),
            [("view_reportspage", "Can view Reports")],
        )
