from django.db import models
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class User(models.Model):
    username = models.CharField(max_length=100)
    email = models.EmailField()

    def __str__(self):
        return self.username


@python_2_unicode_compatible
class UserProfile(models.Model):
    user = models.OneToOneField(User)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=2)

    def __str__(self):
        return "%s, %s" % (self.city, self.state)


@python_2_unicode_compatible
class UserStatResult(models.Model):
    results = models.CharField(max_length=50)

    def __str__(self):
        return 'UserStatResults, results = %s' % (self.results,)


@python_2_unicode_compatible
class UserStat(models.Model):
    user = models.OneToOneField(User, primary_key=True)
    posts = models.IntegerField()
    results = models.ForeignKey(UserStatResult)

    def __str__(self):
        return 'UserStat, posts = %s' % (self.posts,)


@python_2_unicode_compatible
class StatDetails(models.Model):
    base_stats = models.OneToOneField(UserStat)
    comments = models.IntegerField()

    def __str__(self):
        return 'StatDetails, comments = %s' % (self.comments,)


class AdvancedUserStat(UserStat):
    karma = models.IntegerField()


class Image(models.Model):
    name = models.CharField(max_length=100)


class Product(models.Model):
    name = models.CharField(max_length=100)
    image = models.OneToOneField(Image, null=True)


@python_2_unicode_compatible
class Parent1(models.Model):
    name1 = models.CharField(max_length=50)

    def __str__(self):
        return self.name1


@python_2_unicode_compatible
class Parent2(models.Model):
    # Avoid having two "id" fields in the Child1 subclass
    id2 = models.AutoField(primary_key=True)
    name2 = models.CharField(max_length=50)

    def __str__(self):
        return self.name2


@python_2_unicode_compatible
class Child1(Parent1, Parent2):
    value = models.IntegerField()

    def __str__(self):
        return self.name1


@python_2_unicode_compatible
class Child2(Parent1):
    parent2 = models.OneToOneField(Parent2)
    value = models.IntegerField()

    def __str__(self):
        return self.name1


class Child3(Child2):
    value3 = models.IntegerField()


class Child4(Child1):
    value4 = models.IntegerField()
