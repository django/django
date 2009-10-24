from django.conf.urls.defaults import *
from django.contrib import admin
from django.contrib.comments.admin import CommentsAdmin
from django.contrib.comments.models import Comment

# Make a new AdminSite to avoid picking up the deliberately broken admin
# modules in other tests.
admin_site = admin.AdminSite()
admin_site.register(Comment, CommentsAdmin)

urlpatterns = patterns('',
    (r'^admin/', include(admin_site.urls)),
)
