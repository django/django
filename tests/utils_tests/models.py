from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=100)

    def next(self):
        return self


class Thing(models.Model):
    name = models.CharField(max_length=100)
    category = models.ForeignKey(Category, models.CASCADE)


class CategoryInfo(models.Model):
    category = models.OneToOneField(Category, models.CASCADE)
