from unittest import expectedFailure

from django.contrib.contenttypes.fields import (
    GenericForeignKey, GenericRelation,
)
from django.contrib.contenttypes.models import ContentType
from django.core.checks import Error
from django.core.exceptions import FieldDoesNotExist, FieldError
from django.db import models
from django.db.models.query_utils import DeferredAttribute
from django.test import SimpleTestCase
from django.test.utils import isolate_apps


@isolate_apps('model_inheritance')
class AbstractInheritanceTests(SimpleTestCase):
    def setUp(self):
        self.classes = {}

    def _build_class(self, model_name, base_names=None, field_len=None, abstract=False):
        """ Util to allow whipping up a model class in one line.
            If `field_len` is set, adds a CharField `foo` with that
            max_length to the class.
        """
        attrs = {
            '__module__': __name__,
            'Meta': type('Meta', (object,), {'abstract': abstract})
        }
        if field_len is not None:
            attrs['foo'] = models.CharField(max_length=field_len)
        if base_names is None:
            bases = (models.Model,)
        else:
            bases = tuple(self.classes[base_name] for base_name in base_names)
        self.classes[model_name] = type(model_name, bases, attrs)

    def assertCorrectInheritance(self, model_name, field_len):
        self.assertEqual(self.classes[model_name]._meta.get_field('foo').max_length, field_len)

    def test_single_parent(self):
        """ Test multiple levels of ancestry, but with a single parent at each level.
            NO = non-overriding, O = overriding.
        """
        self._build_class('AbstractBase', None, 30, abstract=True)
        self._build_class('AbstractDescendantNO', ['AbstractBase'], abstract=True)
        self._build_class('AbstractDescendantO', ['AbstractBase'], 40, abstract=True)
        self._build_class('DerivedFromBaseNO', ['AbstractBase'])
        self._build_class('DerivedFromBaseO', ['AbstractBase'], 50)
        self._build_class('DerivedFromDescendantNONO', ['AbstractDescendantNO'])
        self._build_class('DerivedFromDescendantNOO', ['AbstractDescendantNO'], 50)
        self._build_class('DerivedFromDescendantONO', ['AbstractDescendantO'])
        self._build_class('DerivedFromDescendantOO', ['AbstractDescendantO'], 50)

        self.assertCorrectInheritance('DerivedFromBaseNO', 30)
        self.assertCorrectInheritance('DerivedFromBaseO', 50)
        self.assertCorrectInheritance('DerivedFromDescendantNONO', 30)
        self.assertCorrectInheritance('DerivedFromDescendantNOO', 50)
        self.assertCorrectInheritance('DerivedFromDescendantONO', 40)
        self.assertCorrectInheritance('DerivedFromDescendantOO', 50)

    def test_multi_parent(self):
        """ Test mro preserved when inheriting from multiple parents at once.
            NO = non-overriding, O = overriding.
        """
        self._build_class('AbstractBase1', None, 30, abstract=True)
        self._build_class('AbstractBase2', None, 40, abstract=True)
        self._build_class('AbstractBase3', None, None, abstract=True)
        self._build_class('DerivedFromBases12NO', ['AbstractBase1', 'AbstractBase2'])
        self._build_class('DerivedFromBases13NO', ['AbstractBase1', 'AbstractBase3'])
        self._build_class('DerivedFromBases32NO', ['AbstractBase3', 'AbstractBase2'])
        self._build_class('DerivedFromBases12O', ['AbstractBase1', 'AbstractBase2'], 50)
        self._build_class('DerivedFromBases13O', ['AbstractBase1', 'AbstractBase3'], 50)
        self._build_class('DerivedFromBases32O', ['AbstractBase3', 'AbstractBase2'], 50)

        self.assertCorrectInheritance('DerivedFromBases12NO', 30)
        self.assertCorrectInheritance('DerivedFromBases13NO', 30)
        self.assertCorrectInheritance('DerivedFromBases32NO', 40)
        self.assertCorrectInheritance('DerivedFromBases12O', 50)
        self.assertCorrectInheritance('DerivedFromBases13O', 50)
        self.assertCorrectInheritance('DerivedFromBases32O', 50)

    @expectedFailure
    def test_multi_parent_diamond(self):
        """ Test mro preserved when inheriting from multiple parents in diamond formation.
            NO = non-overriding, O = overriding.

            NOTE: We need a rewrite of `ModelBase.__new__()` to support this properly.
            It's marked as expected failure for now, and because we can't control
            the inheritance the way we'd like to, we should block users from building
            diamond cases at all, rather than testing for the converse.
        """
        self._build_class('AbstractBase', None, 30, abstract=True)
        self._build_class('AbstractDescendantNO', ['AbstractBase'], abstract=True)
        self._build_class('AbstractDescendantO', ['AbstractBase'], 40, abstract=True)
        self._build_class('DerivedFromDescendantsNOFirstNO', ['AbstractDescendantNO', 'AbstractDescendantO'])
        self._build_class('DerivedFromDescendantsOFirstNO', ['AbstractDescendantO', 'AbstractDescendantNO'])
        self._build_class('DerivedFromDescendantsNOFirstO', ['AbstractDescendantNO', 'AbstractDescendantO'], 50)
        self._build_class('DerivedFromDescendantsOFirstO', ['AbstractDescendantO', 'AbstractDescendantNO'], 50)

        self.assertCorrectInheritance('DerivedFromDescendantsNOFirstNO', 40)
        self.assertCorrectInheritance('DerivedFromDescendantsOFirstNO', 40)
        self.assertCorrectInheritance('DerivedFromDescendantsNOFirstO', 50)
        self.assertCorrectInheritance('DerivedFromDescendantsOFirstO', 50)

    def test_multiple_inheritance_cannot_shadow_concrete_inherited_field(self):
        class ConcreteParent(models.Model):
            name = models.CharField(max_length=255)

        class AbstractParent(models.Model):
            name = models.IntegerField()

            class Meta:
                abstract = True

        class FirstChild(ConcreteParent, AbstractParent):
            pass

        class AnotherChild(AbstractParent, ConcreteParent):
            pass

        self.assertIsInstance(FirstChild._meta.get_field('name'), models.CharField)
        self.assertEqual(
            AnotherChild.check(),
            [Error(
                "The field 'name' clashes with the field 'name' "
                "from model 'model_inheritance.concreteparent'.",
                obj=AnotherChild._meta.get_field('name'),
                id="models.E006",
            )]
        )

    def test_virtual_field(self):
        class RelationModel(models.Model):
            content_type = models.ForeignKey(ContentType, models.CASCADE)
            object_id = models.PositiveIntegerField()
            content_object = GenericForeignKey('content_type', 'object_id')

        class RelatedModelAbstract(models.Model):
            field = GenericRelation(RelationModel)

            class Meta:
                abstract = True

        class ModelAbstract(models.Model):
            field = models.CharField(max_length=100)

            class Meta:
                abstract = True

        class OverrideRelatedModelAbstract(RelatedModelAbstract):
            field = models.CharField(max_length=100)

        class ExtendModelAbstract(ModelAbstract):
            field = GenericRelation(RelationModel)

        self.assertIsInstance(OverrideRelatedModelAbstract._meta.get_field('field'), models.CharField)
        self.assertIsInstance(ExtendModelAbstract._meta.get_field('field'), GenericRelation)

    def test_cannot_override_indirect_abstract_field(self):
        class AbstractBase(models.Model):
            name = models.CharField(max_length=30)

            class Meta:
                abstract = True

        class ConcreteDescendant(AbstractBase):
            pass

        msg = (
            "Local field 'name' in class 'Descendant' clashes with field of "
            "the same name from base class 'ConcreteDescendant'."
        )
        with self.assertRaisesMessage(FieldError, msg):
            class Descendant(ConcreteDescendant):
                name = models.IntegerField()

    def test_override_field_with_attr(self):
        class AbstractBase(models.Model):
            first_name = models.CharField(max_length=50)
            last_name = models.CharField(max_length=50)
            middle_name = models.CharField(max_length=30)
            full_name = models.CharField(max_length=150)

            class Meta:
                abstract = True

        class Descendant(AbstractBase):
            middle_name = None

            def full_name(self):
                return self.first_name + self.last_name

        msg = "Descendant has no field named %r"
        with self.assertRaisesMessage(FieldDoesNotExist, msg % 'middle_name'):
            Descendant._meta.get_field('middle_name')

        with self.assertRaisesMessage(FieldDoesNotExist, msg % 'full_name'):
            Descendant._meta.get_field('full_name')

    def test_overriding_field_removed_by_concrete_model(self):
        class AbstractModel(models.Model):
            foo = models.CharField(max_length=30)

            class Meta:
                abstract = True

        class RemovedAbstractModelField(AbstractModel):
            foo = None

        class OverrideRemovedFieldByConcreteModel(RemovedAbstractModelField):
            foo = models.CharField(max_length=50)

        self.assertEqual(OverrideRemovedFieldByConcreteModel._meta.get_field('foo').max_length, 50)

    def test_shadowed_fkey_id(self):
        class Foo(models.Model):
            pass

        class AbstractBase(models.Model):
            foo = models.ForeignKey(Foo, models.CASCADE)

            class Meta:
                abstract = True

        class Descendant(AbstractBase):
            foo_id = models.IntegerField()

        self.assertEqual(
            Descendant.check(),
            [Error(
                "The field 'foo_id' clashes with the field 'foo' "
                "from model 'model_inheritance.descendant'.",
                obj=Descendant._meta.get_field('foo_id'),
                id='models.E006',
            )]
        )

    def test_shadow_related_name_when_set_to_none(self):
        class AbstractBase(models.Model):
            bar = models.IntegerField()

            class Meta:
                abstract = True

        class Foo(AbstractBase):
            bar = None
            foo = models.IntegerField()

        class Bar(models.Model):
            bar = models.ForeignKey(Foo, models.CASCADE, related_name='bar')

        self.assertEqual(Bar.check(), [])

    def test_reverse_foreign_key(self):
        class AbstractBase(models.Model):
            foo = models.CharField(max_length=100)

            class Meta:
                abstract = True

        class Descendant(AbstractBase):
            pass

        class Foo(models.Model):
            foo = models.ForeignKey(Descendant, models.CASCADE, related_name='foo')

        self.assertEqual(
            Foo._meta.get_field('foo').check(),
            [
                Error(
                    "Reverse accessor for 'Foo.foo' clashes with field name 'Descendant.foo'.",
                    hint=(
                        "Rename field 'Descendant.foo', or add/change a related_name "
                        "argument to the definition for field 'Foo.foo'."
                    ),
                    obj=Foo._meta.get_field('foo'),
                    id='fields.E302',
                ),
                Error(
                    "Reverse query name for 'Foo.foo' clashes with field name 'Descendant.foo'.",
                    hint=(
                        "Rename field 'Descendant.foo', or add/change a related_name "
                        "argument to the definition for field 'Foo.foo'."
                    ),
                    obj=Foo._meta.get_field('foo'),
                    id='fields.E303',
                ),
            ]
        )

    def test_multi_inheritance_field_clashes(self):
        class AbstractBase(models.Model):
            name = models.CharField(max_length=30)

            class Meta:
                abstract = True

        class ConcreteBase(AbstractBase):
            pass

        class AbstractDescendant(ConcreteBase):
            class Meta:
                abstract = True

        class ConcreteDescendant(AbstractDescendant):
            name = models.CharField(max_length=100)

        self.assertEqual(
            ConcreteDescendant.check(),
            [Error(
                "The field 'name' clashes with the field 'name' from "
                "model 'model_inheritance.concretebase'.",
                obj=ConcreteDescendant._meta.get_field('name'),
                id="models.E006",
            )]
        )

    def test_override_one2one_relation_auto_field_clashes(self):
        class ConcreteParent(models.Model):
            name = models.CharField(max_length=255)

        class AbstractParent(models.Model):
            name = models.IntegerField()

            class Meta:
                abstract = True

        msg = (
            "Auto-generated field 'concreteparent_ptr' in class 'Descendant' "
            "for parent_link to base class 'ConcreteParent' clashes with "
            "declared field of the same name."
        )
        with self.assertRaisesMessage(FieldError, msg):
            class Descendant(ConcreteParent, AbstractParent):
                concreteparent_ptr = models.CharField(max_length=30)

    def test_abstract_model_with_regular_python_mixin_mro(self):
        class AbstractModel(models.Model):
            name = models.CharField(max_length=255)
            age = models.IntegerField()

            class Meta:
                abstract = True

        class Mixin:
            age = None

        class Mixin2:
            age = 2

        class DescendantMixin(Mixin):
            pass

        class ConcreteModel(models.Model):
            foo = models.IntegerField()

        class ConcreteModel2(ConcreteModel):
            age = models.SmallIntegerField()

        def fields(model):
            if not hasattr(model, '_meta'):
                return []
            return [(f.name, f.__class__) for f in model._meta.get_fields()]

        model_dict = {'__module__': 'model_inheritance'}
        model1 = type('Model1', (AbstractModel, Mixin), model_dict.copy())
        model2 = type('Model2', (Mixin2, AbstractModel), model_dict.copy())
        model3 = type('Model3', (DescendantMixin, AbstractModel), model_dict.copy())
        model4 = type('Model4', (Mixin2, Mixin, AbstractModel), model_dict.copy())
        model5 = type('Model5', (Mixin2, ConcreteModel2, Mixin, AbstractModel), model_dict.copy())

        self.assertEqual(
            fields(model1),
            [('id', models.AutoField), ('name', models.CharField), ('age', models.IntegerField)]
        )

        self.assertEqual(fields(model2), [('id', models.AutoField), ('name', models.CharField)])
        self.assertEqual(getattr(model2, 'age'), 2)

        self.assertEqual(fields(model3), [('id', models.AutoField), ('name', models.CharField)])

        self.assertEqual(fields(model4), [('id', models.AutoField), ('name', models.CharField)])
        self.assertEqual(getattr(model4, 'age'), 2)

        self.assertEqual(
            fields(model5),
            [
                ('id', models.AutoField), ('foo', models.IntegerField),
                ('concretemodel_ptr', models.OneToOneField),
                ('age', models.SmallIntegerField), ('concretemodel2_ptr', models.OneToOneField),
                ('name', models.CharField),
            ]
        )

    def test_shadow_parent_attribute_with_field(self):
        class Base(models.Model):
            foo = 1

        class Inherited(Base):
            foo = models.IntegerField()

        self.assertEqual(type(Inherited.foo), DeferredAttribute)

    def test_shadow_parent_property_with_field(self):
        class Base(models.Model):
            @property
            def foo(self):
                pass

        class Inherited(Base):
            foo = models.IntegerField()

        self.assertEqual(type(Inherited.foo), DeferredAttribute)

    def test_shadow_parent_method_with_field(self):
        class Base(models.Model):
            def foo(self):
                pass

        class Inherited(Base):
            foo = models.IntegerField()

        self.assertEqual(type(Inherited.foo), DeferredAttribute)
