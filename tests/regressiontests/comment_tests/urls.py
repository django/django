from __future__ import absolute_import

from django.conf.urls import patterns, url
from django.contrib.comments.feeds import LatestCommentFeed

from .custom_comments import views


feeds = {
     'comments': LatestCommentFeed,
}

urlpatterns = patterns('',
    url(r'^post/$', views.custom_submit_comment),
    url(r'^flag/(\d+)/$', views.custom_flag_comment),
    url(r'^delete/(\d+)/$', views.custom_delete_comment),
    url(r'^approve/(\d+)/$', views.custom_approve_comment),
)

urlpatterns += patterns('',
    (r'^rss/comments/$', LatestCommentFeed()),
)
