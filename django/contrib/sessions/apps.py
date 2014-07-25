from importlib import import_module

from django.apps import AppConfig
from django.conf import settings
from django.utils.translation import ugettext_lazy as _


class SessionsConfig(AppConfig):
    """
    Override the base `AppConfig` to only return models when the session store
    needs it.
    """
    name = 'django.contrib.sessions'
    verbose_name = _("Sessions")

    def _models_needed(self):
        """
        Check settings and return true if we are using any database session
        backends.
        """
        engine = import_module(settings.SESSION_ENGINE)
        return engine.SessionStore.requires_session_model

    def get_model(self, model_name):
        self.check_models_ready()
        if self._models_needed():
            return super(SessionsConfig, self).get_model(model_name)
        else:
            raise LookupError(
                "App '%s' doesn't have a '%s' model." % (self.label, model_name))

    def get_models(self, include_auto_created=False,
                   include_deferred=False, include_swapped=False):
        if self._models_needed():
            return super(SessionsConfig, self).get_models(
                include_auto_created, include_deferred, include_swapped)
        else:
            return []
