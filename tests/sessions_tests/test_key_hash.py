from unittest import mock

from asgiref.sync import async_to_sync, sync_to_async

from django.conf import settings
from django.contrib.sessions.backends.base import SessionBase, UpdateError
from django.contrib.sessions.backends.cache import SessionStore as CacheSession
from django.contrib.sessions.backends.cached_db import SessionStore as CacheDBSession
from django.contrib.sessions.backends.db import SessionStore as DatabaseSession
from django.contrib.sessions.backends.file import SessionStore as FileSession
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.sessions.models import Session
from django.core.cache import caches
from django.core.exceptions import ImproperlyConfigured
from django.db import DatabaseError, transaction
from django.db.models import QuerySet
from django.http import HttpResponse
from django.test import (
    RequestFactory,
    SimpleTestCase,
    TestCase,
    TransactionTestCase,
    override_settings,
)

from .models import (
    CachedReferencedSessionStore,
    MultiTenantSessionNote,
    MultiTenantSessionStore,
    ReferencedSessionStore,
    SessionReference,
)
from .models import SessionStore as CustomDatabaseSession


class SessionBackendKeyTests(SimpleTestCase):
    session_key = "0123456789abcdefghijklmnopqrstuv"
    backend_key = "sha256$omzx6r474fynopst4jd7gbjoijb4zhbk"

    @override_settings(SESSION_STORE_KEY_HASH=False)
    def test_get_backend_key(self):
        self.assertEqual(
            SessionBase().get_backend_key(self.session_key), self.session_key
        )

    def test_get_backend_key_hashed(self):
        for value in (True, "transition"):
            with self.subTest(SESSION_STORE_KEY_HASH=value):
                with self.settings(SESSION_STORE_KEY_HASH=value):
                    self.assertEqual(
                        SessionBase().get_backend_key(self.session_key),
                        self.backend_key,
                    )

    def test_get_backend_key_none(self):
        for value in (False, True, "transition"):
            with self.subTest(SESSION_STORE_KEY_HASH=value):
                with self.settings(SESSION_STORE_KEY_HASH=value):
                    self.assertIsNone(SessionBase().get_backend_key(None))

    def test_valid_session_keys(self):
        for value in (False, True, "transition"):
            for session_key in (self.session_key, "testkey1234", "a-b_c.d:e=f"):
                with self.subTest(
                    SESSION_STORE_KEY_HASH=value, session_key=session_key
                ):
                    with self.settings(SESSION_STORE_KEY_HASH=value):
                        self.assertEqual(
                            SessionBase(session_key).session_key, session_key
                        )

    def test_backend_key_lookalikes_are_invalid_session_keys(self):
        # A database collation may ignore case, trailing spaces, and accents.
        invalid_session_keys = (
            self.backend_key,
            self.backend_key.upper(),
            self.backend_key + " ",
            " " + self.backend_key,
            self.backend_key.replace("$", "\N{FULLWIDTH DOLLAR SIGN}"),
            self.backend_key.replace("s", "\N{LATIN SMALL LETTER S WITH ACUTE}", 1),
            self.backend_key.replace("$", "\N{ZERO WIDTH JOINER}$"),
            "abcdefgh$",
            "abcdefg\N{LATIN SMALL LETTER H WITH CIRCUMFLEX}",
            b"abcdefgh",
            12345678,
        )
        for value in (False, True, "transition"):
            for session_key in invalid_session_keys:
                with self.subTest(
                    SESSION_STORE_KEY_HASH=value, session_key=session_key
                ):
                    with self.settings(SESSION_STORE_KEY_HASH=value):
                        self.assertIsNone(SessionBase(session_key).session_key)


