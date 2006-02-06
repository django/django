"""
25. Reverse lookups

This demonstrates the reverse lookup features of the database API.
"""

from django.db import models

class User(models.Model):
    name = models.CharField(maxlength=200)
    def __repr__(self):
        return self.name

class Poll(models.Model):
    question = models.CharField(maxlength=200)
    creator = models.ForeignKey(User)
    def __repr__(self):
        return self.question

class Choice(models.Model):
    name = models.CharField(maxlength=100)
    poll = models.ForeignKey(Poll, related_name="poll_choice")
    related_poll = models.ForeignKey(Poll, related_name="related_choice")
    def __repr(self):
        return self.name

API_TESTS = """
>>> john = User(name="John Doe")
>>> john.save()
>>> jim = User(name="Jim Bo")
>>> jim.save()
>>> first_poll = Poll(question="What's the first question?", creator=john)
>>> first_poll.save()
>>> second_poll = Poll(question="What's the second question?", creator=jim)
>>> second_poll.save()
>>> new_choice = Choice(poll=first_poll, related_poll=second_poll, name="This is the answer.")
>>> new_choice.save()

>>> # Reverse lookups by field name:
>>> User.objects.get(poll__question__exact="What's the first question?")
John Doe
>>> User.objects.get(poll__question__exact="What's the second question?")
Jim Bo

>>> # Reverse lookups by related_name:
>>> Poll.objects.get(poll_choice__name__exact="This is the answer.")
What's the first question?
>>> Poll.objects.get(related_choice__name__exact="This is the answer.")
What's the second question?

>>> # If a related_name is given you can't use the field name instead:
>>> Poll.objects.get(choice__name__exact="This is the answer")
Traceback (most recent call last):
    ...
TypeError: Cannot resolve keyword 'choice' into field
"""
