from django.test import TestCase

from django.db.models import F
from django.core.exceptions import FieldError

from models import Employee, Company

class ExpressionsTestCase(TestCase):
    fixtures = ['f_expression_testdata.json']

    def test_basic_f_expression(self):
        company_query = Company.objects.values('name','num_employees',
                                               'num_chairs'
                                               ).order_by('name',
                                                          'num_employees',
                                                          'num_chairs')
        # We can filter for companies where the number of employees is
        # greater than the number of chairs.
        self.assertItemsEqual(company_query.filter(
                num_employees__gt=F('num_chairs')),
                         [{'num_chairs': 5, 'name': u'Example Inc.', 
                           'num_employees': 2300}, 
                          {'num_chairs': 1, 'name': u'Test GmbH', 
                           'num_employees': 32}])

        # We can set one field to have the value of another field Make
        # sure we have enough chairs
        company_query.update(num_chairs=F('num_employees'))
        self.assertItemsEqual(company_query,
                         [{'num_chairs': 2300, 'name': u'Example Inc.',
                           'num_employees': 2300}, 
                          {'num_chairs': 3, 'name': u'Foobar Ltd.', 
                           'num_employees': 3}, 
                          {'num_chairs': 32, 'name': u'Test GmbH', 
                           'num_employees': 32}])

        # We can perform arithmetic operations in expressions. Make
        # sure we have 2 spare chairs
        company_query.update(num_chairs=F('num_employees')+2)
        self.assertItemsEqual(company_query,
                         [{'num_chairs': 2302, 'name': u'Example Inc.',
                           'num_employees': 2300}, 
                          {'num_chairs': 5, 'name': u'Foobar Ltd.', 
                           'num_employees': 3}, 
                          {'num_chairs': 34, 'name': u'Test GmbH', 
                           'num_employees': 32}])

        # Law of order of operations is followed
        company_query.update(num_chairs=F('num_employees') + 
                             2 * F('num_employees'))
        self.assertItemsEqual(company_query,
                         [{'num_chairs': 6900, 'name': u'Example Inc.', 
                           'num_employees': 2300}, 
                          {'num_chairs': 9, 'name': u'Foobar Ltd.', 
                           'num_employees': 3}, 
                          {'num_chairs': 96, 'name': u'Test GmbH', 
                           'num_employees': 32}])

        # Law of order of operations can be overridden by parentheses
        company_query.update(num_chairs=((F('num_employees') + 2) * 
                                         F('num_employees')))
        self.assertItemsEqual(company_query,
                         [{'num_chairs': 5294600, 'name': u'Example Inc.', 
                           'num_employees': 2300}, 
                          {'num_chairs': 15, 'name': u'Foobar Ltd.',
                           'num_employees': 3}, 
                          {'num_chairs': 1088, 'name': u'Test GmbH',
                           'num_employees': 32}])

        # The relation of a foreign key can become copied over to an
        # other foreign key.
        self.assertEqual(Company.objects.update(point_of_contact=F('ceo')), 3)


        self.assertEqual(repr([c.point_of_contact for 
                               c in Company.objects.all()]),
                         '[<Employee: Joe Smith>, <Employee: Frank Meyer>, <Employee: Max Mustermann>]')

    def test_f_expression_spanning_join(self):
        # F Expressions can also span joins
        self.assertQuerysetEqual(
            Company.objects.filter(
                ceo__firstname=F('point_of_contact__firstname')
                ).distinct().order_by('name'),
            ['<Company: Foobar Ltd.>', '<Company: Test GmbH>'])

        Company.objects.exclude(
            ceo__firstname=F('point_of_contact__firstname')
            ).update(name='foo')
        self.assertEqual(Company.objects.exclude(
                ceo__firstname=F('point_of_contact__firstname')
                ).get().name, 
                         u'foo')

        self.assertRaises(FieldError,
                          Company.objects.exclude(ceo__firstname=F('point_of_contact__firstname')).update,
                          name=F('point_of_contact__lastname'))

    def test_f_expression_update_attribute(self):
        # F expressions can be used to update attributes on single objects
        test_gmbh = Company.objects.get(name='Test GmbH')
        self.assertEqual(test_gmbh.num_employees, 32)
        test_gmbh.num_employees = F('num_employees') + 4
        test_gmbh.save()
        test_gmbh = Company.objects.get(pk=test_gmbh.pk)
        self.assertEqual(test_gmbh.num_employees, 36)
        
        # F expressions cannot be used to update attributes which are
        # foreign keys, or attributes which involve joins.
        test_gmbh.point_of_contact = None
        test_gmbh.save()
        self.assertEqual(test_gmbh.point_of_contact, None)
        self.assertRaises(ValueError,
                          setattr,
                          test_gmbh, 'point_of_contact', F('ceo'))

        test_gmbh.point_of_contact = test_gmbh.ceo
        test_gmbh.save()
        test_gmbh.name = F('ceo__last_name')
        self.assertRaises(FieldError,
                          test_gmbh.save)
        
        # F expressions cannot be used to update attributes on objects
        # which do not yet exist in the database
        acme = Company(name='The Acme Widget Co.', num_employees=12, 
                       num_chairs=5, ceo=test_gmbh.ceo)
        acme.num_employees = F('num_employees') + 16
        self.assertRaises(TypeError,
                          acme.save)
