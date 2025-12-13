import gc

from django.db.models.base import ModelState, ModelStateFieldsCacheDescriptor
from django.test import SimpleTestCase
from django.test.utils import garbage_collect

from .models import CycleChild, CycleParent


class ModelStateTests(SimpleTestCase):
    def test_fields_cache_descriptor(self):
        self.assertIsInstance(ModelState.fields_cache, ModelStateFieldsCacheDescriptor)

    def test_model_state_del_no_cache(self):

        state = ModelState()
        self.assertFalse(hasattr(state, "_fields_cache"))
        del state

    def test_one_to_one_field_cycle_collection(self):
        self.addCleanup(gc.set_debug, gc.get_debug())
        gc.set_debug(gc.DEBUG_SAVEALL)

        def clear_garbage():
            del gc.garbage[:]

        self.addCleanup(clear_garbage)

        p = CycleParent()
        c = CycleChild(parent=p)
        p_id = id(p)

        del p
        del c

        garbage_collect()

        leaked = [obj for obj in gc.garbage if id(obj) == p_id]
        self.assertEqual(leaked, [])
