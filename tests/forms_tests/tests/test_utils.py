import copy
import json

from django.core.exceptions import ValidationError
from django.forms.renderers import DjangoTemplates
from django.forms.utils import (
    ErrorDict,
    ErrorList,
    RenderableFieldMixin,
    RenderableMixin,
    flatatt,
    pretty_name,
)
from django.test import SimpleTestCase
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy


class FormsUtilsTestCase(SimpleTestCase):
    # Tests for forms/utils.py module.

    def test_flatatt(self):
        ###########
        # flatatt #
        ###########

        self.assertEqual(flatatt({"id": "header"}), ' id="header"')
        self.assertEqual(
            flatatt({"class": "news", "title": "Read this"}),
            ' class="news" title="Read this"',
        )
        self.assertEqual(
            flatatt({"class": "news", "title": "Read this", "required": "required"}),
            ' class="news" required="required" title="Read this"',
        )
        self.assertEqual(
            flatatt({"class": "news", "title": "Read this", "required": True}),
            ' class="news" title="Read this" required',
        )
        self.assertEqual(
            flatatt({"class": "news", "title": "Read this", "required": False}),
            ' class="news" title="Read this"',
        )
        self.assertEqual(flatatt({"class": None}), "")
        self.assertEqual(flatatt({}), "")

    def test_flatatt_no_side_effects(self):
        """
        flatatt() does not modify the dict passed in.
        """
        attrs = {"foo": "bar", "true": True, "false": False}
        attrs_copy = copy.copy(attrs)
        self.assertEqual(attrs, attrs_copy)

        first_run = flatatt(attrs)
        self.assertEqual(attrs, attrs_copy)
        self.assertEqual(first_run, ' foo="bar" true')

        second_run = flatatt(attrs)
        self.assertEqual(attrs, attrs_copy)

        self.assertEqual(first_run, second_run)

    def test_validation_error(self):
        ###################
        # ValidationError #
        ###################

        # Can take a string.
        self.assertHTMLEqual(
            str(ErrorList(ValidationError("There was an error.").messages)),
            '<ul class="errorlist"><li>There was an error.</li></ul>',
        )
        # Can take a Unicode string.
        self.assertHTMLEqual(
            str(ErrorList(ValidationError("Not \u03c0.").messages)),
            '<ul class="errorlist"><li>Not π.</li></ul>',
        )
        # Can take a lazy string.
        self.assertHTMLEqual(
            str(ErrorList(ValidationError(gettext_lazy("Error.")).messages)),
            '<ul class="errorlist"><li>Error.</li></ul>',
        )
        # Can take a list.
        self.assertHTMLEqual(
            str(ErrorList(ValidationError(["Error one.", "Error two."]).messages)),
            '<ul class="errorlist"><li>Error one.</li><li>Error two.</li></ul>',
        )
        # Can take a dict.
        self.assertHTMLEqual(
            str(
                ErrorList(
                    sorted(
                        ValidationError(
                            {"error_1": "1. Error one.", "error_2": "2. Error two."}
                        ).messages
                    )
                )
            ),
            '<ul class="errorlist"><li>1. Error one.</li><li>2. Error two.</li></ul>',
        )
        # Can take a mixture in a list.
        self.assertHTMLEqual(
            str(
                ErrorList(
                    sorted(
                        ValidationError(
                            [
                                "1. First error.",
                                "2. Not \u03c0.",
                                gettext_lazy("3. Error."),
                                {
                                    "error_1": "4. First dict error.",
                                    "error_2": "5. Second dict error.",
                                },
                            ]
                        ).messages
                    )
                )
            ),
            '<ul class="errorlist">'
            "<li>1. First error.</li>"
            "<li>2. Not π.</li>"
            "<li>3. Error.</li>"
            "<li>4. First dict error.</li>"
            "<li>5. Second dict error.</li>"
            "</ul>",
        )

        class VeryBadError:
            def __str__(self):
                return "A very bad error."

        # Can take a non-string.
        self.assertHTMLEqual(
            str(ErrorList(ValidationError(VeryBadError()).messages)),
            '<ul class="errorlist"><li>A very bad error.</li></ul>',
        )

        # Escapes non-safe input but not input marked safe.
        example = 'Example of link: <a href="http://www.example.com/">example</a>'
        self.assertHTMLEqual(
            str(ErrorList([example])),
            '<ul class="errorlist"><li>Example of link: '
            "&lt;a href=&quot;http://www.example.com/&quot;&gt;example&lt;/a&gt;"
            "</li></ul>",
        )
        self.assertHTMLEqual(
            str(ErrorList([mark_safe(example)])),
            '<ul class="errorlist"><li>Example of link: '
            '<a href="http://www.example.com/">example</a></li></ul>',
        )
        self.assertHTMLEqual(
            str(ErrorDict({"name": example})),
            '<ul class="errorlist"><li>nameExample of link: '
            "&lt;a href=&quot;http://www.example.com/&quot;&gt;example&lt;/a&gt;"
            "</li></ul>",
        )
        self.assertHTMLEqual(
            str(ErrorDict({"name": mark_safe(example)})),
            '<ul class="errorlist"><li>nameExample of link: '
            '<a href="http://www.example.com/">example</a></li></ul>',
        )

    def test_error_list_copy(self):
        e = ErrorList(
            [
                ValidationError(
                    message="message %(i)s",
                    params={"i": 1},
                ),
                ValidationError(
                    message="message %(i)s",
                    params={"i": 2},
                ),
            ]
        )

        e_copy = copy.copy(e)
        self.assertEqual(e, e_copy)
        self.assertEqual(e.as_data(), e_copy.as_data())

    def test_error_list_copy_attributes(self):
        class CustomRenderer(DjangoTemplates):
            pass

        renderer = CustomRenderer()
        e = ErrorList(error_class="woopsies", renderer=renderer)

        e_copy = e.copy()
        self.assertEqual(e.error_class, e_copy.error_class)
        self.assertEqual(e.renderer, e_copy.renderer)

    def test_error_dict_copy(self):
        e = ErrorDict()
        e["__all__"] = ErrorList(
            [
                ValidationError(
                    message="message %(i)s",
                    params={"i": 1},
                ),
                ValidationError(
                    message="message %(i)s",
                    params={"i": 2},
                ),
            ]
        )

        e_copy = copy.copy(e)
        self.assertEqual(e, e_copy)
        self.assertEqual(e.as_data(), e_copy.as_data())

        e_deepcopy = copy.deepcopy(e)
        self.assertEqual(e, e_deepcopy)

    def test_error_dict_copy_attributes(self):
        class CustomRenderer(DjangoTemplates):
            pass

        renderer = CustomRenderer()
        e = ErrorDict(renderer=renderer)

        e_copy = copy.copy(e)
        self.assertEqual(e.renderer, e_copy.renderer)

    def test_error_dict_html_safe(self):
        e = ErrorDict()
        e["username"] = "Invalid username."
        self.assertTrue(hasattr(ErrorDict, "__html__"))
        self.assertEqual(str(e), e.__html__())

    def test_error_list_html_safe(self):
        e = ErrorList(["Invalid username."])
        self.assertTrue(hasattr(ErrorList, "__html__"))
        self.assertEqual(str(e), e.__html__())

    def test_error_dict_is_dict(self):
        self.assertIsInstance(ErrorDict(), dict)

    def test_error_dict_is_json_serializable(self):
        init_errors = ErrorDict(
            [
                (
                    "__all__",
                    ErrorList(
                        [ValidationError("Sorry this form only works on leap days.")]
                    ),
                ),
                ("name", ErrorList([ValidationError("This field is required.")])),
            ]
        )
        min_value_error_list = ErrorList(
            [ValidationError("Ensure this value is greater than or equal to 0.")]
        )
        e = ErrorDict(
            init_errors,
            date=ErrorList(
                [
                    ErrorDict(
                        {
                            "day": min_value_error_list,
                            "month": min_value_error_list,
                            "year": min_value_error_list,
                        }
                    ),
                ]
            ),
        )
        e["renderer"] = ErrorList(
            [
                ValidationError(
                    "Select a valid choice. That choice is not one of the "
                    "available choices."
                ),
            ]
        )
        self.assertJSONEqual(
            json.dumps(e),
            {
                "__all__": ["Sorry this form only works on leap days."],
                "name": ["This field is required."],
                "date": [
                    {
                        "day": ["Ensure this value is greater than or equal to 0."],
                        "month": ["Ensure this value is greater than or equal to 0."],
                        "year": ["Ensure this value is greater than or equal to 0."],
                    },
                ],
                "renderer": [
                    "Select a valid choice. That choice is not one of the "
                    "available choices."
                ],
            },
        )

    def test_get_context_must_be_implemented(self):
        mixin = RenderableMixin()
        msg = "Subclasses of RenderableMixin must provide a get_context() method."
        with self.assertRaisesMessage(NotImplementedError, msg):
            mixin.get_context()

    def test_field_mixin_as_hidden_must_be_implemented(self):
        mixin = RenderableFieldMixin()
        msg = "Subclasses of RenderableFieldMixin must provide an as_hidden() method."
        with self.assertRaisesMessage(NotImplementedError, msg):
            mixin.as_hidden()

    def test_field_mixin_as_widget_must_be_implemented(self):
        mixin = RenderableFieldMixin()
        msg = "Subclasses of RenderableFieldMixin must provide an as_widget() method."
        with self.assertRaisesMessage(NotImplementedError, msg):
            mixin.as_widget()

    def test_pretty_name(self):
        self.assertEqual(pretty_name("john_doe"), "John doe")
        self.assertEqual(pretty_name(None), "")
        self.assertEqual(pretty_name(""), "")
