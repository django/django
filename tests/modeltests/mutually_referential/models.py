"""
24. Mutually referential many-to-one relationships

To define a many-to-one relationship, use ``ForeignKey()`` .
"""

from django.db.models import *

class Parent(Model):
    name = CharField(maxlength=100)
    bestchild = ForeignKey("Child", null=True)
    
class Child(Model):
    name = CharField(maxlength=100)
    parent = ForeignKey(Parent)
    
API_TESTS = """
# Create a Parent
>>> q = Parent(name='Elizabeth')
>>> q.save()

# Create some children
>>> c = q.add_child(name='Charles') 
>>> e = q.add_child(name='Edward')

# Set the best child
>>> q.bestchild_id = c.id
>>> q.save()

>>> q.delete()

"""