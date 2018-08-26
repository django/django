from django.db import connection
from django.db.models import Count, Q
from django.db.models.functions import Lower
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from .models import Classroom, School, Student

queries = (
    Classroom.objects.annotate(Count('students')),
    Classroom.objects.annotate(a=Lower('name')),
    Student.objects.annotate(a=Count('classroom__school__classroom')),
    Student.objects.annotate(a=Count('classroom', filter=Q(pk=1))),
    Classroom.objects.select_related('school')
)


class TestSimplifyCount(TestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.school = School.objects.create()
        cls.classroom = Classroom.objects.create(school=cls.school, name='test')
        cls.student1 = Student.objects.create(school=cls.school)
        cls.student2 = Student.objects.create(school=cls.school)
        cls.classroom.students.add(cls.student1, cls.student2)

    def test_simple_count_optimization(self):
        for query in queries:
            with self.subTest():
                with CaptureQueriesContext(connection) as captured_queries:
                    self.assertEqual(query.model.objects.count(), query.count())
                self.assertEqual(captured_queries[0]['sql'], captured_queries[1]['sql'])
                self.assertNotIn('JOIN', captured_queries[1]['sql'])

    def test_filter_removes_optimization(self):
        for query in queries:
            with self.subTest():
                with CaptureQueriesContext(connection) as captured_queries:
                    self.assertEqual(query.model.objects.count(), query.filter(pk__isnull=False).count())
                self.assertNotEqual(captured_queries[0]['sql'], captured_queries[1]['sql'])
