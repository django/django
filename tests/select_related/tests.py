from django.core.exceptions import FieldError
from django.test import SimpleTestCase, TestCase

from .models import (
    Bookmark, Domain, Family, Genus, HybridSpecies, Kingdom, Klass, Order,
    Phylum, Pizza, Species, TaggedItem,
)


class SelectRelatedTests(TestCase):

    @classmethod
    def create_tree(cls, stringtree):
        """
        Helper to create a complete tree.
        """
        names = stringtree.split()
        models = [Domain, Kingdom, Phylum, Klass, Order, Family, Genus, Species]
        assert len(names) == len(models), (names, models)

        parent = None
        for name, model in zip(names, models):
            try:
                obj = model.objects.get(name=name)
            except model.DoesNotExist:
                obj = model(name=name)
            if parent:
                setattr(obj, parent.__class__.__name__.lower(), parent)
            obj.save()
            parent = obj

    @classmethod
    def setUpTestData(cls):
        cls.create_tree("Eukaryota Animalia Anthropoda Insecta Diptera Drosophilidae Drosophila melanogaster")
        cls.create_tree("Eukaryota Animalia Chordata Mammalia Primates Hominidae Homo sapiens")
        cls.create_tree("Eukaryota Plantae Magnoliophyta Magnoliopsida Fabales Fabaceae Pisum sativum")
        cls.create_tree("Eukaryota Fungi Basidiomycota Homobasidiomycatae Agaricales Amanitacae Amanita muscaria")

    def test_access_fks_without_select_related(self):
        """
        Normally, accessing FKs doesn't fill in related objects
        """
        with self.assertNumQueries(8):
            fly = Species.objects.get(name="melanogaster")
            domain = fly.genus.family.order.klass.phylum.kingdom.domain
            self.assertEqual(domain.name, 'Eukaryota')

    def test_access_fks_with_select_related(self):
        """
        A select_related() call will fill in those related objects without any
        extra queries
        """
        with self.assertNumQueries(1):
            person = (
                Species.objects
                .select_related('genus__family__order__klass__phylum__kingdom__domain')
                .get(name="sapiens")
            )
            domain = person.genus.family.order.klass.phylum.kingdom.domain
            self.assertEqual(domain.name, 'Eukaryota')

    def test_list_without_select_related(self):
        """
        select_related() also of course applies to entire lists, not just
        items. This test verifies the expected behavior without select_related.
        """
        with self.assertNumQueries(9):
            world = Species.objects.all()
            families = [o.genus.family.name for o in world]
            self.assertEqual(sorted(families), [
                'Amanitacae',
                'Drosophilidae',
                'Fabaceae',
                'Hominidae',
            ])

    def test_list_with_select_related(self):
        """
        select_related() also of course applies to entire lists, not just
        items. This test verifies the expected behavior with select_related.
        """
        with self.assertNumQueries(1):
            world = Species.objects.all().select_related()
            families = [o.genus.family.name for o in world]
            self.assertEqual(sorted(families), [
                'Amanitacae',
                'Drosophilidae',
                'Fabaceae',
                'Hominidae',
            ])

    def test_list_with_depth(self):
        """
        Passing a relationship field lookup specifier to select_related() will
        stop the descent at a particular level. This can be used on lists as
        well.
        """
        with self.assertNumQueries(5):
            world = Species.objects.all().select_related('genus__family')
            orders = [o.genus.family.order.name for o in world]
            self.assertEqual(sorted(orders), ['Agaricales', 'Diptera', 'Fabales', 'Primates'])

    def test_select_related_with_extra(self):
        s = (Species.objects.all()
             .select_related()
             .extra(select={'a': 'select_related_species.id + 10'})[0])
        self.assertEqual(s.id + 10, s.a)

    def test_certain_fields(self):
        """
        The optional fields passed to select_related() control which related
        models we pull in. This allows for smaller queries.

        In this case, we explicitly say to select the 'genus' and
        'genus.family' models, leading to the same number of queries as before.
        """
        with self.assertNumQueries(1):
            world = Species.objects.select_related('genus__family')
            families = [o.genus.family.name for o in world]
            self.assertEqual(sorted(families), ['Amanitacae', 'Drosophilidae', 'Fabaceae', 'Hominidae'])

    def test_more_certain_fields(self):
        """
        In this case, we explicitly say to select the 'genus' and
        'genus.family' models, leading to the same number of queries as before.
        """
        with self.assertNumQueries(2):
            world = Species.objects.filter(genus__name='Amanita')\
                .select_related('genus__family')
            orders = [o.genus.family.order.name for o in world]
            self.assertEqual(orders, ['Agaricales'])

    def test_field_traversal(self):
        with self.assertNumQueries(1):
            s = (Species.objects.all()
                 .select_related('genus__family__order')
                 .order_by('id')[0:1].get().genus.family.order.name)
            self.assertEqual(s, 'Diptera')

    def test_none_clears_list(self):
        queryset = Species.objects.select_related('genus').select_related(None)
        self.assertIs(queryset.query.select_related, False)

    def test_chaining(self):
        parent_1, parent_2 = Species.objects.all()[:2]
        HybridSpecies.objects.create(name='hybrid', parent_1=parent_1, parent_2=parent_2)
        queryset = HybridSpecies.objects.select_related('parent_1').select_related('parent_2')
        with self.assertNumQueries(1):
            obj = queryset[0]
            self.assertEqual(obj.parent_1, parent_1)
            self.assertEqual(obj.parent_2, parent_2)

    def test_reverse_relation_caching(self):
        species = Species.objects.select_related('genus').filter(name='melanogaster').first()
        with self.assertNumQueries(0):
            self.assertEqual(species.genus.name, 'Drosophila')
        # The species_set reverse relation isn't cached.
        self.assertEqual(species.genus._state.fields_cache, {})
        with self.assertNumQueries(1):
            self.assertEqual(species.genus.species_set.first().name, 'melanogaster')

    def test_select_related_after_values(self):
        """
        Running select_related() after calling values() raises a TypeError
        """
        message = "Cannot call select_related() after .values() or .values_list()"
        with self.assertRaisesMessage(TypeError, message):
            list(Species.objects.values('name').select_related('genus'))

    def test_select_related_after_values_list(self):
        """
        Running select_related() after calling values_list() raises a TypeError
        """
        message = "Cannot call select_related() after .values() or .values_list()"
        with self.assertRaisesMessage(TypeError, message):
            list(Species.objects.values_list('name').select_related('genus'))


