"""
12. Relating a model to another model more than once

In this example, a ``Person`` can have a ``mother`` and ``father`` -- both of
which are other ``Person`` objects.

Because a ``Person`` has multiple relationships to ``Person``, we need to
distinguish the relationships. Set ``rel_name`` to tell Django what the
relationship should be called, because ``Person`` has two relationships to the
same model. Also, set ``related_name`` to designate what the reverse
relationship is called.
"""

from django.core import meta

class Person(meta.Model):
    fields = (
        meta.CharField('full_name', maxlength=20),
        meta.ForeignKey('self', null=True, rel_name='mother',
            related_name='mothers_child'),
        meta.ForeignKey('self', null=True, rel_name='father',
            related_name='fathers_child'),
    )

    def __repr__(self):
        return self.full_name

API_TESTS = """
# Create two Person objects -- the mom and dad in our family.
>>> dad = persons.Person(id=None, full_name='John Smith Senior', mother_id=None, father_id=None)
>>> dad.save()
>>> mom = persons.Person(id=None, full_name='Jane Smith', mother_id=None, father_id=None)
>>> mom.save()

# Give mom and dad a kid.
>>> kid = persons.Person(id=None, full_name='John Smith Junior', mother_id=mom.id, father_id=dad.id)
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
