from django.conf import settings
from django.contrib.syndication.feeds import Feed
from django.core.exceptions import ObjectDoesNotExist
from django.models.core import sites
from django.models.comments import comments, freecomments

class LatestFreeCommentsFeed(Feed):
    """Feed of latest comments on the current site"""
    
    comments_module = freecomments
    
    def title(self):
        if not hasattr(self, '_site'):
            self._site = sites.get_current()
        return "%s comments" % self._site.name
        
    def link(self):
        if not hasattr(self, '_site'):
            self._site = sites.get_current()
        return "http://%s/" % (self._site.domain)
    
    def description(self):
        if not hasattr(self, '_site'):
            self._site = sites.get_current()
        return "Latest comments on %s" % self._site.name

    def items(self):
        return self.comments_module.get_list(**self._get_lookup_kwargs())

    def _get_lookup_kwargs(self):
        return {
            'site__pk' : settings.SITE_ID,
            'is_public__exact' : True,
            'limit' : 40,
        }

class LatestCommentsFeed(LatestFreeCommentsFeed):
    """Feed of latest free comments on the current site"""
    
    comments_module = comments
    
    def _get_lookup_kwargs(self):
        kwargs = LatestFreeCommentsFeed._get_lookup_kwargs(self)
        kwargs['is_removed__exact'] = False
        if settings.COMMENTS_BANNED_USERS_GROUP:
            kwargs['where'] = ['user_id NOT IN (SELECT user_id FROM auth_users_group WHERE group_id = %s)']
            kwargs['params'] = [settings.COMMENTS_BANNED_USERS_GROUP]
        return kwargs
