from django.urls import path, re_path

from . import views

urlpatterns = [
    path('upload/', views.file_upload_view),
    path('upload_traversal/', views.file_upload_traversal_view),
    path('verify/', views.file_upload_view_verify),
    path('unicode_name/', views.file_upload_unicode_name),
    path('echo/', views.file_upload_echo),
    path('echo_content_type_extra/', views.file_upload_content_type_extra),
    path('echo_content/', views.file_upload_echo_content),
    path('quota/', views.file_upload_quota),
    path('quota/broken/', views.file_upload_quota_broken),
    path('getlist_count/', views.file_upload_getlist_count),
    path('upload_errors/', views.file_upload_errors),
    path('temp_file/stop_upload/', views.file_stop_upload_temporary_file),
    path('temp_file/upload_interrupted/', views.file_upload_interrupted_temporary_file),
    path('filename_case/', views.file_upload_filename_case_view),
    re_path(r'^fd_closing/(?P<access>t|f)/$', views.file_upload_fd_closing),
]
