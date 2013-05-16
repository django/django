from __future__ import unicode_literals

from django.db import models
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class R(models.Model):
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return "%s" % self.pk


get_default_r = lambda: R.objects.get_or_create(is_default=True)[0]


class S(models.Model):
    r = models.ForeignKey(R)


class T(models.Model):
    s = models.ForeignKey(S)


class U(models.Model):
    t = models.ForeignKey(T)


class RChild(R):
    pass


class A(models.Model):
    name = models.CharField(max_length=30)

    auto = models.ForeignKey(R, related_name="auto_set")
    auto_nullable = models.ForeignKey(R, null=True,
        related_name='auto_nullable_set')
    setvalue = models.ForeignKey(R, on_delete=models.SET(get_default_r),
        related_name='setvalue')
    setnull = models.ForeignKey(R, on_delete=models.SET_NULL, null=True,
        related_name='setnull_set')
    setdefault = models.ForeignKey(R, on_delete=models.SET_DEFAULT,
        default=get_default_r, related_name='setdefault_set')
    setdefault_none = models.ForeignKey(R, on_delete=models.SET_DEFAULT,
        default=None, null=True, related_name='setnull_nullable_set')
    cascade = models.ForeignKey(R, on_delete=models.CASCADE,
        related_name='cascade_set')
    cascade_nullable = models.ForeignKey(R, on_delete=models.CASCADE, null=True,
        related_name='cascade_nullable_set')
    protect = models.ForeignKey(R, on_delete=models.PROTECT, null=True)
    donothing = models.ForeignKey(R, on_delete=models.DO_NOTHING, null=True,
        related_name='donothing_set')
    child = models.ForeignKey(RChild, related_name="child")
    child_setnull = models.ForeignKey(RChild, on_delete=models.SET_NULL, null=True,
        related_name="child_setnull")

    # A OneToOneField is just a ForeignKey unique=True, so we don't duplicate
    # all the tests; just one smoke test to ensure on_delete works for it as
    # well.
    o2o_setnull = models.ForeignKey(R, null=True,
        on_delete=models.SET_NULL, related_name="o2o_nullable_set")


def create_a(name):
    a = A(name=name)
    for name in ('auto', 'auto_nullable', 'setvalue', 'setnull', 'setdefault',
                 'setdefault_none', 'cascade', 'cascade_nullable', 'protect',
                 'donothing', 'o2o_setnull'):
        r = R.objects.create()
        setattr(a, name, r)
    a.child = RChild.objects.create()
    a.child_setnull = RChild.objects.create()
    a.save()
    return a


class M(models.Model):
    m2m = models.ManyToManyField(R, related_name="m_set")
    m2m_through = models.ManyToManyField(R, through="MR",
        related_name="m_through_set")
    m2m_through_null = models.ManyToManyField(R, through="MRNull",
        related_name="m_through_null_set")


class MR(models.Model):
    m = models.ForeignKey(M)
    r = models.ForeignKey(R)


class MRNull(models.Model):
    m = models.ForeignKey(M)
    r = models.ForeignKey(R, null=True, on_delete=models.SET_NULL)


class Avatar(models.Model):
    desc = models.TextField(null=True)


class User(models.Model):
    avatar = models.ForeignKey(Avatar, null=True)


class HiddenUser(models.Model):
    r = models.ForeignKey(R, related_name="+")


class HiddenUserProfile(models.Model):
    user = models.ForeignKey(HiddenUser)

class M2MTo(models.Model):
    pass

class M2MFrom(models.Model):
    m2m = models.ManyToManyField(M2MTo)

class Parent(models.Model):
    pass

class Child(Parent):
    pass

class Base(models.Model):
    pass

class RelToBase(models.Model):
    base = models.ForeignKey(Base, on_delete=models.DO_NOTHING)
