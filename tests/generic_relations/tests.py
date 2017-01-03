from __future__ import unicode_literals

from django import forms
from django.contrib.contenttypes.forms import generic_inlineformset_factory
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import FieldError
from django.db import IntegrityError
from django.db.models import Q
from django.test import SimpleTestCase, TestCase

from .models import (
    AllowsNullGFK, Animal, Carrot, Comparison, ConcreteRelatedModel,
    ForConcreteModelModel, ForProxyModelModel, Gecko, ManualPK, Mineral,
    ProxyRelatedModel, Rock, TaggedItem, ValuableRock, ValuableTaggedItem,
    Vegetable,
)


class GenericRelationsTests(TestCase):
    def setUp(self):
        self.lion = Animal.objects.create(
            common_name="Lion", latin_name="Panthera leo")
        self.platypus = Animal.objects.create(
            common_name="Platypus", latin_name="Ornithorhynchus anatinus")
        Vegetable.objects.create(name="Eggplant", is_yucky=True)
        self.bacon = Vegetable.objects.create(name="Bacon", is_yucky=False)
        self.quartz = Mineral.objects.create(name="Quartz", hardness=7)

        # Tagging stuff.
        self.bacon.tags.create(tag="fatty")
        self.bacon.tags.create(tag="salty")
        self.lion.tags.create(tag="yellow")
        self.lion.tags.create(tag="hairy")

        # Original list of tags:
        self.comp_func = lambda obj: (
            obj.tag, obj.content_type.model_class(), obj.object_id
        )

    def test_generic_update_or_create_when_created(self):
        """
        Should be able to use update_or_create from the generic related manager
        to create a tag. Refs #23611.
        """
        count = self.bacon.tags.count()
        tag, created = self.bacon.tags.update_or_create(tag='stinky')
        self.assertTrue(created)
        self.assertEqual(count + 1, self.bacon.tags.count())

    def test_generic_update_or_create_when_updated(self):
        """
        Should be able to use update_or_create from the generic related manager
        to update a tag. Refs #23611.
        """
        count = self.bacon.tags.count()
        tag = self.bacon.tags.create(tag='stinky')
        self.assertEqual(count + 1, self.bacon.tags.count())
        tag, created = self.bacon.tags.update_or_create(defaults={'tag': 'juicy'}, id=tag.id)
        self.assertFalse(created)
        self.assertEqual(count + 1, self.bacon.tags.count())
        self.assertEqual(tag.tag, 'juicy')

    def test_generic_get_or_create_when_created(self):
        """
        Should be able to use get_or_create from the generic related manager
        to create a tag. Refs #23611.
        """
        count = self.bacon.tags.count()
        tag, created = self.bacon.tags.get_or_create(tag='stinky')
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
        tag, created = self.bacon.tags.get_or_create(id=tag.id, defaults={'tag': 'juicy'})
        self.assertFalse(created)
        self.assertEqual(count + 1, self.bacon.tags.count())
        # shouldn't had changed the tag
        self.assertEqual(tag.tag, 'stinky')

    def test_generic_relations_m2m_mimic(self):
        """
        Objects with declared GenericRelations can be tagged directly -- the
        API mimics the many-to-many API.
        """
        self.assertQuerysetEqual(self.lion.tags.all(), [
            "<TaggedItem: hairy>",
            "<TaggedItem: yellow>"
        ])
        self.assertQuerysetEqual(self.bacon.tags.all(), [
            "<TaggedItem: fatty>",
            "<TaggedItem: salty>"
        ])

    def test_access_content_object(self):
        """
        Test accessing the content object like a foreign key.
        """
        tagged_item = TaggedItem.objects.get(tag="salty")
        self.assertEqual(tagged_item.content_object, self.bacon)

    def test_query_content_object(self):
        qs = TaggedItem.objects.filter(
            animal__isnull=False).order_by('animal__common_name', 'tag')
        self.assertQuerysetEqual(
            qs, ["<TaggedItem: hairy>", "<TaggedItem: yellow>"]
        )

        mpk = ManualPK.objects.create(id=1)
        mpk.tags.create(tag='mpk')
        qs = TaggedItem.objects.filter(
            Q(animal__isnull=False) | Q(manualpk__id=1)).order_by('tag')
        self.assertQuerysetEqual(
            qs, ["hairy", "mpk", "yellow"], lambda x: x.tag)

    def test_exclude_generic_relations(self):
        """
        Test lookups over an object without GenericRelations.
        """
        # Recall that the Mineral class doesn't have an explicit GenericRelation
        # defined. That's OK, because you can create TaggedItems explicitly.
        # However, excluding GenericRelations means your lookups have to be a
        # bit more explicit.
        TaggedItem.objects.create(content_object=self.quartz, tag="shiny")
        TaggedItem.objects.create(content_object=self.quartz, tag="clearish")

        ctype = ContentType.objects.get_for_model(self.quartz)
        q = TaggedItem.objects.filter(
            content_type__pk=ctype.id, object_id=self.quartz.id
        )
        self.assertQuerysetEqual(q, [
            "<TaggedItem: clearish>",
            "<TaggedItem: shiny>"
        ])

    def test_access_via_content_type(self):
        """
        Test lookups through content type.
        """
        self.lion.delete()
        self.platypus.tags.create(tag="fatty")

        ctype = ContentType.objects.get_for_model(self.platypus)

        self.assertQuerysetEqual(
            Animal.objects.filter(tags__content_type=ctype),
            ["<Animal: Platypus>"])

    def test_set_foreign_key(self):
        """
        You can set a generic foreign key in the way you'd expect.
        """
        tag1 = TaggedItem.objects.create(content_object=self.quartz, tag="shiny")
        tag1.content_object = self.platypus
        tag1.save()

        self.assertQuerysetEqual(
            self.platypus.tags.all(),
            ["<TaggedItem: shiny>"])

    def test_queries_across_generic_relations(self):
        """
        Queries across generic relations respect the content types. Even though
        there are two TaggedItems with a tag of "fatty", this query only pulls
        out the one with the content type related to Animals.
        """
        self.assertQuerysetEqual(Animal.objects.order_by('common_name'), [
            "<Animal: Lion>",
            "<Animal: Platypus>"
        ])

    def test_queries_content_type_restriction(self):
        """
        Create another fatty tagged instance with different PK to ensure there
        is a content type restriction in the generated queries below.
        """
        mpk = ManualPK.objects.create(id=self.lion.pk)
        mpk.tags.create(tag="fatty")
        self.platypus.tags.create(tag="fatty")

        self.assertQuerysetEqual(
            Animal.objects.filter(tags__tag='fatty'), ["<Animal: Platypus>"])
        self.assertQuerysetEqual(
            Animal.objects.exclude(tags__tag='fatty'), ["<Animal: Lion>"])

    def test_object_deletion_with_generic_relation(self):
        """
        If you delete an object with an explicit Generic relation, the related
        objects are deleted when the source object is deleted.
        """
        self.assertQuerysetEqual(TaggedItem.objects.all(), [
            ('fatty', Vegetable, self.bacon.pk),
            ('hairy', Animal, self.lion.pk),
            ('salty', Vegetable, self.bacon.pk),
            ('yellow', Animal, self.lion.pk)
        ],
            self.comp_func
        )
        self.lion.delete()

        self.assertQuerysetEqual(TaggedItem.objects.all(), [
            ('fatty', Vegetable, self.bacon.pk),
            ('salty', Vegetable, self.bacon.pk),
        ],
            self.comp_func
        )

    def test_object_deletion_without_generic_relation(self):
        """
        If Generic Relation is not explicitly defined, any related objects
        remain after deletion of the source object.
        """
        TaggedItem.objects.create(content_object=self.quartz, tag="clearish")
        quartz_pk = self.quartz.pk
        self.quartz.delete()
        self.assertQuerysetEqual(TaggedItem.objects.all(), [
            ('clearish', Mineral, quartz_pk),
            ('fatty', Vegetable, self.bacon.pk),
            ('hairy', Animal, self.lion.pk),
            ('salty', Vegetable, self.bacon.pk),
            ('yellow', Animal, self.lion.pk),
        ],
            self.comp_func
        )

    def test_tag_deletion_related_objects_unaffected(self):
        """
        If you delete a tag, the objects using the tag are unaffected (other
        than losing a tag).
        """
        ctype = ContentType.objects.get_for_model(self.lion)
        tag = TaggedItem.objects.get(
            content_type__pk=ctype.id, object_id=self.lion.id, tag="hairy")
        tag.delete()

        self.assertQuerysetEqual(self.lion.tags.all(), ["<TaggedItem: yellow>"])
        self.assertQuerysetEqual(TaggedItem.objects.all(), [
            ('fatty', Vegetable, self.bacon.pk),
            ('salty', Vegetable, self.bacon.pk),
            ('yellow', Animal, self.lion.pk)
        ],
            self.comp_func
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
        msg = "<TaggedItem: shiny> instance isn't saved. Use bulk=False or save the object first."
        with self.assertRaisesMessage(ValueError, msg):
            self.bacon.tags.add(t1)

    def test_set(self):
        bacon = Vegetable.objects.create(name="Bacon", is_yucky=False)
        fatty = bacon.tags.create(tag="fatty")
        salty = bacon.tags.create(tag="salty")

        bacon.tags.set([fatty, salty])
        self.assertQuerysetEqual(bacon.tags.all(), [
            "<TaggedItem: fatty>",
            "<TaggedItem: salty>",
        ])

        bacon.tags.set([fatty])
        self.assertQuerysetEqual(bacon.tags.all(), [
            "<TaggedItem: fatty>",
        ])

        bacon.tags.set([])
        self.assertQuerysetEqual(bacon.tags.all(), [])

        bacon.tags.set([fatty, salty], bulk=False, clear=True)
        self.assertQuerysetEqual(bacon.tags.all(), [
            "<TaggedItem: fatty>",
            "<TaggedItem: salty>",
        ])

        bacon.tags.set([fatty], bulk=False, clear=True)
        self.assertQuerysetEqual(bacon.tags.all(), [
            "<TaggedItem: fatty>",
        ])

        bacon.tags.set([], clear=True)
        self.assertQuerysetEqual(bacon.tags.all(), [])

    def test_assign(self):
        bacon = Vegetable.objects.create(name="Bacon", is_yucky=False)
        fatty = bacon.tags.create(tag="fatty")
        salty = bacon.tags.create(tag="salty")

        bacon.tags.set([fatty, salty])
        self.assertQuerysetEqual(bacon.tags.all(), [
            "<TaggedItem: fatty>",
            "<TaggedItem: salty>",
        ])

        bacon.tags.set([fatty])
        self.assertQuerysetEqual(bacon.tags.all(), [
            "<TaggedItem: fatty>",
        ])

        bacon.tags.set([])
        self.assertQuerysetEqual(bacon.tags.all(), [])

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

    def test_generic_relation_related_name_default(self):
        # GenericRelation isn't usable from the reverse side by default.
        with self.assertRaises(FieldError):
            TaggedItem.objects.filter(vegetable__isnull=True)

    def test_multiple_gfk(self):
        # Simple tests for multiple GenericForeignKeys
        # only uses one model, since the above tests should be sufficient.
        tiger = Animal.objects.create(common_name="tiger")
        cheetah = Animal.objects.create(common_name="cheetah")
        bear = Animal.objects.create(common_name="bear")

        # Create directly
        Comparison.objects.create(
            first_obj=cheetah, other_obj=tiger, comparative="faster"
        )
        Comparison.objects.create(
            first_obj=tiger, other_obj=cheetah, comparative="cooler"
        )

        # Create using GenericRelation
        tiger.comparisons.create(other_obj=bear, comparative="cooler")
        tiger.comparisons.create(other_obj=cheetah, comparative="stronger")
        self.assertQuerysetEqual(cheetah.comparisons.all(), [
            "<Comparison: cheetah is faster than tiger>"
        ])

        # Filtering works
        self.assertQuerysetEqual(tiger.comparisons.filter(comparative="cooler"), [
            "<Comparison: tiger is cooler than cheetah>",
            "<Comparison: tiger is cooler than bear>",
        ], ordered=False)

        # Filtering and deleting works
        subjective = ["cooler"]
        tiger.comparisons.filter(comparative__in=subjective).delete()
        self.assertQuerysetEqual(Comparison.objects.all(), [
            "<Comparison: cheetah is faster than tiger>",
            "<Comparison: tiger is stronger than cheetah>"
        ], ordered=False)

        # If we delete cheetah, Comparisons with cheetah as 'first_obj' will be
        # deleted since Animal has an explicit GenericRelation to Comparison
        # through first_obj. Comparisons with cheetah as 'other_obj' will not
        # be deleted.
        cheetah.delete()
        self.assertQuerysetEqual(Comparison.objects.all(), [
            "<Comparison: tiger is stronger than None>"
        ])

    def test_gfk_subclasses(self):
        # GenericForeignKey should work with subclasses (see #8309)
        quartz = Mineral.objects.create(name="Quartz", hardness=7)
        valuedtag = ValuableTaggedItem.objects.create(
            content_object=quartz, tag="shiny", value=10
        )
        self.assertEqual(valuedtag.content_object, quartz)

    def test_generic_relation_to_inherited_child(self):
        # GenericRelations to models that use multi-table inheritance work.
        granite = ValuableRock.objects.create(name='granite', hardness=5)
        ValuableTaggedItem.objects.create(content_object=granite, tag="countertop", value=1)
        self.assertEqual(ValuableRock.objects.filter(tags__value=1).count(), 1)
        # We're generating a slightly inefficient query for tags__tag - we
        # first join ValuableRock -> TaggedItem -> ValuableTaggedItem, and then
        # we fetch tag by joining TaggedItem from ValuableTaggedItem. The last
        # join isn't necessary, as TaggedItem <-> ValuableTaggedItem is a
        # one-to-one join.
        self.assertEqual(ValuableRock.objects.filter(tags__tag="countertop").count(), 1)
        granite.delete()  # deleting the rock should delete the related tag.
        self.assertEqual(ValuableTaggedItem.objects.count(), 0)

    def test_generic_inline_formsets(self):
        GenericFormSet = generic_inlineformset_factory(TaggedItem, extra=1)
        formset = GenericFormSet()
        self.assertHTMLEqual(
            ''.join(form.as_p() for form in formset.forms),
            """<p><label for="id_generic_relations-taggeditem-content_type-object_id-0-tag">
Tag:</label> <input id="id_generic_relations-taggeditem-content_type-object_id-0-tag" type="text"
name="generic_relations-taggeditem-content_type-object_id-0-tag" maxlength="50" /></p>
<p><label for="id_generic_relations-taggeditem-content_type-object_id-0-DELETE">Delete:</label>
<input type="checkbox" name="generic_relations-taggeditem-content_type-object_id-0-DELETE"
id="id_generic_relations-taggeditem-content_type-object_id-0-DELETE" />
<input type="hidden" name="generic_relations-taggeditem-content_type-object_id-0-id"
id="id_generic_relations-taggeditem-content_type-object_id-0-id" /></p>"""
        )

        formset = GenericFormSet(instance=Animal())
        self.assertHTMLEqual(
            ''.join(form.as_p() for form in formset.forms),
            """<p><label for="id_generic_relations-taggeditem-content_type-object_id-0-tag">
Tag:</label> <input id="id_generic_relations-taggeditem-content_type-object_id-0-tag"
type="text" name="generic_relations-taggeditem-content_type-object_id-0-tag" maxlength="50" /></p>
<p><label for="id_generic_relations-taggeditem-content_type-object_id-0-DELETE">Delete:</label>
<input type="checkbox" name="generic_relations-taggeditem-content_type-object_id-0-DELETE"
id="id_generic_relations-taggeditem-content_type-object_id-0-DELETE" /><input type="hidden"
name="generic_relations-taggeditem-content_type-object_id-0-id"
id="id_generic_relations-taggeditem-content_type-object_id-0-id" /></p>"""
        )

        platypus = Animal.objects.create(
            common_name="Platypus", latin_name="Ornithorhynchus anatinus"
        )
        platypus.tags.create(tag="shiny")
        GenericFormSet = generic_inlineformset_factory(TaggedItem, extra=1)
        formset = GenericFormSet(instance=platypus)
        tagged_item_id = TaggedItem.objects.get(
            tag='shiny', object_id=platypus.id
        ).id
        self.assertHTMLEqual(
            ''.join(form.as_p() for form in formset.forms),
            """<p><label for="id_generic_relations-taggeditem-content_type-object_id-0-tag">Tag:</label>
<input id="id_generic_relations-taggeditem-content_type-object_id-0-tag" type="text"
name="generic_relations-taggeditem-content_type-object_id-0-tag" value="shiny" maxlength="50" /></p>
<p><label for="id_generic_relations-taggeditem-content_type-object_id-0-DELETE">Delete:</label>
<input type="checkbox" name="generic_relations-taggeditem-content_type-object_id-0-DELETE"
id="id_generic_relations-taggeditem-content_type-object_id-0-DELETE" />
<input type="hidden" name="generic_relations-taggeditem-content_type-object_id-0-id"
value="%s" id="id_generic_relations-taggeditem-content_type-object_id-0-id" /></p>
<p><label for="id_generic_relations-taggeditem-content_type-object_id-1-tag">Tag:</label>
<input id="id_generic_relations-taggeditem-content_type-object_id-1-tag" type="text"
name="generic_relations-taggeditem-content_type-object_id-1-tag" maxlength="50" /></p>
<p><label for="id_generic_relations-taggeditem-content_type-object_id-1-DELETE">Delete:</label>
<input type="checkbox" name="generic_relations-taggeditem-content_type-object_id-1-DELETE"
id="id_generic_relations-taggeditem-content_type-object_id-1-DELETE" />
<input type="hidden" name="generic_relations-taggeditem-content_type-object_id-1-id"
id="id_generic_relations-taggeditem-content_type-object_id-1-id" /></p>""" % tagged_item_id
        )

        lion = Animal.objects.create(common_name="Lion", latin_name="Panthera leo")
        formset = GenericFormSet(instance=lion, prefix='x')
        self.assertHTMLEqual(
            ''.join(form.as_p() for form in formset.forms),
            """<p><label for="id_x-0-tag">Tag:</label>
<input id="id_x-0-tag" type="text" name="x-0-tag" maxlength="50" /></p>
<p><label for="id_x-0-DELETE">Delete:</label> <input type="checkbox" name="x-0-DELETE" id="id_x-0-DELETE" />
<input type="hidden" name="x-0-id" id="id_x-0-id" /></p>"""
        )

    def test_gfk_manager(self):
        # GenericForeignKey should not use the default manager (which may filter objects) #16048
        tailless = Gecko.objects.create(has_tail=False)
        tag = TaggedItem.objects.create(content_object=tailless, tag="lizard")
        self.assertEqual(tag.content_object, tailless)

    def test_subclasses_with_gen_rel(self):
        """
        Concrete model subclasses with generic relations work
        correctly (ticket 11263).
        """
        granite = Rock.objects.create(name='granite', hardness=5)
        TaggedItem.objects.create(content_object=granite, tag="countertop")
        self.assertEqual(Rock.objects.get(tags__tag="countertop"), granite)

    def test_subclasses_with_parent_gen_rel(self):
        """
        Generic relations on a base class (Vegetable) work correctly in
        subclasses (Carrot).
        """
        bear = Carrot.objects.create(name='carrot')
        TaggedItem.objects.create(content_object=bear, tag='orange')
        self.assertEqual(Carrot.objects.get(tags__tag='orange'), bear)

    def test_generic_inline_formsets_initial(self):
        """
        Test for #17927 Initial values support for BaseGenericInlineFormSet.
        """
        quartz = Mineral.objects.create(name="Quartz", hardness=7)

        GenericFormSet = generic_inlineformset_factory(TaggedItem, extra=1)
        ctype = ContentType.objects.get_for_model(quartz)
        initial_data = [{
            'tag': 'lizard',
            'content_type': ctype.pk,
            'object_id': quartz.pk,
        }]
        formset = GenericFormSet(initial=initial_data)
        self.assertEqual(formset.forms[0].initial, initial_data[0])

    def test_get_or_create(self):
        # get_or_create should work with virtual fields (content_object)
        quartz = Mineral.objects.create(name="Quartz", hardness=7)
        tag, created = TaggedItem.objects.get_or_create(tag="shiny", defaults={'content_object': quartz})
        self.assertTrue(created)
        self.assertEqual(tag.tag, "shiny")
        self.assertEqual(tag.content_object.id, quartz.id)

    def test_update_or_create_defaults(self):
        # update_or_create should work with virtual fields (content_object)
        quartz = Mineral.objects.create(name="Quartz", hardness=7)
        diamond = Mineral.objects.create(name="Diamond", hardness=7)
        tag, created = TaggedItem.objects.update_or_create(tag="shiny", defaults={'content_object': quartz})
        self.assertTrue(created)
        self.assertEqual(tag.content_object.id, quartz.id)

        tag, created = TaggedItem.objects.update_or_create(tag="shiny", defaults={'content_object': diamond})
        self.assertFalse(created)
        self.assertEqual(tag.content_object.id, diamond.id)

    def test_query_content_type(self):
        msg = "Field 'content_object' does not generate an automatic reverse relation"
        with self.assertRaisesMessage(FieldError, msg):
            TaggedItem.objects.get(content_object='')

    def test_unsaved_instance_on_generic_foreign_key(self):
        """
        Assigning an unsaved object to GenericForeignKey should raise an
        exception on model.save().
        """
        quartz = Mineral(name="Quartz", hardness=7)
        with self.assertRaises(IntegrityError):
            TaggedItem.objects.create(tag="shiny", content_object=quartz)

    def test_cache_invalidation_for_content_type_id(self):
        # Create a Vegetable and Mineral with the same id.
        new_id = max(Vegetable.objects.order_by('-id')[0].id,
                     Mineral.objects.order_by('-id')[0].id) + 1
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


class CustomWidget(forms.TextInput):
    pass


class TaggedItemForm(forms.ModelForm):
    class Meta:
        model = TaggedItem
        fields = '__all__'
        widgets = {'tag': CustomWidget}


class GenericInlineFormsetTest(TestCase):
    def test_generic_inlineformset_factory(self):
        """
        Regression for #14572: Using base forms with widgets
        defined in Meta should not raise errors.
        """
        Formset = generic_inlineformset_factory(TaggedItem, TaggedItemForm)
        form = Formset().forms[0]
        self.assertIsInstance(form['tag'].field.widget, CustomWidget)

    def test_save_new_uses_form_save(self):
        """
        Regression for #16260: save_new should call form.save()
        """
        class SaveTestForm(forms.ModelForm):
            def save(self, *args, **kwargs):
                self.instance.saved_by = "custom method"
                return super(SaveTestForm, self).save(*args, **kwargs)

        Formset = generic_inlineformset_factory(ForProxyModelModel, fields='__all__', form=SaveTestForm)

        instance = ProxyRelatedModel.objects.create()

        data = {
            'form-TOTAL_FORMS': '1',
            'form-INITIAL_FORMS': '0',
            'form-MAX_NUM_FORMS': '',
            'form-0-title': 'foo',
        }

        formset = Formset(data, instance=instance, prefix='form')
        self.assertTrue(formset.is_valid())
        new_obj = formset.save()[0]
        self.assertEqual(new_obj.saved_by, "custom method")

    def test_save_new_for_proxy(self):
        Formset = generic_inlineformset_factory(ForProxyModelModel, fields='__all__', for_concrete_model=False)

        instance = ProxyRelatedModel.objects.create()

        data = {
            'form-TOTAL_FORMS': '1',
            'form-INITIAL_FORMS': '0',
            'form-MAX_NUM_FORMS': '',
            'form-0-title': 'foo',
        }

        formset = Formset(data, instance=instance, prefix='form')
        self.assertTrue(formset.is_valid())

        new_obj, = formset.save()
        self.assertEqual(new_obj.obj, instance)

    def test_save_new_for_concrete(self):
        Formset = generic_inlineformset_factory(ForProxyModelModel, fields='__all__', for_concrete_model=True)

        instance = ProxyRelatedModel.objects.create()

        data = {
            'form-TOTAL_FORMS': '1',
            'form-INITIAL_FORMS': '0',
            'form-MAX_NUM_FORMS': '',
            'form-0-title': 'foo',
        }

        formset = Formset(data, instance=instance, prefix='form')
        self.assertTrue(formset.is_valid())

        new_obj, = formset.save()
        self.assertNotIsInstance(new_obj.obj, ProxyRelatedModel)


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
