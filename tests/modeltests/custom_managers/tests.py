from django.test import TestCase

from models import PersonManager, PublishedBookManager
from models import Person, Book, Car

class CustomManagersTestCase(TestCase):
    fixtures = ['custom_managers_testdata.json']

    def test_related_manager(self):
        self.assertQuerysetEqual(Person.objects.get_fun_people(),
                                 ['<Person: Bugs Bunny>'])
        

        # The RelatedManager used on the 'books' descriptor extends
        # the default manager
        p2 = Person.objects.get(first_name='Droopy')
        self.assertTrue(isinstance(p2.books, PublishedBookManager))


        # The default manager, "objects", doesn't exist, because a
        # custom one was provided.
        self.assertRaises(AttributeError,
                          getattr,
                          Book, 'objects')


        # The RelatedManager used on the 'authors' descriptor extends
        # the default manager
        b2 = Book(title='How to be smart', 
                  author='Albert Einstein', 
                  is_published=False)
        b2.save()

        self.assertTrue(isinstance(b2.authors, PersonManager))
        self.assertQuerysetEqual(Book.published_objects.all(),
                                 ['<Book: How to program>'])

        self.assertQuerysetEqual(Car.cars.order_by('name'),
                                 ['<Car: Corvette>', '<Car: Neon>'])
        self.assertQuerysetEqual(Car.fast_cars.all(),
                                 ['<Car: Corvette>'])

        # Each model class gets a "_default_manager" attribute, which
        # is a reference to the first manager defined in the class. In
        # this case, it's "cars".
        self.assertQuerysetEqual(Car._default_manager.order_by('name'),
                                 ['<Car: Corvette>', '<Car: Neon>'])
