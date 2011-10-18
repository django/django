"""
Colombian-specific form helpers.
"""

from __future__ import absolute_import

from django.contrib.localflavor.co.co_departments import DEPARTMENT_CHOICES
from django.forms.fields import Select


class CODepartmentSelect(Select):
    """
    A Select widget that uses a list of Colombian states as its choices.
    """
    def __init__(self, attrs=None):
        super(CODepartmentSelect, self).__init__(attrs, choices=DEPARTMENT_CHOICES)
