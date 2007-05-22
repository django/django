"Commonly-used date structures"

from django.utils.translation import ugettext_lazy as _

WEEKDAYS = {
    0:_('Monday'), 1:_('Tuesday'), 2:_('Wednesday'), 3:_('Thursday'), 4:_('Friday'),
    5:_('Saturday'), 6:_('Sunday')
}
WEEKDAYS_ABBR = {
    0:_('Mon'), 1:_('Tue'), 2:_('Wed'), 3:_('Thu'), 4:_('Fri'),
    5:_('Sat'), 6:_('Sun')
}
WEEKDAYS_REV = {
    'monday':0, 'tuesday':1, 'wednesday':2, 'thursday':3, 'friday':4,
    'saturday':5, 'sunday':6
}
MONTHS = {
    1:_('January'), 2:_('February'), 3:_('March'), 4:_('April'), 5:_('May'), 6:_('June'),
    7:_('July'), 8:_('August'), 9:_('September'), 10:_('October'), 11:_('November'),
    12:_('December')
}
MONTHS_3 = {
    1:_('jan'), 2:_('feb'), 3:_('mar'), 4:_('apr'), 5:_('may'), 6:_('jun'),
    7:_('jul'), 8:_('aug'), 9:_('sep'), 10:_('oct'), 11:_('nov'), 12:_('dec')
}
MONTHS_3_REV = {
    'jan':1, 'feb':2, 'mar':3, 'apr':4, 'may':5, 'jun':6, 'jul':7, 'aug':8,
    'sep':9, 'oct':10, 'nov':11, 'dec':12
}
MONTHS_AP = { # month names in Associated Press style
    1:_('Jan.'), 2:_('Feb.'), 3:_('March'), 4:_('April'), 5:_('May'), 6:_('June'), 7:_('July'),
    8:_('Aug.'), 9:_('Sept.'), 10:_('Oct.'), 11:_('Nov.'), 12:_('Dec.')
}