class SessionStoreKeyHashTestsMixin:
    # Tests of SESSION_STORE_KEY_HASH for the backends that keep sessions in a
    # session store. This does not inherit from TestCase to avoid any tests
    # being run with this class.

    backend = None  # subclasses must specify
    stores = None  # subclasses must specify: where a session is kept.

    def setUp(self):
        self.addCleanup(caches["default"].clear)

    def create_session(self, **data):
        session = self.backend()
        session.update(data)
        session.save()
        return session

    async def acreate_session(self, **data):
        session = self.backend()
        await session.aupdate(data)
        await session.asave()
        return session

    def create_unhashed_session(self, **data):
        # A session as it's kept before SESSION_STORE_KEY_HASH is enabled.
        with self.settings(SESSION_STORE_KEY_HASH=False):
            return self.create_session(**data)

    async def acreate_unhashed_session(self, **data):
        with self.settings(SESSION_STORE_KEY_HASH=False):
            return await self.acreate_session(**data)

    def stores_holding(self, backend_key):
        stores = set()
        if "db" in self.stores:
            model = self.backend.get_model_class()
            if model.objects.filter(session_key=backend_key).exists():
                stores.add("db")
        if "cache" in self.stores:
            if self.backend.cache_key_prefix + backend_key in caches["default"]:
                stores.add("cache")
        return stores

    def assertKeptUnder(self, backend_key):
        self.assertEqual(self.stores_holding(backend_key), self.stores)

    def assertNotKeptUnder(self, backend_key):
        self.assertEqual(self.stores_holding(backend_key), set())

    @override_settings(SESSION_STORE_KEY_HASH=True)
    def test_session_kept_under_hashed_backend_key(self):
        session = self.create_session(color="red")
        session_key = session.session_key
        backend_key = session.get_backend_key(session_key)
        self.assertNotEqual(backend_key, session_key)
        self.assertKeptUnder(backend_key)
        self.assertNotKeptUnder(session_key)
        self.assertEqual(self.backend(session_key)["color"], "red")
        self.assertIs(self.backend().exists(session_key), True)

    @override_settings(SESSION_STORE_KEY_HASH=True)
    async def test_session_kept_under_hashed_backend_key_async(self):
        session = await self.acreate_session(color="red")
        session_key = session.session_key
        backend_key = session.get_backend_key(session_key)
        await sync_to_async(self.assertKeptUnder)(backend_key)
        await sync_to_async(self.assertNotKeptUnder)(session_key)
        self.assertEqual(await self.backend(session_key).aget("color"), "red")
        self.assertIs(await self.backend().aexists(session_key), True)

    def test_backend_key_is_not_accepted_as_session_key(self):
        with self.settings(SESSION_STORE_KEY_HASH=True):
            session = self.create_session(color="red")
            backend_key = session.get_backend_key(session.session_key)
        for value in (False, True, "transition"):
            for session_key in (backend_key, backend_key.upper(), backend_key + " "):
                with self.subTest(
                    SESSION_STORE_KEY_HASH=value, session_key=session_key
                ):
                    with self.settings(SESSION_STORE_KEY_HASH=value):
                        other = self.backend(session_key)
                        self.assertIsNone(other.session_key)
                        self.assertIsNone(other.get("color"))
        self.assertKeptUnder(backend_key)

    def test_transition_moves_session_to_hashed_backend_key(self):
        session = self.create_unhashed_session(color="red")
        session_key = session.session_key
        with self.settings(SESSION_STORE_KEY_HASH="transition"):
            backend_key = session.get_backend_key(session_key)
            # Loading the session doesn't move it, but has it saved.
            other = self.backend(session_key)
            self.assertEqual(other["color"], "red")
            self.assertIs(other.modified, True)
            self.assertKeptUnder(session_key)
            self.assertNotKeptUnder(backend_key)
            other.save()
            self.assertKeptUnder(backend_key)
            self.assertNotKeptUnder(session_key)
            other = self.backend(session_key)
            self.assertEqual(other["color"], "red")
            self.assertIs(other.modified, False)
        with self.settings(SESSION_STORE_KEY_HASH=True):
            self.assertEqual(self.backend(session_key)["color"], "red")

    async def test_transition_moves_session_to_hashed_backend_key_async(self):
        session = await self.acreate_unhashed_session(color="red")
        session_key = session.session_key
        with self.settings(SESSION_STORE_KEY_HASH="transition"):
            backend_key = session.get_backend_key(session_key)
            other = self.backend(session_key)
            self.assertEqual(await other.aget("color"), "red")
            self.assertIs(other.modified, True)
            await sync_to_async(self.assertKeptUnder)(session_key)
            await sync_to_async(self.assertNotKeptUnder)(backend_key)
            await other.asave()
            await sync_to_async(self.assertKeptUnder)(backend_key)
            await sync_to_async(self.assertNotKeptUnder)(session_key)
            other = self.backend(session_key)
            self.assertEqual(await other.aget("color"), "red")
            self.assertIs(other.modified, False)
        with self.settings(SESSION_STORE_KEY_HASH=True):
            self.assertEqual(await self.backend(session_key).aget("color"), "red")

    @override_settings(SESSION_STORE_KEY_HASH="transition")
    def test_transition_keeps_new_session_under_hashed_backend_key(self):
        session = self.create_session(color="red")
        self.assertKeptUnder(session.get_backend_key(session.session_key))
        self.assertNotKeptUnder(session.session_key)
        self.assertEqual(self.backend(session.session_key)["color"], "red")

    def test_session_kept_under_session_key_requires_transition(self):
        session = self.create_unhashed_session(color="red")
        session_key = session.session_key
        with self.settings(SESSION_STORE_KEY_HASH=True):
            other = self.backend(session_key)
            self.assertEqual(other.load(), {})
            self.assertIsNone(other.session_key)
            self.assertIs(self.backend().exists(session_key), False)
        self.assertKeptUnder(session_key)

    async def test_session_kept_under_session_key_requires_transition_async(self):
        session = await self.acreate_unhashed_session(color="red")
        session_key = session.session_key
        with self.settings(SESSION_STORE_KEY_HASH=True):
            other = self.backend(session_key)
            self.assertEqual(await other.aload(), {})
            self.assertIsNone(other.session_key)
            self.assertIs(await self.backend().aexists(session_key), False)
        await sync_to_async(self.assertKeptUnder)(session_key)

    @override_settings(SESSION_STORE_KEY_HASH="transition")
    def test_transition_unknown_session_key(self):
        session = self.backend("someunknownkey")
        self.assertEqual(session.load(), {})
        self.assertIsNone(session.session_key)
        self.assertNotKeptUnder("someunknownkey")
        self.assertNotKeptUnder(session.get_backend_key("someunknownkey"))

    def test_transition_exists(self):
        session = self.create_unhashed_session(color="red")
        with self.settings(SESSION_STORE_KEY_HASH="transition"):
            self.assertIs(self.backend().exists(session.session_key), True)
            self.assertIs(self.backend().exists("someunknownkey"), False)

    async def test_transition_exists_async(self):
        session = await self.acreate_unhashed_session(color="red")
        with self.settings(SESSION_STORE_KEY_HASH="transition"):
            self.assertIs(await self.backend().aexists(session.session_key), True)
            self.assertIs(await self.backend().aexists("someunknownkey"), False)

    def test_transition_delete(self):
        session = self.create_unhashed_session(color="red")
        with self.settings(SESSION_STORE_KEY_HASH="transition"):
            self.backend(session.session_key).delete()
            self.assertNotKeptUnder(session.session_key)
            self.assertIs(self.backend().exists(session.session_key), False)

    async def test_transition_delete_async(self):
        session = await self.acreate_unhashed_session(color="red")
        with self.settings(SESSION_STORE_KEY_HASH="transition"):
            await self.backend(session.session_key).adelete()
            await sync_to_async(self.assertNotKeptUnder)(session.session_key)
            self.assertIs(await self.backend().aexists(session.session_key), False)

    def test_transition_save_without_loading(self):
        session = self.create_unhashed_session(color="red")
        session_key = session.session_key
        with self.settings(SESSION_STORE_KEY_HASH="transition"):
            other = self.backend(session_key)
            other.clear()
            other.save()
            self.assertKeptUnder(other.get_backend_key(session_key))
            self.assertNotKeptUnder(session_key)
            self.assertEqual(self.backend(session_key).load(), {})

    async def test_transition_save_without_loading_async(self):
        session = await self.acreate_unhashed_session(color="red")
        session_key = session.session_key
        with self.settings(SESSION_STORE_KEY_HASH="transition"):
            other = self.backend(session_key)
            other.clear()
            await other.asave()
            await sync_to_async(self.assertKeptUnder)(
                other.get_backend_key(session_key)
            )
            await sync_to_async(self.assertNotKeptUnder)(session_key)
            self.assertEqual(await self.backend(session_key).aload(), {})

    def test_transition_save_does_not_resurrect_deleted_session(self):
        session = self.create_unhashed_session(color="red")
        with self.settings(SESSION_STORE_KEY_HASH="transition"):
            other = self.backend(session.session_key)
            other["color"] = "blue"
            self.backend(session.session_key).delete()
            with self.assertRaises(UpdateError):
                other.save()
            self.assertEqual(other.load(), {})

    async def test_transition_save_does_not_resurrect_deleted_session_async(self):
        session = await self.acreate_unhashed_session(color="red")
        with self.settings(SESSION_STORE_KEY_HASH="transition"):
            other = self.backend(session.session_key)
            await other.aset("color", "blue")
            await self.backend(session.session_key).adelete()
            with self.assertRaises(UpdateError):
                await other.asave()
            self.assertEqual(await other.aload(), {})

    def test_transition_save_of_expired_session(self):
        session = self.create_unhashed_session(color="red")
        session_key = session.session_key
        with self.settings(SESSION_STORE_KEY_HASH="transition"):
            other = self.backend(session_key)
            other.set_expiry(-3600)
            other.save()
            self.assertNotKeptUnder(session_key)
            self.assertEqual(self.backend(session_key).load(), {})

    async def test_transition_save_of_expired_session_async(self):
        session = await self.acreate_unhashed_session(color="red")
        session_key = session.session_key
        with self.settings(SESSION_STORE_KEY_HASH="transition"):
            other = self.backend(session_key)
            await other.aset_expiry(-3600)
            await other.asave()
            await sync_to_async(self.assertNotKeptUnder)(session_key)
            self.assertEqual(await self.backend(session_key).aload(), {})

    @override_settings(SESSION_STORE_KEY_HASH=True)
    def test_cycle_key(self):
        session = self.create_session(color="red")
        old_session_key = session.session_key
        session.cycle_key()
        session.save()
        self.assertNotEqual(session.session_key, old_session_key)
        self.assertNotKeptUnder(session.get_backend_key(old_session_key))
        self.assertKeptUnder(session.get_backend_key(session.session_key))
        self.assertEqual(self.backend(session.session_key)["color"], "red")

    @override_settings(SESSION_STORE_KEY_HASH=True)
    async def test_cycle_key_async(self):
        session = await self.acreate_session(color="red")
        old_session_key = session.session_key
        await session.acycle_key()
        await session.asave()
        self.assertNotEqual(session.session_key, old_session_key)
        await sync_to_async(self.assertNotKeptUnder)(
            session.get_backend_key(old_session_key)
        )
        await sync_to_async(self.assertKeptUnder)(
            session.get_backend_key(session.session_key)
        )
        self.assertEqual(await self.backend(session.session_key).aget("color"), "red")

    @override_settings(SESSION_STORE_KEY_HASH=True)
    def test_flush(self):
        session = self.create_session(color="red")
        backend_key = session.get_backend_key(session.session_key)
        session.flush()
        self.assertIsNone(session.session_key)
        self.assertNotKeptUnder(backend_key)

    @override_settings(SESSION_STORE_KEY_HASH=True)
    async def test_flush_async(self):
        session = await self.acreate_session(color="red")
        backend_key = session.get_backend_key(session.session_key)
        await session.aflush()
        self.assertIsNone(session.session_key)
        await sync_to_async(self.assertNotKeptUnder)(backend_key)


