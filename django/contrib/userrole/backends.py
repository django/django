#!/usr/bin/env python
# coding: utf-8

from models import UserRole

from django.contrib.auth.models import Permission, User


class UserRoleBackend(object):
    '''
    UserRoleBackend does not Authenticates User. It only  Authorise permissions
    '''
    supports_object_permissions = False
    supports_anonymous_user = False
    supports_inactive_user = False

    def authenticate(self, username=None, password=None):
        return None

    def get_group_permissions(self, user_obj, obj=None):
        """
        Returns a set of permission strings that this user has through his/her
        user roles.
        """
        if not hasattr(user_obj, '_user_role_group_perm_cache'):
            # find all user groups the user belongs to
            user_roles = UserRole.objects.filter(users=user_obj)
            perms = []
            for ur in user_roles:
                perm_queryset = Permission.objects.filter(group__userrole=ur)
                perms += perm_queryset.values_list('content_type__app_label', 'codename').order_by()
            user_obj._user_role_group_perm_cache = set(["%s.%s" % (ct, name) for ct, name in perms])
        return user_obj._user_role_group_perm_cache

    def get_all_permissions(self, user_obj, obj=None):
        if not hasattr(user_obj, '_user_role_perm_cache'):
            user_roles = UserRole.objects.filter(users=user_obj)
            user_obj._user_role_perm_cache = set()
            for ur in user_roles:
                user_obj._userrole_perm_cache.update(
                    set([u"%s.%s" % (p.content_type.app_label, p.codename) for p in ur.permissions.select_related()])
                )
            user_obj._userrole_perm_cache.update(self.get_group_permissions(user_obj))
        return user_obj._user_role_perm_cache

    def has_perm(self, user_obj, perm, obj=None):
        if not user_obj.is_active:
            return False
        return perm in self.get_all_permissions(user_obj)

    def has_module_perms(self, user_obj, app_label):
        """
        Returns True if user_obj has any permissions in the given app_label.
        """
        if not user_obj.is_active:
            return False
        for perm in self.get_all_permissions(user_obj):
            if perm[:perm.index('.')] == app_label:
                return True
        return False

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
