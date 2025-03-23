import datetime
from decimal import Decimal
from unittest import mock

from django.core.exceptions import FieldError
from django.db import NotSupportedError, connection
from django.db.models import (
    Avg,
    Case,
    Count,
    F,
    IntegerField,
    Max,
    Min,
    OuterRef,
    Q,
    RowRange,
    Subquery,
    Sum,
    Value,
    ValueRange,
    When,
    Window,
    WindowFrame,
    WindowFrameExclusion,
)
from django.db.models.fields.json import KeyTextTransform, KeyTransform
from django.db.models.functions import (
    Cast,
    CumeDist,
    DenseRank,
    ExtractYear,
    FirstValue,
    Lag,
    LastValue,
    Lead,
    NthValue,
    Ntile,
    PercentRank,
    Rank,
    RowNumber,
    Upper,
)
from django.db.models.lookups import Exact
from django.test import SimpleTestCase, TestCase, skipIfDBFeature, skipUnlessDBFeature
from django.test.utils import CaptureQueriesContext

from .models import Classification, Detail, Employee, PastEmployeeDepartment


@skipUnlessDBFeature("supports_over_clause")
class WindowFunctionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        classification = Classification.objects.create()
        Employee.objects.bulk_create(
            [
                Employee(
                    name=e[0],
                    salary=e[1],
                    department=e[2],
                    hire_date=e[3],
                    age=e[4],
                    bonus=Decimal(e[1]) / 400,
                    classification=classification,
                )
                for e in [
                    ("Jones", 45000, "Accounting", datetime.datetime(2005, 11, 1), 20),
                    (
                        "Williams",
                        37000,
                        "Accounting",
                        datetime.datetime(2009, 6, 1),
                        20,
                    ),
                    ("Jenson", 45000, "Accounting", datetime.datetime(2008, 4, 1), 20),
                    ("Adams", 50000, "Accounting", datetime.datetime(2013, 7, 1), 50),
                    ("Smith", 55000, "Sales", datetime.datetime(2007, 6, 1), 30),
                    ("Brown", 53000, "Sales", datetime.datetime(2009, 9, 1), 30),
                    ("Johnson", 40000, "Marketing", datetime.datetime(2012, 3, 1), 30),
                    ("Smith", 38000, "Marketing", datetime.datetime(2009, 10, 1), 20),
                    ("Wilkinson", 60000, "IT", datetime.datetime(2011, 3, 1), 40),
                    ("Moore", 34000, "IT", datetime.datetime(2013, 8, 1), 40),
                    ("Miller", 100000, "Management", datetime.datetime(2005, 6, 1), 40),
                    ("Johnson", 80000, "Management", datetime.datetime(2005, 7, 1), 50),
                ]
            ]
        )
        employees = list(Employee.objects.order_by("pk"))
        PastEmployeeDepartment.objects.bulk_create(
            [
                PastEmployeeDepartment(employee=employees[6], department="Sales"),
                PastEmployeeDepartment(employee=employees[10], department="IT"),
            ]
        )

    def test_dense_rank(self):
        tests = [
            ExtractYear(F("hire_date")).asc(),
            F("hire_date__year").asc(),
            "hire_date__year",
        ]
        for order_by in tests:
            with self.subTest(order_by=order_by):
                qs = Employee.objects.annotate(
                    rank=Window(expression=DenseRank(), order_by=order_by),
                )
                self.assertQuerySetEqual(
                    qs,
                    [
                        ("Jones", 45000, "Accounting", datetime.date(2005, 11, 1), 1),
                        ("Miller", 100000, "Management", datetime.date(2005, 6, 1), 1),
                        ("Johnson", 80000, "Management", datetime.date(2005, 7, 1), 1),
                        ("Smith", 55000, "Sales", datetime.date(2007, 6, 1), 2),
                        ("Jenson", 45000, "Accounting", datetime.date(2008, 4, 1), 3),
                        ("Smith", 38000, "Marketing", datetime.date(2009, 10, 1), 4),
                        ("Brown", 53000, "Sales", datetime.date(2009, 9, 1), 4),
                        ("Williams", 37000, "Accounting", datetime.date(2009, 6, 1), 4),
                        ("Wilkinson", 60000, "IT", datetime.date(2011, 3, 1), 5),
                        ("Johnson", 40000, "Marketing", datetime.date(2012, 3, 1), 6),
                        ("Moore", 34000, "IT", datetime.date(2013, 8, 1), 7),
                        ("Adams", 50000, "Accounting", datetime.date(2013, 7, 1), 7),
                    ],
                    lambda entry: (
                        entry.name,
                        entry.salary,
                        entry.department,
                        entry.hire_date,
                        entry.rank,
                    ),
                    ordered=False,
                )

    def test_department_salary(self):
        qs = Employee.objects.annotate(
            department_sum=Window(
                expression=Sum("salary"),
                partition_by=F("department"),
                order_by=[F("hire_date").asc()],
            )
        ).order_by("department", "department_sum")
        self.assertQuerySetEqual(
            qs,
            [
                ("Jones", "Accounting", 45000, 45000),
                ("Jenson", "Accounting", 45000, 90000),
                ("Williams", "Accounting", 37000, 127000),
                ("Adams", "Accounting", 50000, 177000),
                ("Wilkinson", "IT", 60000, 60000),
                ("Moore", "IT", 34000, 94000),
                ("Miller", "Management", 100000, 100000),
                ("Johnson", "Management", 80000, 180000),
                ("Smith", "Marketing", 38000, 38000),
                ("Johnson", "Marketing", 40000, 78000),
                ("Smith", "Sales", 55000, 55000),
                ("Brown", "Sales", 53000, 108000),
            ],
            lambda entry: (
                entry.name,
                entry.department,
                entry.salary,
                entry.department_sum,
            ),
        )

    def test_rank(self):
        """
        Rank the employees based on the year they're were hired. Since there
        are multiple employees hired in different years, this will contain
        gaps.
        """
        qs = Employee.objects.annotate(
            rank=Window(
                expression=Rank(),
                order_by=F("hire_date__year").asc(),
            )
        )
        self.assertQuerySetEqual(
            qs,
            [
                ("Jones", 45000, "Accounting", datetime.date(2005, 11, 1), 1),
                ("Miller", 100000, "Management", datetime.date(2005, 6, 1), 1),
                ("Johnson", 80000, "Management", datetime.date(2005, 7, 1), 1),
                ("Smith", 55000, "Sales", datetime.date(2007, 6, 1), 4),
                ("Jenson", 45000, "Accounting", datetime.date(2008, 4, 1), 5),
                ("Smith", 38000, "Marketing", datetime.date(2009, 10, 1), 6),
                ("Brown", 53000, "Sales", datetime.date(2009, 9, 1), 6),
                ("Williams", 37000, "Accounting", datetime.date(2009, 6, 1), 6),
                ("Wilkinson", 60000, "IT", datetime.date(2011, 3, 1), 9),
                ("Johnson", 40000, "Marketing", datetime.date(2012, 3, 1), 10),
                ("Moore", 34000, "IT", datetime.date(2013, 8, 1), 11),
                ("Adams", 50000, "Accounting", datetime.date(2013, 7, 1), 11),
            ],
            lambda entry: (
                entry.name,
                entry.salary,
                entry.department,
                entry.hire_date,
                entry.rank,
            ),
            ordered=False,
        )

    def test_row_number(self):
        """
        The row number window function computes the number based on the order
        in which the tuples were inserted. Depending on the backend,

        Oracle requires an ordering-clause in the Window expression.
        """
        qs = Employee.objects.annotate(
            row_number=Window(
                expression=RowNumber(),
                order_by=F("pk").asc(),
            )
        ).order_by("pk")
        self.assertQuerySetEqual(
            qs,
            [
                ("Jones", "Accounting", 1),
                ("Williams", "Accounting", 2),
                ("Jenson", "Accounting", 3),
                ("Adams", "Accounting", 4),
                ("Smith", "Sales", 5),
                ("Brown", "Sales", 6),
                ("Johnson", "Marketing", 7),
                ("Smith", "Marketing", 8),
                ("Wilkinson", "IT", 9),
                ("Moore", "IT", 10),
                ("Miller", "Management", 11),
                ("Johnson", "Management", 12),
            ],
            lambda entry: (entry.name, entry.department, entry.row_number),
        )

    def test_row_number_no_ordering(self):
        """
        The row number window function computes the number based on the order
        in which the tuples were inserted.
        """
        # Add a default ordering for consistent results across databases.
        qs = Employee.objects.annotate(
            row_number=Window(
                expression=RowNumber(),
            )
        ).order_by("pk")
        self.assertQuerySetEqual(
            qs,
            [
                ("Jones", "Accounting", 1),
                ("Williams", "Accounting", 2),
                ("Jenson", "Accounting", 3),
                ("Adams", "Accounting", 4),
                ("Smith", "Sales", 5),
                ("Brown", "Sales", 6),
                ("Johnson", "Marketing", 7),
                ("Smith", "Marketing", 8),
                ("Wilkinson", "IT", 9),
                ("Moore", "IT", 10),
                ("Miller", "Management", 11),
                ("Johnson", "Management", 12),
            ],
            lambda entry: (entry.name, entry.department, entry.row_number),
        )

    def test_avg_salary_department(self):
        qs = Employee.objects.annotate(
            avg_salary=Window(
                expression=Avg("salary"),
                order_by=F("department").asc(),
                partition_by="department",
            )
        ).order_by("department", "-salary", "name")
        self.assertQuerySetEqual(
            qs,
            [
                ("Adams", 50000, "Accounting", 44250.00),
                ("Jenson", 45000, "Accounting", 44250.00),
                ("Jones", 45000, "Accounting", 44250.00),
                ("Williams", 37000, "Accounting", 44250.00),
                ("Wilkinson", 60000, "IT", 47000.00),
                ("Moore", 34000, "IT", 47000.00),
                ("Miller", 100000, "Management", 90000.00),
                ("Johnson", 80000, "Management", 90000.00),
                ("Johnson", 40000, "Marketing", 39000.00),
                ("Smith", 38000, "Marketing", 39000.00),
                ("Smith", 55000, "Sales", 54000.00),
                ("Brown", 53000, "Sales", 54000.00),
            ],
            transform=lambda row: (
                row.name,
                row.salary,
                row.department,
                row.avg_salary,
            ),
        )

    def test_lag(self):
        """
        Compute the difference between an employee's salary and the next
        highest salary in the employee's department. Return None if the
        employee has the lowest salary.
        """
        qs = Employee.objects.annotate(
            lag=Window(
                expression=Lag(expression="salary", offset=1),
                partition_by=F("department"),
                order_by=[F("salary").asc(), F("name").asc()],
            )
        ).order_by("department", F("salary").asc(), F("name").asc())
        self.assertQuerySetEqual(
            qs,
            [
                ("Williams", 37000, "Accounting", None),
                ("Jenson", 45000, "Accounting", 37000),
                ("Jones", 45000, "Accounting", 45000),
                ("Adams", 50000, "Accounting", 45000),
                ("Moore", 34000, "IT", None),
                ("Wilkinson", 60000, "IT", 34000),
                ("Johnson", 80000, "Management", None),
                ("Miller", 100000, "Management", 80000),
                ("Smith", 38000, "Marketing", None),
                ("Johnson", 40000, "Marketing", 38000),
                ("Brown", 53000, "Sales", None),
                ("Smith", 55000, "Sales", 53000),
            ],
            transform=lambda row: (row.name, row.salary, row.department, row.lag),
        )

    def test_lag_decimalfield(self):
        qs = Employee.objects.annotate(
            lag=Window(
                expression=Lag(expression="bonus", offset=1),
                partition_by=F("department"),
                order_by=[F("bonus").asc(), F("name").asc()],
            )
        ).order_by("department", F("bonus").asc(), F("name").asc())
        self.assertQuerySetEqual(
            qs,
            [
                ("Williams", 92.5, "Accounting", None),
                ("Jenson", 112.5, "Accounting", 92.5),
                ("Jones", 112.5, "Accounting", 112.5),
                ("Adams", 125, "Accounting", 112.5),
                ("Moore", 85, "IT", None),
                ("Wilkinson", 150, "IT", 85),
                ("Johnson", 200, "Management", None),
                ("Miller", 250, "Management", 200),
                ("Smith", 95, "Marketing", None),
                ("Johnson", 100, "Marketing", 95),
                ("Brown", 132.5, "Sales", None),
                ("Smith", 137.5, "Sales", 132.5),
            ],
            transform=lambda row: (row.name, row.bonus, row.department, row.lag),
        )

    def test_order_by_decimalfield(self):
        qs = Employee.objects.annotate(
            rank=Window(expression=Rank(), order_by="bonus")
        ).order_by("-bonus", "id")
        self.assertQuerySetEqual(
            qs,
            [
                ("Miller", 250.0, 12),
                ("Johnson", 200.0, 11),
                ("Wilkinson", 150.0, 10),
                ("Smith", 137.5, 9),
                ("Brown", 132.5, 8),
                ("Adams", 125.0, 7),
                ("Jones", 112.5, 5),
                ("Jenson", 112.5, 5),
                ("Johnson", 100.0, 4),
                ("Smith", 95.0, 3),
                ("Williams", 92.5, 2),
                ("Moore", 85.0, 1),
            ],
            transform=lambda row: (row.name, float(row.bonus), row.rank),
        )

    def test_first_value(self):
        qs = Employee.objects.annotate(
            first_value=Window(
                expression=FirstValue("salary"),
                partition_by=F("department"),
                order_by=F("hire_date").asc(),
            )
        ).order_by("department", "hire_date")
        self.assertQuerySetEqual(
            qs,
            [
                ("Jones", 45000, "Accounting", datetime.date(2005, 11, 1), 45000),
                ("Jenson", 45000, "Accounting", datetime.date(2008, 4, 1), 45000),
                ("Williams", 37000, "Accounting", datetime.date(2009, 6, 1), 45000),
                ("Adams", 50000, "Accounting", datetime.date(2013, 7, 1), 45000),
                ("Wilkinson", 60000, "IT", datetime.date(2011, 3, 1), 60000),
                ("Moore", 34000, "IT", datetime.date(2013, 8, 1), 60000),
                ("Miller", 100000, "Management", datetime.date(2005, 6, 1), 100000),
                ("Johnson", 80000, "Management", datetime.date(2005, 7, 1), 100000),
                ("Smith", 38000, "Marketing", datetime.date(2009, 10, 1), 38000),
                ("Johnson", 40000, "Marketing", datetime.date(2012, 3, 1), 38000),
                ("Smith", 55000, "Sales", datetime.date(2007, 6, 1), 55000),
                ("Brown", 53000, "Sales", datetime.date(2009, 9, 1), 55000),
            ],
            lambda row: (
                row.name,
                row.salary,
                row.department,
                row.hire_date,
                row.first_value,
            ),
        )

    def test_last_value(self):
        qs = Employee.objects.annotate(
            last_value=Window(
                expression=LastValue("hire_date"),
                partition_by=F("department"),
                order_by=F("hire_date").asc(),
            )
        )
        self.assertQuerySetEqual(
            qs,
            [
                (
                    "Adams",
                    "Accounting",
                    datetime.date(2013, 7, 1),
                    50000,
                    datetime.date(2013, 7, 1),
                ),
                (
                    "Jenson",
                    "Accounting",
                    datetime.date(2008, 4, 1),
                    45000,
                    datetime.date(2008, 4, 1),
                ),
                (
                    "Jones",
                    "Accounting",
                    datetime.date(2005, 11, 1),
                    45000,
                    datetime.date(2005, 11, 1),
                ),
                (
                    "Williams",
                    "Accounting",
                    datetime.date(2009, 6, 1),
                    37000,
                    datetime.date(2009, 6, 1),
                ),
                (
                    "Moore",
                    "IT",
                    datetime.date(2013, 8, 1),
                    34000,
                    datetime.date(2013, 8, 1),
                ),
                (
                    "Wilkinson",
                    "IT",
                    datetime.date(2011, 3, 1),
                    60000,
                    datetime.date(2011, 3, 1),
                ),
                (
                    "Miller",
                    "Management",
                    datetime.date(2005, 6, 1),
                    100000,
                    datetime.date(2005, 6, 1),
                ),
                (
                    "Johnson",
                    "Management",
                    datetime.date(2005, 7, 1),
                    80000,
                    datetime.date(2005, 7, 1),
                ),
                (
                    "Johnson",
                    "Marketing",
                    datetime.date(2012, 3, 1),
                    40000,
                    datetime.date(2012, 3, 1),
                ),
                (
                    "Smith",
                    "Marketing",
                    datetime.date(2009, 10, 1),
                    38000,
                    datetime.date(2009, 10, 1),
                ),
                (
                    "Brown",
                    "Sales",
                    datetime.date(2009, 9, 1),
                    53000,
                    datetime.date(2009, 9, 1),
                ),
                (
                    "Smith",
                    "Sales",
                    datetime.date(2007, 6, 1),
                    55000,
                    datetime.date(2007, 6, 1),
                ),
            ],
            transform=lambda row: (
                row.name,
                row.department,
                row.hire_date,
                row.salary,
                row.last_value,
            ),
            ordered=False,
        )

    def test_function_list_of_values(self):
        qs = (
            Employee.objects.annotate(
                lead=Window(
                    expression=Lead(expression="salary"),
                    order_by=[F("hire_date").asc(), F("name").desc()],
                    partition_by="department",
                )
            )
            .values_list("name", "salary", "department", "hire_date", "lead")
            .order_by("department", F("hire_date").asc(), F("name").desc())
        )
        self.assertNotIn("GROUP BY", str(qs.query))
        self.assertSequenceEqual(
            qs,
            [
                ("Jones", 45000, "Accounting", datetime.date(2005, 11, 1), 45000),
                ("Jenson", 45000, "Accounting", datetime.date(2008, 4, 1), 37000),
                ("Williams", 37000, "Accounting", datetime.date(2009, 6, 1), 50000),
                ("Adams", 50000, "Accounting", datetime.date(2013, 7, 1), None),
                ("Wilkinson", 60000, "IT", datetime.date(2011, 3, 1), 34000),
                ("Moore", 34000, "IT", datetime.date(2013, 8, 1), None),
                ("Miller", 100000, "Management", datetime.date(2005, 6, 1), 80000),
                ("Johnson", 80000, "Management", datetime.date(2005, 7, 1), None),
                ("Smith", 38000, "Marketing", datetime.date(2009, 10, 1), 40000),
                ("Johnson", 40000, "Marketing", datetime.date(2012, 3, 1), None),
                ("Smith", 55000, "Sales", datetime.date(2007, 6, 1), 53000),
                ("Brown", 53000, "Sales", datetime.date(2009, 9, 1), None),
            ],
        )

    def test_min_department(self):
        """An alternative way to specify a query for FirstValue."""
        qs = Employee.objects.annotate(
            min_salary=Window(
                expression=Min("salary"),
                partition_by=F("department"),
                order_by=[F("salary").asc(), F("name").asc()],
            )
        ).order_by("department", "salary", "name")
        self.assertQuerySetEqual(
            qs,
            [
                ("Williams", "Accounting", 37000, 37000),
                ("Jenson", "Accounting", 45000, 37000),
                ("Jones", "Accounting", 45000, 37000),
                ("Adams", "Accounting", 50000, 37000),
                ("Moore", "IT", 34000, 34000),
                ("Wilkinson", "IT", 60000, 34000),
                ("Johnson", "Management", 80000, 80000),
                ("Miller", "Management", 100000, 80000),
                ("Smith", "Marketing", 38000, 38000),
                ("Johnson", "Marketing", 40000, 38000),
                ("Brown", "Sales", 53000, 53000),
                ("Smith", "Sales", 55000, 53000),
            ],
            lambda row: (row.name, row.department, row.salary, row.min_salary),
        )

    def test_max_per_year(self):
        """
        Find the maximum salary awarded in the same year as the
        employee was hired, regardless of the department.
        """
        qs = Employee.objects.annotate(
            max_salary_year=Window(
                expression=Max("salary"),
                order_by=ExtractYear("hire_date").asc(),
                partition_by=ExtractYear("hire_date"),
            )
        ).order_by(ExtractYear("hire_date"), "salary")
        self.assertQuerySetEqual(
            qs,
            [
                ("Jones", "Accounting", 45000, 2005, 100000),
                ("Johnson", "Management", 80000, 2005, 100000),
                ("Miller", "Management", 100000, 2005, 100000),
                ("Smith", "Sales", 55000, 2007, 55000),
                ("Jenson", "Accounting", 45000, 2008, 45000),
                ("Williams", "Accounting", 37000, 2009, 53000),
                ("Smith", "Marketing", 38000, 2009, 53000),
                ("Brown", "Sales", 53000, 2009, 53000),
                ("Wilkinson", "IT", 60000, 2011, 60000),
                ("Johnson", "Marketing", 40000, 2012, 40000),
                ("Moore", "IT", 34000, 2013, 50000),
                ("Adams", "Accounting", 50000, 2013, 50000),
            ],
            lambda row: (
                row.name,
                row.department,
                row.salary,
                row.hire_date.year,
                row.max_salary_year,
            ),
        )

    def test_cume_dist(self):
        """
        Compute the cumulative distribution for the employees based on the
        salary in increasing order. Equal to rank/total number of rows (12).
        """
        qs = Employee.objects.annotate(
            cume_dist=Window(
                expression=CumeDist(),
                order_by=F("salary").asc(),
            )
        ).order_by("salary", "name")
        # Round result of cume_dist because Oracle uses greater precision.
        self.assertQuerySetEqual(
            qs,
            [
                ("Moore", "IT", 34000, 0.0833333333),
                ("Williams", "Accounting", 37000, 0.1666666667),
                ("Smith", "Marketing", 38000, 0.25),
                ("Johnson", "Marketing", 40000, 0.3333333333),
                ("Jenson", "Accounting", 45000, 0.5),
                ("Jones", "Accounting", 45000, 0.5),
                ("Adams", "Accounting", 50000, 0.5833333333),
                ("Brown", "Sales", 53000, 0.6666666667),
                ("Smith", "Sales", 55000, 0.75),
                ("Wilkinson", "IT", 60000, 0.8333333333),
                ("Johnson", "Management", 80000, 0.9166666667),
                ("Miller", "Management", 100000, 1),
            ],
            lambda row: (
                row.name,
                row.department,
                row.salary,
                round(row.cume_dist, 10),
            ),
        )

    def test_nthvalue(self):
        qs = Employee.objects.annotate(
            nth_value=Window(
                expression=NthValue(expression="salary", nth=2),
                order_by=[F("hire_date").asc(), F("name").desc()],
                partition_by=F("department"),
            )
        ).order_by("department", "hire_date", "name")
        self.assertQuerySetEqual(
            qs,
            [
                ("Jones", "Accounting", datetime.date(2005, 11, 1), 45000, None),
                ("Jenson", "Accounting", datetime.date(2008, 4, 1), 45000, 45000),
                ("Williams", "Accounting", datetime.date(2009, 6, 1), 37000, 45000),
                ("Adams", "Accounting", datetime.date(2013, 7, 1), 50000, 45000),
                ("Wilkinson", "IT", datetime.date(2011, 3, 1), 60000, None),
                ("Moore", "IT", datetime.date(2013, 8, 1), 34000, 34000),
                ("Miller", "Management", datetime.date(2005, 6, 1), 100000, None),
                ("Johnson", "Management", datetime.date(2005, 7, 1), 80000, 80000),
                ("Smith", "Marketing", datetime.date(2009, 10, 1), 38000, None),
                ("Johnson", "Marketing", datetime.date(2012, 3, 1), 40000, 40000),
                ("Smith", "Sales", datetime.date(2007, 6, 1), 55000, None),
                ("Brown", "Sales", datetime.date(2009, 9, 1), 53000, 53000),
            ],
            lambda row: (
                row.name,
                row.department,
                row.hire_date,
                row.salary,
                row.nth_value,
            ),
        )

    def test_lead(self):
        """
        Determine what the next person hired in the same department makes.
        Because the dataset is ambiguous, the name is also part of the
        ordering clause. No default is provided, so None/NULL should be
        returned.
        """
        qs = Employee.objects.annotate(
            lead=Window(
                expression=Lead(expression="salary"),
                order_by=[F("hire_date").asc(), F("name").desc()],
                partition_by="department",
            )
        ).order_by("department", F("hire_date").asc(), F("name").desc())
        self.assertQuerySetEqual(
            qs,
            [
                ("Jones", 45000, "Accounting", datetime.date(2005, 11, 1), 45000),
                ("Jenson", 45000, "Accounting", datetime.date(2008, 4, 1), 37000),
                ("Williams", 37000, "Accounting", datetime.date(2009, 6, 1), 50000),
                ("Adams", 50000, "Accounting", datetime.date(2013, 7, 1), None),
                ("Wilkinson", 60000, "IT", datetime.date(2011, 3, 1), 34000),
                ("Moore", 34000, "IT", datetime.date(2013, 8, 1), None),
                ("Miller", 100000, "Management", datetime.date(2005, 6, 1), 80000),
                ("Johnson", 80000, "Management", datetime.date(2005, 7, 1), None),
                ("Smith", 38000, "Marketing", datetime.date(2009, 10, 1), 40000),
                ("Johnson", 40000, "Marketing", datetime.date(2012, 3, 1), None),
                ("Smith", 55000, "Sales", datetime.date(2007, 6, 1), 53000),
                ("Brown", 53000, "Sales", datetime.date(2009, 9, 1), None),
            ],
            transform=lambda row: (
                row.name,
                row.salary,
                row.department,
                row.hire_date,
                row.lead,
            ),
        )

    def test_lead_offset(self):
        """
        Determine what the person hired after someone makes. Due to
        ambiguity, the name is also included in the ordering.
        """
        qs = Employee.objects.annotate(
            lead=Window(
                expression=Lead("salary", offset=2),
                partition_by="department",
                order_by=F("hire_date").asc(),
            )
        )
        self.assertQuerySetEqual(
            qs,
            [
                ("Jones", 45000, "Accounting", datetime.date(2005, 11, 1), 37000),
                ("Jenson", 45000, "Accounting", datetime.date(2008, 4, 1), 50000),
                ("Williams", 37000, "Accounting", datetime.date(2009, 6, 1), None),
                ("Adams", 50000, "Accounting", datetime.date(2013, 7, 1), None),
                ("Wilkinson", 60000, "IT", datetime.date(2011, 3, 1), None),
                ("Moore", 34000, "IT", datetime.date(2013, 8, 1), None),
                ("Johnson", 80000, "Management", datetime.date(2005, 7, 1), None),
                ("Miller", 100000, "Management", datetime.date(2005, 6, 1), None),
                ("Smith", 38000, "Marketing", datetime.date(2009, 10, 1), None),
                ("Johnson", 40000, "Marketing", datetime.date(2012, 3, 1), None),
                ("Smith", 55000, "Sales", datetime.date(2007, 6, 1), None),
                ("Brown", 53000, "Sales", datetime.date(2009, 9, 1), None),
            ],
            transform=lambda row: (
                row.name,
                row.salary,
                row.department,
                row.hire_date,
                row.lead,
            ),
            ordered=False,
        )

    @skipUnlessDBFeature("supports_default_in_lead_lag")
    def test_lead_default(self):
        qs = Employee.objects.annotate(
            lead_default=Window(
                expression=Lead(expression="salary", offset=5, default=60000),
                partition_by=F("department"),
                order_by=F("department").asc(),
            )
        )
        self.assertEqual(
            list(qs.values_list("lead_default", flat=True).distinct()), [60000]
        )

    def test_ntile(self):
        """
        Compute the group for each of the employees across the entire company,
        based on how high the salary is for them. There are twelve employees
        so it divides evenly into four groups.
        """
        qs = Employee.objects.annotate(
            ntile=Window(
                expression=Ntile(num_buckets=4),
                order_by="-salary",
            )
        ).order_by("ntile", "-salary", "name")
        self.assertQuerySetEqual(
            qs,
            [
                ("Miller", "Management", 100000, 1),
                ("Johnson", "Management", 80000, 1),
                ("Wilkinson", "IT", 60000, 1),
                ("Smith", "Sales", 55000, 2),
                ("Brown", "Sales", 53000, 2),
                ("Adams", "Accounting", 50000, 2),
                ("Jenson", "Accounting", 45000, 3),
                ("Jones", "Accounting", 45000, 3),
                ("Johnson", "Marketing", 40000, 3),
                ("Smith", "Marketing", 38000, 4),
                ("Williams", "Accounting", 37000, 4),
                ("Moore", "IT", 34000, 4),
            ],
            lambda x: (x.name, x.department, x.salary, x.ntile),
        )

    def test_percent_rank(self):
        """
        Calculate the percentage rank of the employees across the entire
        company based on salary and name (in case of ambiguity).
        """
        qs = Employee.objects.annotate(
            percent_rank=Window(
                expression=PercentRank(),
                order_by=[F("salary").asc(), F("name").asc()],
            )
        ).order_by("percent_rank")
        # Round to account for precision differences among databases.
        self.assertQuerySetEqual(
            qs,
            [
                ("Moore", "IT", 34000, 0.0),
                ("Williams", "Accounting", 37000, 0.0909090909),
                ("Smith", "Marketing", 38000, 0.1818181818),
                ("Johnson", "Marketing", 40000, 0.2727272727),
                ("Jenson", "Accounting", 45000, 0.3636363636),
                ("Jones", "Accounting", 45000, 0.4545454545),
                ("Adams", "Accounting", 50000, 0.5454545455),
                ("Brown", "Sales", 53000, 0.6363636364),
                ("Smith", "Sales", 55000, 0.7272727273),
                ("Wilkinson", "IT", 60000, 0.8181818182),
                ("Johnson", "Management", 80000, 0.9090909091),
                ("Miller", "Management", 100000, 1.0),
            ],
            transform=lambda row: (
                row.name,
                row.department,
                row.salary,
                round(row.percent_rank, 10),
            ),
        )

    def test_nth_returns_null(self):
        """
        Find the nth row of the data set. None is returned since there are
        fewer than 20 rows in the test data.
        """
        qs = Employee.objects.annotate(
            nth_value=Window(
                expression=NthValue("salary", nth=20), order_by=F("salary").asc()
            )
        )
        self.assertEqual(
            list(qs.values_list("nth_value", flat=True).distinct()), [None]
        )

    def test_multiple_partitioning(self):
        """
        Find the maximum salary for each department for people hired in the
        same year.
        """
        qs = Employee.objects.annotate(
            max=Window(
                expression=Max("salary"),
                partition_by=[F("department"), F("hire_date__year")],
            ),
            past_department_count=Count("past_departments"),
        ).order_by("department", "hire_date", "name")
        self.assertQuerySetEqual(
            qs,
            [
                ("Jones", 45000, "Accounting", datetime.date(2005, 11, 1), 45000, 0),
                ("Jenson", 45000, "Accounting", datetime.date(2008, 4, 1), 45000, 0),
                ("Williams", 37000, "Accounting", datetime.date(2009, 6, 1), 37000, 0),
                ("Adams", 50000, "Accounting", datetime.date(2013, 7, 1), 50000, 0),
                ("Wilkinson", 60000, "IT", datetime.date(2011, 3, 1), 60000, 0),
                ("Moore", 34000, "IT", datetime.date(2013, 8, 1), 34000, 0),
                ("Miller", 100000, "Management", datetime.date(2005, 6, 1), 100000, 1),
                ("Johnson", 80000, "Management", datetime.date(2005, 7, 1), 100000, 0),
                ("Smith", 38000, "Marketing", datetime.date(2009, 10, 1), 38000, 0),
                ("Johnson", 40000, "Marketing", datetime.date(2012, 3, 1), 40000, 1),
                ("Smith", 55000, "Sales", datetime.date(2007, 6, 1), 55000, 0),
                ("Brown", 53000, "Sales", datetime.date(2009, 9, 1), 53000, 0),
            ],
            transform=lambda row: (
                row.name,
                row.salary,
                row.department,
                row.hire_date,
                row.max,
                row.past_department_count,
            ),
        )

    def test_multiple_ordering(self):
        """
        Accumulate the salaries over the departments based on hire_date.
        If two people were hired on the same date in the same department, the
        ordering clause will render a different result for those people.
        """
        qs = Employee.objects.annotate(
            sum=Window(
                expression=Sum("salary"),
                partition_by="department",
                order_by=[F("hire_date").asc(), F("name").asc()],
            )
        ).order_by("department", "sum")
        self.assertQuerySetEqual(
            qs,
            [
                ("Jones", 45000, "Accounting", datetime.date(2005, 11, 1), 45000),
                ("Jenson", 45000, "Accounting", datetime.date(2008, 4, 1), 90000),
                ("Williams", 37000, "Accounting", datetime.date(2009, 6, 1), 127000),
                ("Adams", 50000, "Accounting", datetime.date(2013, 7, 1), 177000),
                ("Wilkinson", 60000, "IT", datetime.date(2011, 3, 1), 60000),
                ("Moore", 34000, "IT", datetime.date(2013, 8, 1), 94000),
                ("Miller", 100000, "Management", datetime.date(2005, 6, 1), 100000),
                ("Johnson", 80000, "Management", datetime.date(2005, 7, 1), 180000),
                ("Smith", 38000, "Marketing", datetime.date(2009, 10, 1), 38000),
                ("Johnson", 40000, "Marketing", datetime.date(2012, 3, 1), 78000),
                ("Smith", 55000, "Sales", datetime.date(2007, 6, 1), 55000),
                ("Brown", 53000, "Sales", datetime.date(2009, 9, 1), 108000),
            ],
            transform=lambda row: (
                row.name,
                row.salary,
                row.department,
                row.hire_date,
                row.sum,
            ),
        )

    def test_empty_ordering(self):
        """
        Explicit empty ordering makes little sense but it is something that
        was historically allowed.
        """
        qs = Employee.objects.annotate(
            sum=Window(
                expression=Sum("salary"),
                partition_by="department",
                order_by=[],
            )
        ).order_by("department", "sum")
        self.assertEqual(len(qs), 12)

    def test_related_ordering_with_count(self):
        qs = Employee.objects.annotate(
            department_sum=Window(
                expression=Sum("salary"),
                partition_by=F("department"),
                order_by=["classification__code"],
            )
        )
        self.assertEqual(qs.count(), 12)

    def test_filter(self):
        qs = Employee.objects.annotate(
            department_salary_rank=Window(
                Rank(), partition_by="department", order_by="-salary"
            ),
            department_avg_age_diff=(
                Window(Avg("age"), partition_by="department") - F("age")
            ),
        ).order_by("department", "name")
        # Direct window reference.
        self.assertQuerySetEqual(
            qs.filter(department_salary_rank=1),
            ["Adams", "Wilkinson", "Miller", "Johnson", "Smith"],
            lambda employee: employee.name,
        )
        # Through a combined expression containing a window.
        self.assertQuerySetEqual(
            qs.filter(department_avg_age_diff__gt=0),
            ["Jenson", "Jones", "Williams", "Miller", "Smith"],
            lambda employee: employee.name,
        )
        # Intersection of multiple windows.
        self.assertQuerySetEqual(
            qs.filter(department_salary_rank=1, department_avg_age_diff__gt=0),
            ["Miller"],
            lambda employee: employee.name,
        )
        # Union of multiple windows.
        self.assertQuerySetEqual(
            qs.filter(Q(department_salary_rank=1) | Q(department_avg_age_diff__gt=0)),
            [
                "Adams",
                "Jenson",
                "Jones",
                "Williams",
                "Wilkinson",
                "Miller",
                "Johnson",
                "Smith",
                "Smith",
            ],
            lambda employee: employee.name,
        )

    def test_filter_conditional_annotation(self):
        qs = (
            Employee.objects.annotate(
                rank=Window(Rank(), partition_by="department", order_by="-salary"),
                case_first_rank=Case(
                    When(rank=1, then=True),
                    default=False,
                ),
                q_first_rank=Q(rank=1),
            )
            .order_by("name")
            .values_list("name", flat=True)
        )
        for annotation in ["case_first_rank", "q_first_rank"]:
            with self.subTest(annotation=annotation):
                self.assertSequenceEqual(
                    qs.filter(**{annotation: True}),
                    ["Adams", "Johnson", "Miller", "Smith", "Wilkinson"],
                )

    def test_filter_conditional_expression(self):
        qs = (
            Employee.objects.filter(
                Exact(Window(Rank(), partition_by="department", order_by="-salary"), 1)
            )
            .order_by("name")
            .values_list("name", flat=True)
        )
        self.assertSequenceEqual(
            qs, ["Adams", "Johnson", "Miller", "Smith", "Wilkinson"]
        )

    def test_filter_column_ref_rhs(self):
        qs = (
            Employee.objects.annotate(
                max_dept_salary=Window(Max("salary"), partition_by="department")
            )
            .filter(max_dept_salary=F("salary"))
            .order_by("name")
            .values_list("name", flat=True)
        )
        self.assertSequenceEqual(
            qs, ["Adams", "Johnson", "Miller", "Smith", "Wilkinson"]
        )

    def test_filter_values(self):
        qs = (
            Employee.objects.annotate(
                department_salary_rank=Window(
                    Rank(), partition_by="department", order_by="-salary"
                ),
            )
            .order_by("department", "name")
            .values_list(Upper("name"), flat=True)
        )
        self.assertSequenceEqual(
            qs.filter(department_salary_rank=1),
            ["ADAMS", "WILKINSON", "MILLER", "JOHNSON", "SMITH"],
        )

    def test_filter_alias(self):
        qs = Employee.objects.alias(
            department_avg_age_diff=(
                Window(Avg("age"), partition_by="department") - F("age")
            ),
        ).order_by("department", "name")
        self.assertQuerySetEqual(
            qs.filter(department_avg_age_diff__gt=0),
            ["Jenson", "Jones", "Williams", "Miller", "Smith"],
            lambda employee: employee.name,
        )

    def test_filter_select_related(self):
        qs = (
            Employee.objects.alias(
                department_avg_age_diff=(
                    Window(Avg("age"), partition_by="department") - F("age")
                ),
            )
            .select_related("classification")
            .filter(department_avg_age_diff__gt=0)
            .order_by("department", "name")
        )
        self.assertQuerySetEqual(
            qs,
            ["Jenson", "Jones", "Williams", "Miller", "Smith"],
            lambda employee: employee.name,
        )
        with self.assertNumQueries(0):
            qs[0].classification

    def test_exclude(self):
        qs = Employee.objects.annotate(
            department_salary_rank=Window(
                Rank(), partition_by="department", order_by="-salary"
            ),
            department_avg_age_diff=(
                Window(Avg("age"), partition_by="department") - F("age")
            ),
        ).order_by("department", "name")
        # Direct window reference.
        self.assertQuerySetEqual(
            qs.exclude(department_salary_rank__gt=1),
            ["Adams", "Wilkinson", "Miller", "Johnson", "Smith"],
            lambda employee: employee.name,
        )
        # Through a combined expression containing a window.
        self.assertQuerySetEqual(
            qs.exclude(department_avg_age_diff__lte=0),
            ["Jenson", "Jones", "Williams", "Miller", "Smith"],
            lambda employee: employee.name,
        )
        # Union of multiple windows.
        self.assertQuerySetEqual(
            qs.exclude(
                Q(department_salary_rank__gt=1) | Q(department_avg_age_diff__lte=0)
            ),
            ["Miller"],
            lambda employee: employee.name,
        )
        # Intersection of multiple windows.
        self.assertQuerySetEqual(
            qs.exclude(department_salary_rank__gt=1, department_avg_age_diff__lte=0),
            [
                "Adams",
                "Jenson",
                "Jones",
                "Williams",
                "Wilkinson",
                "Miller",
                "Johnson",
                "Smith",
                "Smith",
            ],
            lambda employee: employee.name,
        )

    def test_heterogeneous_filter(self):
        qs = (
            Employee.objects.annotate(
                department_salary_rank=Window(
                    Rank(), partition_by="department", order_by="-salary"
                ),
            )
            .order_by("name")
            .values_list("name", flat=True)
        )
        # Heterogeneous filter between window function and aggregates pushes
        # the WHERE clause to the QUALIFY outer query.
        self.assertSequenceEqual(
            qs.filter(
                department_salary_rank=1, department__in=["Accounting", "Management"]
            ),
            ["Adams", "Miller"],
        )
        self.assertSequenceEqual(
            qs.filter(
                Q(department_salary_rank=1)
                | Q(department__in=["Accounting", "Management"])
            ),
            [
                "Adams",
                "Jenson",
                "Johnson",
                "Johnson",
                "Jones",
                "Miller",
                "Smith",
                "Wilkinson",
                "Williams",
            ],
        )
        # Heterogeneous filter between window function and aggregates pushes
        # the HAVING clause to the QUALIFY outer query.
        qs = qs.annotate(past_department_count=Count("past_departments"))
        self.assertSequenceEqual(
            qs.filter(department_salary_rank=1, past_department_count__gte=1),
            ["Johnson", "Miller"],
        )
        self.assertSequenceEqual(
            qs.filter(Q(department_salary_rank=1) | Q(past_department_count__gte=1)),
            ["Adams", "Johnson", "Miller", "Smith", "Wilkinson"],
        )

    def test_limited_filter(self):
        """
        A query filtering against a window function have its limit applied
        after window filtering takes place.
        """
        self.assertQuerySetEqual(
            Employee.objects.annotate(
                department_salary_rank=Window(
                    Rank(), partition_by="department", order_by="-salary"
                )
            )
            .filter(department_salary_rank=1)
            .order_by("department")[0:3],
            ["Adams", "Wilkinson", "Miller"],
            lambda employee: employee.name,
        )

    def test_filter_count(self):
        with CaptureQueriesContext(connection) as ctx:
            self.assertEqual(
                Employee.objects.annotate(
                    department_salary_rank=Window(
                        Rank(), partition_by="department", order_by="-salary"
                    )
                )
                .filter(department_salary_rank=1)
                .count(),
                5,
            )
        self.assertEqual(len(ctx.captured_queries), 1)
        sql = ctx.captured_queries[0]["sql"].lower()
        self.assertEqual(sql.count("select"), 3)
        self.assertNotIn("group by", sql)

    @skipUnlessDBFeature("supports_frame_range_fixed_distance")
    def test_range_n_preceding_and_following(self):
        qs = Employee.objects.annotate(
            sum=Window(
                expression=Sum("salary"),
                order_by=F("salary").asc(),
                partition_by="department",
                frame=ValueRange(start=-2, end=2),
            )
        )
        self.assertIn("RANGE BETWEEN 2 PRECEDING AND 2 FOLLOWING", str(qs.query))
        self.assertQuerySetEqual(
            qs,
            [
                ("Williams", 37000, "Accounting", datetime.date(2009, 6, 1), 37000),
                ("Jones", 45000, "Accounting", datetime.date(2005, 11, 1), 90000),
                ("Jenson", 45000, "Accounting", datetime.date(2008, 4, 1), 90000),
                ("Adams", 50000, "Accounting", datetime.date(2013, 7, 1), 50000),
                ("Brown", 53000, "Sales", datetime.date(2009, 9, 1), 53000),
                ("Smith", 55000, "Sales", datetime.date(2007, 6, 1), 55000),
                ("Johnson", 40000, "Marketing", datetime.date(2012, 3, 1), 40000),
                ("Smith", 38000, "Marketing", datetime.date(2009, 10, 1), 38000),
                ("Wilkinson", 60000, "IT", datetime.date(2011, 3, 1), 60000),
                ("Moore", 34000, "IT", datetime.date(2013, 8, 1), 34000),
                ("Miller", 100000, "Management", datetime.date(2005, 6, 1), 100000),
                ("Johnson", 80000, "Management", datetime.date(2005, 7, 1), 80000),
            ],
            transform=lambda row: (
                row.name,
                row.salary,
                row.department,
                row.hire_date,
                row.sum,
            ),
            ordered=False,
        )

    @skipUnlessDBFeature(
        "supports_frame_exclusion", "supports_frame_range_fixed_distance"
    )
    def test_range_exclude_current(self):
        qs = Employee.objects.annotate(
            sum=Window(
                expression=Sum("salary"),
                order_by=F("salary").asc(),
                partition_by="department",
                frame=ValueRange(end=2, exclusion=WindowFrameExclusion.CURRENT_ROW),
            )
        ).order_by("department", "salary")
        self.assertIn(
            "RANGE BETWEEN UNBOUNDED PRECEDING AND 2 FOLLOWING EXCLUDE CURRENT ROW",
            str(qs.query),
        )
        self.assertQuerySetEqual(
            qs,
            [
                ("Williams", 37000, "Accounting", datetime.date(2009, 6, 1), None),
                ("Jones", 45000, "Accounting", datetime.date(2005, 11, 1), 82000),
                ("Jenson", 45000, "Accounting", datetime.date(2008, 4, 1), 82000),
                ("Adams", 50000, "Accounting", datetime.date(2013, 7, 1), 127000),
                ("Moore", 34000, "IT", datetime.date(2013, 8, 1), None),
                ("Wilkinson", 60000, "IT", datetime.date(2011, 3, 1), 34000),
                ("Johnson", 80000, "Management", datetime.date(2005, 7, 1), None),
                ("Miller", 100000, "Management", datetime.date(2005, 6, 1), 80000),
                ("Smith", 38000, "Marketing", datetime.date(2009, 10, 1), None),
                ("Johnson", 40000, "Marketing", datetime.date(2012, 3, 1), 38000),
                ("Brown", 53000, "Sales", datetime.date(2009, 9, 1), None),
                ("Smith", 55000, "Sales", datetime.date(2007, 6, 1), 53000),
            ],
            transform=lambda row: (
                row.name,
                row.salary,
                row.department,
                row.hire_date,
                row.sum,
            ),
        )

    def test_range_unbound(self):
        """A query with RANGE BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING."""
        qs = Employee.objects.annotate(
            sum=Window(
                expression=Sum("salary"),
                partition_by="age",
                order_by=[F("age").asc()],
                frame=ValueRange(start=None, end=None),
            )
        ).order_by("department", "hire_date", "name")
        self.assertIn(
            "RANGE BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING", str(qs.query)
        )
        self.assertQuerySetEqual(
            qs,
            [
                ("Jones", "Accounting", 45000, datetime.date(2005, 11, 1), 165000),
                ("Jenson", "Accounting", 45000, datetime.date(2008, 4, 1), 165000),
                ("Williams", "Accounting", 37000, datetime.date(2009, 6, 1), 165000),
                ("Adams", "Accounting", 50000, datetime.date(2013, 7, 1), 130000),
                ("Wilkinson", "IT", 60000, datetime.date(2011, 3, 1), 194000),
                ("Moore", "IT", 34000, datetime.date(2013, 8, 1), 194000),
                ("Miller", "Management", 100000, datetime.date(2005, 6, 1), 194000),
                ("Johnson", "Management", 80000, datetime.date(2005, 7, 1), 130000),
                ("Smith", "Marketing", 38000, datetime.date(2009, 10, 1), 165000),
                ("Johnson", "Marketing", 40000, datetime.date(2012, 3, 1), 148000),
                ("Smith", "Sales", 55000, datetime.date(2007, 6, 1), 148000),
                ("Brown", "Sales", 53000, datetime.date(2009, 9, 1), 148000),
            ],
            transform=lambda row: (
                row.name,
                row.department,
                row.salary,
                row.hire_date,
                row.sum,
            ),
        )

    def test_subquery_row_range_rank(self):
        qs = Employee.objects.annotate(
            highest_avg_salary_date=Subquery(
                Employee.objects.filter(
                    department=OuterRef("department"),
                )
                .annotate(
                    avg_salary=Window(
                        expression=Avg("salary"),
                        order_by=[F("hire_date").asc()],
                        frame=RowRange(start=-1, end=1),
                    ),
                )
                .order_by("-avg_salary", "hire_date")
                .values("hire_date")[:1],
            ),
        ).order_by("department", "name")
        self.assertQuerySetEqual(
            qs,
            [
                ("Adams", "Accounting", datetime.date(2005, 11, 1)),
                ("Jenson", "Accounting", datetime.date(2005, 11, 1)),
                ("Jones", "Accounting", datetime.date(2005, 11, 1)),
                ("Williams", "Accounting", datetime.date(2005, 11, 1)),
                ("Moore", "IT", datetime.date(2011, 3, 1)),
                ("Wilkinson", "IT", datetime.date(2011, 3, 1)),
                ("Johnson", "Management", datetime.date(2005, 6, 1)),
                ("Miller", "Management", datetime.date(2005, 6, 1)),
                ("Johnson", "Marketing", datetime.date(2009, 10, 1)),
                ("Smith", "Marketing", datetime.date(2009, 10, 1)),
                ("Brown", "Sales", datetime.date(2007, 6, 1)),
                ("Smith", "Sales", datetime.date(2007, 6, 1)),
            ],
            transform=lambda row: (
                row.name,
                row.department,
                row.highest_avg_salary_date,
            ),
        )

    @skipUnlessDBFeature("supports_frame_exclusion")
    def test_row_range_rank_exclude_current_row(self):
        qs = Employee.objects.annotate(
            avg_salary_cohort=Window(
                expression=Avg("salary"),
                order_by=[F("hire_date").asc(), F("name").desc()],
                frame=RowRange(
                    start=-1, end=1, exclusion=WindowFrameExclusion.CURRENT_ROW
                ),
            )
        ).order_by("hire_date")
        self.assertIn(
            "ROWS BETWEEN 1 PRECEDING AND 1 FOLLOWING EXCLUDE CURRENT ROW",
            str(qs.query),
        )
        self.assertQuerySetEqual(
            qs,
            [
                ("Miller", 100000, "Management", datetime.date(2005, 6, 1), 80000),
                ("Johnson", 80000, "Management", datetime.date(2005, 7, 1), 72500),
                ("Jones", 45000, "Accounting", datetime.date(2005, 11, 1), 67500),
                ("Smith", 55000, "Sales", datetime.date(2007, 6, 1), 45000),
                ("Jenson", 45000, "Accounting", datetime.date(2008, 4, 1), 46000),
                ("Williams", 37000, "Accounting", datetime.date(2009, 6, 1), 49000),
                ("Brown", 53000, "Sales", datetime.date(2009, 9, 1), 37500),
                ("Smith", 38000, "Marketing", datetime.date(2009, 10, 1), 56500),
                ("Wilkinson", 60000, "IT", datetime.date(2011, 3, 1), 39000),
                ("Johnson", 40000, "Marketing", datetime.date(2012, 3, 1), 55000),
                ("Adams", 50000, "Accounting", datetime.date(2013, 7, 1), 37000),
                ("Moore", 34000, "IT", datetime.date(2013, 8, 1), 50000),
            ],
            transform=lambda row: (
                row.name,
                row.salary,
                row.department,
                row.hire_date,
                row.avg_salary_cohort,
            ),
        )

    @skipUnlessDBFeature("supports_frame_exclusion")
    def test_row_range_rank_exclude_group(self):
        qs = Employee.objects.annotate(
            avg_salary_cohort=Window(
                expression=Avg("salary"),
                order_by=[F("hire_date").asc(), F("name").desc()],
                frame=RowRange(start=-1, end=1, exclusion=WindowFrameExclusion.GROUP),
            )
        ).order_by("hire_date")
        self.assertIn(
            "ROWS BETWEEN 1 PRECEDING AND 1 FOLLOWING EXCLUDE GROUP",
            str(qs.query),
        )
        self.assertQuerySetEqual(
            qs,
            [
                ("Miller", 100000, "Management", datetime.date(2005, 6, 1), 80000),
                ("Johnson", 80000, "Management", datetime.date(2005, 7, 1), 72500),
                ("Jones", 45000, "Accounting", datetime.date(2005, 11, 1), 67500),
                ("Smith", 55000, "Sales", datetime.date(2007, 6, 1), 45000),
                ("Jenson", 45000, "Accounting", datetime.date(2008, 4, 1), 46000),
                ("Williams", 37000, "Accounting", datetime.date(2009, 6, 1), 49000),
                ("Brown", 53000, "Sales", datetime.date(2009, 9, 1), 37500),
                ("Smith", 38000, "Marketing", datetime.date(2009, 10, 1), 56500),
                ("Wilkinson", 60000, "IT", datetime.date(2011, 3, 1), 39000),
                ("Johnson", 40000, "Marketing", datetime.date(2012, 3, 1), 55000),
                ("Adams", 50000, "Accounting", datetime.date(2013, 7, 1), 37000),
                ("Moore", 34000, "IT", datetime.date(2013, 8, 1), 50000),
            ],
            transform=lambda row: (
                row.name,
                row.salary,
                row.department,
                row.hire_date,
                row.avg_salary_cohort,
            ),
        )

    @skipUnlessDBFeature("supports_frame_exclusion")
    def test_row_range_rank_exclude_ties(self):
        qs = Employee.objects.annotate(
            sum_salary_cohort=Window(
                expression=Sum("salary"),
                order_by=[F("hire_date").asc(), F("name").desc()],
                frame=RowRange(start=-1, end=1, exclusion=WindowFrameExclusion.TIES),
            )
        ).order_by("hire_date")
        self.assertIn(
            "ROWS BETWEEN 1 PRECEDING AND 1 FOLLOWING EXCLUDE TIES",
            str(qs.query),
        )
        self.assertQuerySetEqual(
            qs,
            [
                ("Miller", 100000, "Management", datetime.date(2005, 6, 1), 180000),
                ("Johnson", 80000, "Management", datetime.date(2005, 7, 1), 225000),
                ("Jones", 45000, "Accounting", datetime.date(2005, 11, 1), 180000),
                ("Smith", 55000, "Sales", datetime.date(2007, 6, 1), 145000),
                ("Jenson", 45000, "Accounting", datetime.date(2008, 4, 1), 137000),
                ("Williams", 37000, "Accounting", datetime.date(2009, 6, 1), 135000),
                ("Brown", 53000, "Sales", datetime.date(2009, 9, 1), 128000),
                ("Smith", 38000, "Marketing", datetime.date(2009, 10, 1), 151000),
                ("Wilkinson", 60000, "IT", datetime.date(2011, 3, 1), 138000),
                ("Johnson", 40000, "Marketing", datetime.date(2012, 3, 1), 150000),
                ("Adams", 50000, "Accounting", datetime.date(2013, 7, 1), 124000),
                ("Moore", 34000, "IT", datetime.date(2013, 8, 1), 84000),
            ],
            transform=lambda row: (
                row.name,
                row.salary,
                row.department,
                row.hire_date,
                row.sum_salary_cohort,
            ),
        )

    @skipUnlessDBFeature("supports_frame_exclusion")
    def test_row_range_rank_exclude_no_others(self):
        qs = Employee.objects.annotate(
            sum_salary_cohort=Window(
                expression=Sum("salary"),
                order_by=[F("hire_date").asc(), F("name").desc()],
                frame=RowRange(
                    start=-1, end=1, exclusion=WindowFrameExclusion.NO_OTHERS
                ),
            )
        ).order_by("hire_date")
        self.assertIn(
            "ROWS BETWEEN 1 PRECEDING AND 1 FOLLOWING EXCLUDE NO OTHERS",
            str(qs.query),
        )
        self.assertQuerySetEqual(
            qs,
            [
                ("Miller", 100000, "Management", datetime.date(2005, 6, 1), 180000),
                ("Johnson", 80000, "Management", datetime.date(2005, 7, 1), 225000),
                ("Jones", 45000, "Accounting", datetime.date(2005, 11, 1), 180000),
                ("Smith", 55000, "Sales", datetime.date(2007, 6, 1), 145000),
                ("Jenson", 45000, "Accounting", datetime.date(2008, 4, 1), 137000),
                ("Williams", 37000, "Accounting", datetime.date(2009, 6, 1), 135000),
                ("Brown", 53000, "Sales", datetime.date(2009, 9, 1), 128000),
                ("Smith", 38000, "Marketing", datetime.date(2009, 10, 1), 151000),
                ("Wilkinson", 60000, "IT", datetime.date(2011, 3, 1), 138000),
                ("Johnson", 40000, "Marketing", datetime.date(2012, 3, 1), 150000),
                ("Adams", 50000, "Accounting", datetime.date(2013, 7, 1), 124000),
                ("Moore", 34000, "IT", datetime.date(2013, 8, 1), 84000),
            ],
            transform=lambda row: (
                row.name,
                row.salary,
                row.department,
                row.hire_date,
                row.sum_salary_cohort,
            ),
        )

    @skipIfDBFeature("supports_frame_exclusion")
    def test_unsupported_frame_exclusion_raises_error(self):
        msg = "This backend does not support window frame exclusions."
        with self.assertRaisesMessage(NotSupportedError, msg):
            list(
                Employee.objects.annotate(
                    avg_salary_cohort=Window(
                        expression=Avg("salary"),
                        order_by=[F("hire_date").asc(), F("name").desc()],
                        frame=RowRange(
                            start=-1, end=1, exclusion=WindowFrameExclusion.CURRENT_ROW
                        ),
                    )
                )
            )

    @skipUnlessDBFeature("supports_frame_exclusion")
    def test_invalid_frame_exclusion_value_raises_error(self):
        msg = "RowRange.exclusion must be a WindowFrameExclusion instance."
        with self.assertRaisesMessage(TypeError, msg):
            Employee.objects.annotate(
                avg_salary_cohort=Window(
                    expression=Avg("salary"),
                    order_by=[F("hire_date").asc(), F("name").desc()],
                    frame=RowRange(start=-1, end=1, exclusion="RUBBISH"),
                )
            )

    def test_row_range_rank(self):
        """
        A query with ROWS BETWEEN UNBOUNDED PRECEDING AND 3 FOLLOWING.
        The resulting sum is the sum of the three next (if they exist) and all
        previous rows according to the ordering clause.
        """
        qs = Employee.objects.annotate(
            sum=Window(
                expression=Sum("salary"),
                order_by=[F("hire_date").asc(), F("name").desc()],
                frame=RowRange(start=None, end=3),
            )
        ).order_by("sum", "hire_date")
        self.assertIn("ROWS BETWEEN UNBOUNDED PRECEDING AND 3 FOLLOWING", str(qs.query))
        self.assertQuerySetEqual(
            qs,
            [
                ("Miller", 100000, "Management", datetime.date(2005, 6, 1), 280000),
                ("Johnson", 80000, "Management", datetime.date(2005, 7, 1), 325000),
                ("Jones", 45000, "Accounting", datetime.date(2005, 11, 1), 362000),
                ("Smith", 55000, "Sales", datetime.date(2007, 6, 1), 415000),
                ("Jenson", 45000, "Accounting", datetime.date(2008, 4, 1), 453000),
                ("Williams", 37000, "Accounting", datetime.date(2009, 6, 1), 513000),
                ("Brown", 53000, "Sales", datetime.date(2009, 9, 1), 553000),
                ("Smith", 38000, "Marketing", datetime.date(2009, 10, 1), 603000),
                ("Wilkinson", 60000, "IT", datetime.date(2011, 3, 1), 637000),
                ("Johnson", 40000, "Marketing", datetime.date(2012, 3, 1), 637000),
                ("Adams", 50000, "Accounting", datetime.date(2013, 7, 1), 637000),
                ("Moore", 34000, "IT", datetime.date(2013, 8, 1), 637000),
            ],
            transform=lambda row: (
                row.name,
                row.salary,
                row.department,
                row.hire_date,
                row.sum,
            ),
        )

    def test_row_range_both_preceding(self):
        """
        A query with ROWS BETWEEN 2 PRECEDING AND 1 PRECEDING.
        The resulting sum is the sum of the previous two (if they exist) rows
        according to the ordering clause.
        """
        qs = Employee.objects.annotate(
            sum=Window(
                expression=Sum("salary"),
                order_by=[F("hire_date").asc(), F("name").desc()],
                frame=RowRange(start=-2, end=-1),
            )
        ).order_by("hire_date")
        self.assertIn("ROWS BETWEEN 2 PRECEDING AND 1 PRECEDING", str(qs.query))
        self.assertQuerySetEqual(
            qs,
            [
                ("Miller", 100000, "Management", datetime.date(2005, 6, 1), None),
                ("Johnson", 80000, "Management", datetime.date(2005, 7, 1), 100000),
                ("Jones", 45000, "Accounting", datetime.date(2005, 11, 1), 180000),
                ("Smith", 55000, "Sales", datetime.date(2007, 6, 1), 125000),
                ("Jenson", 45000, "Accounting", datetime.date(2008, 4, 1), 100000),
                ("Williams", 37000, "Accounting", datetime.date(2009, 6, 1), 100000),
                ("Brown", 53000, "Sales", datetime.date(2009, 9, 1), 82000),
                ("Smith", 38000, "Marketing", datetime.date(2009, 10, 1), 90000),
                ("Wilkinson", 60000, "IT", datetime.date(2011, 3, 1), 91000),
                ("Johnson", 40000, "Marketing", datetime.date(2012, 3, 1), 98000),
                ("Adams", 50000, "Accounting", datetime.date(2013, 7, 1), 100000),
                ("Moore", 34000, "IT", datetime.date(2013, 8, 1), 90000),
            ],
            transform=lambda row: (
                row.name,
                row.salary,
                row.department,
                row.hire_date,
                row.sum,
            ),
        )

    def test_row_range_both_following(self):
        """
        A query with ROWS BETWEEN 1 FOLLOWING AND 2 FOLLOWING.
        The resulting sum is the sum of the following two (if they exist) rows
        according to the ordering clause.
        """
        qs = Employee.objects.annotate(
            sum=Window(
                expression=Sum("salary"),
                order_by=[F("hire_date").asc(), F("name").desc()],
                frame=RowRange(start=1, end=2),
            )
        ).order_by("hire_date")
        self.assertIn("ROWS BETWEEN 1 FOLLOWING AND 2 FOLLOWING", str(qs.query))
        self.assertQuerySetEqual(
            qs,
            [
                ("Miller", 100000, "Management", datetime.date(2005, 6, 1), 125000),
                ("Johnson", 80000, "Management", datetime.date(2005, 7, 1), 100000),
                ("Jones", 45000, "Accounting", datetime.date(2005, 11, 1), 100000),
                ("Smith", 55000, "Sales", datetime.date(2007, 6, 1), 82000),
                ("Jenson", 45000, "Accounting", datetime.date(2008, 4, 1), 90000),
                ("Williams", 37000, "Accounting", datetime.date(2009, 6, 1), 91000),
                ("Brown", 53000, "Sales", datetime.date(2009, 9, 1), 98000),
                ("Smith", 38000, "Marketing", datetime.date(2009, 10, 1), 100000),
                ("Wilkinson", 60000, "IT", datetime.date(2011, 3, 1), 90000),
                ("Johnson", 40000, "Marketing", datetime.date(2012, 3, 1), 84000),
                ("Adams", 50000, "Accounting", datetime.date(2013, 7, 1), 34000),
                ("Moore", 34000, "IT", datetime.date(2013, 8, 1), None),
            ],
            transform=lambda row: (
                row.name,
                row.salary,
                row.department,
                row.hire_date,
                row.sum,
            ),
        )

    @skipUnlessDBFeature("can_distinct_on_fields")
    def test_distinct_window_function(self):
        """
        Window functions are not aggregates, and hence a query to filter out
        duplicates may be useful.
        """
        qs = (
            Employee.objects.annotate(
                sum=Window(
                    expression=Sum("salary"),
                    partition_by=ExtractYear("hire_date"),
                    order_by=ExtractYear("hire_date"),
                ),
                year=ExtractYear("hire_date"),
            )
            .filter(sum__gte=45000)
            .values("year", "sum")
            .distinct("year")
            .order_by("year")
        )
        results = [
            {"year": 2005, "sum": 225000},
            {"year": 2007, "sum": 55000},
            {"year": 2008, "sum": 45000},
            {"year": 2009, "sum": 128000},
            {"year": 2011, "sum": 60000},
            {"year": 2013, "sum": 84000},
        ]
        for idx, val in zip(range(len(results)), results):
            with self.subTest(result=val):
                self.assertEqual(qs[idx], val)

    def test_fail_update(self):
        """Window expressions can't be used in an UPDATE statement."""
        msg = (
            "Window expressions are not allowed in this query (salary=<Window: "
            "Max(Col(expressions_window_employee, expressions_window.Employee.salary)) "
            "OVER (PARTITION BY Col(expressions_window_employee, "
            "expressions_window.Employee.department))>)."
        )
        with self.assertRaisesMessage(FieldError, msg):
            Employee.objects.filter(department="Management").update(
                salary=Window(expression=Max("salary"), partition_by="department"),
            )

    def test_fail_insert(self):
        """Window expressions can't be used in an INSERT statement."""
        msg = (
            "Window expressions are not allowed in this query (salary=<Window: "
            "Sum(Value(10000)) OVER ()"
        )
        with self.assertRaisesMessage(FieldError, msg):
            Employee.objects.create(
                name="Jameson",
                department="Management",
                hire_date=datetime.date(2007, 7, 1),
                salary=Window(expression=Sum(Value(10000))),
            )

    def test_window_expression_within_subquery(self):
        subquery_qs = Employee.objects.annotate(
            highest=Window(
                FirstValue("id"),
                partition_by=F("department"),
                order_by=F("salary").desc(),
            )
        ).values("highest")
        highest_salary = Employee.objects.filter(pk__in=subquery_qs)
        self.assertCountEqual(
            highest_salary.values("department", "salary"),
            [
                {"department": "Accounting", "salary": 50000},
                {"department": "Sales", "salary": 55000},
                {"department": "Marketing", "salary": 40000},
                {"department": "IT", "salary": 60000},
                {"department": "Management", "salary": 100000},
            ],
        )

    @skipUnlessDBFeature("supports_json_field")
    def test_key_transform(self):
        Detail.objects.bulk_create(
            [
                Detail(value={"department": "IT", "name": "Smith", "salary": 37000}),
                Detail(value={"department": "IT", "name": "Nowak", "salary": 32000}),
                Detail(value={"department": "HR", "name": "Brown", "salary": 50000}),
                Detail(value={"department": "HR", "name": "Smith", "salary": 55000}),
                Detail(value={"department": "PR", "name": "Moore", "salary": 90000}),
            ]
        )
        tests = [
            (KeyTransform("department", "value"), KeyTransform("name", "value")),
            (F("value__department"), F("value__name")),
        ]
        for partition_by, order_by in tests:
            with self.subTest(partition_by=partition_by, order_by=order_by):
                qs = Detail.objects.annotate(
                    department_sum=Window(
                        expression=Sum(
                            Cast(
                                KeyTextTransform("salary", "value"),
                                output_field=IntegerField(),
                            )
                        ),
                        partition_by=[partition_by],
                        order_by=[order_by],
                    )
                ).order_by("value__department", "department_sum")
                self.assertQuerySetEqual(
                    qs,
                    [
                        ("Brown", "HR", 50000, 50000),
                        ("Smith", "HR", 55000, 105000),
                        ("Nowak", "IT", 32000, 32000),
                        ("Smith", "IT", 37000, 69000),
                        ("Moore", "PR", 90000, 90000),
                    ],
                    lambda entry: (
                        entry.value["name"],
                        entry.value["department"],
                        entry.value["salary"],
                        entry.department_sum,
                    ),
                )

    def test_invalid_start_value_range(self):
        msg = "start argument must be a negative integer, zero, or None, but got '3'."
        with self.assertRaisesMessage(ValueError, msg):
            list(
                Employee.objects.annotate(
                    test=Window(
                        expression=Sum("salary"),
                        order_by=F("hire_date").asc(),
                        frame=ValueRange(start=3),
                    )
                )
            )

    def test_invalid_end_value_range(self):
        msg = "end argument must be a positive integer, zero, or None, but got '-3'."
        with self.assertRaisesMessage(ValueError, msg):
            list(
                Employee.objects.annotate(
                    test=Window(
                        expression=Sum("salary"),
                        order_by=F("hire_date").asc(),
                        frame=ValueRange(end=-3),
                    )
                )
            )

    def test_invalid_start_end_value_for_row_range(self):
        msg = "start cannot be greater than end."
        with self.assertRaisesMessage(ValueError, msg):
            list(
                Employee.objects.annotate(
                    test=Window(
                        expression=Sum("salary"),
                        order_by=F("hire_date").asc(),
                        frame=RowRange(start=4, end=-3),
                    )
                )
            )

    def test_invalid_type_end_value_range(self):
        msg = "end argument must be a positive integer, zero, or None, but got 'a'."
        with self.assertRaisesMessage(ValueError, msg):
            list(
                Employee.objects.annotate(
                    test=Window(
                        expression=Sum("salary"),
                        order_by=F("hire_date").asc(),
                        frame=ValueRange(end="a"),
                    )
                )
            )

    def test_invalid_type_start_value_range(self):
        msg = "start argument must be a negative integer, zero, or None, but got 'a'."
        with self.assertRaisesMessage(ValueError, msg):
            list(
                Employee.objects.annotate(
                    test=Window(
                        expression=Sum("salary"),
                        frame=ValueRange(start="a"),
                    )
                )
            )

    def test_invalid_type_end_row_range(self):
        msg = "end argument must be an integer, zero, or None, but got 'a'."
        with self.assertRaisesMessage(ValueError, msg):
            list(
                Employee.objects.annotate(
                    test=Window(
                        expression=Sum("salary"),
                        frame=RowRange(end="a"),
                    )
                )
            )

    @skipUnlessDBFeature("only_supports_unbounded_with_preceding_and_following")
    def test_unsupported_range_frame_start(self):
        msg = (
            "%s only supports UNBOUNDED together with PRECEDING and FOLLOWING."
            % connection.display_name
        )
        with self.assertRaisesMessage(NotSupportedError, msg):
            list(
                Employee.objects.annotate(
                    test=Window(
                        expression=Sum("salary"),
                        order_by=F("hire_date").asc(),
                        frame=ValueRange(start=-1),
                    )
                )
            )

    @skipUnlessDBFeature("only_supports_unbounded_with_preceding_and_following")
    def test_unsupported_range_frame_end(self):
        msg = (
            "%s only supports UNBOUNDED together with PRECEDING and FOLLOWING."
            % connection.display_name
        )
        with self.assertRaisesMessage(NotSupportedError, msg):
            list(
                Employee.objects.annotate(
                    test=Window(
                        expression=Sum("salary"),
                        order_by=F("hire_date").asc(),
                        frame=ValueRange(end=1),
                    )
                )
            )

    def test_invalid_type_start_row_range(self):
        msg = "start argument must be an integer, zero, or None, but got 'a'."
        with self.assertRaisesMessage(ValueError, msg):
            list(
                Employee.objects.annotate(
                    test=Window(
                        expression=Sum("salary"),
                        order_by=F("hire_date").asc(),
                        frame=RowRange(start="a"),
                    )
                )
            )

    def test_invalid_filter(self):
        msg = (
            "Heterogeneous disjunctive predicates against window functions are not "
            "implemented when performing conditional aggregation."
        )
        qs = Employee.objects.annotate(
            window=Window(Rank()),
            past_dept_cnt=Count("past_departments"),
        )
        with self.assertRaisesMessage(NotImplementedError, msg):
            list(qs.filter(Q(window=1) | Q(department="Accounting")))
        with self.assertRaisesMessage(NotImplementedError, msg):
            list(qs.exclude(window=1, department="Accounting"))


