"""
Mutually referential many-to-one relationships

Strings can be used instead of model literals to set up "lazy" relations.
"""

from django.db import models


class Parent(models.Model):
    name = models.CharField(max_length=100)

    # Use a simple string for forward declarations.
    bestchild = models.ForeignKey(
        "Child", models.SET_NULL, null=True, related_name="favored_by"
    )


class Child(models.Model):
    name = models.CharField(max_length=100)

    # You can also explicitly specify the related app.
    parent = models.ForeignKey("mutually_referential.Parent", models.CASCADE)
