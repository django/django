from django.db import models


class C1(models.Model):
    pass


class C2(models.Model):
    a1 = models.ForeignKey('lookuperror_a.A1')


class C3(models.Model):
    pass
