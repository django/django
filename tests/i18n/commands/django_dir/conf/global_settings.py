"""
Mocked file based on default settings to trigger xgettext extraction
"""


# This is defined here as a do-nothing function because we can't import
# django.utils.translation -- that module depends on the settings.
def gettext_noop(s):
    return s


# Languages we provide translations for, out of the box.
LANGUAGES = [
    ('lv', gettext_noop('Love')),
]
