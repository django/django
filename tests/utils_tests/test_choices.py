import collections.abc
from unittest import mock

from django.db.models import TextChoices
from django.test import SimpleTestCase
from django.utils.choices import (
    BaseChoiceIterator,
    CallableChoiceIterator,
    flatten_choices,
    normalize_choices,
)
from django.utils.translation import gettext_lazy as _


class SimpleChoiceIterator(BaseChoiceIterator):
    def __iter__(self):
        return ((i, f"Item #{i}") for i in range(1, 4))


class ChoiceIteratorTests(SimpleTestCase):
    def test_not_implemented_error_on_missing_iter(self):
        class InvalidChoiceIterator(BaseChoiceIterator):
            pass  # Not overriding __iter__().

        msg = "BaseChoiceIterator subclasses must implement __iter__()."
        with self.assertRaisesMessage(NotImplementedError, msg):
            iter(InvalidChoiceIterator())

    def test_eq(self):
        unrolled = [(1, "Item #1"), (2, "Item #2"), (3, "Item #3")]
        self.assertEqual(SimpleChoiceIterator(), unrolled)
        self.assertEqual(unrolled, SimpleChoiceIterator())

    def test_eq_instances(self):
        self.assertEqual(SimpleChoiceIterator(), SimpleChoiceIterator())

    def test_not_equal_subset(self):
        self.assertNotEqual(SimpleChoiceIterator(), [(1, "Item #1"), (2, "Item #2")])

    def test_not_equal_superset(self):
        self.assertNotEqual(
            SimpleChoiceIterator(),
            [(1, "Item #1"), (2, "Item #2"), (3, "Item #3"), None],
        )

    def test_getitem(self):
        choices = SimpleChoiceIterator()
        for i, expected in [(0, (1, "Item #1")), (-1, (3, "Item #3"))]:
            with self.subTest(index=i):
                self.assertEqual(choices[i], expected)

    def test_getitem_indexerror(self):
        choices = SimpleChoiceIterator()
        for i in (4, -4):
            with self.subTest(index=i):
                with self.assertRaises(IndexError) as ctx:
                    choices[i]
                self.assertTrue(str(ctx.exception).endswith("index out of range"))


class FlattenChoicesTests(SimpleTestCase):
    def test_empty(self):
        def generator():
            yield from ()

        for choices in ({}, [], (), set(), frozenset(), generator(), None, ""):
            with self.subTest(choices=choices):
                result = flatten_choices(choices)
                self.assertIsInstance(result, collections.abc.Generator)
                self.assertEqual(list(result), [])

    def test_non_empty(self):
        choices = [
            ("C", _("Club")),
            ("D", _("Diamond")),
            ("H", _("Heart")),
            ("S", _("Spade")),
        ]
        result = flatten_choices(choices)
        self.assertIsInstance(result, collections.abc.Generator)
        self.assertEqual(list(result), choices)

    def test_nested_choices(self):
        choices = [
            ("Audio", [("vinyl", _("Vinyl")), ("cd", _("CD"))]),
            ("Video", [("vhs", _("VHS Tape")), ("dvd", _("DVD"))]),
            ("unknown", _("Unknown")),
        ]
        expected = [
            ("vinyl", _("Vinyl")),
            ("cd", _("CD")),
            ("vhs", _("VHS Tape")),
            ("dvd", _("DVD")),
            ("unknown", _("Unknown")),
        ]
        result = flatten_choices(choices)
        self.assertIsInstance(result, collections.abc.Generator)
        self.assertEqual(list(result), expected)


