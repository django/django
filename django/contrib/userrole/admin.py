from models import UserRole

from django.contrib import admin
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType


# Register your models here.


class UserRoleAdmin(admin.ModelAdmin):
    filter_horizontal = ('users', 'admins', 'permissions', 'groups',)
    non_superuser_disabled_fields = ('name', 'admins', 'permissions', 'groups',)

    def get_readonly_fields(self, request, obj=None):
        if request.user.is_superuser:
            return []
        else:
            return self.non_superuser_disabled_fields

    def queryset(self, request):
        """
        UserRole admin has 'change' permission to UserRoles managed by him/her
        """
        qs = super(UserRoleAdmin, self).queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(admins=request.user)

    def response_add(self, request, obj, post_url_continue='../%s/'):
        ret = super(UserRoleAdmin, self).response_add(request, obj, post_url_continue)
        self.add_admin_permission(obj)
        return ret

    def response_change(self, request, obj):
        ret = super(UserRoleAdmin, self).response_change(request, obj)
        self.add_admin_permission(obj)
        return ret

    def add_admin_permission(self, obj):
        """
        Add change permission to UserRole admins
        :param obj:
        :return:
        """
        content_type = ContentType.objects.get_for_model(obj)
        codename = "change_%s" % content_type.model
        perms = Permission.objects.filter(content_type=content_type, codename=codename)
        if not perms:
            raise Exception('failed to get permission: %s, %s' % (content_type, codename))
        for role_admin in obj.admins.all():
            role_admin.user_permissions.add(perms[0])


admin.site.register(UserRole, UserRoleAdmin)
