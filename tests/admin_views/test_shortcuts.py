"""
Tests for Django admin keyboard shortcuts functionality.
"""
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from .admin import ArticleAdmin
from .models import Article


class AdminShortcutsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="super", password="secret", email="super@example.com"
        )

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_shortcuts_js_included_in_change_form(self):
        """Test that shortcuts.js is included in change form pages."""
        # Test add form
        response = self.client.get(reverse("admin:admin_views_article_add"))
        self.assertContains(response, 'src="/static/admin/js/shortcuts.js"')
        self.assertEqual(response.status_code, 200)

        # Test change form
        article = Article.objects.create(
            title="Test Article",
            content="Test content",
            date=None,
        )
        response = self.client.get(
            reverse("admin:admin_views_article_change", args=[article.pk])
        )
        self.assertContains(response, 'src="/static/admin/js/shortcuts.js"')
        self.assertEqual(response.status_code, 200)

    def test_shortcuts_not_included_in_changelist(self):
        """Test that shortcuts.js is not included in changelist pages."""
        response = self.client.get(reverse("admin:admin_views_article_changelist"))
        self.assertNotContains(response, 'src="/static/admin/js/shortcuts.js"')
        self.assertEqual(response.status_code, 200)

    def test_shortcuts_not_included_in_admin_index(self):
        """Test that shortcuts.js is not included in admin index."""
        response = self.client.get(reverse("admin:index"))
        self.assertNotContains(response, 'src="/static/admin/js/shortcuts.js"')
        self.assertEqual(response.status_code, 200)

    def test_form_buttons_present_for_shortcuts(self):
        """Test that the form buttons targeted by shortcuts are present."""
        # Test add form - should have save, save and add another, but not save and continue
        response = self.client.get(reverse("admin:admin_views_article_add"))
        self.assertContains(response, 'name="_save"')
        self.assertContains(response, 'name="_addanother"')
        # Continue button typically not present on add forms
        self.assertNotContains(response, 'name="_continue"')

        # Test change form - should have all three buttons
        article = Article.objects.create(
            title="Test Article",
            content="Test content",
            date=None,
        )
        response = self.client.get(
            reverse("admin:admin_views_article_change", args=[article.pk])
        )
        self.assertContains(response, 'name="_save"')
        self.assertContains(response, 'name="_addanother"')
        self.assertContains(response, 'name="_continue"')

    def test_shortcuts_js_async_loading(self):
        """Test that shortcuts.js is loaded asynchronously."""
        response = self.client.get(reverse("admin:admin_views_article_add"))
        # The async attribute should be present for performance
        self.assertContains(response, 'shortcuts.js" async')

    @override_settings(DEBUG=True)
    def test_shortcuts_work_in_debug_mode(self):
        """Test that shortcuts work properly in debug mode."""
        response = self.client.get(reverse("admin:admin_views_article_add"))
        self.assertContains(response, 'src="/static/admin/js/shortcuts.js"')
        self.assertEqual(response.status_code, 200)

    def test_shortcuts_in_popup_forms(self):
        """Test that shortcuts work in popup forms."""
        # Test add form in popup
        response = self.client.get(
            reverse("admin:admin_views_article_add") + "?_popup=1"
        )
        self.assertContains(response, 'src="/static/admin/js/shortcuts.js"')
        # In popup mode, continue and add another buttons should not be present
        self.assertNotContains(response, 'name="_continue"')
        self.assertNotContains(response, 'name="_addanother"')

        # Test change form in popup
        article = Article.objects.create(
            title="Test Article",
            content="Test content",
            date=None,
        )
        response = self.client.get(
            reverse("admin:admin_views_article_change", args=[article.pk]) + "?_popup=1"
        )
        self.assertContains(response, 'src="/static/admin/js/shortcuts.js"')
        # In popup mode, continue and add another buttons should not be present
        self.assertNotContains(response, 'name="_continue"')
        self.assertNotContains(response, 'name="_addanother"')


class AdminShortcutsJavaScriptTests(TestCase):
    """
    Tests for the JavaScript functionality of admin shortcuts.
    Note: These tests verify HTML structure and script inclusion.
    Full keyboard event testing would require a JavaScript testing framework.
    """

    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="super", password="secret", email="super@example.com"
        )

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_button_selectors_in_html(self):
        """Test that the buttons with correct selectors are present in HTML."""
        response = self.client.get(reverse("admin:admin_views_article_add"))
        
        # Check for input elements with the expected names
        self.assertContains(response, 'input[name="_save"]')
        self.assertContains(response, 'input[name="_addanother"]')

    def test_form_structure_for_shortcuts(self):
        """Test that the form structure supports keyboard shortcuts."""
        article = Article.objects.create(
            title="Test Article",
            content="Test content", 
            date=None,
        )
        response = self.client.get(
            reverse("admin:admin_views_article_change", args=[article.pk])
        )
        
        # Verify form has the expected ID that might be used by JavaScript
        self.assertContains(response, 'id="article_form"')
        
        # Verify buttons are input type="submit"
        self.assertContains(response, 'type="submit"')

    def test_no_javascript_conflicts(self):
        """Test that there are no obvious JavaScript conflicts in the page."""
        response = self.client.get(reverse("admin:admin_views_article_add"))
        
        # Should include jQuery (required by admin)
        self.assertContains(response, "jquery")
        
        # Should include our shortcuts script
        self.assertContains(response, "shortcuts.js")
        
        # Should not have duplicate script inclusions
        content = response.content.decode()
        shortcuts_count = content.count("shortcuts.js")
        self.assertEqual(shortcuts_count, 1, "shortcuts.js should only be included once")
