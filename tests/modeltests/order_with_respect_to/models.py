"""
Tests for the order_with_respect_to Meta attribute.
"""

from django.db import models

class Question(models.Model):
    text = models.CharField(max_length=200)

class Answer(models.Model):
    text = models.CharField(max_length=200)
    question = models.ForeignKey(Question)

    class Meta:
        order_with_respect_to = 'question'

    def __unicode__(self):
        return unicode(self.text)

__test__ = {'API_TESTS': """
>>> q1 = Question(text="Which Beatle starts with the letter 'R'?")
>>> q1.save()
>>> q2 = Question(text="What is your name?")
>>> q2.save()
>>> Answer(text="John", question=q1).save()
>>> Answer(text="Jonno",question=q2).save()
>>> Answer(text="Paul", question=q1).save()
>>> Answer(text="Paulo", question=q2).save()
>>> Answer(text="George", question=q1).save()
>>> Answer(text="Ringo", question=q1).save()

The answers will always be ordered in the order they were inserted.

>>> q1.answer_set.all()
[<Answer: John>, <Answer: Paul>, <Answer: George>, <Answer: Ringo>]

We can retrieve the answers related to a particular object, in the order
they were created, once we have a particular object.

>>> a1 = Answer.objects.filter(question=q1)[0]
>>> a1
<Answer: John>
>>> a2 = a1.get_next_in_order()
>>> a2
<Answer: Paul>
>>> a4 = list(Answer.objects.filter(question=q1))[-1]
>>> a4
<Answer: Ringo>
>>> a4.get_previous_in_order()
<Answer: George>

Determining (and setting) the ordering for a particular item is also possible.

>>> id_list = [o.pk for o in q1.answer_set.all()]
>>> a2.question.get_answer_order() == id_list
True

>>> a5 = Answer(text="Number five", question=q1)
>>> a5.save()

It doesn't matter which answer we use to check the order, it will always be the same.

>>> a2.question.get_answer_order() == a5.question.get_answer_order()
True

The ordering can be altered:

>>> id_list = [o.pk for o in q1.answer_set.all()]
>>> x = id_list.pop()
>>> id_list.insert(-1, x)
>>> a5.question.get_answer_order() == id_list
False
>>> a5.question.set_answer_order(id_list)
>>> q1.answer_set.all()
[<Answer: John>, <Answer: Paul>, <Answer: George>, <Answer: Number five>, <Answer: Ringo>]

"""
}
