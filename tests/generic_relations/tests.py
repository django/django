from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import FieldError
from django.db.models import Q
from django.test import SimpleTestCase, TestCase, skipUnlessDBFeature

from .models import (
    AllowsNullGFK,
    Animal,
    Carrot,
    Comparison,
    ConcreteRelatedModel,
    ForConcreteModelModel,
    ForProxyModelModel,
    Gecko,
    ManualPK,
    Mineral,
    ProxyRelatedModel,
    Rock,
    TaggedItem,
    ValuableRock,
    ValuableTaggedItem,
    Vegetable,
)


class GenericRelationsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.lion = Animal.objects.create(common_name="Lion", latin_name="Panthera leo")
        cls.platypus = Animal.objects.create(
            common_name="Platypus",
            latin_name="Ornithorhynchus anatinus",
        )
        Vegetable.objects.create(name="Eggplant", is_yucky=True)
        cls.bacon = Vegetable.objects.create(name="Bacon", is_yucky=False)
        cls.quartz = Mineral.objects.create(name="Quartz", hardness=7)

        # Tagging stuff.
        cls.fatty = cls.bacon.tags.create(tag="fatty")
        cls.salty = cls.bacon.tags.create(tag="salty")
        cls.yellow = cls.lion.tags.create(tag="yellow")
        cls.hairy = cls.lion.tags.create(tag="hairy")

    def comp_func(self, obj):
        # Original list of tags:
        return obj.tag, obj.content_type.model_class(), obj.object_id

    def test_generic_update_or_create_when_created(self):
        """
        Should be able to use update_or_create from the generic related manager
        to create a tag. Refs #23611.
        """
        count = self.bacon.tags.count()
        tag, created = self.bacon.tags.update_or_create(tag="stinky")
        self.assertTrue(created)
        self.assertEqual(count + 1, self.bacon.tags.count())

    def test_generic_update_or_create_when_updated(self):
        """
        Should be able to use update_or_create from the generic related manager
        to update a tag. Refs #23611.
        """
        count = self.bacon.tags.count()
        tag = self.bacon.tags.create(tag="stinky")
        self.assertEqual(count + 1, self.bacon.tags.count())
        tag, created = self.bacon.tags.update_or_create(
            defaults={"tag": "juicy"}, id=tag.id
        )
        self.assertFalse(created)
        self.assertEqual(count + 1, self.bacon.tags.count())
        self.assertEqual(tag.tag, "juicy")

    def test_generic_get_or_create_when_created(self):
        """
        Should be able to use get_or_create from the generic related manager
        to create a tag. Refs #23611.
        """
        count = self.bacon.tags.count()
        tag, created = self.bacon.tags.get_or_create(tag="stinky")
        self.assertTrue(created)
        self.assertEqual(count + 1, self.bacon.tags.count())

    def test_generic_get_or_create_when_exists(self):
        """
        Should be able to use get_or_create from the generic related manager
        to get a tag. Refs #23611.
        """
        count = self.bacon.tags.count()
        tag = self.bacon.tags.create(tag="stinky")
        self.assertEqual(count + 1, self.bacon.tags.count())
        tag, created = self.bacon.tags.get_or_create(
            id=tag.id, defaults={"tag": "juicy"}
        )
        self.assertFalse(created)
        self.assertEqual(count + 1, self.bacon.tags.count())
        # shouldn't had changed the tag
        self.assertEqual(tag.tag, "stinky")

    def test_generic_relations_m2m_mimic(self):
        """
        Objects with declared GenericRelations can be tagged directly -- the
        API mimics the many-to-many API.
        """
        self.assertSequenceEqual(self.lion.tags.all(), [self.hairy, self.yellow])
        self.assertSequenceEqual(self.bacon.tags.all(), [self.fatty, self.salty])

    def test_access_content_object(self):
        """
        Test accessing the content object like a foreign key.
        """
        tagged_item = TaggedItem.objects.get(tag="salty")
        self.assertEqual(tagged_item.content_object, self.bacon)

    def test_query_content_object(self):
        qs = TaggedItem.objects.filter(animal__isnull=False).order_by(
            "animal__common_name", "tag"
        )
        self.assertSequenceEqual(qs, [self.hairy, self.yellow])

        mpk = ManualPK.objects.create(id=1)
        mpk.tags.create(tag="mpk")
        qs = TaggedItem.objects.filter(
            Q(animal__isnull=False) | Q(manualpk__id=1)
        ).order_by("tag")
        self.assertQuerySetEqual(qs, ["hairy", "mpk", "yellow"], lambda x: x.tag)

    def test_exclude_generic_relations(self):
        """
        Test lookups over an object without GenericRelations.
        """
        # Recall that the Mineral class doesn't have an explicit GenericRelation
        # defined. That's OK, because you can create TaggedItems explicitly.
        # However, excluding GenericRelations means your lookups have to be a
        # bit more explicit.
        shiny = TaggedItem.objects.create(content_object=self.quartz, tag="shiny")
        clearish = TaggedItem.objects.create(content_object=self.quartz, tag="clearish")

        ctype = ContentType.objects.get_for_model(self.quartz)
        q = TaggedItem.objects.filter(
            content_type__pk=ctype.id, object_id=self.quartz.id
        )
        self.assertSequenceEqual(q, [clearish, shiny])

    def test_access_via_content_type(self):
        """
        Test lookups through content type.
        """
        self.lion.delete()
        self.platypus.tags.create(tag="fatty")

        ctype = ContentType.objects.get_for_model(self.platypus)

        self.assertSequenceEqual(
            Animal.objects.filter(tags__content_type=ctype),
            [self.platypus],
        )

    def test_set_foreign_key(self):
        """
        You can set a generic foreign key in the way you'd expect.
        """
        tag1 = TaggedItem.objects.create(content_object=self.quartz, tag="shiny")
        tag1.content_object = self.platypus
        tag1.save()

        self.assertSequenceEqual(self.platypus.tags.all(), [tag1])

    def test_queries_across_generic_relations(self):
        """
        Queries across generic relations respect the content types. Even though
        there are two TaggedItems with a tag of "fatty", this query only pulls
        out the one with the content type related to Animals.
        """
        self.assertSequenceEqual(
            Animal.objects.order_by("common_name"),
            [self.lion, self.platypus],
        )

    def test_queries_content_type_restriction(self):
        """
        Create another fatty tagged instance with different PK to ensure there
        is a content type restriction in the generated queries below.
        """
        mpk = ManualPK.objects.create(id=self.lion.pk)
        mpk.tags.create(tag="fatty")
        self.platypus.tags.create(tag="fatty")

        self.assertSequenceEqual(
            Animal.objects.filter(tags__tag="fatty"),
            [self.platypus],
        )
        self.assertSequenceEqual(
            Animal.objects.exclude(tags__tag="fatty"),
            [self.lion],
        )

    def test_object_deletion_with_generic_relation(self):
        """
        If you delete an object with an explicit Generic relation, the related
        objects are deleted when the source object is deleted.
        """
        self.assertQuerySetEqual(
            TaggedItem.objects.all(),
            [
                ("fatty", Vegetable, self.bacon.pk),
                ("hairy", Animal, self.lion.pk),
                ("salty", Vegetable, self.bacon.pk),
                ("yellow", Animal, self.lion.pk),
            ],
            self.comp_func,
        )
        self.lion.delete()

        self.assertQuerySetEqual(
            TaggedItem.objects.all(),
            [
                ("fatty", Vegetable, self.bacon.pk),
                ("salty", Vegetable, self.bacon.pk),
            ],
            self.comp_func,
        )

    def test_object_deletion_without_generic_relation(self):
        """
        If Generic Relation is not explicitly defined, any related objects
        remain after deletion of the source object.
        """
        TaggedItem.objects.create(content_object=self.quartz, tag="clearish")
        quartz_pk = self.quartz.pk
        self.quartz.delete()
        self.assertQuerySetEqual(
            TaggedItem.objects.all(),
            [
                ("clearish", Mineral, quartz_pk),
                ("fatty", Vegetable, self.bacon.pk),
                ("hairy", Animal, self.lion.pk),
                ("salty", Vegetable, self.bacon.pk),
                ("yellow", Animal, self.lion.pk),
            ],
            self.comp_func,
        )

    def test_tag_deletion_related_objects_unaffected(self):
        """
        If you delete a tag, the objects using the tag are unaffected (other
        than losing a tag).
        """
        ctype = ContentType.objects.get_for_model(self.lion)
        tag = TaggedItem.objects.get(
            content_type__pk=ctype.id, object_id=self.lion.id, tag="hairy"
        )
        tag.delete()

        self.assertSequenceEqual(self.lion.tags.all(), [self.yellow])
        self.assertQuerySetEqual(
            TaggedItem.objects.all(),
            [
                ("fatty", Vegetable, self.bacon.pk),
                ("salty", Vegetable, self.bacon.pk),
                ("yellow", Animal, self.lion.pk),
            ],
            self.comp_func,
        )

    def test_add_bulk(self):
        bacon = Vegetable.objects.create(name="Bacon", is_yucky=False)
        t1 = TaggedItem.objects.create(content_object=self.quartz, tag="shiny")
        t2 = TaggedItem.objects.create(content_object=self.quartz, tag="clearish")
        # One update() query.
        with self.assertNumQueries(1):
            bacon.tags.add(t1, t2)
        self.assertEqual(t1.content_object, bacon)
        self.assertEqual(t2.content_object, bacon)

    def test_add_bulk_false(self):
        bacon = Vegetable.objects.create(name="Bacon", is_yucky=False)
        t1 = TaggedItem.objects.create(content_object=self.quartz, tag="shiny")
        t2 = TaggedItem.objects.create(content_object=self.quartz, tag="clearish")
        # One save() for each object.
        with self.assertNumQueries(2):
            bacon.tags.add(t1, t2, bulk=False)
        self.assertEqual(t1.content_object, bacon)
        self.assertEqual(t2.content_object, bacon)

    def test_add_rejects_unsaved_objects(self):
        t1 = TaggedItem(content_object=self.quartz, tag="shiny")
        msg = (
            "<TaggedItem: shiny> instance isn't saved. Use bulk=False or save the "
            "object first."
        )
        with self.assertRaisesMessage(ValueError, msg):
            self.bacon.tags.add(t1)

    def test_add_rejects_wrong_instances(self):
        msg = "'TaggedItem' instance expected, got <Animal: Lion>"
        with self.assertRaisesMessage(TypeError, msg):
            self.bacon.tags.add(self.lion)

    def test_set(self):
        bacon = Vegetable.objects.create(name="Bacon", is_yucky=False)
        fatty = bacon.tags.create(tag="fatty")
        salty = bacon.tags.create(tag="salty")

        bacon.tags.set([fatty, salty])
        self.assertSequenceEqual(bacon.tags.all(), [fatty, salty])

        bacon.tags.set([fatty])
        self.assertSequenceEqual(bacon.tags.all(), [fatty])

        bacon.tags.set([])
        self.assertSequenceEqual(bacon.tags.all(), [])

        bacon.tags.set([fatty, salty], bulk=False, clear=True)
        self.assertSequenceEqual(bacon.tags.all(), [fatty, salty])

        bacon.tags.set([fatty], bulk=False, clear=True)
        self.assertSequenceEqual(bacon.tags.all(), [fatty])

        bacon.tags.set([], clear=True)
        self.assertSequenceEqual(bacon.tags.all(), [])

    def test_assign(self):
        bacon = Vegetable.objects.create(name="Bacon", is_yucky=False)
        fatty = bacon.tags.create(tag="fatty")
        salty = bacon.tags.create(tag="salty")

        bacon.tags.set([fatty, salty])
        self.assertSequenceEqual(bacon.tags.all(), [fatty, salty])

        bacon.tags.set([fatty])
        self.assertSequenceEqual(bacon.tags.all(), [fatty])

        bacon.tags.set([])
        self.assertSequenceEqual(bacon.tags.all(), [])

    def test_assign_with_queryset(self):
        # Querysets used in reverse GFK assignments are pre-evaluated so their
        # value isn't affected by the clearing operation
        # in ManyRelatedManager.set() (#19816).
        bacon = Vegetable.objects.create(name="Bacon", is_yucky=False)
        bacon.tags.create(tag="fatty")
        bacon.tags.create(tag="salty")
        self.assertEqual(2, bacon.tags.count())

        qs = bacon.tags.filter(tag="fatty")
        bacon.tags.set(qs)

        self.assertEqual(1, bacon.tags.count())
        self.assertEqual(1, qs.count())

    def test_clear(self):
        self.assertSequenceEqual(
            TaggedItem.objects.order_by("tag"),
            [self.fatty, self.hairy, self.salty, self.yellow],
        )
        self.bacon.tags.clear()
        self.assertSequenceEqual(self.bacon.tags.all(), [])
        self.assertSequenceEqual(
            TaggedItem.objects.order_by("tag"),
            [self.hairy, self.yellow],
        )

    def test_remove(self):
        self.assertSequenceEqual(
            TaggedItem.objects.order_by("tag"),
            [self.fatty, self.hairy, self.salty, self.yellow],
        )
        self.bacon.tags.remove(self.fatty)
        self.assertSequenceEqual(self.bacon.tags.all(), [self.salty])
        self.assertSequenceEqual(
            TaggedItem.objects.order_by("tag"),
            [self.hairy, self.salty, self.yellow],
        )

    def test_generic_relation_related_name_default(self):
        # GenericRelation isn't usable from the reverse side by default.
        msg = (
            "Cannot resolve keyword 'vegetable' into field. Choices are: "
            "animal, content_object, content_type, content_type_id, id, "
            "manualpk, object_id, tag, valuabletaggeditem"
        )
        with self.assertRaisesMessage(FieldError, msg):
            TaggedItem.objects.filter(vegetable__isnull=True)

    def test_multiple_gfk(self):
        # Simple tests for multiple GenericForeignKeys
        # only uses one model, since the above tests should be sufficient.
        tiger = Animal.objects.create(common_name="tiger")
        cheetah = Animal.objects.create(common_name="cheetah")
        bear = Animal.objects.create(common_name="bear")

        # Create directly
        c1 = Comparison.objects.create(
            first_obj=cheetah, other_obj=tiger, comparative="faster"
        )
        c2 = Comparison.objects.create(
            first_obj=tiger, other_obj=cheetah, comparative="cooler"
        )

        # Create using GenericRelation
        c3 = tiger.comparisons.create(other_obj=bear, comparative="cooler")
        c4 = tiger.comparisons.create(other_obj=cheetah, comparative="stronger")
        self.assertSequenceEqual(cheetah.comparisons.all(), [c1])

        # Filtering works
        self.assertCountEqual(
            tiger.comparisons.filter(comparative="cooler"),
            [c2, c3],
        )

        # Filtering and deleting works
        subjective = ["cooler"]
        tiger.comparisons.filter(comparative__in=subjective).delete()
        self.assertCountEqual(Comparison.objects.all(), [c1, c4])

        # If we delete cheetah, Comparisons with cheetah as 'first_obj' will be
        # deleted since Animal has an explicit GenericRelation to Comparison
        # through first_obj. Comparisons with cheetah as 'other_obj' will not
        # be deleted.
        cheetah.delete()
        self.assertSequenceEqual(Comparison.objects.all(), [c4])

    def test_gfk_subclasses(self):
        # GenericForeignKey should work with subclasses (see #8309)
        quartz = Mineral.objects.create(name="Quartz", hardness=7)
        valuedtag = ValuableTaggedItem.objects.create(
            content_object=quartz, tag="shiny", value=10
        )
        self.assertEqual(valuedtag.content_object, quartz)

    def test_generic_relation_to_inherited_child(self):
        # GenericRelations to models that use multi-table inheritance work.
        granite = ValuableRock.objects.create(name="granite", hardness=5)
        ValuableTaggedItem.objects.create(
            content_object=granite, tag="countertop", value=1
        )
        self.assertEqual(ValuableRock.objects.filter(tags__value=1).count(), 1)
        # We're generating a slightly inefficient query for tags__tag - we
        # first join ValuableRock -> TaggedItem -> ValuableTaggedItem, and then
        # we fetch tag by joining TaggedItem from ValuableTaggedItem. The last
        # join isn't necessary, as TaggedItem <-> ValuableTaggedItem is a
        # one-to-one join.
        self.assertEqual(ValuableRock.objects.filter(tags__tag="countertop").count(), 1)
        granite.delete()  # deleting the rock should delete the related tag.
        self.assertEqual(ValuableTaggedItem.objects.count(), 0)

    def test_gfk_manager(self):
        # GenericForeignKey should not use the default manager (which may
        # filter objects).
        tailless = Gecko.objects.create(has_tail=False)
        tag = TaggedItem.objects.create(content_object=tailless, tag="lizard")
        self.assertEqual(tag.content_object, tailless)

    def test_subclasses_with_gen_rel(self):
        """
        Concrete model subclasses with generic relations work
        correctly (ticket 11263).
        """
        granite = Rock.objects.create(name="granite", hardness=5)
        TaggedItem.objects.create(content_object=granite, tag="countertop")
        self.assertEqual(Rock.objects.get(tags__tag="countertop"), granite)

    def test_subclasses_with_parent_gen_rel(self):
        """
        Generic relations on a base class (Vegetable) work correctly in
        subclasses (Carrot).
        """
        bear = Carrot.objects.create(name="carrot")
        TaggedItem.objects.create(content_object=bear, tag="orange")
        self.assertEqual(Carrot.objects.get(tags__tag="orange"), bear)

    def test_get_or_create(self):
        # get_or_create should work with virtual fields (content_object)
        quartz = Mineral.objects.create(name="Quartz", hardness=7)
        tag, created = TaggedItem.objects.get_or_create(
            tag="shiny", defaults={"content_object": quartz}
        )
        self.assertTrue(created)
        self.assertEqual(tag.tag, "shiny")
        self.assertEqual(tag.content_object.id, quartz.id)

    def test_update_or_create_defaults(self):
        # update_or_create should work with virtual fields (content_object)
        quartz = Mineral.objects.create(name="Quartz", hardness=7)
        diamond = Mineral.objects.create(name="Diamond", hardness=7)
        tag, created = TaggedItem.objects.update_or_create(
            tag="shiny", defaults={"content_object": quartz}
        )
        self.assertTrue(created)
        self.assertEqual(tag.content_object.id, quartz.id)

        tag, created = TaggedItem.objects.update_or_create(
            tag="shiny", defaults={"content_object": diamond}
        )
        self.assertFalse(created)
        self.assertEqual(tag.content_object.id, diamond.id)

    def test_query_content_type(self):
        msg = "Field 'content_object' does not generate an automatic reverse relation"
        with self.assertRaisesMessage(FieldError, msg):
            TaggedItem.objects.get(content_object="")

    def test_unsaved_generic_foreign_key_parent_save(self):
        quartz = Mineral(name="Quartz", hardness=7)
        tagged_item = TaggedItem(tag="shiny", content_object=quartz)
        msg = (
            "save() prohibited to prevent data loss due to unsaved related object "
            "'content_object'."
        )
        with self.assertRaisesMessage(ValueError, msg):
            tagged_item.save()

    @skipUnlessDBFeature("has_bulk_insert")
    def test_unsaved_generic_foreign_key_parent_bulk_create(self):
        quartz = Mineral(name="Quartz", hardness=7)
        tagged_item = TaggedItem(tag="shiny", content_object=quartz)
        msg = (
            "bulk_create() prohibited to prevent data loss due to unsaved related "
            "object 'content_object'."
        )
        with self.assertRaisesMessage(ValueError, msg):
            TaggedItem.objects.bulk_create([tagged_item])

    def test_cache_invalidation_for_content_type_id(self):
        # Create a Vegetable and Mineral with the same id.
        new_id = (
            max(
                Vegetable.objects.order_by("-id")[0].id,
                Mineral.objects.order_by("-id")[0].id,
            )
            + 1
        )
        broccoli = Vegetable.objects.create(id=new_id, name="Broccoli")
        diamond = Mineral.objects.create(id=new_id, name="Diamond", hardness=7)
        tag = TaggedItem.objects.create(content_object=broccoli, tag="yummy")
        tag.content_type = ContentType.objects.get_for_model(diamond)
        self.assertEqual(tag.content_object, diamond)

    def test_cache_invalidation_for_object_id(self):
        broccoli = Vegetable.objects.create(name="Broccoli")
        cauliflower = Vegetable.objects.create(name="Cauliflower")
        tag = TaggedItem.objects.create(content_object=broccoli, tag="yummy")
        tag.object_id = cauliflower.id
        self.assertEqual(tag.content_object, cauliflower)

    def test_assign_content_object_in_init(self):
        spinach = Vegetable(name="spinach")
        tag = TaggedItem(content_object=spinach)
        self.assertEqual(tag.content_object, spinach)

    def test_create_after_prefetch(self):
        platypus = Animal.objects.prefetch_related("tags").get(pk=self.platypus.pk)
        self.assertSequenceEqual(platypus.tags.all(), [])
        weird_tag = platypus.tags.create(tag="weird")
        self.assertSequenceEqual(platypus.tags.all(), [weird_tag])

    def test_add_after_prefetch(self):
        platypus = Animal.objects.prefetch_related("tags").get(pk=self.platypus.pk)
        self.assertSequenceEqual(platypus.tags.all(), [])
        weird_tag = TaggedItem.objects.create(tag="weird", content_object=platypus)
        platypus.tags.add(weird_tag)
        self.assertSequenceEqual(platypus.tags.all(), [weird_tag])

    def test_remove_after_prefetch(self):
        weird_tag = self.platypus.tags.create(tag="weird")
        platypus = Animal.objects.prefetch_related("tags").get(pk=self.platypus.pk)
        self.assertSequenceEqual(platypus.tags.all(), [weird_tag])
        platypus.tags.remove(weird_tag)
        self.assertSequenceEqual(platypus.tags.all(), [])

    def test_clear_after_prefetch(self):
        weird_tag = self.platypus.tags.create(tag="weird")
        platypus = Animal.objects.prefetch_related("tags").get(pk=self.platypus.pk)
        self.assertSequenceEqual(platypus.tags.all(), [weird_tag])
        platypus.tags.clear()
        self.assertSequenceEqual(platypus.tags.all(), [])

    def test_set_after_prefetch(self):
        platypus = Animal.objects.prefetch_related("tags").get(pk=self.platypus.pk)
        self.assertSequenceEqual(platypus.tags.all(), [])
        furry_tag = TaggedItem.objects.create(tag="furry", content_object=platypus)
        platypus.tags.set([furry_tag])
        self.assertSequenceEqual(platypus.tags.all(), [furry_tag])
        weird_tag = TaggedItem.objects.create(tag="weird", content_object=platypus)
        platypus.tags.set([weird_tag])
        self.assertSequenceEqual(platypus.tags.all(), [weird_tag])

    def test_add_then_remove_after_prefetch(self):
        furry_tag = self.platypus.tags.create(tag="furry")
        platypus = Animal.objects.prefetch_related("tags").get(pk=self.platypus.pk)
        self.assertSequenceEqual(platypus.tags.all(), [furry_tag])
        weird_tag = self.platypus.tags.create(tag="weird")
        platypus.tags.add(weird_tag)
        self.assertSequenceEqual(platypus.tags.all(), [furry_tag, weird_tag])
        platypus.tags.remove(weird_tag)
        self.assertSequenceEqual(platypus.tags.all(), [furry_tag])

    def test_prefetch_related_different_content_types(self):
        TaggedItem.objects.create(content_object=self.platypus, tag="prefetch_tag_1")
        TaggedItem.objects.create(
            content_object=Vegetable.objects.create(name="Broccoli"),
            tag="prefetch_tag_2",
        )
        TaggedItem.objects.create(
            content_object=Animal.objects.create(common_name="Bear"),
            tag="prefetch_tag_3",
        )
        qs = TaggedItem.objects.filter(
            tag__startswith="prefetch_tag_",
        ).prefetch_related("content_object", "content_object__tags")
        with self.assertNumQueries(4):
            tags = list(qs)
        for tag in tags:
            self.assertSequenceEqual(tag.content_object.tags.all(), [tag])

    def test_prefetch_related_custom_object_id(self):
        tiger = Animal.objects.create(common_name="tiger")
        cheetah = Animal.objects.create(common_name="cheetah")
        Comparison.objects.create(
            first_obj=cheetah,
            other_obj=tiger,
            comparative="faster",
        )
        Comparison.objects.create(
            first_obj=tiger,
            other_obj=cheetah,
            comparative="cooler",
        )
        qs = Comparison.objects.prefetch_related("first_obj__comparisons")
        for comparison in qs:
            self.assertSequenceEqual(
                comparison.first_obj.comparisons.all(), [comparison]
            )


