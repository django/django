from django.contrib.contenttypes.fields import (
    GenericForeignKey, GenericRelation,
)
from django.contrib.contenttypes.models import ContentType
from django.db import models


class P(models.Model):
    pass


class R(models.Model):
    is_default = models.BooleanField(default=False)
    p = models.ForeignKey(P, models.CASCADE, null=True)

    def __str__(self):
        return "%s" % self.pk


def get_default_r():
    return R.objects.get_or_create(is_default=True)[0].pk


class S(models.Model):
    r = models.ForeignKey(R, models.CASCADE)


class T(models.Model):
    s = models.ForeignKey(S, models.CASCADE)


class U(models.Model):
    t = models.ForeignKey(T, models.CASCADE)


class RChild(R):
    pass


class RChildChild(RChild):
    pass


class A(models.Model):
    name = models.CharField(max_length=30)

    auto = models.ForeignKey(R, models.CASCADE, related_name="auto_set")
    auto_nullable = models.ForeignKey(R, models.CASCADE, null=True, related_name='auto_nullable_set')
    setvalue = models.ForeignKey(R, models.SET(get_default_r), related_name='setvalue')
    setnull = models.ForeignKey(R, models.SET_NULL, null=True, related_name='setnull_set')
    setdefault = models.ForeignKey(R, models.SET_DEFAULT, default=get_default_r, related_name='setdefault_set')
    setdefault_none = models.ForeignKey(
        R, models.SET_DEFAULT,
        default=None, null=True, related_name='setnull_nullable_set',
    )
    cascade = models.ForeignKey(R, models.CASCADE, related_name='cascade_set')
    cascade_nullable = models.ForeignKey(R, models.CASCADE, null=True, related_name='cascade_nullable_set')
    protect = models.ForeignKey(R, models.PROTECT, null=True, related_name='protect_set')
    restrict = models.ForeignKey(R, models.RESTRICT, null=True, related_name='restrict_set')
    donothing = models.ForeignKey(R, models.DO_NOTHING, null=True, related_name='donothing_set')
    child = models.ForeignKey(RChild, models.CASCADE, related_name="child")
    child_setnull = models.ForeignKey(RChild, models.SET_NULL, null=True, related_name="child_setnull")
    cascade_p = models.ForeignKey(P, models.CASCADE, related_name='cascade_p_set', null=True)

    # A OneToOneField is just a ForeignKey unique=True, so we don't duplicate
    # all the tests; just one smoke test to ensure on_delete works for it as
    # well.
    o2o_setnull = models.ForeignKey(R, models.SET_NULL, null=True, related_name="o2o_nullable_set")


class B(models.Model):
    protect = models.ForeignKey(R, models.PROTECT)


def create_a(name):
    a = A(name=name)
    for name in ('auto', 'auto_nullable', 'setvalue', 'setnull', 'setdefault',
                 'setdefault_none', 'cascade', 'cascade_nullable', 'protect',
                 'restrict', 'donothing', 'o2o_setnull'):
        r = R.objects.create()
        setattr(a, name, r)
    a.child = RChild.objects.create()
    a.child_setnull = RChild.objects.create()
    a.save()
    return a


class M(models.Model):
    m2m = models.ManyToManyField(R, related_name="m_set")
    m2m_through = models.ManyToManyField(R, through="MR", related_name="m_through_set")
    m2m_through_null = models.ManyToManyField(R, through="MRNull", related_name="m_through_null_set")


class MR(models.Model):
    m = models.ForeignKey(M, models.CASCADE)
    r = models.ForeignKey(R, models.CASCADE)


class MRNull(models.Model):
    m = models.ForeignKey(M, models.CASCADE)
    r = models.ForeignKey(R, models.SET_NULL, null=True)


class Avatar(models.Model):
    desc = models.TextField(null=True)


# This model is used to test a duplicate query regression (#25685)
class AvatarProxy(Avatar):
    class Meta:
        proxy = True


class User(models.Model):
    avatar = models.ForeignKey(Avatar, models.CASCADE, null=True)


class HiddenUser(models.Model):
    r = models.ForeignKey(R, models.CASCADE, related_name="+")


class HiddenUserProfile(models.Model):
    user = models.ForeignKey(HiddenUser, models.CASCADE)


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
    base = models.ForeignKey(Base, models.DO_NOTHING)


class Origin(models.Model):
    pass


class Referrer(models.Model):
    origin = models.ForeignKey(Origin, models.CASCADE)
    unique_field = models.IntegerField(unique=True)
    large_field = models.TextField()


class SecondReferrer(models.Model):
    referrer = models.ForeignKey(Referrer, models.CASCADE)
    other_referrer = models.ForeignKey(
        Referrer, models.CASCADE, to_field='unique_field', related_name='+'
    )


class DeleteTop(models.Model):
    b1 = GenericRelation('GenericB1')
    b2 = GenericRelation('GenericB2')


class B1(models.Model):
    delete_top = models.ForeignKey(DeleteTop, models.CASCADE)


class B2(models.Model):
    delete_top = models.ForeignKey(DeleteTop, models.CASCADE)


class DeleteBottom(models.Model):
    b1 = models.ForeignKey(B1, models.RESTRICT)
    b2 = models.ForeignKey(B2, models.CASCADE)


class GenericB1(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    generic_delete_top = GenericForeignKey('content_type', 'object_id')


class GenericB2(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    generic_delete_top = GenericForeignKey('content_type', 'object_id')
    generic_delete_bottom = GenericRelation('GenericDeleteBottom')


class GenericDeleteBottom(models.Model):
    generic_b1 = models.ForeignKey(GenericB1, models.RESTRICT)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    generic_b2 = GenericForeignKey()


class GenericDeleteBottomParent(models.Model):
    generic_delete_bottom = models.ForeignKey(GenericDeleteBottom, on_delete=models.CASCADE)
