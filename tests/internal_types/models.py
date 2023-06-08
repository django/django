from django.db import models


class OneModel(models.Model):
    pass


class ForeignModel(models.Model):
    pass


class ManyModel(models.Model):
    pass


class TestModel(models.Model):
    foreign_test = models.ForeignKey(ForeignModel, on_delete=models.CASCADE)
    many_test = models.ManyToManyField(ManyModel, related_name="testmodels")
    one_test = models.OneToOneField(OneModel, on_delete=models.CASCADE)
