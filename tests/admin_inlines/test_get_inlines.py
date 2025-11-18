"""
Tests for ModelAdmin.get_inlines() hook.
"""
from django.contrib.admin import ModelAdmin, StackedInline, TabularInline
from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase, override_settings

from .admin import site as admin_site
from .models import Holder, Holder4, Inner, Inner2, Inner4Stacked, Inner4Tabular


class Inner2Inline(StackedInline):
    model = Inner2
    extra = 1


class AlternateInnerInline(StackedInline):
    model = Inner
    extra = 2


@override_settings(ROOT_URLCONF='admin_inlines.urls')
class GetInlinesTests(TestCase):
    """
    Tests for the get_inlines() hook.
    """
    factory = RequestFactory()

    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username='super',
            email='super@example.com',
            password='secret'
        )

    def test_get_inlines_default_behavior(self):
        """
        get_inlines() should return the inlines attribute by default.
        """
        class HolderAdmin(ModelAdmin):
            inlines = [AlternateInnerInline]

        ma = HolderAdmin(Holder, admin_site)
        request = self.factory.get('/')
        request.user = self.superuser

        inlines = ma.get_inlines(request)
        self.assertEqual(inlines, [AlternateInnerInline])

    def test_get_inlines_with_obj(self):
        """
        get_inlines() should receive the obj parameter.
        """
        holder = Holder.objects.create(dummy=1)

        class HolderAdmin(ModelAdmin):
            inlines = [AlternateInnerInline]

            def get_inlines(self, request, obj=None):
                # Return different inlines based on obj
                if obj and obj.dummy > 0:
                    return [AlternateInnerInline]
                return []

        ma = HolderAdmin(Holder, admin_site)
        request = self.factory.get('/')
        request.user = self.superuser

        # With obj
        inlines = ma.get_inlines(request, holder)
        self.assertEqual(inlines, [AlternateInnerInline])

        # Without obj
        inlines = ma.get_inlines(request, None)
        self.assertEqual(inlines, [])

    def test_get_inlines_based_on_request(self):
        """
        get_inlines() can return different inlines based on request.
        """
        class HolderAdmin(ModelAdmin):
            inlines = [AlternateInnerInline]

            def get_inlines(self, request, obj=None):
                # Return different inlines based on user
                if request.user.is_superuser:
                    return [AlternateInnerInline]
                return []

        ma = HolderAdmin(Holder, admin_site)

        # Superuser request
        request = self.factory.get('/')
        request.user = self.superuser
        inlines = ma.get_inlines(request)
        self.assertEqual(inlines, [AlternateInnerInline])

        # Regular user request
        regular_user = User.objects.create_user(
            username='regular',
            email='regular@example.com',
            password='secret'
        )
        request = self.factory.get('/')
        request.user = regular_user
        inlines = ma.get_inlines(request)
        self.assertEqual(inlines, [])

    def test_get_inline_instances_uses_get_inlines(self):
        """
        get_inline_instances() should use get_inlines() to get the inline classes.
        """
        class HolderAdmin(ModelAdmin):
            inlines = [AlternateInnerInline]

            def get_inlines(self, request, obj=None):
                if obj:
                    return [AlternateInnerInline]
                return []

        ma = HolderAdmin(Holder, admin_site)
        request = self.factory.get('/')
        request.user = self.superuser

        # Without obj - should return empty list
        inline_instances = ma.get_inline_instances(request, None)
        self.assertEqual(len(inline_instances), 0)

        # With obj - should return one inline instance
        holder = Holder.objects.create(dummy=1)
        inline_instances = ma.get_inline_instances(request, holder)
        self.assertEqual(len(inline_instances), 1)
        self.assertIsInstance(inline_instances[0], AlternateInnerInline)

    def test_get_inlines_multiple_inlines(self):
        """
        get_inlines() can return multiple inlines based on conditions.
        """
        class Inner4StackedInlineClass(StackedInline):
            model = Inner4Stacked

        class Inner4TabularInlineClass(TabularInline):
            model = Inner4Tabular

        class Holder4Admin(ModelAdmin):
            inlines = [Inner4StackedInlineClass, Inner4TabularInlineClass]

            def get_inlines(self, request, obj=None):
                # Return only stacked inline for add view
                if obj is None:
                    return [Inner4StackedInlineClass]
                # Return both for change view
                return self.inlines

        ma = Holder4Admin(Holder4, admin_site)
        request = self.factory.get('/')
        request.user = self.superuser

        # Add view (obj is None)
        inlines = ma.get_inlines(request, None)
        self.assertEqual(len(inlines), 1)
        self.assertEqual(inlines[0], Inner4StackedInlineClass)

        # Change view (obj exists)
        holder4 = Holder4.objects.create(dummy=1)
        inlines = ma.get_inlines(request, holder4)
        self.assertEqual(len(inlines), 2)
        self.assertEqual(inlines, [Inner4StackedInlineClass, Inner4TabularInlineClass])

    def test_get_inlines_empty_list(self):
        """
        get_inlines() can return an empty list to disable all inlines.
        """
        class HolderAdmin(ModelAdmin):
            inlines = [AlternateInnerInline]

            def get_inlines(self, request, obj=None):
                return []

        ma = HolderAdmin(Holder, admin_site)
        request = self.factory.get('/')
        request.user = self.superuser

        inlines = ma.get_inlines(request)
        self.assertEqual(inlines, [])

        inline_instances = ma.get_inline_instances(request)
        self.assertEqual(len(inline_instances), 0)

    def test_get_inlines_conditional_on_object_state(self):
        """
        get_inlines() can return different inlines based on object state.
        """
        holder1 = Holder.objects.create(dummy=5)
        holder2 = Holder.objects.create(dummy=15)

        class HolderAdmin(ModelAdmin):
            inlines = [AlternateInnerInline]

            def get_inlines(self, request, obj=None):
                # Show inlines only if dummy value is greater than 10
                if obj and obj.dummy > 10:
                    return self.inlines
                return []

        ma = HolderAdmin(Holder, admin_site)
        request = self.factory.get('/')
        request.user = self.superuser

        # holder1 with dummy=5 should not have inlines
        inlines = ma.get_inlines(request, holder1)
        self.assertEqual(inlines, [])

        # holder2 with dummy=15 should have inlines
        inlines = ma.get_inlines(request, holder2)
        self.assertEqual(inlines, [AlternateInnerInline])

    def test_get_inlines_integration_with_permissions(self):
        """
        get_inlines() works correctly with permission checks in get_inline_instances().
        """
        holder = Holder.objects.create(dummy=1)

        class RestrictedInnerInline(StackedInline):
            model = Inner

            def has_view_or_change_permission(self, request, obj=None):
                return False

            def has_add_permission(self, request, obj=None):
                return False

            def has_delete_permission(self, request, obj=None):
                return False

        class HolderAdmin(ModelAdmin):
            inlines = [RestrictedInnerInline]

        ma = HolderAdmin(Holder, admin_site)
        request = self.factory.get('/')
        request.user = self.superuser

        # get_inlines should return the inline
        inlines = ma.get_inlines(request, holder)
        self.assertEqual(inlines, [RestrictedInnerInline])

        # But get_inline_instances should filter it out due to permissions
        inline_instances = ma.get_inline_instances(request, holder)
        self.assertEqual(len(inline_instances), 0)
