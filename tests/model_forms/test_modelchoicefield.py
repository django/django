import datetime

from django import forms
from django.core.exceptions import ValidationError
from django.forms.models import ModelChoiceIterator, ModelChoiceIteratorValue
from django.forms.widgets import CheckboxSelectMultiple
from django.template import Context, Template
from django.test import TestCase

from .models import Article, Author, Book, Category, Writer


class ModelChoiceFieldTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.c1 = Category.objects.create(
            name="Entertainment", slug="entertainment", url="entertainment"
        )
        cls.c2 = Category.objects.create(name="A test", slug="test", url="test")
        cls.c3 = Category.objects.create(name="Third", slug="third-test", url="third")

    def test_basics(self):
        f = forms.ModelChoiceField(Category.objects.all())
        self.assertEqual(
            list(f.choices),
            [
                ("", "---------"),
                (self.c1.pk, "Entertainment"),
                (self.c2.pk, "A test"),
                (self.c3.pk, "Third"),
            ],
        )
        with self.assertRaises(ValidationError):
            f.clean("")
        with self.assertRaises(ValidationError):
            f.clean(None)
        with self.assertRaises(ValidationError):
            f.clean(0)

        # Invalid types that require TypeError to be caught.
        with self.assertRaises(ValidationError):
            f.clean([["fail"]])
        with self.assertRaises(ValidationError):
            f.clean([{"foo": "bar"}])

        self.assertEqual(f.clean(self.c2.id).name, "A test")
        self.assertEqual(f.clean(self.c3.id).name, "Third")

        # Add a Category object *after* the ModelChoiceField has already been
        # instantiated. This proves clean() checks the database during clean()
        # rather than caching it at  instantiation time.
        c4 = Category.objects.create(name="Fourth", url="4th")
        self.assertEqual(f.clean(c4.id).name, "Fourth")

        # Delete a Category object *after* the ModelChoiceField has already been
        # instantiated. This proves clean() checks the database during clean()
        # rather than caching it at instantiation time.
        Category.objects.get(url="4th").delete()
        msg = (
            "['Select a valid choice. That choice is not one of the available "
            "choices.']"
        )
        with self.assertRaisesMessage(ValidationError, msg):
            f.clean(c4.id)

    def test_clean_model_instance(self):
        f = forms.ModelChoiceField(Category.objects.all())
        self.assertEqual(f.clean(self.c1), self.c1)
        # An instance of incorrect model.
        msg = (
            "['Select a valid choice. That choice is not one of the available "
            "choices.']"
        )
        with self.assertRaisesMessage(ValidationError, msg):
            f.clean(Book.objects.create())

    def test_clean_to_field_name(self):
        f = forms.ModelChoiceField(Category.objects.all(), to_field_name="slug")
        self.assertEqual(f.clean(self.c1.slug), self.c1)
        self.assertEqual(f.clean(self.c1), self.c1)

    def test_choices(self):
        f = forms.ModelChoiceField(
            Category.objects.filter(pk=self.c1.id), required=False
        )
        self.assertIsNone(f.clean(""))
        self.assertEqual(f.clean(str(self.c1.id)).name, "Entertainment")
        with self.assertRaises(ValidationError):
            f.clean("100")

        # len() can be called on choices.
        self.assertEqual(len(f.choices), 2)

        # queryset can be changed after the field is created.
        f.queryset = Category.objects.exclude(name="Third")
        self.assertEqual(
            list(f.choices),
            [
                ("", "---------"),
                (self.c1.pk, "Entertainment"),
                (self.c2.pk, "A test"),
            ],
        )
        self.assertEqual(f.clean(self.c2.id).name, "A test")
        with self.assertRaises(ValidationError):
            f.clean(self.c3.id)

        # Choices can be iterated repeatedly.
        gen_one = list(f.choices)
        gen_two = f.choices
        self.assertEqual(gen_one[2], (self.c2.pk, "A test"))
        self.assertEqual(
            list(gen_two),
            [
                ("", "---------"),
                (self.c1.pk, "Entertainment"),
                (self.c2.pk, "A test"),
            ],
        )

        # Overriding label_from_instance() to print custom labels.
        f.queryset = Category.objects.all()
        f.label_from_instance = lambda obj: "category " + str(obj)
        self.assertEqual(
            list(f.choices),
            [
                ("", "---------"),
                (self.c1.pk, "category Entertainment"),
                (self.c2.pk, "category A test"),
                (self.c3.pk, "category Third"),
            ],
        )

    def test_choices_freshness(self):
        f = forms.ModelChoiceField(Category.objects.all())
        self.assertEqual(len(f.choices), 4)
        self.assertEqual(
            list(f.choices),
            [
                ("", "---------"),
                (self.c1.pk, "Entertainment"),
                (self.c2.pk, "A test"),
                (self.c3.pk, "Third"),
            ],
        )
        c4 = Category.objects.create(name="Fourth", slug="4th", url="4th")
        self.assertEqual(len(f.choices), 5)
        self.assertEqual(
            list(f.choices),
            [
                ("", "---------"),
                (self.c1.pk, "Entertainment"),
                (self.c2.pk, "A test"),
                (self.c3.pk, "Third"),
                (c4.pk, "Fourth"),
            ],
        )

    def test_choices_bool(self):
        f = forms.ModelChoiceField(Category.objects.all(), empty_label=None)
        self.assertIs(bool(f.choices), True)
        Category.objects.all().delete()
        self.assertIs(bool(f.choices), False)

    def test_choices_bool_empty_label(self):
        f = forms.ModelChoiceField(Category.objects.all(), empty_label="--------")
        Category.objects.all().delete()
        self.assertIs(bool(f.choices), True)

    def test_choices_radio_blank(self):
        choices = [
            (self.c1.pk, "Entertainment"),
            (self.c2.pk, "A test"),
            (self.c3.pk, "Third"),
        ]
        categories = Category.objects.all()
        for widget in [forms.RadioSelect, forms.RadioSelect()]:
            for blank in [True, False]:
                with self.subTest(widget=widget, blank=blank):
                    f = forms.ModelChoiceField(
                        categories,
                        widget=widget,
                        blank=blank,
                    )
                    self.assertEqual(
                        list(f.choices),
                        [("", "---------")] + choices if blank else choices,
                    )

    def test_deepcopies_widget(self):
        class ModelChoiceForm(forms.Form):
            category = forms.ModelChoiceField(Category.objects.all())

        form1 = ModelChoiceForm()
        field1 = form1.fields["category"]
        # To allow the widget to change the queryset of field1.widget.choices
        # without affecting other forms, the following must hold (#11183):
        self.assertIsNot(field1, ModelChoiceForm.base_fields["category"])
        self.assertIs(field1.widget.choices.field, field1)

    def test_result_cache_not_shared(self):
        class ModelChoiceForm(forms.Form):
            category = forms.ModelChoiceField(Category.objects.all())

        form1 = ModelChoiceForm()
        self.assertCountEqual(
            form1.fields["category"].queryset, [self.c1, self.c2, self.c3]
        )
        form2 = ModelChoiceForm()
        self.assertIsNone(form2.fields["category"].queryset._result_cache)

    def test_queryset_none(self):
        class ModelChoiceForm(forms.Form):
            category = forms.ModelChoiceField(queryset=None)

            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.fields["category"].queryset = Category.objects.filter(
                    slug__contains="test"
                )

        form = ModelChoiceForm()
        self.assertCountEqual(form.fields["category"].queryset, [self.c2, self.c3])

    def test_no_extra_query_when_accessing_attrs(self):
        """
        ModelChoiceField with RadioSelect widget doesn't produce unnecessary
        db queries when accessing its BoundField's attrs.
        """

        class ModelChoiceForm(forms.Form):
            category = forms.ModelChoiceField(
                Category.objects.all(), widget=forms.RadioSelect
            )

        form = ModelChoiceForm()
        field = form["category"]  # BoundField
        template = Template("{{ field.name }}{{ field }}{{ field.help_text }}")
        with self.assertNumQueries(1):
            template.render(Context({"field": field}))

    def test_disabled_modelchoicefield(self):
        class ModelChoiceForm(forms.ModelForm):
            author = forms.ModelChoiceField(Author.objects.all(), disabled=True)

            class Meta:
                model = Book
                fields = ["author"]

        book = Book.objects.create(author=Writer.objects.create(name="Test writer"))
        form = ModelChoiceForm({}, instance=book)
        self.assertEqual(
            form.errors["author"],
            ["Select a valid choice. That choice is not one of the available choices."],
        )

    def test_disabled_modelchoicefield_has_changed(self):
        field = forms.ModelChoiceField(Author.objects.all(), disabled=True)
        self.assertIs(field.has_changed("x", "y"), False)

    def test_disabled_modelchoicefield_initial_model_instance(self):
        class ModelChoiceForm(forms.Form):
            categories = forms.ModelChoiceField(
                Category.objects.all(),
                disabled=True,
                initial=self.c1,
            )

        self.assertTrue(ModelChoiceForm(data={"categories": self.c1.pk}).is_valid())

    def test_disabled_multiplemodelchoicefield(self):
        class ArticleForm(forms.ModelForm):
            categories = forms.ModelMultipleChoiceField(
                Category.objects.all(), required=False
            )

            class Meta:
                model = Article
                fields = ["categories"]

        category1 = Category.objects.create(name="cat1")
        category2 = Category.objects.create(name="cat2")
        article = Article.objects.create(
            pub_date=datetime.date(1988, 1, 4),
            writer=Writer.objects.create(name="Test writer"),
        )
        article.categories.set([category1.pk])

        form = ArticleForm(data={"categories": [category2.pk]}, instance=article)
        self.assertEqual(form.errors, {})
        self.assertEqual(
            [x.pk for x in form.cleaned_data["categories"]], [category2.pk]
        )
        # Disabled fields use the value from `instance` rather than `data`.
        form = ArticleForm(data={"categories": [category2.pk]}, instance=article)
        form.fields["categories"].disabled = True
        self.assertEqual(form.errors, {})
        self.assertEqual(
            [x.pk for x in form.cleaned_data["categories"]], [category1.pk]
        )

    def test_disabled_modelmultiplechoicefield_has_changed(self):
        field = forms.ModelMultipleChoiceField(Author.objects.all(), disabled=True)
        self.assertIs(field.has_changed("x", "y"), False)

    def test_overridable_choice_iterator(self):
        """
        Iterator defaults to ModelChoiceIterator and can be overridden with
        the iterator attribute on a ModelChoiceField subclass.
        """
        field = forms.ModelChoiceField(Category.objects.all())
        self.assertIsInstance(field.choices, ModelChoiceIterator)

        class CustomModelChoiceIterator(ModelChoiceIterator):
            pass

        class CustomModelChoiceField(forms.ModelChoiceField):
            iterator = CustomModelChoiceIterator

        field = CustomModelChoiceField(Category.objects.all())
        self.assertIsInstance(field.choices, CustomModelChoiceIterator)

    def test_choice_iterator_passes_model_to_widget(self):
        class CustomCheckboxSelectMultiple(CheckboxSelectMultiple):
            def create_option(
                self, name, value, label, selected, index, subindex=None, attrs=None
            ):
                option = super().create_option(
                    name, value, label, selected, index, subindex, attrs
                )
                # Modify the HTML based on the object being rendered.
                c = value.instance
                option["attrs"]["data-slug"] = c.slug
                return option

        class CustomModelMultipleChoiceField(forms.ModelMultipleChoiceField):
            widget = CustomCheckboxSelectMultiple

        field = CustomModelMultipleChoiceField(Category.objects.all())
        self.assertHTMLEqual(
            field.widget.render("name", []),
            (
                "<div>"
                '<div><label><input type="checkbox" name="name" value="%d" '
                'data-slug="entertainment">Entertainment</label></div>'
                '<div><label><input type="checkbox" name="name" value="%d" '
                'data-slug="test">A test</label></div>'
                '<div><label><input type="checkbox" name="name" value="%d" '
                'data-slug="third-test">Third</label></div>'
                "</div>"
            )
            % (self.c1.pk, self.c2.pk, self.c3.pk),
        )

    def test_custom_choice_iterator_passes_model_to_widget(self):
        class CustomModelChoiceValue:
            def __init__(self, value, obj):
                self.value = value
                self.obj = obj

            def __str__(self):
                return str(self.value)

        class CustomModelChoiceIterator(ModelChoiceIterator):
            def choice(self, obj):
                value, label = super().choice(obj)
                return CustomModelChoiceValue(value, obj), label

        class CustomCheckboxSelectMultiple(CheckboxSelectMultiple):
            def create_option(
                self, name, value, label, selected, index, subindex=None, attrs=None
            ):
                option = super().create_option(
                    name, value, label, selected, index, subindex, attrs
                )
                # Modify the HTML based on the object being rendered.
                c = value.obj
                option["attrs"]["data-slug"] = c.slug
                return option

        class CustomModelMultipleChoiceField(forms.ModelMultipleChoiceField):
            iterator = CustomModelChoiceIterator
            widget = CustomCheckboxSelectMultiple

        field = CustomModelMultipleChoiceField(Category.objects.all())
        self.assertHTMLEqual(
            field.widget.render("name", []),
            """
            <div><div>
            <label><input type="checkbox" name="name" value="%d"
                data-slug="entertainment">Entertainment
            </label></div>
            <div><label>
            <input type="checkbox" name="name" value="%d" data-slug="test">A test
            </label></div>
            <div><label>
            <input type="checkbox" name="name" value="%d" data-slug="third-test">Third
            </label></div></div>
            """
            % (self.c1.pk, self.c2.pk, self.c3.pk),
        )

    def test_choice_value_hash(self):
        value_1 = ModelChoiceIteratorValue(self.c1.pk, self.c1)
        value_2 = ModelChoiceIteratorValue(self.c2.pk, self.c2)
        self.assertEqual(
            hash(value_1), hash(ModelChoiceIteratorValue(self.c1.pk, None))
        )
        self.assertNotEqual(hash(value_1), hash(value_2))

    def test_choices_not_fetched_when_not_rendering(self):
        with self.assertNumQueries(1):
            field = forms.ModelChoiceField(Category.objects.order_by("-name"))
            self.assertEqual("Entertainment", field.clean(self.c1.pk).name)

    def test_queryset_manager(self):
        f = forms.ModelChoiceField(Category.objects)
        self.assertEqual(len(f.choices), 4)
        self.assertEqual(
            list(f.choices),
            [
                ("", "---------"),
                (self.c1.pk, "Entertainment"),
                (self.c2.pk, "A test"),
                (self.c3.pk, "Third"),
            ],
        )

    def test_num_queries(self):
        """
        Widgets that render multiple subwidgets shouldn't make more than one
        database query.
        """
        categories = Category.objects.all()

        class CategoriesForm(forms.Form):
            radio = forms.ModelChoiceField(
                queryset=categories, widget=forms.RadioSelect
            )
            checkbox = forms.ModelMultipleChoiceField(
                queryset=categories, widget=forms.CheckboxSelectMultiple
            )

        template = Template(
            "{% for widget in form.checkbox %}{{ widget }}{% endfor %}"
            "{% for widget in form.radio %}{{ widget }}{% endfor %}"
        )
        with self.assertNumQueries(2):
            template.render(Context({"form": CategoriesForm()}))
