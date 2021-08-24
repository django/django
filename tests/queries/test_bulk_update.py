import datetime

from django.core.exceptions import FieldDoesNotExist
from django.db.models import F
from django.db.models.functions import Lower
from django.test import TestCase, skipUnlessDBFeature

from .models import (
    Article,
    CustomDbColumn,
    CustomPk,
    Detail,
    Individual,
    JSONFieldNullable,
    Member,
    Note,
    Number,
    Order,
    Paragraph,
    SpecialCategory,
    Tag,
    Valid,
)


class BulkUpdateNoteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.notes = [Note.objects.create(note=str(i), misc=str(i)) for i in range(10)]

    def create_tags(self):
        self.tags = [Tag.objects.create(name=str(i)) for i in range(10)]

    def test_simple(self):
        for note in self.notes:
            note.note = "test-%s" % note.id
        with self.assertNumQueries(1):
            Note.objects.bulk_update(self.notes, ["note"])
        self.assertCountEqual(
            Note.objects.values_list("note", flat=True),
            [cat.note for cat in self.notes],
        )

    def test_multiple_fields(self):
        for note in self.notes:
            note.note = "test-%s" % note.id
            note.misc = "misc-%s" % note.id
        with self.assertNumQueries(1):
            Note.objects.bulk_update(self.notes, ["note", "misc"])
        self.assertCountEqual(
            Note.objects.values_list("note", flat=True),
            [cat.note for cat in self.notes],
        )
        self.assertCountEqual(
            Note.objects.values_list("misc", flat=True),
            [cat.misc for cat in self.notes],
        )

    def test_batch_size(self):
        with self.assertNumQueries(len(self.notes)):
            Note.objects.bulk_update(self.notes, fields=["note"], batch_size=1)

    def test_unsaved_models(self):
        objs = self.notes + [Note(note="test", misc="test")]
        msg = "All bulk_update() objects must have a primary key set."
        with self.assertRaisesMessage(ValueError, msg):
            Note.objects.bulk_update(objs, fields=["note"])

    def test_foreign_keys_do_not_lookup(self):
        self.create_tags()
        for note, tag in zip(self.notes, self.tags):
            note.tag = tag
        with self.assertNumQueries(1):
            Note.objects.bulk_update(self.notes, ["tag"])
        self.assertSequenceEqual(Note.objects.filter(tag__isnull=False), self.notes)

    def test_set_field_to_null(self):
        self.create_tags()
        Note.objects.update(tag=self.tags[0])
        for note in self.notes:
            note.tag = None
        Note.objects.bulk_update(self.notes, ["tag"])
        self.assertCountEqual(Note.objects.filter(tag__isnull=True), self.notes)

    def test_set_mixed_fields_to_null(self):
        self.create_tags()
        midpoint = len(self.notes) // 2
        top, bottom = self.notes[:midpoint], self.notes[midpoint:]
        for note in top:
            note.tag = None
        for note in bottom:
            note.tag = self.tags[0]
        Note.objects.bulk_update(self.notes, ["tag"])
        self.assertCountEqual(Note.objects.filter(tag__isnull=True), top)
        self.assertCountEqual(Note.objects.filter(tag__isnull=False), bottom)

    def test_functions(self):
        Note.objects.update(note="TEST")
        for note in self.notes:
            note.note = Lower("note")
        Note.objects.bulk_update(self.notes, ["note"])
        self.assertEqual(set(Note.objects.values_list("note", flat=True)), {"test"})

    # Tests that use self.notes go here, otherwise put them in another class.


