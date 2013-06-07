from __future__ import absolute_import, unicode_literals

from django import forms
from django.contrib.contenttypes.generic import generic_inlineformset_factory
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from .models import (TaggedItem, ValuableTaggedItem, Comparison, Animal,
                     Vegetable, Mineral, Gecko, Rock, ManualPK,
                     ForProxyModelModel, ForConcreteModelModel,
                     ProxyRelatedModel, ConcreteRelatedModel)


class GenericRelationsTests(TestCase):
    def test_generic_relations(self):
        # Create the world in 7 lines of code...
        lion = Animal.objects.create(common_name="Lion", latin_name="Panthera leo")
        platypus = Animal.objects.create(
            common_name="Platypus", latin_name="Ornithorhynchus anatinus"
        )
        eggplant = Vegetable.objects.create(name="Eggplant", is_yucky=True)
        bacon = Vegetable.objects.create(name="Bacon", is_yucky=False)
        quartz = Mineral.objects.create(name="Quartz", hardness=7)

        # Objects with declared GenericRelations can be tagged directly -- the
        # API mimics the many-to-many API.
        bacon.tags.create(tag="fatty")
        bacon.tags.create(tag="salty")
        lion.tags.create(tag="yellow")
        lion.tags.create(tag="hairy")
        platypus.tags.create(tag="fatty")
        self.assertQuerysetEqual(lion.tags.all(), [
            "<TaggedItem: hairy>",
            "<TaggedItem: yellow>"
        ])
        self.assertQuerysetEqual(bacon.tags.all(), [
            "<TaggedItem: fatty>",
            "<TaggedItem: salty>"
        ])

        # You can easily access the content object like a foreign key.
        t = TaggedItem.objects.get(tag="salty")
        self.assertEqual(t.content_object, bacon)

        # Recall that the Mineral class doesn't have an explicit GenericRelation
        # defined. That's OK, because you can create TaggedItems explicitly.
        tag1 = TaggedItem.objects.create(content_object=quartz, tag="shiny")
        tag2 = TaggedItem.objects.create(content_object=quartz, tag="clearish")

        # However, excluding GenericRelations means your lookups have to be a
        # bit more explicit.
        ctype = ContentType.objects.get_for_model(quartz)
        q = TaggedItem.objects.filter(
            content_type__pk=ctype.id, object_id=quartz.id
        )
        self.assertQuerysetEqual(q, [
            "<TaggedItem: clearish>",
            "<TaggedItem: shiny>"
        ])

        # You can set a generic foreign key in the way you'd expect.
        tag1.content_object = platypus
        tag1.save()
        self.assertQuerysetEqual(platypus.tags.all(), [
            "<TaggedItem: fatty>",
            "<TaggedItem: shiny>"
        ])
        q = TaggedItem.objects.filter(
            content_type__pk=ctype.id, object_id=quartz.id
        )
        self.assertQuerysetEqual(q, ["<TaggedItem: clearish>"])

        # Queries across generic relations respect the content types. Even
        # though there are two TaggedItems with a tag of "fatty", this query
        # only pulls out the one with the content type related to Animals.
        self.assertQuerysetEqual(Animal.objects.order_by('common_name'), [
            "<Animal: Lion>",
            "<Animal: Platypus>"
        ])
        # Create another fatty tagged instance with different PK to ensure
        # there is a content type restriction in the generated queries below.
        mpk = ManualPK.objects.create(id=lion.pk)
        mpk.tags.create(tag="fatty")
        self.assertQuerysetEqual(Animal.objects.filter(tags__tag='fatty'), [
            "<Animal: Platypus>"
        ])
        self.assertQuerysetEqual(Animal.objects.exclude(tags__tag='fatty'), [
            "<Animal: Lion>"
        ])
        mpk.delete()

        # If you delete an object with an explicit Generic relation, the related
        # objects are deleted when the source object is deleted.
        # Original list of tags:
        comp_func = lambda obj: (
            obj.tag, obj.content_type.model_class(), obj.object_id
        )

        self.assertQuerysetEqual(TaggedItem.objects.all(), [
                ('clearish', Mineral, quartz.pk),
                ('fatty', Animal, platypus.pk),
                ('fatty', Vegetable, bacon.pk),
                ('hairy', Animal, lion.pk),
                ('salty', Vegetable, bacon.pk),
                ('shiny', Animal, platypus.pk),
                ('yellow', Animal, lion.pk)
            ],
            comp_func
        )
        lion.delete()
        self.assertQuerysetEqual(TaggedItem.objects.all(), [
                ('clearish', Mineral, quartz.pk),
                ('fatty', Animal, platypus.pk),
                ('fatty', Vegetable, bacon.pk),
                ('salty', Vegetable, bacon.pk),
                ('shiny', Animal, platypus.pk)
            ],
            comp_func
        )

        # If Generic Relation is not explicitly defined, any related objects
        # remain after deletion of the source object.
        quartz_pk = quartz.pk
        quartz.delete()
        self.assertQuerysetEqual(TaggedItem.objects.all(), [
                ('clearish', Mineral, quartz_pk),
                ('fatty', Animal, platypus.pk),
                ('fatty', Vegetable, bacon.pk),
                ('salty', Vegetable, bacon.pk),
                ('shiny', Animal, platypus.pk)
            ],
            comp_func
        )
        # If you delete a tag, the objects using the tag are unaffected
        # (other than losing a tag)
        tag = TaggedItem.objects.order_by("id")[0]
        tag.delete()
        self.assertQuerysetEqual(bacon.tags.all(), ["<TaggedItem: salty>"])
        self.assertQuerysetEqual(TaggedItem.objects.all(), [
                ('clearish', Mineral, quartz_pk),
                ('fatty', Animal, platypus.pk),
                ('salty', Vegetable, bacon.pk),
                ('shiny', Animal, platypus.pk)
            ],
            comp_func
        )
        TaggedItem.objects.filter(tag='fatty').delete()
        ctype = ContentType.objects.get_for_model(lion)
        self.assertQuerysetEqual(Animal.objects.filter(tags__content_type=ctype), [
            "<Animal: Platypus>"
        ])


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

    def test_generic_inline_formsets(self):
        GenericFormSet = generic_inlineformset_factory(TaggedItem, extra=1)
        formset = GenericFormSet()
        self.assertHTMLEqual(''.join(form.as_p() for form in formset.forms), """<p><label for="id_generic_relations-taggeditem-content_type-object_id-0-tag">Tag:</label> <input id="id_generic_relations-taggeditem-content_type-object_id-0-tag" type="text" name="generic_relations-taggeditem-content_type-object_id-0-tag" maxlength="50" /></p>
<p><label for="id_generic_relations-taggeditem-content_type-object_id-0-DELETE">Delete:</label> <input type="checkbox" name="generic_relations-taggeditem-content_type-object_id-0-DELETE" id="id_generic_relations-taggeditem-content_type-object_id-0-DELETE" /><input type="hidden" name="generic_relations-taggeditem-content_type-object_id-0-id" id="id_generic_relations-taggeditem-content_type-object_id-0-id" /></p>""")

        formset = GenericFormSet(instance=Animal())
        self.assertHTMLEqual(''.join(form.as_p() for form in formset.forms), """<p><label for="id_generic_relations-taggeditem-content_type-object_id-0-tag">Tag:</label> <input id="id_generic_relations-taggeditem-content_type-object_id-0-tag" type="text" name="generic_relations-taggeditem-content_type-object_id-0-tag" maxlength="50" /></p>
<p><label for="id_generic_relations-taggeditem-content_type-object_id-0-DELETE">Delete:</label> <input type="checkbox" name="generic_relations-taggeditem-content_type-object_id-0-DELETE" id="id_generic_relations-taggeditem-content_type-object_id-0-DELETE" /><input type="hidden" name="generic_relations-taggeditem-content_type-object_id-0-id" id="id_generic_relations-taggeditem-content_type-object_id-0-id" /></p>""")

        platypus = Animal.objects.create(
            common_name="Platypus", latin_name="Ornithorhynchus anatinus"
        )
        platypus.tags.create(tag="shiny")
        GenericFormSet = generic_inlineformset_factory(TaggedItem, extra=1)
        formset = GenericFormSet(instance=platypus)
        tagged_item_id = TaggedItem.objects.get(
            tag='shiny', object_id=platypus.id
        ).id
        self.assertHTMLEqual(''.join(form.as_p() for form in formset.forms), """<p><label for="id_generic_relations-taggeditem-content_type-object_id-0-tag">Tag:</label> <input id="id_generic_relations-taggeditem-content_type-object_id-0-tag" type="text" name="generic_relations-taggeditem-content_type-object_id-0-tag" value="shiny" maxlength="50" /></p>
<p><label for="id_generic_relations-taggeditem-content_type-object_id-0-DELETE">Delete:</label> <input type="checkbox" name="generic_relations-taggeditem-content_type-object_id-0-DELETE" id="id_generic_relations-taggeditem-content_type-object_id-0-DELETE" /><input type="hidden" name="generic_relations-taggeditem-content_type-object_id-0-id" value="%s" id="id_generic_relations-taggeditem-content_type-object_id-0-id" /></p><p><label for="id_generic_relations-taggeditem-content_type-object_id-1-tag">Tag:</label> <input id="id_generic_relations-taggeditem-content_type-object_id-1-tag" type="text" name="generic_relations-taggeditem-content_type-object_id-1-tag" maxlength="50" /></p>
<p><label for="id_generic_relations-taggeditem-content_type-object_id-1-DELETE">Delete:</label> <input type="checkbox" name="generic_relations-taggeditem-content_type-object_id-1-DELETE" id="id_generic_relations-taggeditem-content_type-object_id-1-DELETE" /><input type="hidden" name="generic_relations-taggeditem-content_type-object_id-1-id" id="id_generic_relations-taggeditem-content_type-object_id-1-id" /></p>""" % tagged_item_id)

        lion = Animal.objects.create(common_name="Lion", latin_name="Panthera leo")
        formset = GenericFormSet(instance=lion, prefix='x')
        self.assertHTMLEqual(''.join(form.as_p() for form in formset.forms), """<p><label for="id_x-0-tag">Tag:</label> <input id="id_x-0-tag" type="text" name="x-0-tag" maxlength="50" /></p>
<p><label for="id_x-0-DELETE">Delete:</label> <input type="checkbox" name="x-0-DELETE" id="id_x-0-DELETE" /><input type="hidden" name="x-0-id" id="id_x-0-id" /></p>""")

    def test_gfk_manager(self):
        # GenericForeignKey should not use the default manager (which may filter objects) #16048
        tailless = Gecko.objects.create(has_tail=False)
        tag = TaggedItem.objects.create(content_object=tailless, tag="lizard")
        self.assertEqual(tag.content_object, tailless)

    def test_subclasses_with_gen_rel(self):
        """
        Test that concrete model subclasses with generic relations work
        correctly (ticket 11263).
        """
        granite = Rock.objects.create(name='granite', hardness=5)
        TaggedItem.objects.create(content_object=granite, tag="countertop")
        self.assertEqual(Rock.objects.filter(tags__tag="countertop").count(), 1)

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

    def test_save_new_for_proxy(self):
        Formset = generic_inlineformset_factory(ForProxyModelModel,
            fields='__all__', for_concrete_model=False)

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
        Formset = generic_inlineformset_factory(ForProxyModelModel,
            fields='__all__', for_concrete_model=True)

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

        newrel.bases = [base]
        newrel = ConcreteRelatedModel.objects.get(pk=newrel.pk)
        self.assertEqual(base, newrel.bases.get())
