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
        bulk_create() should properly set _order when parent has no existing
        children.
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
        bulk_create() should maintain separate _order sequences for different
        parents.
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
        The _order field should be correctly set for new Answer objects based
        on the count of existing Answers for each related Question.
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

    def test_bulk_create_respects_mixed_manual_order(self):
        """
        bulk_create() should assign _order automatically only for instances
        where it is not manually set. Mixed objects with and without _order
        should result in expected final order values.
        """
        question_a = self.Question.objects.create(text="Question A")
        question_b = self.Question.objects.create(text="Question B")

        # Existing answers to push initial _order forward.
        self.Answer.objects.create(question=question_a, text="Q-A Existing 0")
        self.Answer.objects.create(question=question_b, text="Q-B Existing 0")
        self.Answer.objects.create(question=question_b, text="Q-B Existing 1")

        answers = [
            self.Answer(question=question_a, text="Q-A Manual 4", _order=4),
            self.Answer(question=question_b, text="Q-B Auto 2"),
            self.Answer(question=question_a, text="Q-A Auto"),
            self.Answer(question=question_b, text="Q-B Manual 10", _order=10),
            self.Answer(question=question_a, text="Q-A Manual 7", _order=7),
            self.Answer(question=question_b, text="Q-B Auto 3"),
        ]

        created_answers = self.Answer.objects.bulk_create(answers)
        (
            qa_manual_4,
            qb_auto_2,
            qa_auto,
            qb_manual_10,
            qa_manual_7,
            qb_auto_3,
        ) = created_answers

        # Manual values should stay untouched.
        self.assertEqual(qa_manual_4._order, 4)
        self.assertEqual(qb_manual_10._order, 10)
        self.assertEqual(qa_manual_7._order, 7)
        # Existing max was 0 → auto should get _order=1.
        self.assertEqual(qa_auto._order, 1)
        # Existing max was 1 → next auto gets 2, then 3 (manual 10 is skipped).
        self.assertEqual(qb_auto_2._order, 2)
        self.assertEqual(qb_auto_3._order, 3)

    def test_bulk_create_allows_duplicate_order_values(self):
        """
        bulk_create() should allow duplicate _order values if the model
        does not enforce uniqueness on the _order field.
        """
        question = self.Question.objects.create(text="Duplicated Test")

        # Existing answer to set initial _order=0.
        self.Answer.objects.create(question=question, text="Existing Answer")
        # Two manually set _order=1 and one auto (which may also be assigned
        # 1).
        answers = [
            self.Answer(question=question, text="Manual Order 1", _order=1),
            self.Answer(question=question, text="Auto Order 1"),
            self.Answer(question=question, text="Auto Order 2"),
            self.Answer(question=question, text="Manual Order 1 Duplicate", _order=1),
        ]

        created_answers = self.Answer.objects.bulk_create(answers)
        manual_1, auto_1, auto_2, manual_2 = created_answers

        # Manual values are as assigned, even if duplicated.
        self.assertEqual(manual_1._order, 1)
        self.assertEqual(manual_2._order, 1)
        # Auto-assigned orders may also use 1 or any value, depending on
        # implementation. If no collision logic, they may overlap with manual
        # values.
        self.assertEqual(auto_1._order, 1)
        self.assertEqual(auto_2._order, 2)