class BulkUpdateTests(TestCase):
    def test_no_fields(self):
        msg = "Field names must be given to bulk_update()."
        with self.assertRaisesMessage(ValueError, msg):
            Note.objects.bulk_update([], fields=[])

    def test_invalid_batch_size(self):
        msg = "Batch size must be a positive integer."
        with self.assertRaisesMessage(ValueError, msg):
            Note.objects.bulk_update([], fields=["note"], batch_size=-1)

    def test_nonexistent_field(self):
        with self.assertRaisesMessage(
            FieldDoesNotExist, "Note has no field named 'nonexistent'"
        ):
            Note.objects.bulk_update([], ["nonexistent"])

    pk_fields_error = "bulk_update() cannot be used with primary key fields."

    def test_update_primary_key(self):
        with self.assertRaisesMessage(ValueError, self.pk_fields_error):
            Note.objects.bulk_update([], ["id"])

    def test_update_custom_primary_key(self):
        with self.assertRaisesMessage(ValueError, self.pk_fields_error):
            CustomPk.objects.bulk_update([], ["name"])

    def test_empty_objects(self):
        with self.assertNumQueries(0):
            rows_updated = Note.objects.bulk_update([], ["note"])
        self.assertEqual(rows_updated, 0)

    def test_large_batch(self):
        Note.objects.bulk_create(
            [Note(note=str(i), misc=str(i)) for i in range(0, 2000)]
        )
        notes = list(Note.objects.all())
        rows_updated = Note.objects.bulk_update(notes, ["note"])
        self.assertEqual(rows_updated, 2000)

    def test_updated_rows_when_passing_duplicates(self):
        note = Note.objects.create(note="test-note", misc="test")
        rows_updated = Note.objects.bulk_update([note, note], ["note"])
        self.assertEqual(rows_updated, 1)
        # Duplicates in different batches.
        rows_updated = Note.objects.bulk_update([note, note], ["note"], batch_size=1)
        self.assertEqual(rows_updated, 2)

    def test_only_concrete_fields_allowed(self):
        obj = Valid.objects.create(valid="test")
        detail = Detail.objects.create(data="test")
        paragraph = Paragraph.objects.create(text="test")
        Member.objects.create(name="test", details=detail)
        msg = "bulk_update() can only be used with concrete fields."
        with self.assertRaisesMessage(ValueError, msg):
            Detail.objects.bulk_update([detail], fields=["member"])
        with self.assertRaisesMessage(ValueError, msg):
            Paragraph.objects.bulk_update([paragraph], fields=["page"])
        with self.assertRaisesMessage(ValueError, msg):
            Valid.objects.bulk_update([obj], fields=["parent"])

    def test_custom_db_columns(self):
        model = CustomDbColumn.objects.create(custom_column=1)
        model.custom_column = 2
        CustomDbColumn.objects.bulk_update([model], fields=["custom_column"])
        model.refresh_from_db()
        self.assertEqual(model.custom_column, 2)

    def test_custom_pk(self):
        custom_pks = [
            CustomPk.objects.create(name="pk-%s" % i, extra="") for i in range(10)
        ]
        for model in custom_pks:
            model.extra = "extra-%s" % model.pk
        CustomPk.objects.bulk_update(custom_pks, ["extra"])
        self.assertCountEqual(
            CustomPk.objects.values_list("extra", flat=True),
            [cat.extra for cat in custom_pks],
        )

    def test_falsey_pk_value(self):
        order = Order.objects.create(pk=0, name="test")
        order.name = "updated"
        Order.objects.bulk_update([order], ["name"])
        order.refresh_from_db()
        self.assertEqual(order.name, "updated")

    def test_inherited_fields(self):
        special_categories = [
            SpecialCategory.objects.create(name=str(i), special_name=str(i))
            for i in range(10)
        ]
        for category in special_categories:
            category.name = "test-%s" % category.id
            category.special_name = "special-test-%s" % category.special_name
        SpecialCategory.objects.bulk_update(
            special_categories, ["name", "special_name"]
        )
        self.assertCountEqual(
            SpecialCategory.objects.values_list("name", flat=True),
            [cat.name for cat in special_categories],
        )
        self.assertCountEqual(
            SpecialCategory.objects.values_list("special_name", flat=True),
            [cat.special_name for cat in special_categories],
        )

    def test_field_references(self):
        numbers = [Number.objects.create(num=0) for _ in range(10)]
        for number in numbers:
            number.num = F("num") + 1
        Number.objects.bulk_update(numbers, ["num"])
        self.assertCountEqual(Number.objects.filter(num=1), numbers)

    def test_booleanfield(self):
        individuals = [Individual.objects.create(alive=False) for _ in range(10)]
        for individual in individuals:
            individual.alive = True
        Individual.objects.bulk_update(individuals, ["alive"])
        self.assertCountEqual(Individual.objects.filter(alive=True), individuals)

    def test_ipaddressfield(self):
        for ip in ("2001::1", "1.2.3.4"):
            with self.subTest(ip=ip):
                models = [
                    CustomDbColumn.objects.create(ip_address="0.0.0.0")
                    for _ in range(10)
                ]
                for model in models:
                    model.ip_address = ip
                CustomDbColumn.objects.bulk_update(models, ["ip_address"])
                self.assertCountEqual(
                    CustomDbColumn.objects.filter(ip_address=ip), models
                )

    def test_datetime_field(self):
        articles = [
            Article.objects.create(name=str(i), created=datetime.datetime.today())
            for i in range(10)
        ]
        point_in_time = datetime.datetime(1991, 10, 31)
        for article in articles:
            article.created = point_in_time
        Article.objects.bulk_update(articles, ["created"])
        self.assertCountEqual(Article.objects.filter(created=point_in_time), articles)

    @skipUnlessDBFeature("supports_json_field")
    def test_json_field(self):
        JSONFieldNullable.objects.bulk_create(
            [JSONFieldNullable(json_field={"a": i}) for i in range(10)]
        )
        objs = JSONFieldNullable.objects.all()
        for obj in objs:
            obj.json_field = {"c": obj.json_field["a"] + 1}
        JSONFieldNullable.objects.bulk_update(objs, ["json_field"])
        self.assertCountEqual(
            JSONFieldNullable.objects.filter(json_field__has_key="c"), objs
        )
