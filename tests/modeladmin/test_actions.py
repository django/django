from django.contrib import admin
from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from .models import Band


class AdminActionsTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(username='super', password='secret', email='super@example.com')
        content_type = ContentType.objects.get_for_model(Band)
        Permission.objects.create(name='custom', codename='custom_band', content_type=content_type)
        for user_type in ('view', 'add', 'change', 'delete', 'custom'):
            username = '%suser' % user_type
            user = User.objects.create_user(username=username, password='secret', is_staff=True)
            permission = Permission.objects.get(codename='%s_band' % user_type, content_type=content_type)
            user.user_permissions.add(permission)
            setattr(cls, username, user)

    def test_get_actions_respects_permissions(self):
        class MockRequest:
            pass

        class BandAdmin(admin.ModelAdmin):
            actions = ['custom_action']

            @admin.action
            def custom_action(modeladmin, request, queryset):
                pass

            def has_custom_permission(self, request):
                return request.user.has_perm('%s.custom_band' % self.opts.app_label)

        ma = BandAdmin(Band, admin.AdminSite())
        mock_request = MockRequest()
        mock_request.GET = {}
        cases = [
            (None, self.viewuser, ['custom_action']),
            ('view', self.superuser, ['delete_selected', 'custom_action']),
            ('view', self.viewuser, ['custom_action']),
            ('add', self.adduser, ['custom_action']),
            ('change', self.changeuser, ['custom_action']),
            ('delete', self.deleteuser, ['delete_selected', 'custom_action']),
            ('custom', self.customuser, ['custom_action']),
        ]
        for permission, user, expected in cases:
            with self.subTest(permission=permission, user=user):
                if permission is None:
                    if hasattr(BandAdmin.custom_action, 'allowed_permissions'):
                        del BandAdmin.custom_action.allowed_permissions
                else:
                    BandAdmin.custom_action.allowed_permissions = (permission,)
                mock_request.user = user
                actions = ma.get_actions(mock_request)
                self.assertEqual(list(actions.keys()), expected)

    def test_actions_inheritance(self):
        class AdminBase(admin.ModelAdmin):
            actions = ['custom_action']

            @admin.action
            def custom_action(modeladmin, request, queryset):
                pass

        class AdminA(AdminBase):
            pass

        class AdminB(AdminBase):
            actions = None

        ma1 = AdminA(Band, admin.AdminSite())
        action_names = [name for _, name, _ in ma1._get_base_actions()]
        self.assertEqual(action_names, ['delete_selected', 'custom_action'])
        # `actions = None` removes actions from superclasses.
        ma2 = AdminB(Band, admin.AdminSite())
        action_names = [name for _, name, _ in ma2._get_base_actions()]
        self.assertEqual(action_names, ['delete_selected'])

    def test_global_actions_description(self):
        @admin.action(description='Site-wide admin action 1.')
        def global_action_1(modeladmin, request, queryset):
            pass

        @admin.action
        def global_action_2(modeladmin, request, queryset):
            pass

        admin_site = admin.AdminSite()
        admin_site.add_action(global_action_1)
        admin_site.add_action(global_action_2)

        class BandAdmin(admin.ModelAdmin):
            pass

        ma = BandAdmin(Band, admin_site)
        self.assertEqual(
            [description for _, _, description in ma._get_base_actions()],
            [
                'Delete selected %(verbose_name_plural)s',
                'Site-wide admin action 1.',
                'Global action 2',
            ],
        )

    def test_actions_replace_global_action(self):
        @admin.action(description='Site-wide admin action 1.')
        def global_action_1(modeladmin, request, queryset):
            pass

        @admin.action(description='Site-wide admin action 2.')
        def global_action_2(modeladmin, request, queryset):
            pass

        admin.site.add_action(global_action_1, name='custom_action_1')
        admin.site.add_action(global_action_2, name='custom_action_2')

        @admin.action(description='Local admin action 1.')
        def custom_action_1(modeladmin, request, queryset):
            pass

        class BandAdmin(admin.ModelAdmin):
            actions = [custom_action_1, 'custom_action_2']

            @admin.action(description='Local admin action 2.')
            def custom_action_2(self, request, queryset):
                pass

        ma = BandAdmin(Band, admin.site)
        self.assertEqual(ma.check(), [])
        self.assertEqual(
            [
                desc
                for _, name, desc in ma._get_base_actions()
                if name.startswith('custom_action')
            ],
            [
                'Local admin action 1.',
                'Local admin action 2.',
            ],
        )
