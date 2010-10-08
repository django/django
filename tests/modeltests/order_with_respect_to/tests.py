from operator import attrgetter

from django.test import TestCase

from models import Question, Answer


class OrderWithRespectToTests(TestCase):
    def test_basic(self):
        q1 = Question.objects.create(text="Which Beatle starts with the letter 'R'?")
        q2 = Question.objects.create(text="What is your name?")
        
        Answer.objects.create(text="John", question=q1)
        Answer.objects.create(text="Jonno", question=q2)
        Answer.objects.create(text="Paul", question=q1)
        Answer.objects.create(text="Paulo", question=q2)
        Answer.objects.create(text="George", question=q1)
        Answer.objects.create(text="Ringo", question=q1)
        
        # The answers will always be ordered in the order they were inserted.
        self.assertQuerysetEqual(
            q1.answer_set.all(), [
                "John", "Paul", "George", "Ringo",
            ],
            attrgetter("text"),
        )
        
        # We can retrieve the answers related to a particular object, in the
        # order they were created, once we have a particular object.
        a1 = Answer.objects.filter(question=q1)[0]
        self.assertEqual(a1.text, "John")
        a2 = a1.get_next_in_order()
        self.assertEqual(a2.text, "Paul")
        a4 = list(Answer.objects.filter(question=q1))[-1]
        self.assertEqual(a4.text, "Ringo")
        self.assertEqual(a4.get_previous_in_order().text, "George")
        
        # Determining (and setting) the ordering for a particular item is also
        # possible.
        id_list = [o.pk for o in q1.answer_set.all()]
        self.assertEqual(a2.question.get_answer_order(), id_list)
        
        a5 = Answer.objects.create(text="Number five", question=q1)
        
        # It doesn't matter which answer we use to check the order, it will
        # always be the same.
        self.assertEqual(
            a2.question.get_answer_order(), a5.question.get_answer_order()
        )
        
        # The ordering can be altered:
        id_list = [o.pk for o in q1.answer_set.all()]
        x = id_list.pop()
        id_list.insert(-1, x)
        self.assertNotEqual(a5.question.get_answer_order(), id_list)
        a5.question.set_answer_order(id_list)
        self.assertQuerysetEqual(
            q1.answer_set.all(), [
                "John", "Paul", "George", "Number five", "Ringo"
            ],
            attrgetter("text")
        )
