from django.conf.urls.defaults import *

urlpatterns = patterns('regressiontests.comment_tests.custom_comments.views',
    url(r'^post/$',          'custom_submit_comment'),
    url(r'^flag/(\d+)/$',    'custom_flag_comment'),
    url(r'^delete/(\d+)/$',  'custom_delete_comment'),
    url(r'^approve/(\d+)/$', 'custom_approve_comment'),
)

