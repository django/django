from django.db import models


class B1(models.Model):
    pass


class B2(models.Model):
    a1 = models.ForeignKey('lookuperror_a.A1')


class B3(models.Model):
    pass
