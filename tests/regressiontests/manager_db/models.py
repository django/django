from django.db import models

class Insect(models.Model):
    common_name = models.CharField(maxlength=64)
    latin_name = models.CharField(maxlength=128)