class NormalizeFieldChoicesTests(SimpleTestCase):
    expected = [
        ("C", _("Club")),
        ("D", _("Diamond")),
        ("H", _("Heart")),
        ("S", _("Spade")),
    ]
    expected_nested = [
        ("Audio", [("vinyl", _("Vinyl")), ("cd", _("CD"))]),
        ("Video", [("vhs", _("VHS Tape")), ("dvd", _("DVD"))]),
        ("unknown", _("Unknown")),
    ]
    invalid = [
        1j,
        123,
        123.45,
        "invalid",
        b"invalid",
        _("invalid"),
        object(),
        None,
        True,
        False,
    ]
    invalid_iterable = [
        # Special cases of a string-likes which would unpack incorrectly.
        ["ab"],
        [b"ab"],
        [_("ab")],
        # Non-iterable items or iterable items with incorrect number of
        # elements that cannot be unpacked.
        [123],
        [("value",)],
        [("value", "label", "other")],
    ]
    invalid_nested = [
        # Nested choices can only be two-levels deep, so return callables,
        # mappings, iterables, etc. at deeper levels unmodified.
        [("Group", [("Value", lambda: "Label")])],
        [("Group", [("Value", {"Label 1?": "Label 2?"})])],
        [("Group", [("Value", [("Label 1?", "Label 2?")])])],
    ]

    def test_empty(self):
        def generator():
            yield from ()

        for choices in ({}, [], (), set(), frozenset(), generator()):
            with self.subTest(choices=choices):
                self.assertEqual(normalize_choices(choices), [])

    def test_choices(self):
        class Medal(TextChoices):
            GOLD = "GOLD", _("Gold")
            SILVER = "SILVER", _("Silver")
            BRONZE = "BRONZE", _("Bronze")

        expected = [
            ("GOLD", _("Gold")),
            ("SILVER", _("Silver")),
            ("BRONZE", _("Bronze")),
        ]
        self.assertEqual(normalize_choices(Medal), expected)

    def test_callable(self):
        def get_choices():
            return {
                "C": _("Club"),
                "D": _("Diamond"),
                "H": _("Heart"),
                "S": _("Spade"),
            }

        get_choices_spy = mock.Mock(wraps=get_choices)
        output = normalize_choices(get_choices_spy)

        get_choices_spy.assert_not_called()
        self.assertIsInstance(output, CallableChoiceIterator)
        self.assertEqual(output, self.expected)
        get_choices_spy.assert_called_once()

    def test_mapping(self):
        choices = {
            "C": _("Club"),
            "D": _("Diamond"),
            "H": _("Heart"),
            "S": _("Spade"),
        }
        self.assertEqual(normalize_choices(choices), self.expected)

    def test_iterable(self):
        choices = [
            ("C", _("Club")),
            ("D", _("Diamond")),
            ("H", _("Heart")),
            ("S", _("Spade")),
        ]
        self.assertEqual(normalize_choices(choices), self.expected)

    def test_iterator(self):
        def generator():
            yield "C", _("Club")
            yield "D", _("Diamond")
            yield "H", _("Heart")
            yield "S", _("Spade")

        choices = generator()
        self.assertEqual(normalize_choices(choices), self.expected)

    def test_nested_callable(self):
        def get_audio_choices():
            return [("vinyl", _("Vinyl")), ("cd", _("CD"))]

        def get_video_choices():
            return [("vhs", _("VHS Tape")), ("dvd", _("DVD"))]

        def get_media_choices():
            return [
                ("Audio", get_audio_choices),
                ("Video", get_video_choices),
                ("unknown", _("Unknown")),
            ]

        get_media_choices_spy = mock.Mock(wraps=get_media_choices)
        output = normalize_choices(get_media_choices_spy)

        get_media_choices_spy.assert_not_called()
        self.assertIsInstance(output, CallableChoiceIterator)
        self.assertEqual(output, self.expected_nested)
        get_media_choices_spy.assert_called_once()

    def test_nested_mapping(self):
        choices = {
            "Audio": {"vinyl": _("Vinyl"), "cd": _("CD")},
            "Video": {"vhs": _("VHS Tape"), "dvd": _("DVD")},
            "unknown": _("Unknown"),
        }
        self.assertEqual(normalize_choices(choices), self.expected_nested)

    def test_nested_iterable(self):
        choices = [
            ("Audio", [("vinyl", _("Vinyl")), ("cd", _("CD"))]),
            ("Video", [("vhs", _("VHS Tape")), ("dvd", _("DVD"))]),
            ("unknown", _("Unknown")),
        ]
        self.assertEqual(normalize_choices(choices), self.expected_nested)

    def test_nested_iterator(self):
        def generate_audio_choices():
            yield "vinyl", _("Vinyl")
            yield "cd", _("CD")

        def generate_video_choices():
            yield "vhs", _("VHS Tape")
            yield "dvd", _("DVD")

        def generate_media_choices():
            yield "Audio", generate_audio_choices()
            yield "Video", generate_video_choices()
            yield "unknown", _("Unknown")

        choices = generate_media_choices()
        self.assertEqual(normalize_choices(choices), self.expected_nested)

    def test_callable_non_canonical(self):
        # Canonical form is list of 2-tuple, but nested lists should work.
        def get_choices():
            return [
                ["C", _("Club")],
                ["D", _("Diamond")],
                ["H", _("Heart")],
                ["S", _("Spade")],
            ]

        get_choices_spy = mock.Mock(wraps=get_choices)
        output = normalize_choices(get_choices_spy)

        get_choices_spy.assert_not_called()
        self.assertIsInstance(output, CallableChoiceIterator)
        self.assertEqual(output, self.expected)
        get_choices_spy.assert_called_once()

    def test_iterable_non_canonical(self):
        # Canonical form is list of 2-tuple, but nested lists should work.
        choices = [
            ["C", _("Club")],
            ["D", _("Diamond")],
            ["H", _("Heart")],
            ["S", _("Spade")],
        ]
        self.assertEqual(normalize_choices(choices), self.expected)

    def test_iterator_non_canonical(self):
        # Canonical form is list of 2-tuple, but nested lists should work.
        def generator():
            yield ["C", _("Club")]
            yield ["D", _("Diamond")]
            yield ["H", _("Heart")]
            yield ["S", _("Spade")]

        choices = generator()
        self.assertEqual(normalize_choices(choices), self.expected)

    def test_nested_callable_non_canonical(self):
        # Canonical form is list of 2-tuple, but nested lists should work.

        def get_audio_choices():
            return [["vinyl", _("Vinyl")], ["cd", _("CD")]]

        def get_video_choices():
            return [["vhs", _("VHS Tape")], ["dvd", _("DVD")]]

        def get_media_choices():
            return [
                ["Audio", get_audio_choices],
                ["Video", get_video_choices],
                ["unknown", _("Unknown")],
            ]

        get_media_choices_spy = mock.Mock(wraps=get_media_choices)
        output = normalize_choices(get_media_choices_spy)

        get_media_choices_spy.assert_not_called()
        self.assertIsInstance(output, CallableChoiceIterator)
        self.assertEqual(output, self.expected_nested)
        get_media_choices_spy.assert_called_once()

    def test_nested_iterable_non_canonical(self):
        # Canonical form is list of 2-tuple, but nested lists should work.
        choices = [
            ["Audio", [["vinyl", _("Vinyl")], ["cd", _("CD")]]],
            ["Video", [["vhs", _("VHS Tape")], ["dvd", _("DVD")]]],
            ["unknown", _("Unknown")],
        ]
        self.assertEqual(normalize_choices(choices), self.expected_nested)

    def test_nested_iterator_non_canonical(self):
        # Canonical form is list of 2-tuple, but nested lists should work.
        def generator():
            yield ["Audio", [["vinyl", _("Vinyl")], ["cd", _("CD")]]]
            yield ["Video", [["vhs", _("VHS Tape")], ["dvd", _("DVD")]]]
            yield ["unknown", _("Unknown")]

        choices = generator()
        self.assertEqual(normalize_choices(choices), self.expected_nested)

    def test_nested_mixed_mapping_and_iterable(self):
        # Although not documented, as it's better to stick to either mappings
        # or iterables, nesting of mappings within iterables and vice versa
        # works and is likely to occur in the wild. This is supported by the
        # recursive call to `normalize_choices()` which will normalize nested
        # choices.
        choices = {
            "Audio": [("vinyl", _("Vinyl")), ("cd", _("CD"))],
            "Video": [("vhs", _("VHS Tape")), ("dvd", _("DVD"))],
            "unknown": _("Unknown"),
        }
        self.assertEqual(normalize_choices(choices), self.expected_nested)
        choices = [
            ("Audio", {"vinyl": _("Vinyl"), "cd": _("CD")}),
            ("Video", {"vhs": _("VHS Tape"), "dvd": _("DVD")}),
            ("unknown", _("Unknown")),
        ]
        self.assertEqual(normalize_choices(choices), self.expected_nested)

    def test_iterable_set(self):
        # Although not documented, as sets are unordered which results in
        # randomised order in form fields, passing a set of 2-tuples works.
        # Consistent ordering of choices on model fields in migrations is
        # enforced by the migrations serializer.
        choices = {
            ("C", _("Club")),
            ("D", _("Diamond")),
            ("H", _("Heart")),
            ("S", _("Spade")),
        }
        self.assertEqual(sorted(normalize_choices(choices)), sorted(self.expected))

    def test_unsupported_values_returned_unmodified(self):
        # Unsupported values must be returned unmodified for model system check
        # to work correctly.
        for value in self.invalid + self.invalid_iterable + self.invalid_nested:
            with self.subTest(value=value):
                self.assertEqual(normalize_choices(value), value)

    def test_unsupported_values_from_callable_returned_unmodified(self):
        for value in self.invalid_iterable + self.invalid_nested:
            with self.subTest(value=value):
                self.assertEqual(normalize_choices(lambda: value), value)

    def test_unsupported_values_from_iterator_returned_unmodified(self):
        for value in self.invalid_nested:
            with self.subTest(value=value):
                self.assertEqual(
                    normalize_choices((lambda: (yield from value))()),
                    value,
                )