class DatabaseSessionStoreKeyHashTests(SessionStoreKeyHashTestsMixin, TestCase):
    backend = DatabaseSession
    stores = {"db"}

    @property
    def model(self):
        return self.backend.get_model_class()

    @override_settings(SESSION_STORE_KEY_HASH=True)
    def test_backend_key_fits_session_key_field(self):
        session = self.create_session()
        self.assertLessEqual(
            len(session.get_backend_key(session.session_key)),
            self.model._meta.get_field("session_key").max_length,
        )

    def test_load_queries(self):
        for value in (False, True, "transition"):
            with self.subTest(SESSION_STORE_KEY_HASH=value):
                with self.settings(SESSION_STORE_KEY_HASH=value):
                    session = self.create_session(color="red")
                    with self.assertNumQueries(1):
                        self.backend(session.session_key).load()

    def test_transition_load_queries(self):
        session = self.create_unhashed_session(color="red")
        with self.settings(SESSION_STORE_KEY_HASH="transition"):
            with self.assertNumQueries(1):
                self.backend(session.session_key).load()
            with self.assertNumQueries(1):
                self.backend("someunknownkey").load()

    def test_transition_save_when_session_cannot_be_moved(self):
        # For example, when another model references a custom session model.
        def update(queryset, **kwargs):
            if "session_key" in kwargs:
                raise DatabaseError
            return queryset_update(queryset, **kwargs)

        queryset_update = QuerySet.update
        session = self.create_unhashed_session(color="red")
        session_key = session.session_key
        with self.settings(SESSION_STORE_KEY_HASH="transition"):
            other = self.backend(session_key)
            other["color"] = "blue"
            with mock.patch.object(QuerySet, "update", update):
                other.save()
            self.assertKeptUnder(session_key)
            self.assertNotKeptUnder(other.get_backend_key(session_key))
            self.assertEqual(self.backend(session_key)["color"], "blue")

    def test_transition_save_of_session_being_moved(self):
        # A concurrent request moves the session right after this one failed to
        # save it under its hashed backend key.
        def update(queryset, **kwargs):
            if "session_key" in kwargs and not moved:
                moved.append(True)
                other.save()
            return queryset_update(queryset, **kwargs)

        moved = []
        queryset_update = QuerySet.update
        session = self.create_unhashed_session(color="red")
        session_key = session.session_key
        with self.settings(SESSION_STORE_KEY_HASH="transition"):
            other = self.backend(session_key)
            other["color"] = "blue"
            current = self.backend(session_key)
            current["color"] = "green"
            with mock.patch.object(QuerySet, "update", update):
                current.save()
            self.assertEqual(moved, [True])
            self.assertNotKeptUnder(session_key)
            self.assertEqual(self.backend(session_key)["color"], "green")

    async def test_transition_save_of_session_being_moved_async(self):
        def update(queryset, **kwargs):
            if "session_key" in kwargs and not moved:
                moved.append(True)
                other.save()
            return queryset_update(queryset, **kwargs)

        moved = []
        queryset_update = QuerySet.update
        session = await self.acreate_unhashed_session(color="red")
        session_key = session.session_key
        with self.settings(SESSION_STORE_KEY_HASH="transition"):
            other = self.backend(session_key)
            await other.aset("color", "blue")
            current = self.backend(session_key)
            await current.aset("color", "green")
            with mock.patch.object(QuerySet, "update", update):
                await current.asave()
            self.assertEqual(moved, [True])
            await sync_to_async(self.assertNotKeptUnder)(session_key)
            self.assertEqual(await self.backend(session_key).aget("color"), "green")

    def test_transition_delete_of_session_being_moved(self):
        # A concurrent request moves the session right after it wasn't found
        # under the first backend key that was looked up.
        def get(queryset, *args, **kwargs):
            lookups.append(kwargs)
            try:
                return queryset_get(queryset, *args, **kwargs)
            except self.model.DoesNotExist:
                if len(lookups) == 1:
                    other.save()
                raise

        lookups = []
        queryset_get = QuerySet.get
        session = self.create_unhashed_session(color="red")
        session_key = session.session_key
        with self.settings(SESSION_STORE_KEY_HASH="transition"):
            other = self.backend(session_key)
            self.assertEqual(other["color"], "red")
            with mock.patch.object(QuerySet, "get", get):
                self.backend(session_key).delete()
            self.assertNotKeptUnder(session_key)
            self.assertNotKeptUnder(other.get_backend_key(session_key))

    def test_transition_prefers_hashed_backend_key(self):
        session = self.create_unhashed_session(color="red")
        session_key = session.session_key
        with self.settings(SESSION_STORE_KEY_HASH="transition"):
            s = self.model.objects.get(session_key=session_key)
            self.model.objects.save(
                session.get_backend_key(session_key), {"color": "blue"}, s.expire_date
            )
            self.assertEqual(self.backend(session_key)["color"], "blue")
            self.backend(session_key).delete()
            self.assertEqual(self.model.objects.count(), 0)


