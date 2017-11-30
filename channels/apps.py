from django.apps import AppConfig

# We import this here to ensure the reactor is installed very early on
# in case other packages accidentally import twisted.internet.reactor
# (e.g. raven does this).
import daphne.server  # noqa

#from .binding.base import BindingMetaclass
from .package_checks import check_all


class ChannelsConfig(AppConfig):

    name = "channels"
    verbose_name = "Channels"

    def ready(self):
        # Check versions
        check_all()
        # Do django monkeypatches
        from .hacks import monkeypatch_django
        monkeypatch_django()
        # Instantiate bindings
        #BindingMetaclass.register_all()
