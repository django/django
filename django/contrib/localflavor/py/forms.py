"""
PY-specific Form helpers.
"""

from __future__ import absolute_import

from django.contrib.localflavor.py.py_department import DEPARTMENT_CHOICES, DEPARTMENT_ROMAN_CHOICES
from django.forms.fields import Select


class PyDepartmentSelect(Select):
    """
    A Select widget with a list of Paraguayan departments as choices.
    """
    def __init__(self, attrs=None):
        super(PyDepartmentSelect, self).__init__(attrs, choices=DEPARTMENT_CHOICES)


class PyNumberedDepartmentSelect(Select):
    """
    A Select widget with a roman numbered list of Paraguayan departments as choices.
    """
    def __init__(self, attrs=None):
        super(PyNumberedDepartmentSelect, self).__init__(attrs, choices=DEPARTMENT_ROMAN_CHOICES)
