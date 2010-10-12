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
