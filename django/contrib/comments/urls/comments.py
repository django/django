from django.conf.urls.defaults import *

urlpatterns = patterns('django.views',
    (r'^post/$', 'comments.comments.post_comment'),
    (r'^postfree/$', 'comments.comments.post_free_comment'),
    (r'^posted/$', 'comments.comments.comment_was_posted'),
    (r'^karma/vote/(?P<comment_id>\d+)/(?P<vote>up|down)/$', 'comments.karma.vote'),
    (r'^flag/(?P<comment_id>\d+)/$', 'comments.userflags.flag'),
    (r'^flag/(?P<comment_id>\d+)/done/$', 'comments.userflags.flag_done'),
    (r'^delete/(?P<comment_id>\d+)/$', 'comments.userflags.delete'),
    (r'^delete/(?P<comment_id>\d+)/done/$', 'comments.userflags.delete_done'),
)
