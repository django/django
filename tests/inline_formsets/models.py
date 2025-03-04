from django.db import models


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
            models.UniqueConstraint(
                models.F("mother"),
                models.F("father"),
                name="unique_parents",
            ),
        ]


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


class SingleInstanceModel(models.Model):
    pass


class ZeroInstancesModel(models.Model):
    parent = models.ForeignKey(
        SingleInstanceModel, models.CASCADE, related_name="child_set"
    )
    name = models.CharField(max_length=20)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(parent=1),
                name="parent_1_no_child",
            )
        ]
