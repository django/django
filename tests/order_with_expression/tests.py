from operator import attrgetter
from unittest import mock, skip

from django.db import models
from django.test import TestCase

from .models import Album, Musician, Song


class OrderWithExpressionTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.musician1 = Musician.objects.create(instrument='mayonaise')
        cls.musician3 = Musician.objects.create(instrument=None)
        cls.musician2 = Musician.objects.create(instrument='zoo')

        cls.album1 = Album.objects.create(
            artist=cls.musician1,
            name='Album 1',
        )
        cls.album3 = Album.objects.create(
            artist=cls.musician3,
            name='Album 3',
        )
        cls.album2 = Album.objects.create(
            artist=cls.musician2,
            name='Album 2',
        )

        cls.song1 = Song.objects.create(
            album=cls.album1,
            name='Song 1',
        )
        cls.song3 = Song.objects.create(
            album=cls.album3,
            name='Song 3',
        )
        cls.song2 = Song.objects.create(
            album=cls.album2,
            name='Song 2',
        )

    def test_order_by_expression_nulls_last(self):
        self.assertQuerysetEqual(
            Musician.objects.all(),
            ['mayonaise', 'zoo', None],
            attrgetter('instrument')
        )

    def test_order_by_related_expression_nulls_last(self):
        self.assertQuerysetEqual(
            Album.objects.all(),
            ['Album 1', 'Album 2', 'Album 3'],
            attrgetter('name')
        )

    def test_order_by_related_expression_through_related_field_nulls_last(self):
        self.assertQuerysetEqual(
            Song.objects.all(),
            ['Song 1', 'Song 2', 'Song 3'],
            attrgetter('name')
        )

    def test_order_by_expression_nulls_first(self):

        ordering = [models.F('instrument').asc(nulls_first=True)]

        with mock.patch.object(Musician._meta, 'ordering', ordering):
            self.assertQuerysetEqual(
                Musician.objects.all(),
                [None, 'mayonaise', 'zoo'],
                attrgetter('instrument')
            )

    def test_order_by_related_expression_nulls_first(self):

        ordering = [models.F('instrument').asc(nulls_first=True)]

        with mock.patch.object(Musician._meta, 'ordering', ordering):
            self.assertQuerysetEqual(
                Album.objects.all(),
                ['Album 3', 'Album 1', 'Album 2'],
                attrgetter('name')
            )

    def test_depth_3_nulls_first(self):

        ordering = [models.F('instrument').asc(nulls_first=True)]

        with mock.patch.object(Musician._meta, 'ordering', ordering):
            self.assertQuerysetEqual(
                Song.objects.all(),
                ['Song 3', 'Song 1', 'Song 2'],
                attrgetter('name')
            )

    @skip('What should the behavior be?')
    def test_order_by_related_expression_through_expression(self):

        ordering = [models.F('artist').asc(nulls_first=True)]

        with mock.patch.object(Album._meta, 'ordering', ordering):
            self.assertQuerysetEqual(
                Album.objects.all(),
                ['Album 3', 'Album 1', 'Album 2'],
                attrgetter('name')
            )

    @skip('What should the behavior be?')
    def test_order_by_related_expression_through_related_expression(self):

        ordering = [models.F('artist').asc(nulls_first=True)]

        with mock.patch.object(Album._meta, 'ordering', ordering):
            self.assertQuerysetEqual(
                Song.objects.all(),
                ['Song 3', 'Song 1', 'Song 2'],
                attrgetter('name')
            )

    def test_order_by_expression_through_double_forward_relation(self):

        ordering = ['album__artist']

        with mock.patch.object(Song._meta, 'ordering', ordering):
            self.assertQuerysetEqual(
                Song.objects.all(),
                ['Song 1', 'Song 2', 'Song 3'],
                attrgetter('name')
            )
