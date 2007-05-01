from django.db import models

class Poll(models.Model):
    question = models.CharField(maxlength=200)

    def __str__(self):
        return "Q: %s " % self.question

class Choice(models.Model):
    poll = models.ForeignKey(Poll)
    choice = models.CharField(maxlength=200)

    def __str__(self):
        return "Choice: %s in poll %s" % (self.choice, self.poll)

__test__ = {'API_TESTS':"""
# Regression test for the use of None as a query value. None is interpreted as 
# an SQL NULL, but only in __exact queries.
# Set up some initial polls and choices
>>> p1 = Poll(question='Why?')
>>> p1.save()
>>> c1 = Choice(poll=p1, choice='Because.')
>>> c1.save()
>>> c2 = Choice(poll=p1, choice='Why Not?')
>>> c2.save()

# Exact query with value None returns nothing (=NULL in sql)
>>> Choice.objects.filter(id__exact=None)
[]

# Valid query, but fails because foo isn't a keyword
>>> Choice.objects.filter(foo__exact=None) 
Traceback (most recent call last):
...
TypeError: Cannot resolve keyword 'foo' into field, choices are: id, poll, choice

# Can't use None on anything other than __exact
>>> Choice.objects.filter(id__gt=None)
Traceback (most recent call last):
...
ValueError: Cannot use None as a query value

# Can't use None on anything other than __exact
>>> Choice.objects.filter(foo__gt=None)
Traceback (most recent call last):
...
ValueError: Cannot use None as a query value

# Related managers use __exact=None implicitly if the object hasn't been saved.
>>> p2 = Poll(question="How?")
>>> p2.choice_set.all()
[]

"""}
