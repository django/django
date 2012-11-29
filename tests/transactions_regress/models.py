from django.db import models


class Mod(models.Model):
    fld = models.IntegerField()

class SubMod(Mod):
    cnt = models.IntegerField(unique=True)

class M2mA(models.Model):
    others = models.ManyToManyField('M2mB')


class M2mB(models.Model):
    fld = models.IntegerField()