class CustomDatabaseSessionStoreKeyHashTests(DatabaseSessionStoreKeyHashTests):
    backend = CustomDatabaseSession

    def test_transition_keeps_extra_session_field(self):
        session = self.create_unhashed_session(_auth_user_id=42)
        session_key = session.session_key
        with self.settings(SESSION_STORE_KEY_HASH="transition"):
            other = self.backend(session_key)
            other.load()
            other.save()
            s = self.model.objects.get(session_key=session.get_backend_key(session_key))
        self.assertEqual(s.account_id, 42)


class CacheDBSessionStoreKeyHashTests(
    SessionStoreKeyHashTestsMixin, TransactionTestCase
):
    # These tests aren't run inside a transaction: while
    # SESSION_STORE_KEY_HASH is "transition", a session that's saved inside a
    # transaction isn't cached.

    available_apps = ["django.contrib.sessions"]
    backend = CacheDBSession
    stores = {"db", "cache"}

    @override_settings(SESSION_STORE_KEY_HASH=True)
    def test_load_from_cache(self):
        session = self.create_session(color="red")
        with self.assertNumQueries(0):
            self.assertEqual(self.backend(session.session_key)["color"], "red")
            self.assertIs(self.backend().exists(session.session_key), True)


class CacheDBSessionStoreKeyHashTransactionTests(TransactionTestCase):
    # While SESSION_STORE_KEY_HASH is "transition", the cache follows the
    # database, whatever becomes of the transaction that saves a session.

    available_apps = ["django.contrib.sessions"]
    backend = CacheDBSession
    using = "default"

    def setUp(self):
        self.addCleanup(caches["default"].clear)

    def create_unhashed_session(self, **data):
        # A session as it's kept before SESSION_STORE_KEY_HASH is enabled.
        with self.settings(SESSION_STORE_KEY_HASH=False):
            session = self.backend()
            session.update(data)
            session.save()
        return session

    def create_moved_session(self, **data):
        # A session that was moved to its hashed backend key, and is cached.
        session = self.create_unhashed_session(**data)
        with self.settings(SESSION_STORE_KEY_HASH="transition"):
            self.backend(session.session_key).save()
        return session

    def get_hashed_backend_key(self, session_key):
        with self.settings(SESSION_STORE_KEY_HASH=True):
            return self.backend().get_backend_key(session_key)

    def assertStored(self, session_key, db, cache=None):
        """
        The color of the session where it's kept, in the database and, if
        given, in the cache: under its hashed backend key or under its session
        key.
        """
        names = {
            self.get_hashed_backend_key(session_key): "hashed",
            session_key: "unhashed",
        }
        sessions = self.backend.get_model_class().objects.using(self.using)
        self.assertEqual(
            {
                names[s.session_key]: s.get_decoded()["color"]
                for s in sessions.filter(session_key__in=names)
            },
            db,
        )
        if cache is None:
            return
        cached = caches["default"].get_many(
            [self.backend.cache_key_prefix + backend_key for backend_key in names]
        )
        self.assertEqual(
            {
                names[key.removeprefix(self.backend.cache_key_prefix)]: data["color"]
                for key, data in cached.items()
            },
            cache,
        )

    def assertLoads(self, session_key, transition, strict):
        """
        The color of the session that session stores load, and the one that
        they load once SESSION_STORE_KEY_HASH is True, first with the cache as
        it is and then with an empty cache.
        """
        for clear_cache in (False, True):
            for value, color in (("transition", transition), (True, strict)):
                with (
                    self.subTest(SESSION_STORE_KEY_HASH=value, clear_cache=clear_cache),
                    self.settings(SESSION_STORE_KEY_HASH=value),
                ):
                    if clear_cache:
                        caches["default"].clear()
                    self.assertEqual(self.backend(session_key).get("color"), color)

    def assertRolledBack(self, session_key):
        # The session is where, and as, it was before the transaction.
        self.assertStored(session_key, db={"unhashed": "red"}, cache={})
        self.assertLoads(session_key, transition="red", strict=None)

    def test_transition_saves_in_rolled_back_transaction(self):
        session = self.create_unhashed_session(color="red")
        with self.settings(SESSION_STORE_KEY_HASH="transition"):
            other = self.backend(session.session_key)
            with transaction.atomic(using=self.using):
                other["color"] = "blue"
                other.save()
                # This save finds the session where the first one moved it.
                other["color"] = "green"
                other.save()
                transaction.set_rollback(True, using=self.using)
        self.assertRolledBack(session.session_key)

    def test_transition_saves_by_two_stores_in_rolled_back_transaction(self):
        session = self.create_unhashed_session(color="red")
        with self.settings(SESSION_STORE_KEY_HASH="transition"):
            with transaction.atomic(using=self.using):
                other = self.backend(session.session_key)
                other["color"] = "blue"
                other.save()
                other = self.backend(session.session_key)
                other["color"] = "green"
                other.save()
                transaction.set_rollback(True, using=self.using)
        self.assertRolledBack(session.session_key)

    def test_transition_saves_in_committed_transaction(self):
        session = self.create_unhashed_session(color="red")
        with self.settings(SESSION_STORE_KEY_HASH="transition"):
            other = self.backend(session.session_key)
            with transaction.atomic(using=self.using):
                other["color"] = "blue"
                other.save()
                other["color"] = "green"
                other.save()
        self.assertStored(session.session_key, db={"hashed": "green"})
        self.assertLoads(session.session_key, transition="green", strict="green")

    def test_transition_asave_in_rolled_back_transaction(self):
        session = self.create_unhashed_session(color="red")
        with self.settings(SESSION_STORE_KEY_HASH="transition"):
            other = self.backend(session.session_key)
            other["color"] = "blue"
            with transaction.atomic(using=self.using):
                async_to_sync(other.asave)()
                transaction.set_rollback(True, using=self.using)
        self.assertRolledBack(session.session_key)

    def test_transition_load_in_rolled_back_transaction(self):
        session = self.create_unhashed_session(color="red")
        with self.settings(SESSION_STORE_KEY_HASH="transition"):
            other = self.backend(session.session_key)
            other["color"] = "blue"
            with transaction.atomic(using=self.using):
                other.save()
                # Another session store finds the session where it was moved.
                self.assertEqual(self.backend(session.session_key)["color"], "blue")
                transaction.set_rollback(True, using=self.using)
        self.assertRolledBack(session.session_key)

    def test_transition_aload_in_rolled_back_transaction(self):
        session = self.create_unhashed_session(color="red")
        with self.settings(SESSION_STORE_KEY_HASH="transition"):
            other = self.backend(session.session_key)
            other["color"] = "blue"
            with transaction.atomic(using=self.using):
                other.save()
                reader = self.backend(session.session_key)
                self.assertEqual(async_to_sync(reader.aget)("color"), "blue")
                transaction.set_rollback(True, using=self.using)
        self.assertRolledBack(session.session_key)

    def test_transition_save_in_manual_transaction(self):
        # Autocommit is off, and no atomic block is entered.
        session = self.create_unhashed_session(color="red")
        session_key = session.session_key
        with self.settings(SESSION_STORE_KEY_HASH="transition"):
            other = self.backend(session_key)
            other["color"] = "blue"
            transaction.set_autocommit(False, using=self.using)
            try:
                other.save()
            finally:
                transaction.rollback(using=self.using)
                transaction.set_autocommit(True, using=self.using)
        # Whether or not the database rolled the session back, session stores
        # load it from where, and as, the database has it.
        model = self.backend.get_model_class()
        colors = {
            s.session_key: s.get_decoded()["color"]
            for s in model.objects.using(self.using).all()
        }
        strict = colors.get(self.get_hashed_backend_key(session_key))
        self.assertLoads(
            session_key, transition=strict or colors[session_key], strict=strict
        )

    def test_transition_save_of_moved_session_in_rolled_back_transaction(self):
        session = self.create_moved_session(color="red")
        session_key = session.session_key
        self.assertStored(session_key, db={"hashed": "red"}, cache={"hashed": "red"})
        with self.settings(SESSION_STORE_KEY_HASH="transition"):
            other = self.backend(session_key)
            other["color"] = "blue"
            with transaction.atomic(using=self.using):
                other.save()
                # The session is removed from the cache.
                self.assertStored(session_key, db={"hashed": "blue"}, cache={})
                transaction.set_rollback(True, using=self.using)
        self.assertStored(session_key, db={"hashed": "red"}, cache={})
        self.assertLoads(session_key, transition="red", strict="red")

    def test_transition_save_of_moved_session_in_committed_transaction(self):
        session = self.create_moved_session(color="red")
        session_key = session.session_key
        with self.settings(SESSION_STORE_KEY_HASH="transition"):
            other = self.backend(session_key)
            other["color"] = "blue"
            with transaction.atomic(using=self.using):
                other.save()
        self.assertStored(session_key, db={"hashed": "blue"})
        self.assertLoads(session_key, transition="blue", strict="blue")

    def cache_as_concurrent_request(self, session_key, color):
        # A concurrent request, which isn't inside the transaction, loads the
        # session as the database has it for now, and caches it.
        backend_key = self.get_hashed_backend_key(session_key)
        caches["default"].set(
            self.backend.cache_key_prefix + backend_key, {"color": color}
        )

    def test_transition_save_of_moved_session_cached_before_commit(self):
        session = self.create_moved_session(color="red")
        session_key = session.session_key
        with self.settings(SESSION_STORE_KEY_HASH="transition"):
            other = self.backend(session_key)
            other["color"] = "blue"
            with transaction.atomic(using=self.using):
                other.save()
                self.cache_as_concurrent_request(session_key, "red")
        # The session is removed from the cache again once the transaction is
        # committed.
        self.assertStored(session_key, db={"hashed": "blue"}, cache={})
        self.assertLoads(session_key, transition="blue", strict="blue")

    def test_transition_asave_of_moved_session_cached_before_commit(self):
        session = self.create_moved_session(color="red")
        session_key = session.session_key
        with self.settings(SESSION_STORE_KEY_HASH="transition"):
            other = self.backend(session_key)
            other["color"] = "blue"
            with transaction.atomic(using=self.using):
                async_to_sync(other.asave)()
                self.cache_as_concurrent_request(session_key, "red")
        self.assertStored(session_key, db={"hashed": "blue"}, cache={})
        self.assertLoads(session_key, transition="blue", strict="blue")

    def test_transition_save_of_moved_session_cached_before_commit_of_savepoint(self):
        session = self.create_moved_session(color="red")
        session_key = session.session_key
        with self.settings(SESSION_STORE_KEY_HASH="transition"):
            other = self.backend(session_key)
            other["color"] = "blue"
            with transaction.atomic(using=self.using):
                with transaction.atomic(using=self.using):
                    other.save()
                # The transaction isn't committed yet.
                self.cache_as_concurrent_request(session_key, "red")
        self.assertStored(session_key, db={"hashed": "blue"}, cache={})
        self.assertLoads(session_key, transition="blue", strict="blue")

    def test_transition_save_of_moved_session_cached_before_rollback(self):
        session = self.create_moved_session(color="red")
        session_key = session.session_key
        with self.settings(SESSION_STORE_KEY_HASH="transition"):
            other = self.backend(session_key)
            other["color"] = "blue"
            with transaction.atomic(using=self.using):
                other.save()
                self.cache_as_concurrent_request(session_key, "red")
                transaction.set_rollback(True, using=self.using)
        # What the concurrent request cached is what the database has.
        self.assertStored(session_key, db={"hashed": "red"}, cache={"hashed": "red"})
        self.assertLoads(session_key, transition="red", strict="red")

    def test_transition_save_of_moved_session_cached_before_rollback_of_savepoint(self):
        session = self.create_moved_session(color="red")
        session_key = session.session_key
        with self.settings(SESSION_STORE_KEY_HASH="transition"):
            other = self.backend(session_key)
            other["color"] = "blue"
            with transaction.atomic(using=self.using):
                with transaction.atomic(using=self.using):
                    other.save()
                    self.cache_as_concurrent_request(session_key, "red")
                    transaction.set_rollback(True, using=self.using)
        self.assertStored(session_key, db={"hashed": "red"}, cache={"hashed": "red"})
        self.assertLoads(session_key, transition="red", strict="red")

    def test_transition_load_of_moved_session_in_transaction(self):
        session = self.create_moved_session(color="red")
        session_key = session.session_key
        caches["default"].clear()
        with self.settings(SESSION_STORE_KEY_HASH="transition"):
            # A session that's loaded inside a transaction isn't cached.
            with transaction.atomic(using=self.using):
                self.assertEqual(self.backend(session_key)["color"], "red")
            self.assertStored(session_key, db={"hashed": "red"}, cache={})
            # It's cached when it's loaded outside of a transaction.
            self.assertEqual(self.backend(session_key)["color"], "red")
            self.assertStored(
                session_key, db={"hashed": "red"}, cache={"hashed": "red"}
            )
            with (
                transaction.atomic(using=self.using),
                self.assertNumQueries(0, using=self.using),
            ):
                self.assertEqual(self.backend(session_key)["color"], "red")

    @override_settings(SESSION_STORE_KEY_HASH="transition")
    def test_transition_create_in_transaction(self):
        # A session that's created inside a transaction is cached, as with the
        # other values of the setting.
        with transaction.atomic(using=self.using):
            session = self.backend()
            session["color"] = "red"
            session.save()
            self.assertStored(
                session.session_key, db={"hashed": "red"}, cache={"hashed": "red"}
            )


