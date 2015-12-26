from django.utils.translation import ugettext as _, ungettext

# Translators: This comment should be extracted
dummy1 = _("This is a translatable string.")

# This comment should not be extracted
dummy2 = _("This is another translatable string.")

# This file has a literal with plural forms. When processed first, makemessages
# shouldn't create a .po file with duplicate `Plural-Forms` headers
number = 3
dummy3 = ungettext("%(number)s Foo", "%(number)s Foos", number) % {'number': number}

dummy4 = _('Size')
