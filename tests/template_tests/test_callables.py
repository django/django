from unittest import TestCase

from django.db import models
from django.template import Context, Engine


class CallableVariablesTests(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.engine = Engine()
        super().setUpClass()

    def test_callable(self):

        class Doodad:
            def __init__(self, value):
                self.num_calls = 0
                self.value = value

            def __call__(self):
                self.num_calls += 1
                return {"the_value": self.value}

        my_doodad = Doodad(42)
        c = Context({"my_doodad": my_doodad})

        # We can't access ``my_doodad.value`` in the template, because
        # ``my_doodad.__call__`` will be invoked first, yielding a dictionary
        # without a key ``value``.
        t = self.engine.from_string('{{ my_doodad.value }}')
        self.assertEqual(t.render(c), '')

        # We can confirm that the doodad has been called
        self.assertEqual(my_doodad.num_calls, 1)

        # But we can access keys on the dict that's returned
        # by ``__call__``, instead.
        t = self.engine.from_string('{{ my_doodad.the_value }}')
        self.assertEqual(t.render(c), '42')
        self.assertEqual(my_doodad.num_calls, 2)

    def test_alters_data(self):

        class Doodad:
            alters_data = True

            def __init__(self, value):
                self.num_calls = 0
                self.value = value

            def __call__(self):
                self.num_calls += 1
                return {"the_value": self.value}

        my_doodad = Doodad(42)
        c = Context({"my_doodad": my_doodad})

        # Since ``my_doodad.alters_data`` is True, the template system will not
        # try to call our doodad but will use string_if_invalid
        t = self.engine.from_string('{{ my_doodad.value }}')
        self.assertEqual(t.render(c), '')
        t = self.engine.from_string('{{ my_doodad.the_value }}')
        self.assertEqual(t.render(c), '')

        # Double-check that the object was really never called during the
        # template rendering.
        self.assertEqual(my_doodad.num_calls, 0)

    def test_do_not_call(self):

        class Doodad:
            do_not_call_in_templates = True

            def __init__(self, value):
                self.num_calls = 0
                self.value = value

            def __call__(self):
                self.num_calls += 1
                return {"the_value": self.value}

        my_doodad = Doodad(42)
        c = Context({"my_doodad": my_doodad})

        # Since ``my_doodad.do_not_call_in_templates`` is True, the template
        # system will not try to call our doodad.  We can access its attributes
        # as normal, and we don't have access to the dict that it returns when
        # called.
        t = self.engine.from_string('{{ my_doodad.value }}')
        self.assertEqual(t.render(c), '42')
        t = self.engine.from_string('{{ my_doodad.the_value }}')
        self.assertEqual(t.render(c), '')

        # Double-check that the object was really never called during the
        # template rendering.
        self.assertEqual(my_doodad.num_calls, 0)

    def test_do_not_call_and_alters_data(self):
        # If we combine ``alters_data`` and ``do_not_call_in_templates``, the
        # ``alters_data`` attribute will not make any difference in the
        # template system's behavior.

        class Doodad:
            do_not_call_in_templates = True
            alters_data = True

            def __init__(self, value):
                self.num_calls = 0
                self.value = value

            def __call__(self):
                self.num_calls += 1
                return {"the_value": self.value}

        my_doodad = Doodad(42)
        c = Context({"my_doodad": my_doodad})

        t = self.engine.from_string('{{ my_doodad.value }}')
        self.assertEqual(t.render(c), '42')
        t = self.engine.from_string('{{ my_doodad.the_value }}')
        self.assertEqual(t.render(c), '')

        # Double-check that the object was really never called during the
        # template rendering.
        self.assertEqual(my_doodad.num_calls, 0)

    def test_choices_enum_in_templates(self):
        # Test that enumeration types (Choices classes) can be used in templates
        # without being called.
        class YearInSchool(models.TextChoices):
            FRESHMAN = 'FR', 'Freshman'
            SOPHOMORE = 'SO', 'Sophomore'
            JUNIOR = 'JR', 'Junior'
            SENIOR = 'SR', 'Senior'

        class Student:
            def __init__(self, year_in_school):
                self.year_in_school = year_in_school

        student = Student(YearInSchool.FRESHMAN)
        c = Context({'student': student, 'YearInSchool': YearInSchool})

        # Test comparison with enum member in template
        t = self.engine.from_string('{% if student.year_in_school == YearInSchool.FRESHMAN %}freshman{% endif %}')
        self.assertEqual(t.render(c), 'freshman')

        # Test that accessing enum class attributes works
        t = self.engine.from_string('{{ YearInSchool.FRESHMAN }}')
        self.assertEqual(t.render(c), 'FR')

        # Test with different year
        student.year_in_school = YearInSchool.SENIOR
        t = self.engine.from_string('{% if student.year_in_school == YearInSchool.SENIOR %}senior{% endif %}')
        self.assertEqual(t.render(c), 'senior')

        # Test that comparison with wrong enum member returns empty
        t = self.engine.from_string('{% if student.year_in_school == YearInSchool.FRESHMAN %}freshman{% endif %}')
        self.assertEqual(t.render(c), '')

    def test_integerchoices_enum_in_templates(self):
        # Test that IntegerChoices also work in templates
        class Priority(models.IntegerChoices):
            LOW = 1, 'Low'
            MEDIUM = 2, 'Medium'
            HIGH = 3, 'High'

        class Task:
            def __init__(self, priority):
                self.priority = priority

        task = Task(Priority.HIGH)
        c = Context({'task': task, 'Priority': Priority})

        # Test comparison with enum member in template
        t = self.engine.from_string('{% if task.priority == Priority.HIGH %}high priority{% endif %}')
        self.assertEqual(t.render(c), 'high priority')

        # Test that accessing enum class attributes works
        t = self.engine.from_string('{{ Priority.HIGH }}')
        self.assertEqual(t.render(c), '3')

        # Test that enum members are accessible
        t = self.engine.from_string('{{ Priority.LOW.value }}')
        self.assertEqual(t.render(c), '1')
