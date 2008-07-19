from django import forms

DEFAULT_DATE_INPUT_FORMATS = (
    '%Y-%m-%d', '%d/%m/%Y', '%d/%m/%y', # '2006-10-25', '25/10/2006', '25/10/06'
    '%b %d %Y', '%b %d, %Y',            # 'Oct 25 2006', 'Oct 25, 2006'
    '%d %b %Y', '%d %b, %Y',            # '25 Oct 2006', '25 Oct, 2006'
    '%B %d %Y', '%B %d, %Y',            # 'October 25 2006', 'October 25, 2006'
    '%d %B %Y', '%d %B, %Y',            # '25 October 2006', '25 October, 2006'
)

DEFAULT_DATETIME_INPUT_FORMATS = (
    '%Y-%m-%d %H:%M:%S',     # '2006-10-25 14:30:59'
    '%Y-%m-%d %H:%M',        # '2006-10-25 14:30'
    '%Y-%m-%d',              # '2006-10-25'
    '%d/%m/%Y %H:%M:%S',     # '25/10/2006 14:30:59'
    '%d/%m/%Y %H:%M',        # '25/10/2006 14:30'
    '%d/%m/%Y',              # '25/10/2006'
    '%d/%m/%y %H:%M:%S',     # '25/10/06 14:30:59'
    '%d/%m/%y %H:%M',        # '25/10/06 14:30'
    '%d/%m/%y',              # '25/10/06'
)

class DateField(forms.DateField):
    """
    A date input field which uses non-US date input formats by default.
    """
    def __init__(self, input_formats=None, *args, **kwargs):
        input_formats = input_formats or DEFAULT_DATE_INPUT_FORMATS
        super(DateField, self).__init__(input_formats=input_formats, *args, **kwargs)

class DateTimeField(forms.DateTimeField):
    """
    A date and time input field which uses non-US date and time input formats
    by default.
    """
    def __init__(self, input_formats=None, *args, **kwargs):
        input_formats = input_formats or DEFAULT_DATETIME_INPUT_FORMATS
        super(DateTimeField, self).__init__(input_formats=input_formats, *args, **kwargs)
