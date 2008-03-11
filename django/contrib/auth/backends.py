from django.db import connection
from django.contrib.auth.models import User

try: 
    set 
except NameError: 
    from sets import Set as set # Python 2.3 fallback
 	
class ModelBackend(object):
    """
    Authenticate against django.contrib.auth.models.User
    """
    # TODO: Model, login attribute name and password attribute name should be
    # configurable.
    def authenticate(self, username=None, password=None):
        try:
            user = User.objects.get(username=username)
            if user.check_password(password):
                return user
        except User.DoesNotExist:
            return None

    def get_group_permissions(self, user_obj):
        "Returns a list of permission strings that this user has through his/her groups."
        if not hasattr(user_obj, '_group_perm_cache'):
            cursor = connection.cursor()
            # The SQL below works out to the following, after DB quoting:
            # cursor.execute("""
            #     SELECT ct."app_label", p."codename"
            #     FROM "auth_permission" p, "auth_group_permissions" gp, "auth_user_groups" ug, "django_content_type" ct
            #     WHERE p."id" = gp."permission_id"
            #         AND gp."group_id" = ug."group_id"
            #         AND ct."id" = p."content_type_id"
            #         AND ug."user_id" = %s, [self.id])
            qn = connection.ops.quote_name
            sql = """
                SELECT ct.%s, p.%s
                FROM %s p, %s gp, %s ug, %s ct
                WHERE p.%s = gp.%s
                    AND gp.%s = ug.%s
                    AND ct.%s = p.%s
                    AND ug.%s = %%s""" % (
                qn('app_label'), qn('codename'),
                qn('auth_permission'), qn('auth_group_permissions'),
                qn('auth_user_groups'), qn('django_content_type'),
                qn('id'), qn('permission_id'),
                qn('group_id'), qn('group_id'),
                qn('id'), qn('content_type_id'),
                qn('user_id'),)
            cursor.execute(sql, [user_obj.id])
            user_obj._group_perm_cache = set(["%s.%s" % (row[0], row[1]) for row in cursor.fetchall()])
        return user_obj._group_perm_cache
    
    def get_all_permissions(self, user_obj):
        if not hasattr(user_obj, '_perm_cache'):
            user_obj._perm_cache = set([u"%s.%s" % (p.content_type.app_label, p.codename) for p in user_obj.user_permissions.select_related()])
            user_obj._perm_cache.update(self.get_group_permissions(user_obj))
        return user_obj._perm_cache

    def has_perm(self, user_obj, perm):
        return perm in self.get_all_permissions(user_obj)

    def has_module_perms(self, user_obj, app_label):
        return bool(len([p for p in self.get_all_permissions(user_obj) if p[:p.index('.')] == app_label]))

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