class SessionRouter:
    # Sessions are kept in the other database. Like a router that needs to know
    # the instance that's written, it only routes the writes of an instance.

    def db_for_read(self, model, **hints):
        if model._meta.app_label == "sessions":
            return "other"

    def db_for_write(self, model, **hints):
        if model._meta.app_label == "sessions" and hints.get("instance") is not None:
            return "other"


@override_settings(DATABASE_ROUTERS=[SessionRouter()])
class CacheDBSessionStoreKeyHashRouterTests(CacheDBSessionStoreKeyHashTransactionTests):
    # The transactions are those of the database that the sessions are in.

    databases = {"default", "other"}
    using = "other"


class CacheSessionStoreKeyHashTests(SessionStoreKeyHashTestsMixin, SimpleTestCase):
    backend = CacheSession
    stores = {"cache"}

    def test_transition_load_of_session_being_moved(self):
        # A concurrent request moves the session right after it wasn't found
        # under its hashed backend key.
        def get(key, *args, **kwargs):
            if key == unhashed_cache_key and other.modified:
                other.modified = False
                other.save()
            return cache_get(key, *args, **kwargs)

        cache_get = caches["default"].get
        session = self.create_unhashed_session(color="red")
        session_key = session.session_key
        unhashed_cache_key = self.backend.cache_key_prefix + session_key
        with self.settings(SESSION_STORE_KEY_HASH="transition"):
            other = self.backend(session_key)
            self.assertEqual(other["color"], "red")
            with mock.patch.object(caches["default"], "get", get):
                self.assertEqual(self.backend(session_key)["color"], "red")
            self.assertNotKeptUnder(session_key)

    def test_transition_save_when_cache_fails_silently(self):
        session = self.create_unhashed_session(color="red")
        session_key = session.session_key
        with self.settings(SESSION_STORE_KEY_HASH="transition"):
            other = self.backend(session_key)
            other["color"] = "blue"
            with mock.patch.object(caches["default"], "set"):
                other.save()
            # The only copy of the session isn't deleted.
            self.assertKeptUnder(session_key)
            self.assertEqual(self.backend(session_key)["color"], "red")

    async def test_transition_save_when_cache_fails_silently_async(self):
        session = await self.acreate_unhashed_session(color="red")
        session_key = session.session_key
        with self.settings(SESSION_STORE_KEY_HASH="transition"):
            other = self.backend(session_key)
            await other.aset("color", "blue")
            with mock.patch.object(caches["default"], "aset", mock.AsyncMock()):
                await other.asave()
            await sync_to_async(self.assertKeptUnder)(session_key)
            self.assertEqual(await self.backend(session_key).aget("color"), "red")


