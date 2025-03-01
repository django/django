from django.db.models import (
    FETCH_ONE,
    FETCH_PEERS,
    RAISE,
    fetch_mode,
    set_default_fetch_mode,
)
from django.db.models.fields.fetch_modes import get_fetch_mode
from django.test import SimpleTestCase


class FetchModeTests(SimpleTestCase):
    def test_set_default_fetch_mode(self):
        try:
            set_default_fetch_mode(RAISE)
            self.assertIs(get_fetch_mode(), RAISE)
        finally:
            set_default_fetch_mode(FETCH_ONE)

    def test_set_default_non_callable(self):
        msg = "'RAISE' is not a callable object"
        with self.assertRaisesMessage(TypeError, msg):
            set_default_fetch_mode("RAISE")

    def test_set_default_incorrect_signature(self):
        msg = "mode must have signature (fetcher, instance)."
        with self.assertRaisesMessage(TypeError, msg):
            set_default_fetch_mode(lambda x: x)

    def test_fetch_mode_context_manager(self):
        self.assertIs(get_fetch_mode(), FETCH_ONE)

        with fetch_mode(RAISE):
            self.assertIs(get_fetch_mode(), RAISE)

        self.assertIs(get_fetch_mode(), FETCH_ONE)

    def test_fetch_mode_nested(self):
        with fetch_mode(RAISE):
            self.assertIs(get_fetch_mode(), RAISE)
            with fetch_mode(FETCH_PEERS):
                self.assertIs(get_fetch_mode(), FETCH_PEERS)
            self.assertIs(get_fetch_mode(), RAISE)

    @fetch_mode(RAISE)
    def test_fetch_mode_decorator(self):
        self.assertIs(get_fetch_mode(), RAISE)

    def test_fetch_mode_non_callable(self):
        msg = "'RAISE' is not a callable object"
        with self.assertRaisesMessage(TypeError, msg):
            with fetch_mode("RAISE"):
                pass

    def test_bad_argument(self):
        msg = "mode must have signature (fetcher, instance)."
        with self.assertRaisesMessage(TypeError, msg):
            with fetch_mode(lambda x: x):
                pass
