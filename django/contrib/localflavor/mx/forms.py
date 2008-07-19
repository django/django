"""
Mexican-specific form helpers.
"""

from django.forms.fields import Select

class MXStateSelect(Select):
    """
    A Select widget that uses a list of Mexican states as its choices.
    """
    def __init__(self, attrs=None):
        from mx_states import STATE_CHOICES
        super(MXStateSelect, self).__init__(attrs, choices=STATE_CHOICES)

