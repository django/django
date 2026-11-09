from django.contrib.auth.backends import ModelBackend
from django.contrib.contenttypes.models import ContentType


class ObjectLevelPermissionBackend(ModelBackend):
    def has_perm(self, user_obj, perm, obj=None):
        if perm == "admin_views.delete_fooaccountproxy" and obj is None:
            return False

        if obj is None:
            return super().has_perm(user_obj, perm, obj)

        if not user_obj.is_active:
            return False

        opts = obj._meta
        codename = f"delete_{opts.model_name}"

        if perm != f"{opts.app_label}.{codename}":
            return False

        content_type = ContentType.objects.get_for_model(
            obj,
            for_concrete_model=False,
        )

        return user_obj.user_permissions.filter(
            content_type=content_type,
            codename=codename,
        ).exists()
