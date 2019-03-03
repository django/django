import datetime
from unittest import mock, skipIf, skipUnless

from django.core.exceptions import FieldError
from django.db import NotSupportedError, connection
from django.db.models import (
    F, OuterRef, RowRange, Subquery, Value, ValueRange, Window, WindowFrame,
)
from django.db.models.aggregates import Avg, Max, Min, Sum
from django.db.models.functions import (
    CumeDist, DenseRank, ExtractYear, FirstValue, Lag, LastValue, Lead,
    NthValue, Ntile, PercentRank, Rank, RowNumber, Upper,
)
from django.test import SimpleTestCase, TestCase, skipUnlessDBFeature

from .models import Employee


@skipUnlessDBFeature('supports_over_clause')
class WindowFunctionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Employee.objects.bulk_create([
            Employee(name=e[0], salary=e[1], department=e[2], hire_date=e[3], age=e[4])
            for e in [
                ('Jones', 45000, 'Accounting', datetime.datetime(2005, 11, 1), 20),
                ('Williams', 37000, 'Accounting', datetime.datetime(2009, 6, 1), 20),
                ('Jenson', 45000, 'Accounting', datetime.datetime(2008, 4, 1), 20),
                ('Adams', 50000, 'Accounting', datetime.datetime(2013, 7, 1), 50),
                ('Smith', 55000, 'Sales', datetime.datetime(2007, 6, 1), 30),
                ('Brown', 53000, 'Sales', datetime.datetime(2009, 9, 1), 30),
                ('Johnson', 40000, 'Marketing', datetime.datetime(2012, 3, 1), 30),
                ('Smith', 38000, 'Marketing', datetime.datetime(2009, 10, 1), 20),
                ('Wilkinson', 60000, 'IT', datetime.datetime(2011, 3, 1), 40),
                ('Moore', 34000, 'IT', datetime.datetime(2013, 8, 1), 40),
                ('Miller', 100000, 'Management', datetime.datetime(2005, 6, 1), 40),
                ('Johnson', 80000, 'Management', datetime.datetime(2005, 7, 1), 50),
            ]
        ])

    def test_dense_rank(self):
        qs = Employee.objects.annotate(rank=Window(
            expression=DenseRank(),
            order_by=ExtractYear(F('hire_date')).asc(),
        ))
        self.assertQuerysetEqual(qs, [
            ('Jones', 45000, 'Accounting', datetime.date(2005, 11, 1), 1),
            ('Miller', 100000, 'Management', datetime.date(2005, 6, 1), 1),
            ('Johnson', 80000, 'Management', datetime.date(2005, 7, 1), 1),
            ('Smith', 55000, 'Sales', datetime.date(2007, 6, 1), 2),
            ('Jenson', 45000, 'Accounting', datetime.date(2008, 4, 1), 3),
            ('Smith', 38000, 'Marketing', datetime.date(2009, 10, 1), 4),
            ('Brown', 53000, 'Sales', datetime.date(2009, 9, 1), 4),
            ('Williams', 37000, 'Accounting', datetime.date(2009, 6, 1), 4),
            ('Wilkinson', 60000, 'IT', datetime.date(2011, 3, 1), 5),
            ('Johnson', 40000, 'Marketing', datetime.date(2012, 3, 1), 6),
            ('Moore', 34000, 'IT', datetime.date(2013, 8, 1), 7),
            ('Adams', 50000, 'Accounting', datetime.date(2013, 7, 1), 7),
        ], lambda entry: (entry.name, entry.salary, entry.department, entry.hire_date, entry.rank), ordered=False)

    def test_department_salary(self):
        qs = Employee.objects.annotate(department_sum=Window(
            expression=Sum('salary'),
            partition_by=F('department'),
            order_by=[F('hire_date').asc()],
        )).order_by('department', 'department_sum')
        self.assertQuerysetEqual(qs, [
            ('Jones', 'Accounting', 45000, 45000),
            ('Jenson', 'Accounting', 45000, 90000),
            ('Williams', 'Accounting', 37000, 127000),
            ('Adams', 'Accounting', 50000, 177000),
            ('Wilkinson', 'IT', 60000, 60000),
            ('Moore', 'IT', 34000, 94000),
            ('Miller', 'Management', 100000, 100000),
            ('Johnson', 'Management', 80000, 180000),
            ('Smith', 'Marketing', 38000, 38000),
            ('Johnson', 'Marketing', 40000, 78000),
            ('Smith', 'Sales', 55000, 55000),
            ('Brown', 'Sales', 53000, 108000),
        ], lambda entry: (entry.name, entry.department, entry.salary, entry.department_sum))

    def test_rank(self):
        """
        Rank the employees based on the year they're were hired. Since there
        are multiple employees hired in different years, this will contain
        gaps.
        """
        qs = Employee.objects.annotate(rank=Window(
            expression=Rank(),
            order_by=ExtractYear(F('hire_date')).asc(),
        ))
        self.assertQuerysetEqual(qs, [
            ('Jones', 45000, 'Accounting', datetime.date(2005, 11, 1), 1),
            ('Miller', 100000, 'Management', datetime.date(2005, 6, 1), 1),
            ('Johnson', 80000, 'Management', datetime.date(2005, 7, 1), 1),
            ('Smith', 55000, 'Sales', datetime.date(2007, 6, 1), 4),
            ('Jenson', 45000, 'Accounting', datetime.date(2008, 4, 1), 5),
            ('Smith', 38000, 'Marketing', datetime.date(2009, 10, 1), 6),
            ('Brown', 53000, 'Sales', datetime.date(2009, 9, 1), 6),
            ('Williams', 37000, 'Accounting', datetime.date(2009, 6, 1), 6),
            ('Wilkinson', 60000, 'IT', datetime.date(2011, 3, 1), 9),
            ('Johnson', 40000, 'Marketing', datetime.date(2012, 3, 1), 10),
            ('Moore', 34000, 'IT', datetime.date(2013, 8, 1), 11),
            ('Adams', 50000, 'Accounting', datetime.date(2013, 7, 1), 11),
        ], lambda entry: (entry.name, entry.salary, entry.department, entry.hire_date, entry.rank), ordered=False)

    def test_row_number(self):
        """
        The row number window function computes the number based on the order
        in which the tuples were inserted. Depending on the backend,

        Oracle requires an ordering-clause in the Window expression.
        """
        qs = Employee.objects.annotate(row_number=Window(
            expression=RowNumber(),
            order_by=F('pk').asc(),
        )).order_by('pk')
        self.assertQuerysetEqual(qs, [
            ('Jones', 'Accounting', 1),
            ('Williams', 'Accounting', 2),
            ('Jenson', 'Accounting', 3),
            ('Adams', 'Accounting', 4),
            ('Smith', 'Sales', 5),
            ('Brown', 'Sales', 6),
            ('Johnson', 'Marketing', 7),
            ('Smith', 'Marketing', 8),
            ('Wilkinson', 'IT', 9),
            ('Moore', 'IT', 10),
            ('Miller', 'Management', 11),
            ('Johnson', 'Management', 12),
        ], lambda entry: (entry.name, entry.department, entry.row_number))

    @skipIf(connection.vendor == 'oracle', "Oracle requires ORDER BY in row_number, ANSI:SQL doesn't")
    def test_row_number_no_ordering(self):
        """
        The row number window function computes the number based on the order
        in which the tuples were inserted.
        """
        # Add a default ordering for consistent results across databases.
        qs = Employee.objects.annotate(row_number=Window(
            expression=RowNumber(),
        )).order_by('pk')
        self.assertQuerysetEqual(qs, [
            ('Jones', 'Accounting', 1),
            ('Williams', 'Accounting', 2),
            ('Jenson', 'Accounting', 3),
            ('Adams', 'Accounting', 4),
            ('Smith', 'Sales', 5),
            ('Brown', 'Sales', 6),
            ('Johnson', 'Marketing', 7),
            ('Smith', 'Marketing', 8),
            ('Wilkinson', 'IT', 9),
            ('Moore', 'IT', 10),
            ('Miller', 'Management', 11),
            ('Johnson', 'Management', 12),
        ], lambda entry: (entry.name, entry.department, entry.row_number))

    def test_avg_salary_department(self):
        qs = Employee.objects.annotate(avg_salary=Window(
            expression=Avg('salary'),
            order_by=F('department').asc(),
            partition_by='department',
        )).order_by('department', '-salary', 'name')
        self.assertQuerysetEqual(qs, [
            ('Adams', 50000, 'Accounting', 44250.00),
            ('Jenson', 45000, 'Accounting', 44250.00),
            ('Jones', 45000, 'Accounting', 44250.00),
            ('Williams', 37000, 'Accounting', 44250.00),
            ('Wilkinson', 60000, 'IT', 47000.00),
            ('Moore', 34000, 'IT', 47000.00),
            ('Miller', 100000, 'Management', 90000.00),
            ('Johnson', 80000, 'Management', 90000.00),
            ('Johnson', 40000, 'Marketing', 39000.00),
            ('Smith', 38000, 'Marketing', 39000.00),
            ('Smith', 55000, 'Sales', 54000.00),
            ('Brown', 53000, 'Sales', 54000.00),
        ], transform=lambda row: (row.name, row.salary, row.department, row.avg_salary))

    def test_lag(self):
        """
        Compute the difference between an employee's salary and the next
        highest salary in the employee's department. Return None if the
        employee has the lowest salary.
        """
        qs = Employee.objects.annotate(lag=Window(
            expression=Lag(expression='salary', offset=1),
            partition_by=F('department'),
            order_by=[F('salary').asc(), F('name').asc()],
        )).order_by('department', F('salary').asc(), F('name').asc())
        self.assertQuerysetEqual(qs, [
            ('Williams', 37000, 'Accounting', None),
            ('Jenson', 45000, 'Accounting', 37000),
            ('Jones', 45000, 'Accounting', 45000),
            ('Adams', 50000, 'Accounting', 45000),
            ('Moore', 34000, 'IT', None),
            ('Wilkinson', 60000, 'IT', 34000),
            ('Johnson', 80000, 'Management', None),
            ('Miller', 100000, 'Management', 80000),
            ('Smith', 38000, 'Marketing', None),
            ('Johnson', 40000, 'Marketing', 38000),
            ('Brown', 53000, 'Sales', None),
            ('Smith', 55000, 'Sales', 53000),
        ], transform=lambda row: (row.name, row.salary, row.department, row.lag))

    def test_first_value(self):
        qs = Employee.objects.annotate(first_value=Window(
            expression=FirstValue('salary'),
            partition_by=F('department'),
            order_by=F('hire_date').asc(),
        )).order_by('department', 'hire_date')
        self.assertQuerysetEqual(qs, [
            ('Jones', 45000, 'Accounting', datetime.date(2005, 11, 1), 45000),
            ('Jenson', 45000, 'Accounting', datetime.date(2008, 4, 1), 45000),
            ('Williams', 37000, 'Accounting', datetime.date(2009, 6, 1), 45000),
            ('Adams', 50000, 'Accounting', datetime.date(2013, 7, 1), 45000),
            ('Wilkinson', 60000, 'IT', datetime.date(2011, 3, 1), 60000),
            ('Moore', 34000, 'IT', datetime.date(2013, 8, 1), 60000),
            ('Miller', 100000, 'Management', datetime.date(2005, 6, 1), 100000),
            ('Johnson', 80000, 'Management', datetime.date(2005, 7, 1), 100000),
            ('Smith', 38000, 'Marketing', datetime.date(2009, 10, 1), 38000),
            ('Johnson', 40000, 'Marketing', datetime.date(2012, 3, 1), 38000),
            ('Smith', 55000, 'Sales', datetime.date(2007, 6, 1), 55000),
            ('Brown', 53000, 'Sales', datetime.date(2009, 9, 1), 55000),
        ], lambda row: (row.name, row.salary, row.department, row.hire_date, row.first_value))

    def test_last_value(self):
        qs = Employee.objects.annotate(last_value=Window(
            expression=LastValue('hire_date'),
            partition_by=F('department'),
            order_by=F('hire_date').asc(),
        ))
        self.assertQuerysetEqual(qs, [
            ('Adams', 'Accounting', datetime.date(2013, 7, 1), 50000, datetime.date(2013, 7, 1)),
            ('Jenson', 'Accounting', datetime.date(2008, 4, 1), 45000, datetime.date(2008, 4, 1)),
            ('Jones', 'Accounting', datetime.date(2005, 11, 1), 45000, datetime.date(2005, 11, 1)),
            ('Williams', 'Accounting', datetime.date(2009, 6, 1), 37000, datetime.date(2009, 6, 1)),
            ('Moore', 'IT', datetime.date(2013, 8, 1), 34000, datetime.date(2013, 8, 1)),
            ('Wilkinson', 'IT', datetime.date(2011, 3, 1), 60000, datetime.date(2011, 3, 1)),
            ('Miller', 'Management', datetime.date(2005, 6, 1), 100000, datetime.date(2005, 6, 1)),
            ('Johnson', 'Management', datetime.date(2005, 7, 1), 80000, datetime.date(2005, 7, 1)),
            ('Johnson', 'Marketing', datetime.date(2012, 3, 1), 40000, datetime.date(2012, 3, 1)),
            ('Smith', 'Marketing', datetime.date(2009, 10, 1), 38000, datetime.date(2009, 10, 1)),
            ('Brown', 'Sales', datetime.date(2009, 9, 1), 53000, datetime.date(2009, 9, 1)),
            ('Smith', 'Sales', datetime.date(2007, 6, 1), 55000, datetime.date(2007, 6, 1)),
        ], transform=lambda row: (row.name, row.department, row.hire_date, row.salary, row.last_value), ordered=False)

    def test_function_list_of_values(self):
        qs = Employee.objects.annotate(lead=Window(
            expression=Lead(expression='salary'),
            order_by=[F('hire_date').asc(), F('name').desc()],
            partition_by='department',
        )).values_list('name', 'salary', 'department', 'hire_date', 'lead') \
          .order_by('department', F('hire_date').asc(), F('name').desc())
        self.assertNotIn('GROUP BY', str(qs.query))
        self.assertSequenceEqual(qs, [
            ('Jones', 45000, 'Accounting', datetime.date(2005, 11, 1), 45000),
            ('Jenson', 45000, 'Accounting', datetime.date(2008, 4, 1), 37000),
            ('Williams', 37000, 'Accounting', datetime.date(2009, 6, 1), 50000),
            ('Adams', 50000, 'Accounting', datetime.date(2013, 7, 1), None),
            ('Wilkinson', 60000, 'IT', datetime.date(2011, 3, 1), 34000),
            ('Moore', 34000, 'IT', datetime.date(2013, 8, 1), None),
            ('Miller', 100000, 'Management', datetime.date(2005, 6, 1), 80000),
            ('Johnson', 80000, 'Management', datetime.date(2005, 7, 1), None),
            ('Smith', 38000, 'Marketing', datetime.date(2009, 10, 1), 40000),
            ('Johnson', 40000, 'Marketing', datetime.date(2012, 3, 1), None),
            ('Smith', 55000, 'Sales', datetime.date(2007, 6, 1), 53000),
            ('Brown', 53000, 'Sales', datetime.date(2009, 9, 1), None),
        ])

    def test_min_department(self):
        """An alternative way to specify a query for FirstValue."""
        qs = Employee.objects.annotate(min_salary=Window(
            expression=Min('salary'),
            partition_by=F('department'),
            order_by=[F('salary').asc(), F('name').asc()]
        )).order_by('department', 'salary', 'name')
        self.assertQuerysetEqual(qs, [
            ('Williams', 'Accounting', 37000, 37000),
            ('Jenson', 'Accounting', 45000, 37000),
            ('Jones', 'Accounting', 45000, 37000),
            ('Adams', 'Accounting', 50000, 37000),
            ('Moore', 'IT', 34000, 34000),
            ('Wilkinson', 'IT', 60000, 34000),
            ('Johnson', 'Management', 80000, 80000),
            ('Miller', 'Management', 100000, 80000),
            ('Smith', 'Marketing', 38000, 38000),
            ('Johnson', 'Marketing', 40000, 38000),
            ('Brown', 'Sales', 53000, 53000),
            ('Smith', 'Sales', 55000, 53000),
        ], lambda row: (row.name, row.department, row.salary, row.min_salary))

    def test_max_per_year(self):
        """
        Find the maximum salary awarded in the same year as the
        employee was hired, regardless of the department.
        """
        qs = Employee.objects.annotate(max_salary_year=Window(
            expression=Max('salary'),
            order_by=ExtractYear('hire_date').asc(),
            partition_by=ExtractYear('hire_date')
        )).order_by(ExtractYear('hire_date'), 'salary')
        self.assertQuerysetEqual(qs, [
            ('Jones', 'Accounting', 45000, 2005, 100000),
            ('Johnson', 'Management', 80000, 2005, 100000),
            ('Miller', 'Management', 100000, 2005, 100000),
            ('Smith', 'Sales', 55000, 2007, 55000),
            ('Jenson', 'Accounting', 45000, 2008, 45000),
            ('Williams', 'Accounting', 37000, 2009, 53000),
            ('Smith', 'Marketing', 38000, 2009, 53000),
            ('Brown', 'Sales', 53000, 2009, 53000),
            ('Wilkinson', 'IT', 60000, 2011, 60000),
            ('Johnson', 'Marketing', 40000, 2012, 40000),
            ('Moore', 'IT', 34000, 2013, 50000),
            ('Adams', 'Accounting', 50000, 2013, 50000),
        ], lambda row: (row.name, row.department, row.salary, row.hire_date.year, row.max_salary_year))

    def test_cume_dist(self):
        """
        Compute the cumulative distribution for the employees based on the
        salary in increasing order. Equal to rank/total number of rows (12).
        """
        qs = Employee.objects.annotate(cume_dist=Window(
            expression=CumeDist(),
            order_by=F('salary').asc(),
        )).order_by('salary', 'name')
        # Round result of cume_dist because Oracle uses greater precision.
        self.assertQuerysetEqual(qs, [
            ('Moore', 'IT', 34000, 0.0833333333),
            ('Williams', 'Accounting', 37000, 0.1666666667),
            ('Smith', 'Marketing', 38000, 0.25),
            ('Johnson', 'Marketing', 40000, 0.3333333333),
            ('Jenson', 'Accounting', 45000, 0.5),
            ('Jones', 'Accounting', 45000, 0.5),
            ('Adams', 'Accounting', 50000, 0.5833333333),
            ('Brown', 'Sales', 53000, 0.6666666667),
            ('Smith', 'Sales', 55000, 0.75),
            ('Wilkinson', 'IT', 60000, 0.8333333333),
            ('Johnson', 'Management', 80000, 0.9166666667),
            ('Miller', 'Management', 100000, 1),
        ], lambda row: (row.name, row.department, row.salary, round(row.cume_dist, 10)))

    def test_nthvalue(self):
        qs = Employee.objects.annotate(
            nth_value=Window(expression=NthValue(
                expression='salary', nth=2),
                order_by=[F('hire_date').asc(), F('name').desc()],
                partition_by=F('department'),
            )
        ).order_by('department', 'hire_date', 'name')
        self.assertQuerysetEqual(qs, [
            ('Jones', 'Accounting', datetime.date(2005, 11, 1), 45000, None),
            ('Jenson', 'Accounting', datetime.date(2008, 4, 1), 45000, 45000),
            ('Williams', 'Accounting', datetime.date(2009, 6, 1), 37000, 45000),
            ('Adams', 'Accounting', datetime.date(2013, 7, 1), 50000, 45000),
            ('Wilkinson', 'IT', datetime.date(2011, 3, 1), 60000, None),
            ('Moore', 'IT', datetime.date(2013, 8, 1), 34000, 34000),
            ('Miller', 'Management', datetime.date(2005, 6, 1), 100000, None),
            ('Johnson', 'Management', datetime.date(2005, 7, 1), 80000, 80000),
            ('Smith', 'Marketing', datetime.date(2009, 10, 1), 38000, None),
            ('Johnson', 'Marketing', datetime.date(2012, 3, 1), 40000, 40000),
            ('Smith', 'Sales', datetime.date(2007, 6, 1), 55000, None),
            ('Brown', 'Sales', datetime.date(2009, 9, 1), 53000, 53000),
        ], lambda row: (row.name, row.department, row.hire_date, row.salary, row.nth_value))

    def test_lead(self):
        """
        Determine what the next person hired in the same department makes.
        Because the dataset is ambiguous, the name is also part of the
        ordering clause. No default is provided, so None/NULL should be
        returned.
        """
        qs = Employee.objects.annotate(lead=Window(
            expression=Lead(expression='salary'),
            order_by=[F('hire_date').asc(), F('name').desc()],
            partition_by='department',
        )).order_by('department', F('hire_date').asc(), F('name').desc())
        self.assertQuerysetEqual(qs, [
            ('Jones', 45000, 'Accounting', datetime.date(2005, 11, 1), 45000),
            ('Jenson', 45000, 'Accounting', datetime.date(2008, 4, 1), 37000),
            ('Williams', 37000, 'Accounting', datetime.date(2009, 6, 1), 50000),
            ('Adams', 50000, 'Accounting', datetime.date(2013, 7, 1), None),
            ('Wilkinson', 60000, 'IT', datetime.date(2011, 3, 1), 34000),
            ('Moore', 34000, 'IT', datetime.date(2013, 8, 1), None),
            ('Miller', 100000, 'Management', datetime.date(2005, 6, 1), 80000),
            ('Johnson', 80000, 'Management', datetime.date(2005, 7, 1), None),
            ('Smith', 38000, 'Marketing', datetime.date(2009, 10, 1), 40000),
            ('Johnson', 40000, 'Marketing', datetime.date(2012, 3, 1), None),
            ('Smith', 55000, 'Sales', datetime.date(2007, 6, 1), 53000),
            ('Brown', 53000, 'Sales', datetime.date(2009, 9, 1), None),
        ], transform=lambda row: (row.name, row.salary, row.department, row.hire_date, row.lead))

    def test_lead_offset(self):
        """
        Determine what the person hired after someone makes. Due to
        ambiguity, the name is also included in the ordering.
        """
        qs = Employee.objects.annotate(lead=Window(
            expression=Lead('salary', offset=2),
            partition_by='department',
            order_by=F('hire_date').asc(),
        ))
        self.assertQuerysetEqual(qs, [
            ('Jones', 45000, 'Accounting', datetime.date(2005, 11, 1), 37000),
            ('Jenson', 45000, 'Accounting', datetime.date(2008, 4, 1), 50000),
            ('Williams', 37000, 'Accounting', datetime.date(2009, 6, 1), None),
            ('Adams', 50000, 'Accounting', datetime.date(2013, 7, 1), None),
            ('Wilkinson', 60000, 'IT', datetime.date(2011, 3, 1), None),
            ('Moore', 34000, 'IT', datetime.date(2013, 8, 1), None),
            ('Johnson', 80000, 'Management', datetime.date(2005, 7, 1), None),
            ('Miller', 100000, 'Management', datetime.date(2005, 6, 1), None),
            ('Smith', 38000, 'Marketing', datetime.date(2009, 10, 1), None),
            ('Johnson', 40000, 'Marketing', datetime.date(2012, 3, 1), None),
            ('Smith', 55000, 'Sales', datetime.date(2007, 6, 1), None),
            ('Brown', 53000, 'Sales', datetime.date(2009, 9, 1), None),
        ], transform=lambda row: (row.name, row.salary, row.department, row.hire_date, row.lead),
            ordered=False
        )

    @skipUnlessDBFeature('supports_default_in_lead_lag')
    def test_lead_default(self):
        qs = Employee.objects.annotate(lead_default=Window(
            expression=Lead(expression='salary', offset=5, default=60000),
            partition_by=F('department'),
            order_by=F('department').asc(),
        ))
        self.assertEqual(list(qs.values_list('lead_default', flat=True).distinct()), [60000])

    def test_ntile(self):
        """
        Compute the group for each of the employees across the entire company,
        based on how high the salary is for them. There are twelve employees
        so it divides evenly into four groups.
        """
        qs = Employee.objects.annotate(ntile=Window(
            expression=Ntile(num_buckets=4),
            order_by=F('salary').desc(),
        )).order_by('ntile', '-salary', 'name')
        self.assertQuerysetEqual(qs, [
            ('Miller', 'Management', 100000, 1),
            ('Johnson', 'Management', 80000, 1),
            ('Wilkinson', 'IT', 60000, 1),
            ('Smith', 'Sales', 55000, 2),
            ('Brown', 'Sales', 53000, 2),
            ('Adams', 'Accounting', 50000, 2),
            ('Jenson', 'Accounting', 45000, 3),
            ('Jones', 'Accounting', 45000, 3),
            ('Johnson', 'Marketing', 40000, 3),
            ('Smith', 'Marketing', 38000, 4),
            ('Williams', 'Accounting', 37000, 4),
            ('Moore', 'IT', 34000, 4),
        ], lambda x: (x.name, x.department, x.salary, x.ntile))

    def test_percent_rank(self):
        """
        Calculate the percentage rank of the employees across the entire
        company based on salary and name (in case of ambiguity).
        """
        qs = Employee.objects.annotate(percent_rank=Window(
            expression=PercentRank(),
            order_by=[F('salary').asc(), F('name').asc()],
        )).order_by('percent_rank')
        # Round to account for precision differences among databases.
        self.assertQuerysetEqual(qs, [
            ('Moore', 'IT', 34000, 0.0),
            ('Williams', 'Accounting', 37000, 0.0909090909),
            ('Smith', 'Marketing', 38000, 0.1818181818),
            ('Johnson', 'Marketing', 40000, 0.2727272727),
            ('Jenson', 'Accounting', 45000, 0.3636363636),
            ('Jones', 'Accounting', 45000, 0.4545454545),
            ('Adams', 'Accounting', 50000, 0.5454545455),
            ('Brown', 'Sales', 53000, 0.6363636364),
            ('Smith', 'Sales', 55000, 0.7272727273),
            ('Wilkinson', 'IT', 60000, 0.8181818182),
            ('Johnson', 'Management', 80000, 0.9090909091),
            ('Miller', 'Management', 100000, 1.0),
        ], transform=lambda row: (row.name, row.department, row.salary, round(row.percent_rank, 10)))

    def test_nth_returns_null(self):
        """
        Find the nth row of the data set. None is returned since there are
        fewer than 20 rows in the test data.
        """
        qs = Employee.objects.annotate(nth_value=Window(
            expression=NthValue('salary', nth=20),
            order_by=F('salary').asc()
        ))
        self.assertEqual(list(qs.values_list('nth_value', flat=True).distinct()), [None])

    def test_multiple_partitioning(self):
        """
        Find the maximum salary for each department for people hired in the
        same year.
        """
        qs = Employee.objects.annotate(max=Window(
            expression=Max('salary'),
            partition_by=[F('department'), ExtractYear(F('hire_date'))],
        )).order_by('department', 'hire_date', 'name')
        self.assertQuerysetEqual(qs, [
            ('Jones', 45000, 'Accounting', datetime.date(2005, 11, 1), 45000),
            ('Jenson', 45000, 'Accounting', datetime.date(2008, 4, 1), 45000),
            ('Williams', 37000, 'Accounting', datetime.date(2009, 6, 1), 37000),
            ('Adams', 50000, 'Accounting', datetime.date(2013, 7, 1), 50000),
            ('Wilkinson', 60000, 'IT', datetime.date(2011, 3, 1), 60000),
            ('Moore', 34000, 'IT', datetime.date(2013, 8, 1), 34000),
            ('Miller', 100000, 'Management', datetime.date(2005, 6, 1), 100000),
            ('Johnson', 80000, 'Management', datetime.date(2005, 7, 1), 100000),
            ('Smith', 38000, 'Marketing', datetime.date(2009, 10, 1), 38000),
            ('Johnson', 40000, 'Marketing', datetime.date(2012, 3, 1), 40000),
            ('Smith', 55000, 'Sales', datetime.date(2007, 6, 1), 55000),
            ('Brown', 53000, 'Sales', datetime.date(2009, 9, 1), 53000),
        ], transform=lambda row: (row.name, row.salary, row.department, row.hire_date, row.max))

    def test_multiple_ordering(self):
        """
        Accumulate the salaries over the departments based on hire_date.
        If two people were hired on the same date in the same department, the
        ordering clause will render a different result for those people.
        """
        qs = Employee.objects.annotate(sum=Window(
            expression=Sum('salary'),
            partition_by='department',
            order_by=[F('hire_date').asc(), F('name').asc()],
        )).order_by('department', 'sum')
        self.assertQuerysetEqual(qs, [
            ('Jones', 45000, 'Accounting', datetime.date(2005, 11, 1), 45000),
            ('Jenson', 45000, 'Accounting', datetime.date(2008, 4, 1), 90000),
            ('Williams', 37000, 'Accounting', datetime.date(2009, 6, 1), 127000),
            ('Adams', 50000, 'Accounting', datetime.date(2013, 7, 1), 177000),
            ('Wilkinson', 60000, 'IT', datetime.date(2011, 3, 1), 60000),
            ('Moore', 34000, 'IT', datetime.date(2013, 8, 1), 94000),
            ('Miller', 100000, 'Management', datetime.date(2005, 6, 1), 100000),
            ('Johnson', 80000, 'Management', datetime.date(2005, 7, 1), 180000),
            ('Smith', 38000, 'Marketing', datetime.date(2009, 10, 1), 38000),
            ('Johnson', 40000, 'Marketing', datetime.date(2012, 3, 1), 78000),
            ('Smith', 55000, 'Sales', datetime.date(2007, 6, 1), 55000),
            ('Brown', 53000, 'Sales', datetime.date(2009, 9, 1), 108000),
        ], transform=lambda row: (row.name, row.salary, row.department, row.hire_date, row.sum))

    @skipUnlessDBFeature('supports_frame_range_fixed_distance')
    def test_range_n_preceding_and_following(self):
        qs = Employee.objects.annotate(sum=Window(
            expression=Sum('salary'),
            order_by=F('salary').asc(),
            partition_by='department',
            frame=ValueRange(start=-2, end=2),
        ))
        self.assertIn('RANGE BETWEEN 2 PRECEDING AND 2 FOLLOWING', str(qs.query))
        self.assertQuerysetEqual(qs, [
            ('Williams', 37000, 'Accounting', datetime.date(2009, 6, 1), 37000),
            ('Jones', 45000, 'Accounting', datetime.date(2005, 11, 1), 90000),
            ('Jenson', 45000, 'Accounting', datetime.date(2008, 4, 1), 90000),
            ('Adams', 50000, 'Accounting', datetime.date(2013, 7, 1), 50000),
            ('Brown', 53000, 'Sales', datetime.date(2009, 9, 1), 53000),
            ('Smith', 55000, 'Sales', datetime.date(2007, 6, 1), 55000),
            ('Johnson', 40000, 'Marketing', datetime.date(2012, 3, 1), 40000),
            ('Smith', 38000, 'Marketing', datetime.date(2009, 10, 1), 38000),
            ('Wilkinson', 60000, 'IT', datetime.date(2011, 3, 1), 60000),
            ('Moore', 34000, 'IT', datetime.date(2013, 8, 1), 34000),
            ('Miller', 100000, 'Management', datetime.date(2005, 6, 1), 100000),
            ('Johnson', 80000, 'Management', datetime.date(2005, 7, 1), 80000),
        ], transform=lambda row: (row.name, row.salary, row.department, row.hire_date, row.sum), ordered=False)

    def test_range_unbound(self):
        """A query with RANGE BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING."""
        qs = Employee.objects.annotate(sum=Window(
            expression=Sum('salary'),
            partition_by='age',
            order_by=[F('age').asc()],
            frame=ValueRange(start=None, end=None),
        )).order_by('department', 'hire_date', 'name')
        self.assertIn('RANGE BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING', str(qs.query))
        self.assertQuerysetEqual(qs, [
            ('Jones', 'Accounting', 45000, datetime.date(2005, 11, 1), 165000),
            ('Jenson', 'Accounting', 45000, datetime.date(2008, 4, 1), 165000),
            ('Williams', 'Accounting', 37000, datetime.date(2009, 6, 1), 165000),
            ('Adams', 'Accounting', 50000, datetime.date(2013, 7, 1), 130000),
            ('Wilkinson', 'IT', 60000, datetime.date(2011, 3, 1), 194000),
            ('Moore', 'IT', 34000, datetime.date(2013, 8, 1), 194000),
            ('Miller', 'Management', 100000, datetime.date(2005, 6, 1), 194000),
            ('Johnson', 'Management', 80000, datetime.date(2005, 7, 1), 130000),
            ('Smith', 'Marketing', 38000, datetime.date(2009, 10, 1), 165000),
            ('Johnson', 'Marketing', 40000, datetime.date(2012, 3, 1), 148000),
            ('Smith', 'Sales', 55000, datetime.date(2007, 6, 1), 148000),
            ('Brown', 'Sales', 53000, datetime.date(2009, 9, 1), 148000)
        ], transform=lambda row: (row.name, row.department, row.salary, row.hire_date, row.sum))

    @skipIf(
        connection.vendor == 'sqlite' and connection.Database.sqlite_version_info < (3, 27),
        'Nondeterministic failure on SQLite < 3.27.'
    )
    def test_subquery_row_range_rank(self):
        qs = Employee.objects.annotate(
            highest_avg_salary_date=Subquery(
                Employee.objects.filter(
                    department=OuterRef('department'),
                ).annotate(
                    avg_salary=Window(
                        expression=Avg('salary'),
                        order_by=[F('hire_date').asc()],
                        frame=RowRange(start=-1, end=1),
                    ),
                ).order_by('-avg_salary', 'hire_date').values('hire_date')[:1],
            ),
        ).order_by('department', 'name')
        self.assertQuerysetEqual(qs, [
            ('Adams', 'Accounting', datetime.date(2005, 11, 1)),
            ('Jenson', 'Accounting', datetime.date(2005, 11, 1)),
            ('Jones', 'Accounting', datetime.date(2005, 11, 1)),
            ('Williams', 'Accounting', datetime.date(2005, 11, 1)),
            ('Moore', 'IT', datetime.date(2011, 3, 1)),
            ('Wilkinson', 'IT', datetime.date(2011, 3, 1)),
            ('Johnson', 'Management', datetime.date(2005, 6, 1)),
            ('Miller', 'Management', datetime.date(2005, 6, 1)),
            ('Johnson', 'Marketing', datetime.date(2009, 10, 1)),
            ('Smith', 'Marketing', datetime.date(2009, 10, 1)),
            ('Brown', 'Sales', datetime.date(2007, 6, 1)),
            ('Smith', 'Sales', datetime.date(2007, 6, 1)),
        ], transform=lambda row: (row.name, row.department, row.highest_avg_salary_date))

    def test_row_range_rank(self):
        """
        A query with ROWS BETWEEN UNBOUNDED PRECEDING AND 3 FOLLOWING.
        The resulting sum is the sum of the three next (if they exist) and all
        previous rows according to the ordering clause.
        """
        qs = Employee.objects.annotate(sum=Window(
            expression=Sum('salary'),
            order_by=[F('hire_date').asc(), F('name').desc()],
            frame=RowRange(start=None, end=3),
        )).order_by('sum', 'hire_date')
        self.assertIn('ROWS BETWEEN UNBOUNDED PRECEDING AND 3 FOLLOWING', str(qs.query))
        self.assertQuerysetEqual(qs, [
            ('Miller', 100000, 'Management', datetime.date(2005, 6, 1), 280000),
            ('Johnson', 80000, 'Management', datetime.date(2005, 7, 1), 325000),
            ('Jones', 45000, 'Accounting', datetime.date(2005, 11, 1), 362000),
            ('Smith', 55000, 'Sales', datetime.date(2007, 6, 1), 415000),
            ('Jenson', 45000, 'Accounting', datetime.date(2008, 4, 1), 453000),
            ('Williams', 37000, 'Accounting', datetime.date(2009, 6, 1), 513000),
            ('Brown', 53000, 'Sales', datetime.date(2009, 9, 1), 553000),
            ('Smith', 38000, 'Marketing', datetime.date(2009, 10, 1), 603000),
            ('Wilkinson', 60000, 'IT', datetime.date(2011, 3, 1), 637000),
            ('Johnson', 40000, 'Marketing', datetime.date(2012, 3, 1), 637000),
            ('Adams', 50000, 'Accounting', datetime.date(2013, 7, 1), 637000),
            ('Moore', 34000, 'IT', datetime.date(2013, 8, 1), 637000),
        ], transform=lambda row: (row.name, row.salary, row.department, row.hire_date, row.sum))

    @skipUnlessDBFeature('can_distinct_on_fields')
    def test_distinct_window_function(self):
        """
        Window functions are not aggregates, and hence a query to filter out
        duplicates may be useful.
        """
        qs = Employee.objects.annotate(
            sum=Window(
                expression=Sum('salary'),
                partition_by=ExtractYear('hire_date'),
                order_by=ExtractYear('hire_date')
            ),
            year=ExtractYear('hire_date'),
        ).values('year', 'sum').distinct('year').order_by('year')
        results = [
            {'year': 2005, 'sum': 225000}, {'year': 2007, 'sum': 55000},
            {'year': 2008, 'sum': 45000}, {'year': 2009, 'sum': 128000},
            {'year': 2011, 'sum': 60000}, {'year': 2012, 'sum': 40000},
            {'year': 2013, 'sum': 84000},
        ]
        for idx, val in zip(range(len(results)), results):
            with self.subTest(result=val):
                self.assertEqual(qs[idx], val)

    def test_fail_update(self):
        """Window expressions can't be used in an UPDATE statement."""
        msg = (
            'Window expressions are not allowed in this query (salary=<Window: '
            'Max(Col(expressions_window_employee, expressions_window.Employee.salary)) '
            'OVER (PARTITION BY Col(expressions_window_employee, '
            'expressions_window.Employee.department))>).'
        )
        with self.assertRaisesMessage(FieldError, msg):
            Employee.objects.filter(department='Management').update(
                salary=Window(expression=Max('salary'), partition_by='department'),
            )

    def test_fail_insert(self):
        """Window expressions can't be used in an INSERT statement."""
        msg = (
            'Window expressions are not allowed in this query (salary=<Window: '
            'Sum(Value(10000), order_by=OrderBy(F(pk), descending=False)) OVER ()'
        )
        with self.assertRaisesMessage(FieldError, msg):
            Employee.objects.create(
                name='Jameson', department='Management', hire_date=datetime.date(2007, 7, 1),
                salary=Window(expression=Sum(Value(10000), order_by=F('pk').asc())),
            )

    def test_window_expression_within_subquery(self):
        subquery_qs = Employee.objects.annotate(
            highest=Window(FirstValue('id'), partition_by=F('department'), order_by=F('salary').desc())
        ).values('highest')
        highest_salary = Employee.objects.filter(pk__in=subquery_qs)
        self.assertSequenceEqual(highest_salary.values('department', 'salary'), [
            {'department': 'Accounting', 'salary': 50000},
            {'department': 'Sales', 'salary': 55000},
            {'department': 'Marketing', 'salary': 40000},
            {'department': 'IT', 'salary': 60000},
            {'department': 'Management', 'salary': 100000}
        ])

    def test_invalid_start_value_range(self):
        msg = "start argument must be a negative integer, zero, or None, but got '3'."
        with self.assertRaisesMessage(ValueError, msg):
            list(Employee.objects.annotate(test=Window(
                expression=Sum('salary'),
                order_by=F('hire_date').asc(),
                frame=ValueRange(start=3),
            )))

    def test_invalid_end_value_range(self):
        msg = "end argument must be a positive integer, zero, or None, but got '-3'."
        with self.assertRaisesMessage(ValueError, msg):
            list(Employee.objects.annotate(test=Window(
                expression=Sum('salary'),
                order_by=F('hire_date').asc(),
                frame=ValueRange(end=-3),
            )))

    def test_invalid_type_end_value_range(self):
        msg = "end argument must be a positive integer, zero, or None, but got 'a'."
        with self.assertRaisesMessage(ValueError, msg):
            list(Employee.objects.annotate(test=Window(
                expression=Sum('salary'),
                order_by=F('hire_date').asc(),
                frame=ValueRange(end='a'),
            )))

    def test_invalid_type_start_value_range(self):
        msg = "start argument must be a negative integer, zero, or None, but got 'a'."
        with self.assertRaisesMessage(ValueError, msg):
            list(Employee.objects.annotate(test=Window(
                expression=Sum('salary'),
                frame=ValueRange(start='a'),
            )))

    def test_invalid_type_end_row_range(self):
        msg = "end argument must be a positive integer, zero, or None, but got 'a'."
        with self.assertRaisesMessage(ValueError, msg):
            list(Employee.objects.annotate(test=Window(
                expression=Sum('salary'),
                frame=RowRange(end='a'),
            )))

    @skipUnless(connection.vendor == 'postgresql', 'Frame construction not allowed on PostgreSQL')
    def test_postgresql_illegal_range_frame_start(self):
        msg = 'PostgreSQL only supports UNBOUNDED together with PRECEDING and FOLLOWING.'
        with self.assertRaisesMessage(NotSupportedError, msg):
            list(Employee.objects.annotate(test=Window(
                expression=Sum('salary'),
                order_by=F('hire_date').asc(),
                frame=ValueRange(start=-1),
            )))

    @skipUnless(connection.vendor == 'postgresql', 'Frame construction not allowed on PostgreSQL')
    def test_postgresql_illegal_range_frame_end(self):
        msg = 'PostgreSQL only supports UNBOUNDED together with PRECEDING and FOLLOWING.'
        with self.assertRaisesMessage(NotSupportedError, msg):
            list(Employee.objects.annotate(test=Window(
                expression=Sum('salary'),
                order_by=F('hire_date').asc(),
                frame=ValueRange(end=1),
            )))

    def test_invalid_type_start_row_range(self):
        msg = "start argument must be a negative integer, zero, or None, but got 'a'."
        with self.assertRaisesMessage(ValueError, msg):
            list(Employee.objects.annotate(test=Window(
                expression=Sum('salary'),
                order_by=F('hire_date').asc(),
                frame=RowRange(start='a'),
            )))


