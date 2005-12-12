"""
12. Relating a model to another model more than once

In this example, a ``Person`` can have a ``mother`` and ``father`` -- both of
which are other ``Person`` objects.

Set ``related_name`` to designate what the reverse relationship is called.
"""

from django.core import meta

class Person(meta.Model):
    full_name = meta.CharField(maxlength=20)
    mother = meta.ForeignKey('self', null=True, related_name='mothers_child')
    father = meta.ForeignKey('self', null=True, related_name='fathers_child')

    def __repr__(self):
        return self.full_name

API_TESTS = """
# Create two Person objects -- the mom and dad in our family.
>>> dad = Person(full_name='John Smith Senior', mother=None, father=None)
>>> dad.save()
>>> mom = Person(full_name='Jane Smith', mother=None, father=None)
>>> mom.save()

# Give mom and dad a kid.
>>> kid = Person(full_name='John Smith Junior', mother=mom, father=dad)
>>> kid.save()

>>> kid.get_mother()
Jane Smith
>>> kid.get_father()
John Smith Senior
>>> dad.get_fathers_child_list()
[John Smith Junior]
>>> mom.get_mothers_child_list()
[John Smith Junior]
>>> kid.get_mothers_child_list()
[]
>>> kid.get_fathers_child_list()
[]
"""
