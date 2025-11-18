from django.db import models
from django.template import Context, Engine
from django.test import SimpleTestCase
from django.utils.translation import gettext_lazy as _


class YearInSchool(models.TextChoices):
    FRESHMAN = 'FR', _('Freshman')
    SOPHOMORE = 'SO', _('Sophomore')
    JUNIOR = 'JR', _('Junior')
    SENIOR = 'SR', _('Senior')


class Vehicle(models.IntegerChoices):
    CAR = 1, 'Carriage'
    TRUCK = 2, 'Truck'
    JET_SKI = 3, 'Jet Ski'


class ChoicesTemplateTests(SimpleTestCase):
    """Tests for using Choices in templates."""

    @classmethod
    def setUpClass(cls):
        cls.engine = Engine()
        super().setUpClass()

    def test_choices_class_not_called_in_template(self):
        """
        Test that enumeration Choices classes are not called in templates.
        The Choices class itself should be accessible without being called.
        """
        # Test with TextChoices
        c = Context({'YearInSchool': YearInSchool})
        t = self.engine.from_string('{{ YearInSchool.FRESHMAN }}')
        # Should render as the enum member, which renders as its value
        self.assertEqual(t.render(c), 'FR')

        # Test with IntegerChoices
        c = Context({'Vehicle': Vehicle})
        t = self.engine.from_string('{{ Vehicle.CAR }}')
        # Should render as the enum member, which renders as its value
        self.assertEqual(t.render(c), '1')

    def test_choices_comparison_in_template(self):
        """
        Test that enumeration Choices can be compared in template conditions.
        This is the main use case from the issue description.
        """
        # Create a context with an instance attribute and the enum class
        c = Context({
            'year': YearInSchool.FRESHMAN,
            'YearInSchool': YearInSchool,
        })

        # Test equality comparison
        t = self.engine.from_string(
            '{% if year == YearInSchool.FRESHMAN %}freshman{% endif %}'
        )
        self.assertEqual(t.render(c), 'freshman')

        # Test inequality comparison
        t = self.engine.from_string(
            '{% if year == YearInSchool.SENIOR %}senior{% else %}not senior{% endif %}'
        )
        self.assertEqual(t.render(c), 'not senior')

    def test_choices_member_attributes_accessible(self):
        """
        Test that enum member attributes are still accessible in templates.
        """
        c = Context({'YearInSchool': YearInSchool})

        # Access the value attribute
        t = self.engine.from_string('{{ YearInSchool.FRESHMAN.value }}')
        self.assertEqual(t.render(c), 'FR')

        # Access the label attribute
        t = self.engine.from_string('{{ YearInSchool.FRESHMAN.label }}')
        self.assertEqual(t.render(c), 'Freshman')

        # Access the name attribute
        t = self.engine.from_string('{{ YearInSchool.FRESHMAN.name }}')
        self.assertEqual(t.render(c), 'FRESHMAN')

    def test_choices_class_attributes_accessible(self):
        """
        Test that class-level attributes (choices, labels, values, names)
        are accessible in templates.
        """
        c = Context({'YearInSchool': YearInSchool})

        # Access names
        t = self.engine.from_string('{{ YearInSchool.names }}')
        rendered = t.render(c)
        self.assertIn('FRESHMAN', rendered)
        self.assertIn('SOPHOMORE', rendered)

        # Access values
        t = self.engine.from_string('{{ YearInSchool.values }}')
        rendered = t.render(c)
        self.assertIn('FR', rendered)
        self.assertIn('SO', rendered)
