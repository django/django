from thibaud.apps import AppConfig
from thibaud.contrib.messages.storage import base
from thibaud.contrib.messages.utils import get_level_tags
from thibaud.core.signals import setting_changed
from thibaud.utils.functional import SimpleLazyObject
from thibaud.utils.translation import gettext_lazy as _


def update_level_tags(setting, **kwargs):
    if setting == "MESSAGE_TAGS":
        base.LEVEL_TAGS = SimpleLazyObject(get_level_tags)


class MessagesConfig(AppConfig):
    name = "thibaud.contrib.messages"
    verbose_name = _("Messages")

    def ready(self):
        setting_changed.connect(update_level_tags)
