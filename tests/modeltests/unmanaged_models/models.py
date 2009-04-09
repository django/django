"""
Models can have a ``managed`` attribute, which specifies whether the SQL code
is generated for the table on various manage.py operations.
"""

from django.db import models

#  All of these models are creatd in the database by Django.

class A01(models.Model):
    f_a = models.CharField(max_length=10, db_index=True)
    f_b = models.IntegerField()

    class Meta:
        db_table = 'A01'

    def __unicode__(self):
        return self.f_a

class B01(models.Model):
    fk_a = models.ForeignKey(A01)
    f_a = models.CharField(max_length=10, db_index=True)
    f_b = models.IntegerField()

    class Meta:
        db_table = 'B01'
        # 'managed' is True by default. This tests we can set it explicitly.
        managed = True

    def __unicode__(self):
        return self.f_a

class C01(models.Model):
    mm_a = models.ManyToManyField(A01, db_table='D01')
    f_a = models.CharField(max_length=10, db_index=True)
    f_b = models.IntegerField()

    class Meta:
        db_table = 'C01'

    def __unicode__(self):
        return self.f_a

# All of these models use the same tables as the previous set (they are shadows
# of possibly a subset of the columns). There should be no creation errors,
# since we have told Django they aren't managed by Django.

class A02(models.Model):
    f_a = models.CharField(max_length=10, db_index=True)

    class Meta:
        db_table = 'A01'
        managed = False

    def __unicode__(self):
        return self.f_a

class B02(models.Model):
    class Meta:
        db_table = 'B01'
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
        db_table = 'C01'
        managed = False

    def __unicode__(self):
        return self.f_a

class Intermediate(models.Model):
    a02 = models.ForeignKey(A02, db_column="a01_id")
    c02 = models.ForeignKey(C02, db_column="c01_id")

    class Meta:
        db_table = 'D01'
        managed = False

#
# These next models test the creation (or not) of many to many join tables
# between managed and unmanaged models. A join table between two unmanaged 
# models shouldn't be automatically created (see #10647). 
#
class Unmanaged1(models.Model):    
    class Meta:
        managed = False

# Unmanged with an m2m to unmanaged: the intermediary table won't be created.
class Unmanaged2(models.Model):
    mm = models.ManyToManyField(Unmanaged1)
    
    class Meta:
        managed = False

# Here's an unmanaged model with an m2m to a managed one; the intermediary
# table *will* be created (unless given a custom `through` as for C02 above).
class Managed1(models.Model):
    mm = models.ManyToManyField(Unmanaged1)

__test__ = {'API_TESTS':"""
The main test here is that the all the models can be created without any
database errors. We can also do some more simple insertion and lookup tests
whilst we're here to show that the second of models do refer to the tables from
the first set.

# Insert some data into one set of models.
>>> a = A01.objects.create(f_a="foo", f_b=42)
>>> _ = B01.objects.create(fk_a=a, f_a="fred", f_b=1729)
>>> c = C01.objects.create(f_a="barney", f_b=1)
>>> c.mm_a = [a]

# ... and pull it out via the other set.
>>> A02.objects.all()
[<A02: foo>]
>>> b = B02.objects.all()[0]
>>> b
<B02: fred>
>>> b.fk_a
<A02: foo>
>>> C02.objects.filter(f_a=None)
[]
>>> C02.objects.filter(mm_a=a.id)
[<C02: barney>]

"""}
