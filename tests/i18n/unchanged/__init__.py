# This package is used to test whether makemessages leaves files untouched
# when there are no updates to the file. This should include not touching the
# POT-Creation-Date.

from django.utils.translation import gettext as _

dummy1 = _("This is a translatable string.")
dummy2 = _("This is another translatable string.")
