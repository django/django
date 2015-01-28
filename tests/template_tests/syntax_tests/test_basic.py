from django.template.base import Context, TemplateSyntaxError
from django.test import SimpleTestCase

from ..utils import SilentAttrClass, SilentGetItemClass, SomeClass, setup

basic_templates = {
    'basic-syntax01': 'something cool',
    'basic-syntax02': '{{ headline }}',
    'basic-syntax03': '{{ first }} --- {{ second }}',
}


class BasicSyntaxTests(SimpleTestCase):

    @setup(basic_templates)
    def test_basic_syntax01(self):
        """
        Plain text should go through the template parser untouched.
        """
        output = self.engine.render_to_string('basic-syntax01')
        self.assertEqual(output, "something cool")

    @setup(basic_templates)
    def test_basic_syntax02(self):
        """
        Variables should be replaced with their value in the current
        context
        """
        output = self.engine.render_to_string('basic-syntax02', {'headline': 'Success'})
        self.assertEqual(output, 'Success')

    @setup(basic_templates)
    def test_basic_syntax03(self):
        """
        More than one replacement variable is allowed in a template
        """
        output = self.engine.render_to_string('basic-syntax03', {"first": 1, "second": 2})
        self.assertEqual(output, '1 --- 2')

    @setup({'basic-syntax04': 'as{{ missing }}df'})
    def test_basic_syntax04(self):
        """
        Fail silently when a variable is not found in the current context
        """
        output = self.engine.render_to_string('basic-syntax04')
        if self.engine.string_if_invalid:
            self.assertEqual(output, 'asINVALIDdf')
        else:
            self.assertEqual(output, 'asdf')

    @setup({'basic-syntax06': '{{ multi word variable }}'})
    def test_basic_syntax06(self):
        """
        A variable may not contain more than one word
        """
        with self.assertRaises(TemplateSyntaxError):
            self.engine.get_template('basic-syntax06')

    @setup({'basic-syntax07': '{{ }}'})
    def test_basic_syntax07(self):
        """
        Raise TemplateSyntaxError for empty variable tags.
        """
        with self.assertRaises(TemplateSyntaxError):
            self.engine.get_template('basic-syntax07')

    @setup({'basic-syntax08': '{{        }}'})
    def test_basic_syntax08(self):
        """
        Raise TemplateSyntaxError for empty variable tags.
        """
        with self.assertRaises(TemplateSyntaxError):
            self.engine.get_template('basic-syntax08')

    @setup({'basic-syntax09': '{{ var.method }}'})
    def test_basic_syntax09(self):
        """
        Attribute syntax allows a template to call an object's attribute
        """
        output = self.engine.render_to_string('basic-syntax09', {'var': SomeClass()})
        self.assertEqual(output, 'SomeClass.method')

    @setup({'basic-syntax10': '{{ var.otherclass.method }}'})
    def test_basic_syntax10(self):
        """
        Multiple levels of attribute access are allowed.
        """
        output = self.engine.render_to_string('basic-syntax10', {'var': SomeClass()})
        self.assertEqual(output, 'OtherClass.method')

    @setup({'basic-syntax11': '{{ var.blech }}'})
    def test_basic_syntax11(self):
        """
        Fail silently when a variable's attribute isn't found.
        """
        output = self.engine.render_to_string('basic-syntax11', {'var': SomeClass()})

        if self.engine.string_if_invalid:
            self.assertEqual(output, 'INVALID')
        else:
            self.assertEqual(output, '')

    @setup({'basic-syntax12': '{{ var.__dict__ }}'})
    def test_basic_syntax12(self):
        """
        Raise TemplateSyntaxError when trying to access a variable
        beginning with an underscore.
        """
        with self.assertRaises(TemplateSyntaxError):
            self.engine.get_template('basic-syntax12')

    # Raise TemplateSyntaxError when trying to access a variable
    # containing an illegal character.
    @setup({'basic-syntax13': "{{ va>r }}"})
    def test_basic_syntax13(self):
        with self.assertRaises(TemplateSyntaxError):
            self.engine.get_template('basic-syntax13')

    @setup({'basic-syntax14': "{{ (var.r) }}"})
    def test_basic_syntax14(self):
        with self.assertRaises(TemplateSyntaxError):
            self.engine.get_template('basic-syntax14')

    @setup({'basic-syntax15': "{{ sp%am }}"})
    def test_basic_syntax15(self):
        with self.assertRaises(TemplateSyntaxError):
            self.engine.get_template('basic-syntax15')

    @setup({'basic-syntax16': "{{ eggs! }}"})
    def test_basic_syntax16(self):
        with self.assertRaises(TemplateSyntaxError):
            self.engine.get_template('basic-syntax16')

    @setup({'basic-syntax17': "{{ moo? }}"})
    def test_basic_syntax17(self):
        with self.assertRaises(TemplateSyntaxError):
            self.engine.get_template('basic-syntax17')

    @setup({'basic-syntax18': "{{ foo.bar }}"})
    def test_basic_syntax18(self):
        """
        Attribute syntax allows a template to call a dictionary key's
        value.
        """
        output = self.engine.render_to_string('basic-syntax18', {"foo": {"bar": "baz"}})
        self.assertEqual(output, "baz")

    @setup({'basic-syntax19': "{{ foo.spam }}"})
    def test_basic_syntax19(self):
        """
        Fail silently when a variable's dictionary key isn't found.
        """
        output = self.engine.render_to_string('basic-syntax19', {"foo": {"bar": "baz"}})

        if self.engine.string_if_invalid:
            self.assertEqual(output, 'INVALID')
        else:
            self.assertEqual(output, '')

    @setup({'basic-syntax20': "{{ var.method2 }}"})
    def test_basic_syntax20(self):
        """
        Fail silently when accessing a non-simple method
        """
        output = self.engine.render_to_string('basic-syntax20', {'var': SomeClass()})

        if self.engine.string_if_invalid:
            self.assertEqual(output, 'INVALID')
        else:
            self.assertEqual(output, '')

    @setup({'basic-syntax20b': "{{ var.method5 }}"})
    def test_basic_syntax20b(self):
        """
        Don't silence a TypeError if it was raised inside a callable.
        """
        template = self.engine.get_template('basic-syntax20b')

        with self.assertRaises(TypeError):
            template.render(Context({'var': SomeClass()}))

    # Don't get confused when parsing something that is almost, but not
    # quite, a template tag.
    @setup({'basic-syntax21': "a {{ moo %} b"})
    def test_basic_syntax21(self):
        output = self.engine.render_to_string('basic-syntax21')
        self.assertEqual(output, "a {{ moo %} b")

    @setup({'basic-syntax22': "{{ moo #}"})
    def test_basic_syntax22(self):
        output = self.engine.render_to_string('basic-syntax22')
        self.assertEqual(output, "{{ moo #}")

    @setup({'basic-syntax23': "{{ moo #} {{ cow }}"})
    def test_basic_syntax23(self):
        """
        Treat "moo #} {{ cow" as the variable. Not ideal, but costly to work
        around, so this triggers an error.
        """
        with self.assertRaises(TemplateSyntaxError):
            self.engine.get_template('basic-syntax23')

    @setup({'basic-syntax24': "{{ moo\n }}"})
    def test_basic_syntax24(self):
        """
        Embedded newlines make it not-a-tag.
        """
        output = self.engine.render_to_string('basic-syntax24')
        self.assertEqual(output, "{{ moo\n }}")

    # Literal strings are permitted inside variables, mostly for i18n
    # purposes.
    @setup({'basic-syntax25': '{{ "fred" }}'})
    def test_basic_syntax25(self):
        output = self.engine.render_to_string('basic-syntax25')
        self.assertEqual(output, "fred")

    @setup({'basic-syntax26': r'{{ "\"fred\"" }}'})
    def test_basic_syntax26(self):
        output = self.engine.render_to_string('basic-syntax26')
        self.assertEqual(output, "\"fred\"")

    @setup({'basic-syntax27': r'{{ _("\"fred\"") }}'})
    def test_basic_syntax27(self):
        output = self.engine.render_to_string('basic-syntax27')
        self.assertEqual(output, "\"fred\"")

    # #12554 -- Make sure a silent_variable_failure Exception is
    # suppressed on dictionary and attribute lookup.
    @setup({'basic-syntax28': "{{ a.b }}"})
    def test_basic_syntax28(self):
        output = self.engine.render_to_string('basic-syntax28', {'a': SilentGetItemClass()})
        if self.engine.string_if_invalid:
            self.assertEqual(output, 'INVALID')
        else:
            self.assertEqual(output, '')

    @setup({'basic-syntax29': "{{ a.b }}"})
    def test_basic_syntax29(self):
        output = self.engine.render_to_string('basic-syntax29', {'a': SilentAttrClass()})
        if self.engine.string_if_invalid:
            self.assertEqual(output, 'INVALID')
        else:
            self.assertEqual(output, '')

    # Something that starts like a number but has an extra lookup works
    # as a lookup.
    @setup({'basic-syntax30': "{{ 1.2.3 }}"})
    def test_basic_syntax30(self):
        output = self.engine.render_to_string(
            'basic-syntax30',
            {"1": {"2": {"3": "d"}}}
        )
        self.assertEqual(output, 'd')

    @setup({'basic-syntax31': "{{ 1.2.3 }}"})
    def test_basic_syntax31(self):
        output = self.engine.render_to_string(
            'basic-syntax31',
            {"1": {"2": ("a", "b", "c", "d")}},
        )
        self.assertEqual(output, 'd')

    @setup({'basic-syntax32': "{{ 1.2.3 }}"})
    def test_basic_syntax32(self):
        output = self.engine.render_to_string(
            'basic-syntax32',
            {"1": (("x", "x", "x", "x"), ("y", "y", "y", "y"), ("a", "b", "c", "d"))},
        )
        self.assertEqual(output, 'd')

    @setup({'basic-syntax33': "{{ 1.2.3 }}"})
    def test_basic_syntax33(self):
        output = self.engine.render_to_string(
            'basic-syntax33',
            {"1": ("xxxx", "yyyy", "abcd")},
        )
        self.assertEqual(output, 'd')

    @setup({'basic-syntax34': "{{ 1.2.3 }}"})
    def test_basic_syntax34(self):
        output = self.engine.render_to_string(
            'basic-syntax34',
            {"1": ({"x": "x"}, {"y": "y"}, {"z": "z", "3": "d"})}
        )
        self.assertEqual(output, 'd')

    # Numbers are numbers even if their digits are in the context.
    @setup({'basic-syntax35': "{{ 1 }}"})
    def test_basic_syntax35(self):
        output = self.engine.render_to_string('basic-syntax35', {"1": "abc"})
        self.assertEqual(output, '1')

    @setup({'basic-syntax36': "{{ 1.2 }}"})
    def test_basic_syntax36(self):
        output = self.engine.render_to_string('basic-syntax36', {"1": "abc"})
        self.assertEqual(output, '1.2')

    @setup({'basic-syntax37': '{{ callable }}'})
    def test_basic_syntax37(self):
        """
        Call methods in the top level of the context.
        """
        output = self.engine.render_to_string('basic-syntax37', {"callable": lambda: "foo bar"})
        self.assertEqual(output, 'foo bar')

    @setup({'basic-syntax38': '{{ var.callable }}'})
    def test_basic_syntax38(self):
        """
        Call methods returned from dictionary lookups.
        """
        output = self.engine.render_to_string('basic-syntax38', {"var": {"callable": lambda: "foo bar"}})
        self.assertEqual(output, 'foo bar')
