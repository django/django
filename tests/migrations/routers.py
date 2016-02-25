from __future__ import unicode_literals

from .models import ExoPlanet


class TestRouter(object):
    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Make sure the exoplanets app only appears on the 'other' db, and is the only one to appear there.
        """
        if model_name == ExoPlanet._meta.model_name:
            return db == 'other'
        elif db == 'other':
            return False
        return None
