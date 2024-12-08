from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=100)


class CategoryInfo(models.Model):
    category = models.OneToOneField(Category, models.CASCADE)
