# This module has to exist, otherwise pre/post_migrate aren't sent for the
# migrate_signals application.

from django.db import models


class Signal(models.Model):
    pass
