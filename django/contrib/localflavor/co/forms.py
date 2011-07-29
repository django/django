"""
Colombian-specific form helpers.
"""

from django.forms.fields import Select

class CODepartmentSelect(Select):
    """
    A Select widget that uses a list of Colombian states as its choices.
    """
    def __init__(self, attrs=None):
        from co_departments import DEPARTMENT_CHOICES
        super(CODepartmentSelect, self).__init__(attrs, choices=DEPARTMENT_CHOICES)
