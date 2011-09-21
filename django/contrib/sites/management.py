"""
Creates the default Site object.
"""

from django.db.models import signals
from django.db import router
from django.contrib.sites.models import Site
from django.contrib.sites import models as site_app

def create_default_site(app, created_models, verbosity, db, **kwargs):
    # Only create the default sites in databases where Django created the table
    if Site in created_models and router.allow_syncdb(db, Site) :
        if verbosity >= 2:
            print "Creating example.com Site object"
        # The default settings set SITE_ID = 1, and some tests in Django's test
        # suite rely on this value. However, if database sequences are reused
        # (e.g. in the test suite after flush/syncdb), it isn't guaranteed that
        # the next id will be 1, so we coerce it. See #15573 and #16353. This
        # can also crop up outside of tests - see #15346.
        s = Site(pk=1, domain="example.com", name="example.com")
        s.save(using=db)
    Site.objects.clear_cache()

signals.post_syncdb.connect(create_default_site, sender=site_app)