class FileSessionStoreKeyHashTests(SimpleTestCase):
    def test_not_supported(self):
        msg = "The file session backend doesn't support SESSION_STORE_KEY_HASH."
        for value in (True, "transition"):
            with self.subTest(SESSION_STORE_KEY_HASH=value):
                with self.settings(SESSION_STORE_KEY_HASH=value):
                    with self.assertRaisesMessage(ImproperlyConfigured, msg):
                        FileSession()


class SessionStoreKeyHashMiddlewareTests(TestCase):
    request_factory = RequestFactory()

    def test_transition_moves_session_that_is_only_read(self):
        def get_hello(request):
            return HttpResponse(request.session["hello"])

        with self.settings(SESSION_STORE_KEY_HASH=False):
            session = DatabaseSession()
            session["hello"] = "world"
            session.save()
        session_key = session.session_key
        with self.settings(SESSION_STORE_KEY_HASH="transition"):
            request = self.request_factory.get("/")
            request.COOKIES[settings.SESSION_COOKIE_NAME] = session_key
            response = SessionMiddleware(get_hello)(request)
            self.assertEqual(response.content, b"world")
            self.assertEqual(
                response.cookies[settings.SESSION_COOKIE_NAME].value, session_key
            )
            self.assertEqual(
                Session.objects.get().session_key,
                session.get_backend_key(session_key),
            )

    @override_settings(SESSION_STORE_KEY_HASH=True)
    def test_cookie_holds_session_key(self):
        def set_hello(request):
            request.session["hello"] = "world"
            return HttpResponse()

        def get_hello(request):
            return HttpResponse(request.session["hello"])

        response = SessionMiddleware(set_hello)(self.request_factory.get("/"))
        session_key = response.cookies[settings.SESSION_COOKIE_NAME].value
        self.assertRegex(session_key, r"\A[a-z0-9]{32}\Z")
        self.assertEqual(
            Session.objects.get().session_key,
            DatabaseSession().get_backend_key(session_key),
        )
        request = self.request_factory.get("/")
        request.COOKIES[settings.SESSION_COOKIE_NAME] = session_key
        response = SessionMiddleware(get_hello)(request)
        self.assertEqual(response.content, b"world")