class ProxyRelatedModelTest(TestCase):
    def test_default_behavior(self):
        """
        The default for for_concrete_model should be True
        """
        base = ForConcreteModelModel()
        base.obj = rel = ProxyRelatedModel.objects.create()
        base.save()

        base = ForConcreteModelModel.objects.get(pk=base.pk)
        rel = ConcreteRelatedModel.objects.get(pk=rel.pk)
        self.assertEqual(base.obj, rel)

    def test_works_normally(self):
        """
        When for_concrete_model is False, we should still be able to get
        an instance of the concrete class.
        """
        base = ForProxyModelModel()
        base.obj = rel = ConcreteRelatedModel.objects.create()
        base.save()

        base = ForProxyModelModel.objects.get(pk=base.pk)
        self.assertEqual(base.obj, rel)

    def test_proxy_is_returned(self):
        """
        Instances of the proxy should be returned when
        for_concrete_model is False.
        """
        base = ForProxyModelModel()
        base.obj = ProxyRelatedModel.objects.create()
        base.save()

        base = ForProxyModelModel.objects.get(pk=base.pk)
        self.assertIsInstance(base.obj, ProxyRelatedModel)

    def test_query(self):
        base = ForProxyModelModel()
        base.obj = rel = ConcreteRelatedModel.objects.create()
        base.save()

        self.assertEqual(rel, ConcreteRelatedModel.objects.get(bases__id=base.id))

    def test_query_proxy(self):
        base = ForProxyModelModel()
        base.obj = rel = ProxyRelatedModel.objects.create()
        base.save()

        self.assertEqual(rel, ProxyRelatedModel.objects.get(bases__id=base.id))

    def test_generic_relation(self):
        base = ForProxyModelModel()
        base.obj = ProxyRelatedModel.objects.create()
        base.save()

        base = ForProxyModelModel.objects.get(pk=base.pk)
        rel = ProxyRelatedModel.objects.get(pk=base.obj.pk)
        self.assertEqual(base, rel.bases.get())

    def test_generic_relation_set(self):
        base = ForProxyModelModel()
        base.obj = ConcreteRelatedModel.objects.create()
        base.save()
        newrel = ConcreteRelatedModel.objects.create()

        newrel.bases.set([base])
        newrel = ConcreteRelatedModel.objects.get(pk=newrel.pk)
        self.assertEqual(base, newrel.bases.get())


class TestInitWithNoneArgument(SimpleTestCase):
    def test_none_allowed(self):
        # AllowsNullGFK doesn't require a content_type, so None argument should
        # also be allowed.
        AllowsNullGFK(content_object=None)
        # TaggedItem requires a content_type but initializing with None should
        # be allowed.
        TaggedItem(content_object=None)
