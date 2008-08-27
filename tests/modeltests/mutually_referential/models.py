"""
24. Mutually referential many-to-one relationships

Strings can be used instead of model literals to set up "lazy" relations.
"""

from django.db.models import *

class Parent(Model):
    name = CharField(max_length=100)
    
    # Use a simple string for forward declarations.
    bestchild = ForeignKey("Child", null=True, related_name="favoured_by")

class Child(Model):
    name = CharField(max_length=100)
    
    # You can also explicitally specify the related app.
    parent = ForeignKey("mutually_referential.Parent")

__test__ = {'API_TESTS':"""
# Create a Parent
>>> q = Parent(name='Elizabeth')
>>> q.save()

# Create some children
>>> c = q.child_set.create(name='Charles')
>>> e = q.child_set.create(name='Edward')

# Set the best child
>>> q.bestchild = c
>>> q.save()

>>> q.delete()

"""}