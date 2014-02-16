from django.db import models


class ValuesTestModel(models.Model):
    field_a = models.CharField(max_length=100)
    field_b = models.IntegerField()
    field_c = models.TextField()
