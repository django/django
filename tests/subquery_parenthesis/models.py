from django.db import models


class FirstModel(models.Model):
    pass


class SecondModel(models.Model):
    related_field2 = models.ManyToManyField(
        FirstModel, blank=True, related_name="sm_f1",
    )
    related_field1 = models.ManyToManyField(
        FirstModel, blank=True, related_name="sm_f2",
    )