class SelectRelatedValidationTests(SimpleTestCase):
    """
    select_related() should thrown an error on fields that do not exist and
    non-relational fields.
    """
    non_relational_error = "Non-relational field given in select_related: '%s'. Choices are: %s"
    invalid_error = "Invalid field name(s) given in select_related: '%s'. Choices are: %s"

    def test_non_relational_field(self):
        with self.assertRaisesMessage(FieldError, self.non_relational_error % ('name', 'genus')):
            list(Species.objects.select_related('name__some_field'))

        with self.assertRaisesMessage(FieldError, self.non_relational_error % ('name', 'genus')):
            list(Species.objects.select_related('name'))

        with self.assertRaisesMessage(FieldError, self.non_relational_error % ('name', '(none)')):
            list(Domain.objects.select_related('name'))

    def test_non_relational_field_nested(self):
        with self.assertRaisesMessage(FieldError, self.non_relational_error % ('name', 'family')):
            list(Species.objects.select_related('genus__name'))

    def test_many_to_many_field(self):
        with self.assertRaisesMessage(FieldError, self.invalid_error % ('toppings', '(none)')):
            list(Pizza.objects.select_related('toppings'))

    def test_reverse_relational_field(self):
        with self.assertRaisesMessage(FieldError, self.invalid_error % ('child_1', 'genus')):
            list(Species.objects.select_related('child_1'))

    def test_invalid_field(self):
        with self.assertRaisesMessage(FieldError, self.invalid_error % ('invalid_field', 'genus')):
            list(Species.objects.select_related('invalid_field'))

        with self.assertRaisesMessage(FieldError, self.invalid_error % ('related_invalid_field', 'family')):
            list(Species.objects.select_related('genus__related_invalid_field'))

        with self.assertRaisesMessage(FieldError, self.invalid_error % ('invalid_field', '(none)')):
            list(Domain.objects.select_related('invalid_field'))

    def test_generic_relations(self):
        with self.assertRaisesMessage(FieldError, self.invalid_error % ('tags', '')):
            list(Bookmark.objects.select_related('tags'))

        with self.assertRaisesMessage(FieldError, self.invalid_error % ('content_object', 'content_type')):
            list(TaggedItem.objects.select_related('content_object'))