class NonQueryWindowTests(SimpleTestCase):
    def test_window_repr(self):
        self.assertEqual(
            repr(Window(expression=Sum('salary'), partition_by='department')),
            '<Window: Sum(F(salary)) OVER (PARTITION BY F(department))>'
        )
        self.assertEqual(
            repr(Window(expression=Avg('salary'), order_by=F('department').asc())),
            '<Window: Avg(F(salary)) OVER (ORDER BY OrderBy(F(department), descending=False))>'
        )

    def test_window_frame_repr(self):
        self.assertEqual(
            repr(RowRange(start=-1)),
            '<RowRange: ROWS BETWEEN 1 PRECEDING AND UNBOUNDED FOLLOWING>'
        )
        self.assertEqual(
            repr(ValueRange(start=None, end=1)),
            '<ValueRange: RANGE BETWEEN UNBOUNDED PRECEDING AND 1 FOLLOWING>'
        )
        self.assertEqual(
            repr(ValueRange(start=0, end=0)),
            '<ValueRange: RANGE BETWEEN CURRENT ROW AND CURRENT ROW>'
        )
        self.assertEqual(
            repr(RowRange(start=0, end=0)),
            '<RowRange: ROWS BETWEEN CURRENT ROW AND CURRENT ROW>'
        )

    def test_empty_group_by_cols(self):
        window = Window(expression=Sum('pk'))
        self.assertEqual(window.get_group_by_cols(), [])
        self.assertFalse(window.contains_aggregate)

    def test_frame_empty_group_by_cols(self):
        frame = WindowFrame()
        self.assertEqual(frame.get_group_by_cols(), [])

    def test_frame_window_frame_notimplemented(self):
        frame = WindowFrame()
        msg = 'Subclasses must implement window_frame_start_end().'
        with self.assertRaisesMessage(NotImplementedError, msg):
            frame.window_frame_start_end(None, None, None)

    def test_invalid_filter(self):
        msg = 'Window is disallowed in the filter clause'
        with self.assertRaisesMessage(NotSupportedError, msg):
            Employee.objects.annotate(dense_rank=Window(expression=DenseRank())).filter(dense_rank__gte=1)

    def test_unsupported_backend(self):
        msg = 'This backend does not support window expressions.'
        with mock.patch.object(connection.features, 'supports_over_clause', False):
            with self.assertRaisesMessage(NotSupportedError, msg):
                Employee.objects.annotate(dense_rank=Window(expression=DenseRank())).get()

    def test_invalid_order_by(self):
        msg = 'order_by must be either an Expression or a sequence of expressions'
        with self.assertRaisesMessage(ValueError, msg):
            Window(expression=Sum('power'), order_by='-horse')

    def test_invalid_source_expression(self):
        msg = "Expression 'Upper' isn't compatible with OVER clauses."
        with self.assertRaisesMessage(ValueError, msg):
            Window(expression=Upper('name'))
