from django.db import models


class A1(models.Model):
    pass


class A2(models.Model):
    pass


class A3(models.Model):
    b2 = models.ForeignKey('lookuperror_b.B2', models.CASCADE)
    c2 = models.ForeignKey('lookuperror_c.C2', models.CASCADE)


class A4(models.Model):
    pass