class ReferencedSessionStoreKeyHashTests(TransactionTestCase):
    # Another model references the session model, and transactions are
    # committed or rolled back.

    available_apps = ["sessions_tests"]
    backend = ReferencedSessionStore

    def setUp(self):
        self.addCleanup(caches["default"].clear)

    @property
    def model(self):
        return self.backend.get_model_class()

    def create_unhashed_session(self, **data):
        with self.settings(SESSION_STORE_KEY_HASH=False):
            session = self.backend()
            session.update(data)
            session.save()
        return session

    def get_hashed_backend_key(self, session_key):
        with self.settings(SESSION_STORE_KEY_HASH=True):
            return self.backend().get_backend_key(session_key)

    def assertKeptUnderSessionKey(self, session_key):
        backend_key = self.get_hashed_backend_key(session_key)
        self.assertIs(self.model.objects.filter(session_key=session_key).exists(), True)
        self.assertIs(
            self.model.objects.filter(session_key=backend_key).exists(), False
        )

    def assertKeptUnderHashedBackendKey(self, session_key):
        backend_key = self.get_hashed_backend_key(session_key)
        self.assertIs(self.model.objects.filter(session_key=backend_key).exists(), True)
        self.assertIs(
            self.model.objects.filter(session_key=session_key).exists(), False
        )

    def assertIgnoredWithoutTransition(self, session_key):
        # Whether or not the session is in a cache.
        with self.settings(SESSION_STORE_KEY_HASH=True):
            self.assertEqual(self.backend(session_key).load(), {})
            caches["default"].clear()
            self.assertEqual(self.backend(session_key).load(), {})

    def test_transition_load_of_referenced_session(self):
        session = self.create_unhashed_session(color="red")
        session_key = session.session_key
        SessionReference.objects.create(session_id=session_key, memo="before")
        with self.settings(SESSION_STORE_KEY_HASH="transition"):
            other = self.backend(session_key)
            self.assertEqual(other["color"], "red")
            # The session can't be moved, so it isn't saved for that.
            self.assertIs(other.modified, False)

    def test_transition_save_of_referenced_session(self):
        session = self.create_unhashed_session(color="red")
        session_key = session.session_key
        reference = SessionReference.objects.create(
            session_id=session_key, memo="before"
        )
        with self.settings(SESSION_STORE_KEY_HASH="transition"):
            other = self.backend(session_key)
            other["color"] = "blue"
            other.save()
            self.assertKeptUnderSessionKey(session_key)
            self.assertEqual(self.backend(session_key)["color"], "blue")
        reference.refresh_from_db()
        self.assertEqual(reference.session_id, session_key)
        self.assertIgnoredWithoutTransition(session_key)

    async def test_transition_save_of_referenced_session_async(self):
        session = await sync_to_async(self.create_unhashed_session)(color="red")
        session_key = session.session_key
        reference = await SessionReference.objects.acreate(
            session_id=session_key, memo="before"
        )
        with self.settings(SESSION_STORE_KEY_HASH="transition"):
            other = self.backend(session_key)
            await other.aset("color", "blue")
            await other.asave()
            await sync_to_async(self.assertKeptUnderSessionKey)(session_key)
            self.assertEqual(await self.backend(session_key).aget("color"), "blue")
        await reference.arefresh_from_db()
        self.assertEqual(reference.session_id, session_key)

    def test_transition_save_of_referenced_session_in_transaction(self):
        session = self.create_unhashed_session(color="red")
        session_key = session.session_key
        reference = SessionReference.objects.create(
            session_id=session_key, memo="before"
        )
        with self.settings(SESSION_STORE_KEY_HASH="transition"):
            other = self.backend(session_key)
            other["color"] = "blue"
            # The transaction can be committed.
            with transaction.atomic():
                SessionReference.objects.filter(pk=reference.pk).update(memo="after")
                other.save()
            self.assertKeptUnderSessionKey(session_key)
            self.assertEqual(self.backend(session_key)["color"], "blue")
        reference.refresh_from_db()
        self.assertEqual(reference.session_id, session_key)
        self.assertEqual(reference.memo, "after")
        self.assertIgnoredWithoutTransition(session_key)

    def test_transition_save_of_session_without_references(self):
        referenced_session = self.create_unhashed_session(color="red")
        SessionReference.objects.create(
            session_id=referenced_session.session_key, memo="before"
        )
        session = self.create_unhashed_session(color="red")
        session_key = session.session_key
        with self.settings(SESSION_STORE_KEY_HASH="transition"):
            other = self.backend(session_key)
            self.assertEqual(other["color"], "red")
            self.assertIs(other.modified, True)
            with transaction.atomic():
                other.save()
            self.assertKeptUnderHashedBackendKey(session_key)
        with self.settings(SESSION_STORE_KEY_HASH=True):
            self.assertEqual(self.backend(session_key)["color"], "red")
            caches["default"].clear()
            self.assertEqual(self.backend(session_key)["color"], "red")

    def test_transition_save_in_rolled_back_transaction(self):
        session = self.create_unhashed_session(color="red")
        session_key = session.session_key
        with self.settings(SESSION_STORE_KEY_HASH="transition"):
            other = self.backend(session_key)
            other["color"] = "blue"
            with transaction.atomic():
                other.save()
                transaction.set_rollback(True)
            # The session is where, and as, the database has it.
            self.assertKeptUnderSessionKey(session_key)
            self.assertEqual(self.backend(session_key)["color"], "red")
        self.assertIgnoredWithoutTransition(session_key)


