from django.contrib import admin

from .models import Bug, ProxyBug, ProxyTrackerUser, TrackerUser

site = admin.AdminSite(name='admin_proxy')


class CommentInline(admin.TabularInline):
    model = Bug.comment_users.through


class BugAdmin(admin.ModelAdmin):
    inlines = [CommentInline]


class UserAdmin(admin.ModelAdmin):
    inlines = [CommentInline]


site.register(Bug, BugAdmin)
site.register(ProxyBug, BugAdmin)
site.register(TrackerUser, UserAdmin)
site.register(ProxyTrackerUser, UserAdmin)
