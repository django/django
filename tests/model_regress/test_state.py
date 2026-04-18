import gc

from django.db.models.base import ModelState, ModelStateFieldsCacheDescriptor
from django.test import SimpleTestCase
from django.test.utils import garbage_collect

from .models import Worker, WorkerProfile


class ModelStateTests(SimpleTestCase):
    def test_fields_cache_descriptor(self):
        self.assertIsInstance(ModelState.fields_cache, ModelStateFieldsCacheDescriptor)

    def test_one_to_one_field_cycle_collection(self):
        self.addCleanup(gc.set_debug, gc.get_debug())
        gc.set_debug(gc.DEBUG_SAVEALL)

        def clear_garbage():
            del gc.garbage[:]

        self.addCleanup(clear_garbage)

        worker = Worker()
        profile = WorkerProfile(worker=worker)
        worker_id = id(worker)

        del worker
        del profile

        garbage_collect()

        leaked = [obj for obj in gc.garbage if id(obj) == worker_id]
        self.assertEqual(leaked, [])
