"Commonly-used date structures"

from django.utils.translation import gettext_lazy as _, pgettext_lazy

WEEKDAYS = {
    0: _('Monday'), 1: _('Tuesday'), 2: _('Wednesday'), 3: _('Thursday'), 4: _('Friday'),
    5: _('Saturday'), 6: _('Sunday')
}
WEEKDAYS_ABBR = {
    0: _('Mon'), 1: _('Tue'), 2: _('Wed'), 3: _('Thu'), 4: _('Fri'),
    5: _('Sat'), 6: _('Sun')
}
MONTHS = {
    1: _('January'), 2: _('February'), 3: _('March'), 4: _('April'), 5: _('May'), 6: _('June'),
    7: _('July'), 8: _('August'), 9: _('September'), 10: _('October'), 11: _('November'),
    12: _('December')
}
MONTHS_3 = {
    1: _('jan'), 2: _('feb'), 3: _('mar'), 4: _('apr'), 5: _('may'), 6: _('jun'),
    7: _('jul'), 8: _('aug'), 9: _('sep'), 10: _('oct'), 11: _('nov'), 12: _('dec')
}
MONTHS_AP = {  # month names in Associated Press style
    1: pgettext_lazy('abbrev. month', 'Jan.'),
    2: pgettext_lazy('abbrev. month', 'Feb.'),
    3: pgettext_lazy('abbrev. month', 'March'),
    4: pgettext_lazy('abbrev. month', 'April'),
    5: pgettext_lazy('abbrev. month', 'May'),
    6: pgettext_lazy('abbrev. month', 'June'),
    7: pgettext_lazy('abbrev. month', 'July'),
    8: pgettext_lazy('abbrev. month', 'Aug.'),
    9: pgettext_lazy('abbrev. month', 'Sept.'),
    10: pgettext_lazy('abbrev. month', 'Oct.'),
    11: pgettext_lazy('abbrev. month', 'Nov.'),
    12: pgettext_lazy('abbrev. month', 'Dec.')
}
MONTHS_ALT = {  # required for long date representation by some locales
    1: pgettext_lazy('alt. month', 'January'),
    2: pgettext_lazy('alt. month', 'February'),
    3: pgettext_lazy('alt. month', 'March'),
    4: pgettext_lazy('alt. month', 'April'),
    5: pgettext_lazy('alt. month', 'May'),
    6: pgettext_lazy('alt. month', 'June'),
    7: pgettext_lazy('alt. month', 'July'),
    8: pgettext_lazy('alt. month', 'August'),
    9: pgettext_lazy('alt. month', 'September'),
    10: pgettext_lazy('alt. month', 'October'),
    11: pgettext_lazy('alt. month', 'November'),
    12: pgettext_lazy('alt. month', 'December')
}
