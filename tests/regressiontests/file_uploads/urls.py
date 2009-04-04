from django.conf.urls.defaults import *
import views

urlpatterns = patterns('',
    (r'^upload/$',          views.file_upload_view),
    (r'^verify/$',          views.file_upload_view_verify),
    (r'^unicode_name/$',    views.file_upload_unicode_name),
    (r'^echo/$',            views.file_upload_echo),
    (r'^quota/$',           views.file_upload_quota),
    (r'^quota/broken/$',    views.file_upload_quota_broken),
    (r'^getlist_count/$',   views.file_upload_getlist_count),
    (r'^upload_errors/$',   views.file_upload_errors),
)
