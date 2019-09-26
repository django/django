import datetime

from django.test import TestCase

from .models import HotelReservation


class QuerySetQueryTests(TestCase):
    """
    Tests the output of queryset.query for PostgreSQL,
    which should use mogrify() to give an exact output
    of the query to be run.
    """

    def test_queryset_query_dates(self):
        a = HotelReservation.objects.filter(
            start=datetime.datetime(2005, 7, 28),
            end=datetime.datetime(2005, 9, 28),
        )
        self.assertEqual(
            a.query.__str__(),
            '''SELECT "postgres_tests_hotelreservation"."id", "postgres_tests_hotelreservation"."room_id", "postgres_tests_hotelreservation"."datespan", "postgres_tests_hotelreservation"."start", "postgres_tests_hotelreservation"."end", "postgres_tests_hotelreservation"."cancelled" FROM "postgres_tests_hotelreservation" WHERE ("postgres_tests_hotelreservation"."end" = '2005-09-28T00:00:00'::timestamp AND "postgres_tests_hotelreservation"."start" = '2005-07-28T00:00:00'::timestamp)''',
        )

    def test_queryset_query_empty(self):
        a = HotelReservation.objects.all()
        print(a.query)
        self.assertEqual(
            a.query.__str__(),
            '''SELECT "postgres_tests_hotelreservation"."id", "postgres_tests_hotelreservation"."room_id", "postgres_tests_hotelreservation"."datespan", "postgres_tests_hotelreservation"."start", "postgres_tests_hotelreservation"."end", "postgres_tests_hotelreservation"."cancelled" FROM "postgres_tests_hotelreservation"''',
        )
