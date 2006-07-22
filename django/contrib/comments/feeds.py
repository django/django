from django.conf import settings
from django.contrib.comments.models import Comment, FreeComment
from django.contrib.syndication.feeds import Feed
from django.contrib.sites.models import Site

class LatestFreeCommentsFeed(Feed):
    "Feed of latest comments on the current site."

    comments_class = FreeComment

    def title(self):
        if not hasattr(self, '_site'):
            self._site = Site.objects.get_current()
        return "%s comments" % self._site.name

    def link(self):
        if not hasattr(self, '_site'):
            self._site = Site.objects.get_current()
        return "http://%s/" % (self._site.domain)

    def description(self):
        if not hasattr(self, '_site'):
            self._site = Site.objects.get_current()
        return "Latest comments on %s" % self._site.name

    def items(self):
        return self.comments_class.objects.filter(site__pk=settings.SITE_ID, is_public=True)[:40]

class LatestCommentsFeed(LatestFreeCommentsFeed):
    """Feed of latest free comments on the current site"""

    comments_class = Comment

    def items(self):
        qs = LatestFreeCommentsFeed.items(self)
        qs = qs.filter(is_removed=False)
        if settings.COMMENTS_BANNED_USERS_GROUP:
            where = ['user_id NOT IN (SELECT user_id FROM auth_users_group WHERE group_id = %s)']
            params = [settings.COMMENTS_BANNED_USERS_GROUP]
            qs = qs.extra(where=where, params=params)
        return qs
