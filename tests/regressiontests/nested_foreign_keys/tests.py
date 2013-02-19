from __future__ import absolute_import
from django.test import TestCase

from .models import Person, Movie, Event, Screening, ScreeningNullFK, Package, PackageNullFK


# These are tests for #16715. The basic scheme is always the same: 3 models with
# 2 relations. The first relation may be null, while the second is non-nullable.
# In some cases, Django would pick the wrong join type for the second relation,
# resulting in missing objects in the queryset.
#
#   Model A
#   | (Relation A/B : nullable)
#   Model B
#   | (Relation B/C : non-nullable)
#   Model C
#
# Because of the possibility of NULL rows resulting from the LEFT OUTER JOIN
# between Model A and Model B (i.e. instances of A without reference to B),
# the second join must also be LEFT OUTER JOIN, so that we do not ignore
# instances of A that do not reference B.
#
# Relation A/B can either be an explicit foreign key or an implicit reverse
# relation such as introduced by one-to-one relations (through multi-table
# inheritance).
class NestedForeignKeysTests(TestCase):
    def setUp(self):
        self.director = Person.objects.create(name='Terry Gilliam / Terry Jones')
        self.movie = Movie.objects.create(title='Monty Python and the Holy Grail', director=self.director)


    # This test failed in #16715 because in some cases INNER JOIN was selected
    # for the second foreign key relation instead of LEFT OUTER JOIN.
    def testInheritance(self):
        some_event = Event.objects.create()
        screening = Screening.objects.create(movie=self.movie)

        self.assertEqual(len(Event.objects.all()), 2)
        self.assertEqual(len(Event.objects.select_related('screening')), 2)
        # This failed.
        self.assertEqual(len(Event.objects.select_related('screening__movie')), 2)

        self.assertEqual(len(Event.objects.values()), 2)
        self.assertEqual(len(Event.objects.values('screening__pk')), 2)
        self.assertEqual(len(Event.objects.values('screening__movie__pk')), 2)
        self.assertEqual(len(Event.objects.values('screening__movie__title')), 2)
        # This failed.
        self.assertEqual(len(Event.objects.values('screening__movie__pk', 'screening__movie__title')), 2)

        # Simple filter/exclude queries for good measure.
        self.assertEqual(Event.objects.filter(screening__movie=self.movie).count(), 1)
        self.assertEqual(Event.objects.exclude(screening__movie=self.movie).count(), 1)


    # These all work because the second foreign key in the chain has null=True.
    def testInheritanceNullFK(self):
        some_event = Event.objects.create()
        screening = ScreeningNullFK.objects.create(movie=None)
        screening_with_movie = ScreeningNullFK.objects.create(movie=self.movie)

        self.assertEqual(len(Event.objects.all()), 3)
        self.assertEqual(len(Event.objects.select_related('screeningnullfk')), 3)
        self.assertEqual(len(Event.objects.select_related('screeningnullfk__movie')), 3)

        self.assertEqual(len(Event.objects.values()), 3)
        self.assertEqual(len(Event.objects.values('screeningnullfk__pk')), 3)
        self.assertEqual(len(Event.objects.values('screeningnullfk__movie__pk')), 3)
        self.assertEqual(len(Event.objects.values('screeningnullfk__movie__title')), 3)
        self.assertEqual(len(Event.objects.values('screeningnullfk__movie__pk', 'screeningnullfk__movie__title')), 3)

        self.assertEqual(Event.objects.filter(screeningnullfk__movie=self.movie).count(), 1)
        self.assertEqual(Event.objects.exclude(screeningnullfk__movie=self.movie).count(), 2)

    def test_null_exclude(self):
        screening = ScreeningNullFK.objects.create(movie=None)
        ScreeningNullFK.objects.create(movie=self.movie)
        self.assertEqual(
            list(ScreeningNullFK.objects.exclude(movie__id=self.movie.pk)),
            [screening])

    # This test failed in #16715 because in some cases INNER JOIN was selected
    # for the second foreign key relation instead of LEFT OUTER JOIN.
    def testExplicitForeignKey(self):
        package = Package.objects.create()
        screening = Screening.objects.create(movie=self.movie)
        package_with_screening = Package.objects.create(screening=screening)

        self.assertEqual(len(Package.objects.all()), 2)
        self.assertEqual(len(Package.objects.select_related('screening')), 2)
        self.assertEqual(len(Package.objects.select_related('screening__movie')), 2)

        self.assertEqual(len(Package.objects.values()), 2)
        self.assertEqual(len(Package.objects.values('screening__pk')), 2)
        self.assertEqual(len(Package.objects.values('screening__movie__pk')), 2)
        self.assertEqual(len(Package.objects.values('screening__movie__title')), 2)
        # This failed.
        self.assertEqual(len(Package.objects.values('screening__movie__pk', 'screening__movie__title')), 2)

        self.assertEqual(Package.objects.filter(screening__movie=self.movie).count(), 1)
        self.assertEqual(Package.objects.exclude(screening__movie=self.movie).count(), 1)


    # These all work because the second foreign key in the chain has null=True.
    def testExplicitForeignKeyNullFK(self):
        package = PackageNullFK.objects.create()
        screening = ScreeningNullFK.objects.create(movie=None)
        screening_with_movie = ScreeningNullFK.objects.create(movie=self.movie)
        package_with_screening = PackageNullFK.objects.create(screening=screening)
        package_with_screening_with_movie = PackageNullFK.objects.create(screening=screening_with_movie)

        self.assertEqual(len(PackageNullFK.objects.all()), 3)
        self.assertEqual(len(PackageNullFK.objects.select_related('screening')), 3)
        self.assertEqual(len(PackageNullFK.objects.select_related('screening__movie')), 3)

        self.assertEqual(len(PackageNullFK.objects.values()), 3)
        self.assertEqual(len(PackageNullFK.objects.values('screening__pk')), 3)
        self.assertEqual(len(PackageNullFK.objects.values('screening__movie__pk')), 3)
        self.assertEqual(len(PackageNullFK.objects.values('screening__movie__title')), 3)
        self.assertEqual(len(PackageNullFK.objects.values('screening__movie__pk', 'screening__movie__title')), 3)

        self.assertEqual(PackageNullFK.objects.filter(screening__movie=self.movie).count(), 1)
        self.assertEqual(PackageNullFK.objects.exclude(screening__movie=self.movie).count(), 2)


