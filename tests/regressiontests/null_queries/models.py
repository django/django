from django.db import models


class Poll(models.Model):
    question = models.CharField(max_length=200)

    def __unicode__(self):
        return u"Q: %s " % self.question

class Choice(models.Model):
    poll = models.ForeignKey(Poll)
    choice = models.CharField(max_length=200)

    def __unicode__(self):
        return u"Choice: %s in poll %s" % (self.choice, self.poll)

# A set of models with an inner one pointing to two outer ones.
class OuterA(models.Model):
    pass

class OuterB(models.Model):
    data = models.CharField(max_length=10)

class Inner(models.Model):
    first = models.ForeignKey(OuterA)
    second = models.ForeignKey(OuterB, null=True)
