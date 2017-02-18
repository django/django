from django.conf import settings
from django.contrib.messages import constants


def get_level_tags():
    """
    Returns the message level tags.
    """
    level_tags = constants.DEFAULT_TAGS.copy()
    level_tags.update(getattr(settings, 'MESSAGE_TAGS', {}))
    return level_tags
