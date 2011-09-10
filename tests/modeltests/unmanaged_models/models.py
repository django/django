"""
Models can have a ``managed`` attribute, which specifies whether the SQL code
is generated for the table on various manage.py operations.
"""

from django.db import models

#  All of these models are created in the database by Django.

class A01(models.Model):
    f_a = models.CharField(max_length=10, db_index=True)
    f_b = models.IntegerField()

    class Meta:
        db_table = 'a01'

    def __unicode__(self):
        return self.f_a

class B01(models.Model):
    fk_a = models.ForeignKey(A01)
    f_a = models.CharField(max_length=10, db_index=True)
    f_b = models.IntegerField()

    class Meta:
        db_table = 'b01'
        # 'managed' is True by default. This tests we can set it explicitly.
        managed = True

    def __unicode__(self):
        return self.f_a

class C01(models.Model):
    mm_a = models.ManyToManyField(A01, db_table='d01')
    f_a = models.CharField(max_length=10, db_index=True)
    f_b = models.IntegerField()

    class Meta:
        db_table = 'c01'

    def __unicode__(self):
        return self.f_a

# All of these models use the same tables as the previous set (they are shadows
# of possibly a subset of the columns). There should be no creation errors,
# since we have told Django they aren't managed by Django.

class A02(models.Model):
    f_a = models.CharField(max_length=10, db_index=True)

    class Meta:
        db_table = 'a01'
        managed = False

    def __unicode__(self):
        return self.f_a

class B02(models.Model):
    class Meta:
        db_table = 'b01'
        managed = False

    fk_a = models.ForeignKey(A02)
    f_a = models.CharField(max_length=10, db_index=True)
    f_b = models.IntegerField()

    def __unicode__(self):
        return self.f_a

# To re-use the many-to-many intermediate table, we need to manually set up
# things up.
class C02(models.Model):
    mm_a = models.ManyToManyField(A02, through="Intermediate")
    f_a = models.CharField(max_length=10, db_index=True)
    f_b = models.IntegerField()

    class Meta:
        db_table = 'c01'
        managed = False

    def __unicode__(self):
        return self.f_a

class Intermediate(models.Model):
    a02 = models.ForeignKey(A02, db_column="a01_id")
    c02 = models.ForeignKey(C02, db_column="c01_id")

    class Meta:
        db_table = 'd01'
        managed = False

#
# These next models test the creation (or not) of many to many join tables
# between managed and unmanaged models. A join table between two unmanaged
# models shouldn't be automatically created (see #10647).
#

# Firstly, we need some models that will create the tables, purely so that the
# tables are created. This is a test setup, not a requirement for unmanaged
# models.
class Proxy1(models.Model):
    class Meta:
        db_table = "unmanaged_models_proxy1"

class Proxy2(models.Model):
    class Meta:
        db_table = "unmanaged_models_proxy2"

class Unmanaged1(models.Model):
    class Meta:
        managed = False
        db_table = "unmanaged_models_proxy1"

# Unmanged with an m2m to unmanaged: the intermediary table won't be created.
class Unmanaged2(models.Model):
    mm = models.ManyToManyField(Unmanaged1)

    class Meta:
        managed = False
        db_table = "unmanaged_models_proxy2"

# Here's an unmanaged model with an m2m to a managed one; the intermediary
# table *will* be created (unless given a custom `through` as for C02 above).
class Managed1(models.Model):
    mm = models.ManyToManyField(Unmanaged1)
