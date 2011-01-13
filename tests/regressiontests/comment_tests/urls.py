from django.conf.urls.defaults import *
from django.contrib.comments.feeds import LatestCommentFeed

feeds = {
     'comments': LatestCommentFeed,
}

urlpatterns = patterns('regressiontests.comment_tests.custom_comments.views',
    url(r'^post/$',          'custom_submit_comment'),
    url(r'^flag/(\d+)/$',    'custom_flag_comment'),
    url(r'^delete/(\d+)/$',  'custom_delete_comment'),
    url(r'^approve/(\d+)/$', 'custom_approve_comment'),
)

urlpatterns += patterns('',
    (r'^rss/legacy/(?P<url>.*)/$', 'django.contrib.syndication.views.feed', {'feed_dict': feeds}),
    (r'^rss/comments/$', LatestCommentFeed()),
)
