from unittest import TestCase

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
