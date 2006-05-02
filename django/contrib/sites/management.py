"""
Creates the default Site object.
"""

from django.dispatch import dispatcher
from django.db.models import signals
from django.contrib.sites.models import Site
from django.contrib.sites import models as site_app

def create_default_site(app, created_models):
    if Site in created_models:
        print "Creating example.com Site object"
        s = Site(domain="example.com", name="example.com")
        s.save()

dispatcher.connect(create_default_site, sender=site_app, signal=signals.post_syncdb)
