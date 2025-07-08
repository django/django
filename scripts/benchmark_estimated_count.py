"""Benchmark estimated row count vs. ``COUNT()``.

Populate a small table and compare the execution speed of
``QuerySet.count()`` against :func:`estimate_row_count`. If the current
database backend supports row estimation (PostgreSQL or MySQL), the
benchmark uses the real estimation logic. Otherwise the estimate will
fall back to ``None``.
"""

import timeit

from django.contrib.admin.utils import estimate_row_count
from django.db import connection, models


class BenchModel(models.Model):
    class Meta:
        app_label = "bench_app"
        managed = False
        db_table = "bench_table"


def setup_db():
    placeholder = "%s" if connection.vendor != "sqlite" else "?"
    with connection.cursor() as cursor:
        cursor.execute("CREATE TABLE IF NOT EXISTS bench_table (id INTEGER)")
        cursor.execute("DELETE FROM bench_table")
        cursor.executemany(
            f"INSERT INTO bench_table(id) VALUES ({placeholder})",
            [(i,) for i in range(1000)],
        )
        if connection.vendor == "postgresql":
            cursor.execute(f"ANALYZE {BenchModel._meta.db_table}")


def row_count_sql():
    with connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM bench_table")
        return cursor.fetchone()[0]


def run_benchmark():
    setup_db()
    count_time = timeit.timeit(row_count_sql, number=10)
    est_time = timeit.timeit(
        lambda: estimate_row_count(BenchModel, connection),
        number=10,
    )
    print(f"COUNT(): {count_time:.4f}s")
    est = estimate_row_count(BenchModel, connection)
    if est is not None:
        print(f"Estimation: {est_time:.4f}s -> {est}")
    else:
        print("Estimation not supported on this backend.")


if __name__ == "__main__":
    run_benchmark()