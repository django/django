from django.contrib.auth.models import User
from django.db import models


class Animal(models.Model):
    name = models.CharField(max_length=150)
    latin_name = models.CharField(max_length=150)
    count = models.IntegerField()
    weight = models.FloatField()

    # use a non-default name for the default manager
    specimens = models.Manager()

    def __str__(self):
        return self.name


class Plant(models.Model):
    name = models.CharField(max_length=150)

    class Meta:
        # For testing when upper case letter in app name; regression for #4057
        db_table = "Fixtures_regress_plant"


class Stuff(models.Model):
    name = models.CharField(max_length=20, null=True)
    owner = models.ForeignKey(User, models.SET_NULL, null=True)

    def __str__(self):
        return self.name + " is owned by " + str(self.owner)


class Absolute(models.Model):
    name = models.CharField(max_length=40)


class Parent(models.Model):
    name = models.CharField(max_length=10)

    class Meta:
        ordering = ("id",)


class Child(Parent):
    data = models.CharField(max_length=10)


# Models to regression test #7572, #20820
class Channel(models.Model):
    name = models.CharField(max_length=255)


class Article(models.Model):
    title = models.CharField(max_length=255)
    channels = models.ManyToManyField(Channel)

    class Meta:
        ordering = ("id",)


# Subclass of a model with a ManyToManyField for test_ticket_20820
class SpecialArticle(Article):
    pass


# Models to regression test #22421
class CommonFeature(Article):
    class Meta:
        abstract = True


class Feature(CommonFeature):
    pass


# Models to regression test #11428
class Widget(models.Model):
    name = models.CharField(max_length=255)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name


class WidgetProxy(Widget):
    class Meta:
        proxy = True


# Check for forward references in FKs and M2Ms with natural keys
class TestManager(models.Manager):
    def get_by_natural_key(self, key):
        return self.get(name=key)


class Store(models.Model):
    name = models.CharField(max_length=255, unique=True)
    main = models.ForeignKey("self", models.SET_NULL, null=True)

    objects = TestManager()

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name

    def natural_key(self):
        return (self.name,)


class Person(models.Model):
    name = models.CharField(max_length=255, unique=True)

    objects = TestManager()

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name

    # Person doesn't actually have a dependency on store, but we need to define
    # one to test the behavior of the dependency resolution algorithm.
    def natural_key(self):
        return (self.name,)

    natural_key.dependencies = ["fixtures_regress.store"]


class Book(models.Model):
    name = models.CharField(max_length=255)
    author = models.ForeignKey(Person, models.CASCADE)
    stores = models.ManyToManyField(Store)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return "%s by %s (available at %s)" % (
            self.name,
            self.author.name,
            ", ".join(s.name for s in self.stores.all()),
        )


class NKManager(models.Manager):
    def get_by_natural_key(self, data):
        return self.get(data=data)


class NKChild(Parent):
    data = models.CharField(max_length=10, unique=True)
    objects = NKManager()

    def natural_key(self):
        return (self.data,)

    def __str__(self):
        return "NKChild %s:%s" % (self.name, self.data)


class RefToNKChild(models.Model):
    text = models.CharField(max_length=10)
    nk_fk = models.ForeignKey(NKChild, models.CASCADE, related_name="ref_fks")
    nk_m2m = models.ManyToManyField(NKChild, related_name="ref_m2ms")

    def __str__(self):
        return "%s: Reference to %s [%s]" % (
            self.text,
            self.nk_fk,
            ", ".join(str(o) for o in self.nk_m2m.all()),
        )


# ome models with pathological circular dependencies
class Circle1(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def natural_key(self):
        return (self.name,)

    natural_key.dependencies = ["fixtures_regress.circle2"]


class Circle2(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def natural_key(self):
        return (self.name,)

    natural_key.dependencies = ["fixtures_regress.circle1"]


class Circle3(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def natural_key(self):
        return (self.name,)

    natural_key.dependencies = ["fixtures_regress.circle3"]


class Circle4(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def natural_key(self):
        return (self.name,)

    natural_key.dependencies = ["fixtures_regress.circle5"]


class Circle5(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def natural_key(self):
        return (self.name,)

    natural_key.dependencies = ["fixtures_regress.circle6"]


class Circle6(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def natural_key(self):
        return (self.name,)

    natural_key.dependencies = ["fixtures_regress.circle4"]


class ExternalDependency(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def natural_key(self):
        return (self.name,)

    natural_key.dependencies = ["fixtures_regress.book"]


# Model for regression test of #11101
class Thingy(models.Model):
    name = models.CharField(max_length=255)


class M2MToSelf(models.Model):
    parent = models.ManyToManyField("self", blank=True)


class BaseNKModel(models.Model):
    """
    Base model with a natural_key and a manager with `get_by_natural_key`
    """

    data = models.CharField(max_length=20, unique=True)

    objects = NKManager()

    class Meta:
        abstract = True

    def __str__(self):
        return self.data

    def natural_key(self):
        return (self.data,)


class M2MSimpleA(BaseNKModel):
    b_set = models.ManyToManyField("M2MSimpleB")


class M2MSimpleB(BaseNKModel):
    pass


class M2MSimpleCircularA(BaseNKModel):
    b_set = models.ManyToManyField("M2MSimpleCircularB")


class M2MSimpleCircularB(BaseNKModel):
    a_set = models.ManyToManyField("M2MSimpleCircularA")


class M2MComplexA(BaseNKModel):
    b_set = models.ManyToManyField("M2MComplexB", through="M2MThroughAB")


class M2MComplexB(BaseNKModel):
    pass


class M2MThroughAB(BaseNKModel):
    a = models.ForeignKey(M2MComplexA, models.CASCADE)
    b = models.ForeignKey(M2MComplexB, models.CASCADE)


class M2MComplexCircular1A(BaseNKModel):
    b_set = models.ManyToManyField(
        "M2MComplexCircular1B", through="M2MCircular1ThroughAB"
    )


class M2MComplexCircular1B(BaseNKModel):
    c_set = models.ManyToManyField(
        "M2MComplexCircular1C", through="M2MCircular1ThroughBC"
    )


class M2MComplexCircular1C(BaseNKModel):
    a_set = models.ManyToManyField(
        "M2MComplexCircular1A", through="M2MCircular1ThroughCA"
    )


class M2MCircular1ThroughAB(BaseNKModel):
    a = models.ForeignKey(M2MComplexCircular1A, models.CASCADE)
    b = models.ForeignKey(M2MComplexCircular1B, models.CASCADE)


class M2MCircular1ThroughBC(BaseNKModel):
    b = models.ForeignKey(M2MComplexCircular1B, models.CASCADE)
    c = models.ForeignKey(M2MComplexCircular1C, models.CASCADE)


class M2MCircular1ThroughCA(BaseNKModel):
    c = models.ForeignKey(M2MComplexCircular1C, models.CASCADE)
    a = models.ForeignKey(M2MComplexCircular1A, models.CASCADE)


class M2MComplexCircular2A(BaseNKModel):
    b_set = models.ManyToManyField(
        "M2MComplexCircular2B", through="M2MCircular2ThroughAB"
    )


class M2MComplexCircular2B(BaseNKModel):
    def natural_key(self):
        return (self.data,)

    # Fake the dependency for a circularity
    natural_key.dependencies = ["fixtures_regress.M2MComplexCircular2A"]


class M2MCircular2ThroughAB(BaseNKModel):
    a = models.ForeignKey(M2MComplexCircular2A, models.CASCADE)
    b = models.ForeignKey(M2MComplexCircular2B, models.CASCADE)
