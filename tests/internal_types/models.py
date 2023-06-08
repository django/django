from django.db import models


class OneModel(models.Model):
    pass


class ForeignModel(models.Model):
    pass


class ManyModel(models.Model):
    pass


class InheritedForeignkey(models.ForeignKey):
    pass


class InheritedManyToManyField(models.ManyToManyField):
    pass


class InheritedOneToOneField(models.OneToOneField):
    pass


class TestModel(models.Model):
    foreign_test = models.ForeignKey(ForeignModel, on_delete=models.CASCADE)
    many_test = models.ManyToManyField(ManyModel, related_name="testmodels")
    one_test = models.OneToOneField(OneModel, on_delete=models.CASCADE)


class TestInheritedKeyModel(models.Model):
    foreign_test = InheritedForeignkey(ForeignModel, on_delete=models.CASCADE)
    many_test = InheritedManyToManyField(ManyModel, related_name="another_model")
    one_test = InheritedOneToOneField(OneModel, on_delete=models.CASCADE)