class CachedReferencedSessionStoreKeyHashTests(ReferencedSessionStoreKeyHashTests):
    backend = CachedReferencedSessionStore

    def assertKeptUnderSessionKey(self, session_key):
        super().assertKeptUnderSessionKey(session_key)
        # The cache follows the database.
        backend_key = self.get_hashed_backend_key(session_key)
        self.assertNotIn(self.backend.cache_key_prefix + backend_key, caches["default"])
        self.assertNotIn(self.backend.cache_key_prefix + session_key, caches["default"])


class MultiColumnRelationSessionStoreKeyHashTests(TestCase):
    # Another model is related to the session model by several fields, one of
    # which is the primary key of the session model.

    backend = MultiTenantSessionStore

    @property
    def model(self):
        return self.backend.get_model_class()

    def create_unhashed_session(self, **data):
        with self.settings(SESSION_STORE_KEY_HASH=False):
            session = self.backend()
            session.update(data)
            session.save()
        return session

    def assertNotMoved(self, session_key):
        with self.settings(SESSION_STORE_KEY_HASH="transition"):
            other = self.backend(session_key)
            self.assertEqual(other["color"], "red")
            # The session can't be moved, so it isn't saved for that.
            self.assertIs(other.modified, False)
            other["color"] = "blue"
            other.save()
            self.assertEqual(self.backend(session_key)["color"], "blue")
        self.assertQuerySetEqual(
            self.model.objects.values_list("session_key", flat=True), [session_key]
        )

    def assertMoved(self, session_key):
        with self.settings(SESSION_STORE_KEY_HASH="transition"):
            other = self.backend(session_key)
            self.assertEqual(other["color"], "red")
            self.assertIs(other.modified, True)
            other["color"] = "blue"
            other.save()
            backend_key = other.get_backend_key(session_key)
        self.assertQuerySetEqual(
            self.model.objects.values_list("session_key", flat=True), [backend_key]
        )
        with self.settings(SESSION_STORE_KEY_HASH=True):
            self.assertEqual(self.backend(session_key)["color"], "blue")

    def test_transition_save_of_related_session(self):
        session = self.create_unhashed_session(color="red")
        MultiTenantSessionNote.objects.create(session_key=session.session_key)
        self.assertNotMoved(session.session_key)

    def test_transition_save_of_session_without_related_rows(self):
        session = self.create_unhashed_session(color="red")
        self.assertMoved(session.session_key)

    def test_transition_save_of_session_with_partly_matching_row(self):
        # The row has the primary key of the session, but not its tenant, so
        # it isn't related to the session.
        session = self.create_unhashed_session(color="red")
        MultiTenantSessionNote.objects.create(
            session_key=session.session_key, tenant_id=2
        )
        self.assertMoved(session.session_key)

    def test_transition_save_of_session_with_row_without_tenant(self):
        session = self.create_unhashed_session(color="red")
        MultiTenantSessionNote.objects.create(
            session_key=session.session_key, tenant_id=None
        )
        self.assertMoved(session.session_key)

    def test_transition_load_compares_rows_to_stored_session(self):
        # The tenant of the session is the one that the database has, rather
        # than the default of the session model.
        session = self.create_unhashed_session(color="red")
        session_key = session.session_key
        self.model.objects.filter(session_key=session_key).update(tenant_id=2)
        note = MultiTenantSessionNote.objects.create(session_key=session_key)
        with self.settings(SESSION_STORE_KEY_HASH="transition"):
            other = self.backend(session_key)
            self.assertEqual(other["color"], "red")
            self.assertIs(other.modified, True)
            MultiTenantSessionNote.objects.filter(pk=note.pk).update(tenant_id=2)
            other = self.backend(session_key)
            self.assertEqual(other["color"], "red")
            self.assertIs(other.modified, False)
