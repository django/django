"""
PY-specific Form helpers.
"""
from django.forms.fields import Select

class PyDepartmentSelect(Select):
    """
    A Select widget with a list of Paraguayan departments as choices.
    """
    def __init__(self, attrs=None):
        from py_department import DEPARTMENT_CHOICES
        super(PyDepartmentSelect, self).__init__(attrs, choices=DEPARTMENT_CHOICES)


class PyNumberedDepartmentSelect(Select):
    """
    A Select widget with a roman numbered list of Paraguayan departments as choices.
    """
    def __init__(self, attrs=None):
        from py_department import DEPARTMENT_ROMAN_CHOICES
        super(PyNumberedDepartmentSelect, self).__init__(attrs, choices=DEPARTMENT_ROMAN_CHOICES)