# Some additional tests for #16715. The only difference is the depth of the
# nesting as we now use 4 models instead of 3 (and thus 3 relations). This
# checks if promotion of join types works for deeper nesting too.
class DeeplyNestedForeignKeysTests(TestCase):
    def setUp(self):
        self.director = Person.objects.create(name='Terry Gilliam / Terry Jones')
        self.movie = Movie.objects.create(title='Monty Python and the Holy Grail', director=self.director)


    def testInheritance(self):
        some_event = Event.objects.create()
        screening = Screening.objects.create(movie=self.movie)

        self.assertEqual(len(Event.objects.all()), 2)
        self.assertEqual(len(Event.objects.select_related('screening__movie__director')), 2)

        self.assertEqual(len(Event.objects.values()), 2)
        self.assertEqual(len(Event.objects.values('screening__movie__director__pk')), 2)
        self.assertEqual(len(Event.objects.values('screening__movie__director__name')), 2)
        self.assertEqual(len(Event.objects.values('screening__movie__director__pk', 'screening__movie__director__name')), 2)
        self.assertEqual(len(Event.objects.values('screening__movie__pk', 'screening__movie__director__pk')), 2)
        self.assertEqual(len(Event.objects.values('screening__movie__pk', 'screening__movie__director__name')), 2)
        self.assertEqual(len(Event.objects.values('screening__movie__title', 'screening__movie__director__pk')), 2)
        self.assertEqual(len(Event.objects.values('screening__movie__title', 'screening__movie__director__name')), 2)

        self.assertEqual(Event.objects.filter(screening__movie__director=self.director).count(), 1)
        self.assertEqual(Event.objects.exclude(screening__movie__director=self.director).count(), 1)


    def testExplicitForeignKey(self):
        package = Package.objects.create()
        screening = Screening.objects.create(movie=self.movie)
        package_with_screening = Package.objects.create(screening=screening)

        self.assertEqual(len(Package.objects.all()), 2)
        self.assertEqual(len(Package.objects.select_related('screening__movie__director')), 2)

        self.assertEqual(len(Package.objects.values()), 2)
        self.assertEqual(len(Package.objects.values('screening__movie__director__pk')), 2)
        self.assertEqual(len(Package.objects.values('screening__movie__director__name')), 2)
        self.assertEqual(len(Package.objects.values('screening__movie__director__pk', 'screening__movie__director__name')), 2)
        self.assertEqual(len(Package.objects.values('screening__movie__pk', 'screening__movie__director__pk')), 2)
        self.assertEqual(len(Package.objects.values('screening__movie__pk', 'screening__movie__director__name')), 2)
        self.assertEqual(len(Package.objects.values('screening__movie__title', 'screening__movie__director__pk')), 2)
        self.assertEqual(len(Package.objects.values('screening__movie__title', 'screening__movie__director__name')), 2)

        self.assertEqual(Package.objects.filter(screening__movie__director=self.director).count(), 1)
        self.assertEqual(Package.objects.exclude(screening__movie__director=self.director).count(), 1)
