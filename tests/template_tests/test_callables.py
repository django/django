from unittest import TestCase

from django.db.models.utils import AltersData
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
        t = self.engine.from_string("{{ my_doodad.value }}")
        self.assertEqual(t.render(c), "")

        # We can confirm that the doodad has been called
        self.assertEqual(my_doodad.num_calls, 1)

        # But we can access keys on the dict that's returned
        # by ``__call__``, instead.
        t = self.engine.from_string("{{ my_doodad.the_value }}")
        self.assertEqual(t.render(c), "42")
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
        t = self.engine.from_string("{{ my_doodad.value }}")
        self.assertEqual(t.render(c), "")
        t = self.engine.from_string("{{ my_doodad.the_value }}")
        self.assertEqual(t.render(c), "")

        # Double-check that the object was really never called during the
        # template rendering.
        self.assertEqual(my_doodad.num_calls, 0)

    def test_alters_data_propagation(self):
        class GrandParentLeft(AltersData):
            def my_method(self):
                return 42

            my_method.alters_data = True

        class ParentLeft(GrandParentLeft):
            def change_alters_data_method(self):
                return 63

            change_alters_data_method.alters_data = True

            def sub_non_callable_method(self):
                return 64

            sub_non_callable_method.alters_data = True

        class ParentRight(AltersData):
            def other_method(self):
                return 52

            other_method.alters_data = True

        class Child(ParentLeft, ParentRight):
            def my_method(self):
                return 101

            def other_method(self):
                return 102

            def change_alters_data_method(self):
                return 103

            change_alters_data_method.alters_data = False

            sub_non_callable_method = 104

        class GrandChild(Child):
            pass

        child = Child()
        self.assertIs(child.my_method.alters_data, True)
        self.assertIs(child.other_method.alters_data, True)
        self.assertIs(child.change_alters_data_method.alters_data, False)

        grand_child = GrandChild()
        self.assertIs(grand_child.my_method.alters_data, True)
        self.assertIs(grand_child.other_method.alters_data, True)
        self.assertIs(grand_child.change_alters_data_method.alters_data, False)

        c = Context({"element": grand_child})

        t = self.engine.from_string("{{ element.my_method }}")
        self.assertEqual(t.render(c), "")
        t = self.engine.from_string("{{ element.other_method }}")
        self.assertEqual(t.render(c), "")
        t = self.engine.from_string("{{ element.change_alters_data_method }}")
        self.assertEqual(t.render(c), "103")
        t = self.engine.from_string("{{ element.sub_non_callable_method }}")
        self.assertEqual(t.render(c), "104")

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
        t = self.engine.from_string("{{ my_doodad.value }}")
        self.assertEqual(t.render(c), "42")
        t = self.engine.from_string("{{ my_doodad.the_value }}")
        self.assertEqual(t.render(c), "")

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

        t = self.engine.from_string("{{ my_doodad.value }}")
        self.assertEqual(t.render(c), "42")
        t = self.engine.from_string("{{ my_doodad.the_value }}")
        self.assertEqual(t.render(c), "")

        # Double-check that the object was really never called during the
        # template rendering.
        self.assertEqual(my_doodad.num_calls, 0)
