import pickle

from django import forms
from django.core.exceptions import ValidationError
from django.db import models
from django.test import SimpleTestCase, TestCase
from django.utils.functional import lazy

from .models import (
    Bar, Choiceful, Foo, RenamedField, VerboseNameField, Whiz, WhizDelayed,
    WhizIter, WhizIterEmpty,
)


class Nested:
    class Field(models.Field):
        pass


class BasicFieldTests(SimpleTestCase):

    def test_show_hidden_initial(self):
        """
        Fields with choices respect show_hidden_initial as a kwarg to
        formfield().
        """
        choices = [(0, 0), (1, 1)]
        model_field = models.Field(choices=choices)
        form_field = model_field.formfield(show_hidden_initial=True)
        self.assertTrue(form_field.show_hidden_initial)

        form_field = model_field.formfield(show_hidden_initial=False)
        self.assertFalse(form_field.show_hidden_initial)

    def test_field_repr(self):
        """
        __repr__() of a field displays its name.
        """
        f = Foo._meta.get_field('a')
        self.assertEqual(repr(f), '<django.db.models.fields.CharField: a>')
        f = models.fields.CharField()
        self.assertEqual(repr(f), '<django.db.models.fields.CharField>')

    def test_field_repr_nested(self):
        """__repr__() uses __qualname__ for nested class support."""
        self.assertEqual(repr(Nested.Field()), '<model_fields.tests.Nested.Field>')

    def test_field_name(self):
        """
        A defined field name (name="fieldname") is used instead of the model
        model's attribute name (modelname).
        """
        instance = RenamedField()
        self.assertTrue(hasattr(instance, 'get_fieldname_display'))
        self.assertFalse(hasattr(instance, 'get_modelname_display'))

    def test_field_verbose_name(self):
        m = VerboseNameField
        for i in range(1, 23):
            self.assertEqual(m._meta.get_field('field%d' % i).verbose_name, 'verbose field%d' % i)

        self.assertEqual(m._meta.get_field('id').verbose_name, 'verbose pk')

    def test_choices_form_class(self):
        """Can supply a custom choices form class to Field.formfield()"""
        choices = [('a', 'a')]
        field = models.CharField(choices=choices)
        klass = forms.TypedMultipleChoiceField
        self.assertIsInstance(field.formfield(choices_form_class=klass), klass)

    def test_formfield_disabled(self):
        """Field.formfield() sets disabled for fields with choices."""
        field = models.CharField(choices=[('a', 'b')])
        form_field = field.formfield(disabled=True)
        self.assertIs(form_field.disabled, True)

    def test_field_str(self):
        f = models.Field()
        self.assertEqual(str(f), '<django.db.models.fields.Field>')
        f = Foo._meta.get_field('a')
        self.assertEqual(str(f), 'model_fields.Foo.a')

    def test_field_ordering(self):
        """Fields are ordered based on their creation."""
        f1 = models.Field()
        f2 = models.Field(auto_created=True)
        f3 = models.Field()
        self.assertLess(f2, f1)
        self.assertGreater(f3, f1)
        self.assertIsNotNone(f1)
        self.assertNotIn(f2, (None, 1, ''))

    def test_field_instance_is_picklable(self):
        """Field instances can be pickled."""
        field = models.Field(max_length=100, default='a string')
        # Must be picklable with this cached property populated (#28188).
        field._get_default
        pickle.dumps(field)

    def test_deconstruct_nested_field(self):
        """deconstruct() uses __qualname__ for nested class support."""
        name, path, args, kwargs = Nested.Field().deconstruct()
        self.assertEqual(path, 'model_fields.tests.Nested.Field')


