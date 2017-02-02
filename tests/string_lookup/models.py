from django.db import models


class Foo(models.Model):
    name = models.CharField(max_length=50)
    friend = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return "Foo %s" % self.name


class Bar(models.Model):
    name = models.CharField(max_length=50)
    normal = models.ForeignKey(Foo, models.CASCADE, related_name='normal_foo')
    fwd = models.ForeignKey("Whiz", models.CASCADE)
    back = models.ForeignKey("Foo", models.CASCADE)

    def __str__(self):
        return "Bar %s" % self.place.name


class Whiz(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return "Whiz %s" % self.name


class Child(models.Model):
    parent = models.OneToOneField('Base', models.CASCADE)
    name = models.CharField(max_length=50)

    def __str__(self):
        return "Child %s" % self.name


class Base(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return "Base %s" % self.name


class Article(models.Model):
    name = models.CharField(max_length=50)
    text = models.TextField()
    submitted_from = models.GenericIPAddressField(blank=True, null=True)

    def __str__(self):
        return "Article %s" % self.name
