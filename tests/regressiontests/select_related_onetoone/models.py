from django.db import models


class User(models.Model):
    username = models.CharField(max_length=100)
    email = models.EmailField()

    def __unicode__(self):
        return self.username


class UserProfile(models.Model):
    user = models.OneToOneField(User)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=2)

    def __unicode__(self):
        return "%s, %s" % (self.city, self.state)


class UserStatResult(models.Model):
    results = models.CharField(max_length=50)

    def __unicode__(self):
        return 'UserStatResults, results = %s' % (self.results,)


class UserStat(models.Model):
    user = models.OneToOneField(User, primary_key=True)
    posts = models.IntegerField()
    results = models.ForeignKey(UserStatResult)

    def __unicode__(self):
        return 'UserStat, posts = %s' % (self.posts,)


class StatDetails(models.Model):
    base_stats = models.OneToOneField(UserStat)
    comments = models.IntegerField()

    def __unicode__(self):
        return 'StatDetails, comments = %s' % (self.comments,)


class AdvancedUserStat(UserStat):
    pass
