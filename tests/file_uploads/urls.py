from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^upload/$', views.file_upload_view),
    url(r'^verify/$', views.file_upload_view_verify),
    url(r'^unicode_name/$', views.file_upload_unicode_name),
    url(r'^echo/$', views.file_upload_echo),
    url(r'^echo_content_type_extra/$', views.file_upload_content_type_extra),
    url(r'^echo_content/$', views.file_upload_echo_content),
    url(r'^quota/$', views.file_upload_quota),
    url(r'^quota/broken/$', views.file_upload_quota_broken),
    url(r'^getlist_count/$', views.file_upload_getlist_count),
    url(r'^upload_errors/$', views.file_upload_errors),
    url(r'^filename_case/$', views.file_upload_filename_case_view),
    url(r'^fd_closing/(?P<access>t|f)/$', views.file_upload_fd_closing),
]
