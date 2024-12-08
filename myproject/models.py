from django.db import models

class ParentModel(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

class ChildModel(models.Model):
    parent = models.ForeignKey(ParentModel, on_delete=models.CASCADE, related_name="children")
    related_field = models.ManyToManyField(ParentModel, related_name="related_items")

    def __str__(self):
        return f"Child of {self.parent.name}"
