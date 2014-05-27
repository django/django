from freedom.apps import AppConfig

from freedom.utils.translation import ugettext_lazy as _


class MessagesConfig(AppConfig):
    name = 'freedom.contrib.messages'
    verbose_name = _("Messages")
