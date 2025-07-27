import tracemalloc

from django.test import TestCase

from .models import Thing


class BulkUpdateMemoryTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        Thing.objects.bulk_create(
            [Thing(name=f"Thing {i}", description="Old") for i in range(10_000)],
            batch_size=1000,
        )

    def test_bulk_update_all_at_once(self):
        import gc

        things = list(Thing.objects.all())
        for thing in things:
            thing.description = "New"

        gc.collect()

        tracemalloc.start()

        Thing.objects.bulk_update(things, ["description"], batch_size=300)

        current, peak = tracemalloc.get_traced_memory()
        self.assertLess(
            peak / 1024 / 1024,
            5,
            f"Peak memory usage too high: {peak / 1024 / 1024:.2f} MB",
        )

        tracemalloc.stop()
