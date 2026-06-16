from django.db import models
from django.db.models.functions import UUID4


class School(models.Model):
    name = models.CharField(max_length=100)


class Parent(models.Model):
    name = models.CharField(max_length=100)


class Child(models.Model):
    mother = models.ForeignKey(Parent, models.CASCADE, related_name="mothers_children")
    father = models.ForeignKey(Parent, models.CASCADE, related_name="fathers_children")
    school = models.ForeignKey(School, models.CASCADE)
    name = models.CharField(max_length=100)

    class Meta:
        constraints = [
            models.UniqueConstraint("mother", "father", name="unique_parents"),
        ]


class ParentUUIDPk(models.Model):
    uuid = models.UUIDField(primary_key=True, db_default=UUID4(), editable=False)

    class Meta:
        required_db_features = {
            "supports_uuid4_function",
            "supports_expression_defaults",
        }


class ChildUUIDPk(models.Model):
    parent = models.ForeignKey(ParentUUIDPk, models.CASCADE)
    name = models.CharField(max_length=100)

    class Meta:
        required_db_features = {
            "supports_uuid4_function",
            "supports_expression_defaults",
        }


class Poet(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Poem(models.Model):
    poet = models.ForeignKey(Poet, models.CASCADE)
    name = models.CharField(max_length=100)

    class Meta:
        unique_together = ("poet", "name")

    def __str__(self):
        return self.name
