"""
The tests are shared with contenttypes_tests and so shouldn't import or
reference any models directly. Subclasses should inherit django.test.TestCase.
"""

from operator import attrgetter


class BaseOrderWithRespectToTests:
    databases = {"default", "other"}

    # Hook to allow subclasses to run these tests with alternate models.
    Answer = None
    Post = None
    Question = None

    @classmethod
    def setUpTestData(cls):
        cls.q1 = cls.Question.objects.create(
            text="Which Beatle starts with the letter 'R'?"
        )
        cls.Answer.objects.create(text="John", question=cls.q1)
        cls.Answer.objects.create(text="Paul", question=cls.q1)
        cls.Answer.objects.create(text="George", question=cls.q1)
        cls.Answer.objects.create(text="Ringo", question=cls.q1)

    def test_default_to_insertion_order(self):
        # Answers will always be ordered in the order they were inserted.
        self.assertQuerySetEqual(
            self.q1.answer_set.all(),
            [
                "John",
                "Paul",
                "George",
                "Ringo",
            ],
            attrgetter("text"),
        )

    def test_previous_and_next_in_order(self):
        # We can retrieve the answers related to a particular object, in the
        # order they were created, once we have a particular object.
        a1 = self.q1.answer_set.all()[0]
        self.assertEqual(a1.text, "John")
        self.assertEqual(a1.get_next_in_order().text, "Paul")

        a2 = list(self.q1.answer_set.all())[-1]
        self.assertEqual(a2.text, "Ringo")
        self.assertEqual(a2.get_previous_in_order().text, "George")

    def test_item_ordering(self):
        # We can retrieve the ordering of the queryset from a particular item.
        a1 = self.q1.answer_set.all()[1]
        id_list = [o.pk for o in self.q1.answer_set.all()]
        self.assertSequenceEqual(a1.question.get_answer_order(), id_list)

        # It doesn't matter which answer we use to check the order, it will
        # always be the same.
        a2 = self.Answer.objects.create(text="Number five", question=self.q1)
        self.assertEqual(
            list(a1.question.get_answer_order()), list(a2.question.get_answer_order())
        )

    def test_set_order_unrelated_object(self):
        """An answer that's not related isn't updated."""
        q = self.Question.objects.create(text="other")
        a = self.Answer.objects.create(text="Number five", question=q)
        self.q1.set_answer_order([o.pk for o in self.q1.answer_set.all()] + [a.pk])
        self.assertEqual(self.Answer.objects.get(pk=a.pk)._order, 0)

    def test_change_ordering(self):
        # The ordering can be altered
        a = self.Answer.objects.create(text="Number five", question=self.q1)

        # Swap the last two items in the order list
        id_list = [o.pk for o in self.q1.answer_set.all()]
        x = id_list.pop()
        id_list.insert(-1, x)

        # By default, the ordering is different from the swapped version
        self.assertNotEqual(list(a.question.get_answer_order()), id_list)

        # Change the ordering to the swapped version -
        # this changes the ordering of the queryset.
        a.question.set_answer_order(id_list)
        self.assertQuerySetEqual(
            self.q1.answer_set.all(),
            ["John", "Paul", "George", "Number five", "Ringo"],
            attrgetter("text"),
        )

    def test_recursive_ordering(self):
        p1 = self.Post.objects.create(title="1")
        p2 = self.Post.objects.create(title="2")
        p1_1 = self.Post.objects.create(title="1.1", parent=p1)
        p1_2 = self.Post.objects.create(title="1.2", parent=p1)
        self.Post.objects.create(title="2.1", parent=p2)
        p1_3 = self.Post.objects.create(title="1.3", parent=p1)
        self.assertSequenceEqual(p1.get_post_order(), [p1_1.pk, p1_2.pk, p1_3.pk])

    def test_delete_and_insert(self):
        q1 = self.Question.objects.create(text="What is your favorite color?")
        q2 = self.Question.objects.create(text="What color is it?")
        a1 = self.Answer.objects.create(text="Blue", question=q1)
        a2 = self.Answer.objects.create(text="Red", question=q1)
        a3 = self.Answer.objects.create(text="Green", question=q1)
        a4 = self.Answer.objects.create(text="Yellow", question=q1)
        self.assertSequenceEqual(q1.answer_set.all(), [a1, a2, a3, a4])
        a3.question = q2
        a3.save()
        a1.delete()
        new_answer = self.Answer.objects.create(text="Black", question=q1)
        self.assertSequenceEqual(q1.answer_set.all(), [a2, a4, new_answer])

    def test_database_routing(self):
        class WriteToOtherRouter:
            def db_for_write(self, model, **hints):
                return "other"

        with self.settings(DATABASE_ROUTERS=[WriteToOtherRouter()]):
            with (
                self.assertNumQueries(0, using="default"),
                self.assertNumQueries(
                    1,
                    using="other",
                ),
            ):
                self.q1.set_answer_order([3, 1, 2, 4])

    def test_bulk_create_with_empty_parent(self):
        """
        bulk_create() should properly set _order when parent has no existing children.
        """
        question = self.Question.objects.create(text="Test Question")
        answers = [self.Answer(question=question, text=f"Answer {i}") for i in range(3)]
        answer0, answer1, answer2 = self.Answer.objects.bulk_create(answers)

        self.assertEqual(answer0._order, 0)
        self.assertEqual(answer1._order, 1)
        self.assertEqual(answer2._order, 2)

    def test_bulk_create_with_existing_children(self):
        """
        bulk_create() should continue _order sequence from existing children.
        """
        question = self.Question.objects.create(text="Test Question")
        self.Answer.objects.create(question=question, text="Existing 0")
        self.Answer.objects.create(question=question, text="Existing 1")

        new_answers = [
            self.Answer(question=question, text=f"New Answer {i}") for i in range(2)
        ]
        answer2, answer3 = self.Answer.objects.bulk_create(new_answers)

        self.assertEqual(answer2._order, 2)
        self.assertEqual(answer3._order, 3)

    def test_bulk_create_multiple_parents(self):
        """
        bulk_create() should maintain separate _order sequences for different parents.
        """
        question0 = self.Question.objects.create(text="Question 0")
        question1 = self.Question.objects.create(text="Question 1")

        answers = [
            self.Answer(question=question0, text="Q0 Answer 0"),
            self.Answer(question=question1, text="Q1 Answer 0"),
            self.Answer(question=question0, text="Q0 Answer 1"),
            self.Answer(question=question1, text="Q1 Answer 1"),
        ]
        created_answers = self.Answer.objects.bulk_create(answers)
        answer_q0_0, answer_q1_0, answer_q0_1, answer_q1_1 = created_answers

        self.assertEqual(answer_q0_0._order, 0)
        self.assertEqual(answer_q0_1._order, 1)
        self.assertEqual(answer_q1_0._order, 0)
        self.assertEqual(answer_q1_1._order, 1)

    def test_bulk_create_mixed_scenario(self):
        """
        Test bulk_create with mixed Questions having existing and no Answers.
        Validates _order field is correctly set for new Answer objects based on
        the count of existing Answers for each related Question.
        """
        question0 = self.Question.objects.create(text="Question 0")
        question1 = self.Question.objects.create(text="Question 1")

        self.Answer.objects.create(question=question1, text="Q1 Existing 0")
        self.Answer.objects.create(question=question1, text="Q1 Existing 1")

        new_answers = [
            self.Answer(question=question0, text="Q0 New 0"),
            self.Answer(question=question1, text="Q1 New 0"),
            self.Answer(question=question0, text="Q0 New 1"),
        ]
        created_answers = self.Answer.objects.bulk_create(new_answers)
        answer_q0_0, answer_q1_2, answer_q0_1 = created_answers

        self.assertEqual(answer_q0_0._order, 0)
        self.assertEqual(answer_q0_1._order, 1)
        self.assertEqual(answer_q1_2._order, 2)
