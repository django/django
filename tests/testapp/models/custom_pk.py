"""
14. Using a custom primary key

By default, Django adds an ``"id"`` field to each model. But you can override
this behavior by explicitly adding ``primary_key=True`` to a field.

NOTE: This isn't yet supported. This model exists as a unit test that currently
fails.
"""

from django.core import meta

class Employee(meta.Model):
    fields = (
        meta.CharField('employee_code', maxlength=10, primary_key=True),
        meta.CharField('first_name', maxlength=20),
        meta.CharField('last_name', maxlength=20),
    )

    def __repr__(self):
        return "%s %s" % (self.first_name, self.last_name)

API_TESTS = """
>>> e = employees.Employee(employee_code='ABC123', first_name='Dan', last_name='Jones')
>>> e.save()
>>> employees.get_list()
[Dan Jones]
"""
