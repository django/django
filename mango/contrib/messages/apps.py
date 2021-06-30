from mango.apps import AppConfig
from mango.utils.translation import gettext_lazy as _


class MessagesConfig(AppConfig):
    name = 'mango.contrib.messages'
    verbose_name = _("Messages")