class ChoicesTests(SimpleTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.no_choices = Choiceful._meta.get_field('no_choices')
        cls.empty_choices = Choiceful._meta.get_field('empty_choices')
        cls.empty_choices_bool = Choiceful._meta.get_field('empty_choices_bool')
        cls.empty_choices_text = Choiceful._meta.get_field('empty_choices_text')
        cls.with_choices = Choiceful._meta.get_field('with_choices')

    def test_choices(self):
        self.assertIsNone(self.no_choices.choices)
        self.assertEqual(self.empty_choices.choices, ())
        self.assertEqual(self.with_choices.choices, [(1, 'A')])

    def test_flatchoices(self):
        self.assertEqual(self.no_choices.flatchoices, [])
        self.assertEqual(self.empty_choices.flatchoices, [])
        self.assertEqual(self.with_choices.flatchoices, [(1, 'A')])

    def test_check(self):
        self.assertEqual(Choiceful.check(), [])

    def test_invalid_choice(self):
        model_instance = None  # Actual model instance not needed.
        self.no_choices.validate(0, model_instance)
        msg = "['Value 99 is not a valid choice.']"
        with self.assertRaisesMessage(ValidationError, msg):
            self.empty_choices.validate(99, model_instance)
        with self.assertRaisesMessage(ValidationError, msg):
            self.with_choices.validate(99, model_instance)

    def test_formfield(self):
        no_choices_formfield = self.no_choices.formfield()
        self.assertIsInstance(no_choices_formfield, forms.IntegerField)
        fields = (
            self.empty_choices, self.with_choices, self.empty_choices_bool,
            self.empty_choices_text,
        )
        for field in fields:
            with self.subTest(field=field):
                self.assertIsInstance(field.formfield(), forms.ChoiceField)


class GetFieldDisplayTests(SimpleTestCase):

    def test_choices_and_field_display(self):
        """
        get_choices() interacts with get_FIELD_display() to return the expected
        values.
        """
        self.assertEqual(Whiz(c=1).get_c_display(), 'First')    # A nested value
        self.assertEqual(Whiz(c=0).get_c_display(), 'Other')    # A top level value
        self.assertEqual(Whiz(c=9).get_c_display(), 9)          # Invalid value
        self.assertIsNone(Whiz(c=None).get_c_display())         # Blank value
        self.assertEqual(Whiz(c='').get_c_display(), '')        # Empty value
        self.assertEqual(WhizDelayed(c=0).get_c_display(), 'Other')  # Delayed choices

    def test_get_FIELD_display_translated(self):
        """A translated display value is coerced to str."""
        val = Whiz(c=5).get_c_display()
        self.assertIsInstance(val, str)
        self.assertEqual(val, 'translated')

    def test_overriding_FIELD_display(self):
        class FooBar(models.Model):
            foo_bar = models.IntegerField(choices=[(1, 'foo'), (2, 'bar')])

            def get_foo_bar_display(self):
                return 'something'

        f = FooBar(foo_bar=1)
        self.assertEqual(f.get_foo_bar_display(), 'something')

    def test_overriding_inherited_FIELD_display(self):
        class Base(models.Model):
            foo = models.CharField(max_length=254, choices=[('A', 'Base A')])

            class Meta:
                abstract = True

        class Child(Base):
            foo = models.CharField(max_length=254, choices=[('A', 'Child A'), ('B', 'Child B')])

        self.assertEqual(Child(foo='A').get_foo_display(), 'Child A')
        self.assertEqual(Child(foo='B').get_foo_display(), 'Child B')

    def test_iterator_choices(self):
        """
        get_choices() works with Iterators.
        """
        self.assertEqual(WhizIter(c=1).c, 1)          # A nested value
        self.assertEqual(WhizIter(c=9).c, 9)          # Invalid value
        self.assertIsNone(WhizIter(c=None).c)         # Blank value
        self.assertEqual(WhizIter(c='').c, '')        # Empty value

    def test_empty_iterator_choices(self):
        """
        get_choices() works with empty iterators.
        """
        self.assertEqual(WhizIterEmpty(c="a").c, "a")      # A nested value
        self.assertEqual(WhizIterEmpty(c="b").c, "b")      # Invalid value
        self.assertIsNone(WhizIterEmpty(c=None).c)         # Blank value
        self.assertEqual(WhizIterEmpty(c='').c, '')        # Empty value


class GetChoicesTests(SimpleTestCase):

    def test_empty_choices(self):
        choices = []
        f = models.CharField(choices=choices)
        self.assertEqual(f.get_choices(include_blank=False), choices)

    def test_blank_in_choices(self):
        choices = [('', '<><>'), ('a', 'A')]
        f = models.CharField(choices=choices)
        self.assertEqual(f.get_choices(include_blank=True), choices)

    def test_blank_in_grouped_choices(self):
        choices = [
            ('f', 'Foo'),
            ('b', 'Bar'),
            ('Group', (
                ('', 'No Preference'),
                ('fg', 'Foo'),
                ('bg', 'Bar'),
            )),
        ]
        f = models.CharField(choices=choices)
        self.assertEqual(f.get_choices(include_blank=True), choices)

    def test_lazy_strings_not_evaluated(self):
        lazy_func = lazy(lambda x: 0 / 0, int)  # raises ZeroDivisionError if evaluated.
        f = models.CharField(choices=[(lazy_func('group'), (('a', 'A'), ('b', 'B')))])
        self.assertEqual(f.get_choices(include_blank=True)[0], ('', '---------'))


class GetChoicesOrderingTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.foo1 = Foo.objects.create(a='a', d='12.35')
        cls.foo2 = Foo.objects.create(a='b', d='12.34')
        cls.bar1 = Bar.objects.create(a=cls.foo1, b='b')
        cls.bar2 = Bar.objects.create(a=cls.foo2, b='a')
        cls.field = Bar._meta.get_field('a')

    def assertChoicesEqual(self, choices, objs):
        self.assertEqual(choices, [(obj.pk, str(obj)) for obj in objs])

    def test_get_choices(self):
        self.assertChoicesEqual(
            self.field.get_choices(include_blank=False, ordering=('a',)),
            [self.foo1, self.foo2]
        )
        self.assertChoicesEqual(
            self.field.get_choices(include_blank=False, ordering=('-a',)),
            [self.foo2, self.foo1]
        )

    def test_get_choices_default_ordering(self):
        self.addCleanup(setattr, Foo._meta, 'ordering', Foo._meta.ordering)
        Foo._meta.ordering = ('d',)
        self.assertChoicesEqual(
            self.field.get_choices(include_blank=False),
            [self.foo2, self.foo1]
        )

    def test_get_choices_reverse_related_field(self):
        self.assertChoicesEqual(
            self.field.remote_field.get_choices(include_blank=False, ordering=('a',)),
            [self.bar1, self.bar2]
        )
        self.assertChoicesEqual(
            self.field.remote_field.get_choices(include_blank=False, ordering=('-a',)),
            [self.bar2, self.bar1]
        )

    def test_get_choices_reverse_related_field_default_ordering(self):
        self.addCleanup(setattr, Bar._meta, 'ordering', Bar._meta.ordering)
        Bar._meta.ordering = ('b',)
        self.assertChoicesEqual(
            self.field.remote_field.get_choices(include_blank=False),
            [self.bar2, self.bar1]
        )


class GetChoicesLimitChoicesToTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.foo1 = Foo.objects.create(a='a', d='12.34')
        cls.foo2 = Foo.objects.create(a='b', d='12.34')
        cls.bar1 = Bar.objects.create(a=cls.foo1, b='b')
        cls.bar2 = Bar.objects.create(a=cls.foo2, b='a')
        cls.field = Bar._meta.get_field('a')

    def assertChoicesEqual(self, choices, objs):
        self.assertEqual(choices, [(obj.pk, str(obj)) for obj in objs])

    def test_get_choices(self):
        self.assertChoicesEqual(
            self.field.get_choices(include_blank=False, limit_choices_to={'a': 'a'}),
            [self.foo1],
        )
        self.assertChoicesEqual(
            self.field.get_choices(include_blank=False, limit_choices_to={}),
            [self.foo1, self.foo2],
        )

    def test_get_choices_reverse_related_field(self):
        field = self.field.remote_field
        self.assertChoicesEqual(
            field.get_choices(include_blank=False, limit_choices_to={'b': 'b'}),
            [self.bar1],
        )
        self.assertChoicesEqual(
            field.get_choices(include_blank=False, limit_choices_to={}),
            [self.bar1, self.bar2],
        )
