from django.conf import settings
from django.contrib.syndication.views import Feed
from django.contrib.sites.models import Site
from django.contrib import comments
from django.utils.translation import ugettext as _

class LatestCommentFeed(Feed):
    """Feed of latest comments on the current site."""

    def title(self):
        if not hasattr(self, '_site'):
            self._site = Site.objects.get_current()
        return _("%(site_name)s comments") % dict(site_name=self._site.name)

    def link(self):
        if not hasattr(self, '_site'):
            self._site = Site.objects.get_current()
        return "http://%s/" % (self._site.domain)

    def description(self):
        if not hasattr(self, '_site'):
            self._site = Site.objects.get_current()
        return _("Latest comments on %(site_name)s") % dict(site_name=self._site.name)

    def items(self):
        qs = comments.get_model().objects.filter(
            site__pk = settings.SITE_ID,
            is_public = True,
            is_removed = False,
        )
        return qs.order_by('-submit_date')[:40]

    def item_pubdate(self, item):
        return item.submit_date
