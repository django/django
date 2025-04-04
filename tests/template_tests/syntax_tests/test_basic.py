from django.template.base import TemplateSyntaxError
from django.template.context import Context
from django.template.loader_tags import BlockContext, BlockNode
from django.test import SimpleTestCase

from ..utils import SilentAttrClass, SilentGetItemClass, SomeClass, setup

basic_templates = {
    "basic-syntax01": "something cool",
    "basic-syntax02": "{{ headline }}",
    "basic-syntax03": "{{ first }} --- {{ second }}",
}


class BasicSyntaxTests(SimpleTestCase):
    @setup(basic_templates)
    def test_basic_syntax01(self):
        """
        Plain text should go through the template parser untouched.
        """
        output = self.engine.render_to_string("basic-syntax01")
        self.assertEqual(output, "something cool")

    @setup(basic_templates)
    def test_basic_syntax02(self):
        """
        Variables should be replaced with their value in the current
        context
        """
        output = self.engine.render_to_string("basic-syntax02", {"headline": "Success"})
        self.assertEqual(output, "Success")

    @setup(basic_templates)
    def test_basic_syntax03(self):
        """
        More than one replacement variable is allowed in a template
        """
        output = self.engine.render_to_string(
            "basic-syntax03", {"first": 1, "second": 2}
        )
        self.assertEqual(output, "1 --- 2")

    @setup({"basic-syntax04": "as{{ missing }}df"})
    def test_basic_syntax04(self):
        """
        Fail silently when a variable is not found in the current context
        """
        output = self.engine.render_to_string("basic-syntax04")
        if self.engine.string_if_invalid:
            self.assertEqual(output, "asINVALIDdf")
        else:
            self.assertEqual(output, "asdf")

    @setup({"basic-syntax06": "{{ multi word variable }}"})
    def test_basic_syntax06(self):
        """
        A variable may not contain more than one word
        """
        with self.assertRaises(TemplateSyntaxError):
            self.engine.get_template("basic-syntax06")

    @setup({"basic-syntax07": "{{ }}"})
    def test_basic_syntax07(self):
        """
        Raise TemplateSyntaxError for empty variable tags.
        """
        with self.assertRaisesMessage(
            TemplateSyntaxError, "Empty variable tag on line 1"
        ):
            self.engine.get_template("basic-syntax07")

    @setup({"basic-syntax08": "{{        }}"})
    def test_basic_syntax08(self):
        """
        Raise TemplateSyntaxError for empty variable tags.
        """
        with self.assertRaisesMessage(
            TemplateSyntaxError, "Empty variable tag on line 1"
        ):
            self.engine.get_template("basic-syntax08")

    @setup({"basic-syntax09": "{{ var.method }}"})
    def test_basic_syntax09(self):
        """
        Attribute syntax allows a template to call an object's attribute
        """
        output = self.engine.render_to_string("basic-syntax09", {"var": SomeClass()})
        self.assertEqual(output, "SomeClass.method")

    @setup({"basic-syntax10": "{{ var.otherclass.method }}"})
    def test_basic_syntax10(self):
        """
        Multiple levels of attribute access are allowed.
        """
        output = self.engine.render_to_string("basic-syntax10", {"var": SomeClass()})
        self.assertEqual(output, "OtherClass.method")

    @setup({"basic-syntax11": "{{ var.blech }}"})
    def test_basic_syntax11(self):
        """
        Fail silently when a variable's attribute isn't found.
        """
        output = self.engine.render_to_string("basic-syntax11", {"var": SomeClass()})

        if self.engine.string_if_invalid:
            self.assertEqual(output, "INVALID")
        else:
            self.assertEqual(output, "")

    @setup({"basic-syntax12": "{{ var.__dict__ }}"})
    def test_basic_syntax12(self):
        """
        Raise TemplateSyntaxError when trying to access a variable
        beginning with an underscore.
        """
        with self.assertRaises(TemplateSyntaxError):
            self.engine.get_template("basic-syntax12")

    # Raise TemplateSyntaxError when trying to access a variable
    # containing an illegal character.
    @setup({"basic-syntax13": "{{ va>r }}"})
    def test_basic_syntax13(self):
        with self.assertRaises(TemplateSyntaxError):
            self.engine.get_template("basic-syntax13")

    @setup({"basic-syntax14": "{{ (var.r) }}"})
    def test_basic_syntax14(self):
        with self.assertRaises(TemplateSyntaxError):
            self.engine.get_template("basic-syntax14")

    @setup({"basic-syntax15": "{{ sp%am }}"})
    def test_basic_syntax15(self):
        with self.assertRaises(TemplateSyntaxError):
            self.engine.get_template("basic-syntax15")

    @setup({"basic-syntax16": "{{ eggs! }}"})
    def test_basic_syntax16(self):
        with self.assertRaises(TemplateSyntaxError):
            self.engine.get_template("basic-syntax16")

    @setup({"basic-syntax17": "{{ moo? }}"})
    def test_basic_syntax17(self):
        with self.assertRaises(TemplateSyntaxError):
            self.engine.get_template("basic-syntax17")

    @setup({"basic-syntax18": "{{ foo.bar }}"})
    def test_basic_syntax18(self):
        """
        Attribute syntax allows a template to call a dictionary key's
        value.
        """
        output = self.engine.render_to_string("basic-syntax18", {"foo": {"bar": "baz"}})
        self.assertEqual(output, "baz")

    @setup({"basic-syntax19": "{{ foo.spam }}"})
    def test_basic_syntax19(self):
        """
        Fail silently when a variable's dictionary key isn't found.
        """
        output = self.engine.render_to_string("basic-syntax19", {"foo": {"bar": "baz"}})

        if self.engine.string_if_invalid:
            self.assertEqual(output, "INVALID")
        else:
            self.assertEqual(output, "")

    @setup({"basic-syntax20": "{{ var.method2 }}"})
    def test_basic_syntax20(self):
        """
        Fail silently when accessing a non-simple method
        """
        output = self.engine.render_to_string("basic-syntax20", {"var": SomeClass()})

        if self.engine.string_if_invalid:
            self.assertEqual(output, "INVALID")
        else:
            self.assertEqual(output, "")

    @setup({"basic-syntax20b": "{{ var.method5 }}"})
    def test_basic_syntax20b(self):
        """
        Don't silence a TypeError if it was raised inside a callable.
        """
        template = self.engine.get_template("basic-syntax20b")

        with self.assertRaises(TypeError):
            template.render(Context({"var": SomeClass()}))

    # Don't get confused when parsing something that is almost, but not
    # quite, a template tag.
    @setup({"basic-syntax21": "a {{ moo %} b"})
    def test_basic_syntax21(self):
        output = self.engine.render_to_string("basic-syntax21")
        self.assertEqual(output, "a {{ moo %} b")

    @setup({"basic-syntax22": "{{ moo #}"})
    def test_basic_syntax22(self):
        output = self.engine.render_to_string("basic-syntax22")
        self.assertEqual(output, "{{ moo #}")

    @setup({"basic-syntax23": "{{ moo #} {{ cow }}"})
    def test_basic_syntax23(self):
        """
        Treat "moo #} {{ cow" as the variable. Not ideal, but costly to work
        around, so this triggers an error.
        """
        with self.assertRaises(TemplateSyntaxError):
            self.engine.get_template("basic-syntax23")

    @setup({"basic-syntax24": "{{ moo\n }}"})
    def test_basic_syntax24(self):
        """
        Embedded newlines make it not-a-tag.
        """
        output = self.engine.render_to_string("basic-syntax24")
        self.assertEqual(output, "{{ moo\n }}")

    # Literal strings are permitted inside variables, mostly for i18n
    # purposes.
    @setup({"basic-syntax25": '{{ "fred" }}'})
    def test_basic_syntax25(self):
        output = self.engine.render_to_string("basic-syntax25")
        self.assertEqual(output, "fred")

    @setup({"basic-syntax26": r'{{ "\"fred\"" }}'})
    def test_basic_syntax26(self):
        output = self.engine.render_to_string("basic-syntax26")
        self.assertEqual(output, '"fred"')

    @setup({"basic-syntax27": r'{{ _("\"fred\"") }}'})
    def test_basic_syntax27(self):
        output = self.engine.render_to_string("basic-syntax27")
        self.assertEqual(output, '"fred"')

    # #12554 -- Make sure a silent_variable_failure Exception is
    # suppressed on dictionary and attribute lookup.
    @setup({"basic-syntax28": "{{ a.b }}"})
    def test_basic_syntax28(self):
        output = self.engine.render_to_string(
            "basic-syntax28", {"a": SilentGetItemClass()}
        )
        if self.engine.string_if_invalid:
            self.assertEqual(output, "INVALID")
        else:
            self.assertEqual(output, "")

    @setup({"basic-syntax29": "{{ a.b }}"})
    def test_basic_syntax29(self):
        output = self.engine.render_to_string(
            "basic-syntax29", {"a": SilentAttrClass()}
        )
        if self.engine.string_if_invalid:
            self.assertEqual(output, "INVALID")
        else:
            self.assertEqual(output, "")

    # Something that starts like a number but has an extra lookup works
    # as a lookup.
    @setup({"basic-syntax30": "{{ 1.2.3 }}"})
    def test_basic_syntax30(self):
        output = self.engine.render_to_string(
            "basic-syntax30", {"1": {"2": {"3": "d"}}}
        )
        self.assertEqual(output, "d")

    @setup({"basic-syntax31": "{{ 1.2.3 }}"})
    def test_basic_syntax31(self):
        output = self.engine.render_to_string(
            "basic-syntax31",
            {"1": {"2": ("a", "b", "c", "d")}},
        )
        self.assertEqual(output, "d")

    @setup({"basic-syntax32": "{{ 1.2.3 }}"})
    def test_basic_syntax32(self):
        output = self.engine.render_to_string(
            "basic-syntax32",
            {"1": (("x", "x", "x", "x"), ("y", "y", "y", "y"), ("a", "b", "c", "d"))},
        )
        self.assertEqual(output, "d")

    @setup({"basic-syntax33": "{{ 1.2.3 }}"})
    def test_basic_syntax33(self):
        output = self.engine.render_to_string(
            "basic-syntax33",
            {"1": ("xxxx", "yyyy", "abcd")},
        )
        self.assertEqual(output, "d")

    @setup({"basic-syntax34": "{{ 1.2.3 }}"})
    def test_basic_syntax34(self):
        output = self.engine.render_to_string(
            "basic-syntax34", {"1": ({"x": "x"}, {"y": "y"}, {"z": "z", "3": "d"})}
        )
        self.assertEqual(output, "d")

    # Numbers are numbers even if their digits are in the context.
    @setup({"basic-syntax35": "{{ 1 }}"})
    def test_basic_syntax35(self):
        output = self.engine.render_to_string("basic-syntax35", {"1": "abc"})
        self.assertEqual(output, "1")

    @setup({"basic-syntax36": "{{ 1.2 }}"})
    def test_basic_syntax36(self):
        output = self.engine.render_to_string("basic-syntax36", {"1": "abc"})
        self.assertEqual(output, "1.2")

    @setup({"basic-syntax37": "{{ callable }}"})
    def test_basic_syntax37(self):
        """
        Call methods in the top level of the context.
        """
        output = self.engine.render_to_string(
            "basic-syntax37", {"callable": lambda: "foo bar"}
        )
        self.assertEqual(output, "foo bar")

    @setup({"basic-syntax38": "{{ var.callable }}"})
    def test_basic_syntax38(self):
        """
        Call methods returned from dictionary lookups.
        """
        output = self.engine.render_to_string(
            "basic-syntax38", {"var": {"callable": lambda: "foo bar"}}
        )
        self.assertEqual(output, "foo bar")

    @setup({"template": "{% block content %}"})
    def test_unclosed_block(self):
        msg = "Unclosed tag on line 1: 'block'. Looking for one of: endblock."
        with self.assertRaisesMessage(TemplateSyntaxError, msg):
            self.engine.render_to_string("template")

    @setup({"template": "{% if a %}"})
    def test_unclosed_block2(self):
        msg = "Unclosed tag on line 1: 'if'. Looking for one of: elif, else, endif."
        with self.assertRaisesMessage(TemplateSyntaxError, msg):
            self.engine.render_to_string("template")

    @setup({"tpl-str": "%s", "tpl-percent": "%%", "tpl-weird-percent": "% %s"})
    def test_ignores_strings_that_look_like_format_interpolation(self):
        output = self.engine.render_to_string("tpl-str")
        self.assertEqual(output, "%s")
        output = self.engine.render_to_string("tpl-percent")
        self.assertEqual(output, "%%")
        output = self.engine.render_to_string("tpl-weird-percent")
        self.assertEqual(output, "% %s")

    @setup(
        {"template": "{{ class_var.class_property }} | {{ class_var.class_method }}"}
    )
    def test_subscriptable_class(self):
        class MyClass(list):
            # As of Python 3.9 list defines __class_getitem__ which makes it
            # subscriptable.
            class_property = "Example property"
            do_not_call_in_templates = True

            @classmethod
            def class_method(cls):
                return "Example method"

        for case in (MyClass, lambda: MyClass):
            with self.subTest(case=case):
                output = self.engine.render_to_string("template", {"class_var": case})
                self.assertEqual(output, "Example property | Example method")

    @setup({"template": "{{ meals.lunch }}"})
    def test_access_class_property_if_getitem_is_defined_in_metaclass(self):
        """
        If the metaclass defines __getitem__, the template system should use
        it to resolve the dot notation.
        """

        class MealMeta(type):
            def __getitem__(cls, name):
                return getattr(cls, name) + " is yummy."

        class Meals(metaclass=MealMeta):
            lunch = "soup"
            do_not_call_in_templates = True

            # Make class type subscriptable.
            def __class_getitem__(cls, key):
                from types import GenericAlias

                return GenericAlias(cls, key)

        self.assertEqual(Meals.lunch, "soup")
        self.assertEqual(Meals["lunch"], "soup is yummy.")

        output = self.engine.render_to_string("template", {"meals": Meals})
        self.assertEqual(output, "soup is yummy.")


class BlockContextTests(SimpleTestCase):
    def test_repr(self):
        block_context = BlockContext()
        block_context.add_blocks({"content": BlockNode("content", [])})
        self.assertEqual(
            repr(block_context),
            "<BlockContext: blocks=defaultdict(<class 'list'>, "
            "{'content': [<Block Node: content. Contents: []>]})>",
        )
