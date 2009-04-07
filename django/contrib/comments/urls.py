from django.conf.urls.defaults import *

urlpatterns = patterns('django.contrib.comments.views',
    url(r'^post/$',          'comments.post_comment',       name='comments-post-comment'),
    url(r'^posted/$',        'comments.comment_done',       name='comments-comment-done'),
    url(r'^flag/(\d+)/$',    'moderation.flag',             name='comments-flag'),
    url(r'^flagged/$',       'moderation.flag_done',        name='comments-flag-done'),
    url(r'^delete/(\d+)/$',  'moderation.delete',           name='comments-delete'),
    url(r'^deleted/$',       'moderation.delete_done',      name='comments-delete-done'),
    url(r'^moderate/$',      'moderation.moderation_queue', name='comments-moderation-queue'),
    url(r'^approve/(\d+)/$', 'moderation.approve',          name='comments-approve'),
    url(r'^approved/$',      'moderation.approve_done',     name='comments-approve-done'),
)

urlpatterns += patterns('',
    url(r'^cr/(\d+)/(.+)/$', 'django.views.defaults.shortcut', name='comments-url-redirect'),
)