class WindowUnsupportedTests(TestCase):
    def test_unsupported_backend(self):
        msg = "This backend does not support window expressions."
        with mock.patch.object(connection.features, "supports_over_clause", False):
            with self.assertRaisesMessage(NotSupportedError, msg):
                Employee.objects.annotate(
                    dense_rank=Window(expression=DenseRank())
                ).get()

    def test_filter_subquery(self):
        qs = Employee.objects.annotate(
            department_salary_rank=Window(
                Rank(), partition_by="department", order_by="-salary"
            )
        )
        msg = (
            "Referencing outer query window expression is not supported: "
            "department_salary_rank."
        )
        with self.assertRaisesMessage(NotSupportedError, msg):
            qs.annotate(
                employee_name=Subquery(
                    Employee.objects.filter(
                        age=OuterRef("department_salary_rank")
                    ).values("name")[:1]
                )
            )


class NonQueryWindowTests(SimpleTestCase):
    def test_window_repr(self):
        self.assertEqual(
            repr(Window(expression=Sum("salary"), partition_by="department")),
            "<Window: Sum(F(salary)) OVER (PARTITION BY F(department))>",
        )
        self.assertEqual(
            repr(Window(expression=Avg("salary"), order_by=F("department").asc())),
            "<Window: Avg(F(salary)) OVER (OrderBy(F(department), descending=False))>",
        )

    def test_window_frame_repr(self):
        self.assertEqual(
            repr(RowRange(start=-1)),
            "<RowRange: ROWS BETWEEN 1 PRECEDING AND UNBOUNDED FOLLOWING>",
        )
        self.assertEqual(
            repr(ValueRange(start=None, end=1)),
            "<ValueRange: RANGE BETWEEN UNBOUNDED PRECEDING AND 1 FOLLOWING>",
        )
        self.assertEqual(
            repr(ValueRange(start=0, end=0)),
            "<ValueRange: RANGE BETWEEN CURRENT ROW AND CURRENT ROW>",
        )
        self.assertEqual(
            repr(RowRange(start=0, end=0)),
            "<RowRange: ROWS BETWEEN CURRENT ROW AND CURRENT ROW>",
        )
        self.assertEqual(
            repr(RowRange(start=-2, end=-1)),
            "<RowRange: ROWS BETWEEN 2 PRECEDING AND 1 PRECEDING>",
        )
        self.assertEqual(
            repr(RowRange(start=1, end=2)),
            "<RowRange: ROWS BETWEEN 1 FOLLOWING AND 2 FOLLOWING>",
        )
        self.assertEqual(
            repr(RowRange(start=1, end=2, exclusion=WindowFrameExclusion.CURRENT_ROW)),
            "<RowRange: ROWS BETWEEN 1 FOLLOWING AND 2 FOLLOWING EXCLUDE CURRENT ROW>",
        )

    def test_window_frame_exclusion_repr(self):
        self.assertEqual(repr(WindowFrameExclusion.TIES), "WindowFrameExclusion.TIES")

    def test_empty_group_by_cols(self):
        window = Window(expression=Sum("pk"))
        self.assertEqual(window.get_group_by_cols(), [])
        self.assertFalse(window.contains_aggregate)

    def test_frame_empty_group_by_cols(self):
        frame = WindowFrame()
        self.assertEqual(frame.get_group_by_cols(), [])

    def test_frame_window_frame_notimplemented(self):
        frame = WindowFrame()
        msg = "Subclasses must implement window_frame_start_end()."
        with self.assertRaisesMessage(NotImplementedError, msg):
            frame.window_frame_start_end(None, None, None)

    def test_invalid_order_by(self):
        msg = (
            "Window.order_by must be either a string reference to a field, an "
            "expression, or a list or tuple of them not {'-horse'}."
        )
        with self.assertRaisesMessage(ValueError, msg):
            Window(expression=Sum("power"), order_by={"-horse"})

    def test_invalid_source_expression(self):
        msg = "Expression 'Upper' isn't compatible with OVER clauses."
        with self.assertRaisesMessage(ValueError, msg):
            Window(expression=Upper("name"))
