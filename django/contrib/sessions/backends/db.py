import logging
from functools import cached_property

from asgiref.sync import sync_to_async

from django.contrib.sessions.backends.base import CreateError, SessionBase, UpdateError
from django.core.exceptions import SuspiciousOperation
from django.db import DatabaseError, IntegrityError, router, transaction
from django.db.models import Exists, OuterRef
from django.db.models.deletion import get_candidate_relations_to_delete
from django.utils import timezone


class SessionStore(SessionBase):
    """
    Implement database session store.
    """

    def __init__(self, session_key=None):
        super().__init__(session_key)

    @classmethod
    def get_model_class(cls):
        # Avoids a circular import and allows importing SessionStore when
        # django.contrib.sessions is not in INSTALLED_APPS.
        from django.contrib.sessions.models import Session

        return Session

    @cached_property
    def model(self):
        return self.get_model_class()

    # While SESSION_STORE_KEY_HASH is "transition", whether the session was
    # loaded from, or saved to, its session key rather than its hashed backend
    # key.
    _kept_under_session_key = False
    # The database that the session was last saved to.
    _saved_using = None

    def _is_referenced(self, session_key, using=None):
        """
        Return whether rows of other models reference the primary key of the
        session that's kept under session_key, in which case it can't be moved
        to another key.
        """
        for related in get_candidate_relations_to_delete(self.model._meta):
            fields = related.field.related_fields
            pk_fields = [field for field, target in fields if target.primary_key]
            # A relation that the primary key isn't part of isn't affected.
            if not pk_fields:
                continue
            rows = related.related_model._base_manager.using(using).filter(
                **{pk_fields[0].attname: session_key}
            )
            if len(fields) > 1:
                # A row is related to the session by all the fields of the
                # relation, which are compared to the session as it's stored.
                rows = rows.filter(
                    Exists(
                        self.model._base_manager.filter(
                            **{
                                target.attname: OuterRef(field.attname)
                                for field, target in fields
                            }
                        )
                    )
                )
            if rows.exists():
                return True
        return False

    def _select_session(self, sessions, backend_keys):
        # While SESSION_STORE_KEY_HASH is "transition", a session may be kept
        # under either backend key.
        sessions = {s.session_key: s for s in sessions}
        if not sessions:
            raise self.model.DoesNotExist
        self._kept_under_session_key = backend_keys[0] not in sessions
        if self._kept_under_session_key:
            return next(iter(sessions.values()))
        return sessions[backend_keys[0]]

    def _save_kept_under_session_key(self, obj, using):
        """
        While SESSION_STORE_KEY_HASH is "transition", save the session if it's
        still kept under its session key, and move it to its hashed backend key
        if possible. Return whether it was saved.
        """
        backend_keys = self._get_backend_keys(self.session_key)
        if len(backend_keys) == 1:
            return False
        # Moving the session would leave the rows of other models that
        # reference it without a session, which a database that defers
        # constraint checks only reports when the transaction is committed. A
        # session that's referenced isn't moved.
        if not self._is_referenced(backend_keys[1], using):
            sessions = self.model.objects.using(using).filter(
                session_key=backend_keys[1]
            )
            try:
                with transaction.atomic(using=using):
                    sessions.update(session_key=backend_keys[0])
            except DatabaseError:
                # The session can't be moved. It's saved where it is.
                pass
        # A concurrent request may have just moved the session, so its hashed
        # backend key comes first even if no row was moved.
        for backend_key in backend_keys:
            obj.session_key = backend_key
            try:
                with transaction.atomic(using=using):
                    obj.save(force_update=True, using=using)
            except DatabaseError:
                continue
            self._kept_under_session_key = backend_key != backend_keys[0]
            return True
        return False

    def _get_session_from_db(self):
        try:
            backend_keys = self._get_backend_keys(self.session_key)
            if len(backend_keys) == 1:
                return self.model.objects.get(
                    session_key=backend_keys[0], expire_date__gt=timezone.now()
                )
            s = self._select_session(
                self.model.objects.filter(
                    session_key__in=backend_keys, expire_date__gt=timezone.now()
                ),
                backend_keys,
            )
            if self._kept_under_session_key and not self._is_referenced(
                s.session_key, s._state.db
            ):
                # Have the session saved, which moves it to its hashed backend
                # key.
                self.modified = True
            return s
        except (self.model.DoesNotExist, SuspiciousOperation) as e:
            if isinstance(e, SuspiciousOperation):
                logger = logging.getLogger("django.security.%s" % e.__class__.__name__)
                logger.warning(str(e))
            self._session_key = None

    async def _aget_session_from_db(self):
        try:
            backend_keys = self._get_backend_keys(self.session_key)
            if len(backend_keys) == 1:
                return await self.model.objects.aget(
                    session_key=backend_keys[0], expire_date__gt=timezone.now()
                )
            s = self._select_session(
                [
                    s
                    async for s in self.model.objects.filter(
                        session_key__in=backend_keys, expire_date__gt=timezone.now()
                    )
                ],
                backend_keys,
            )
            if self._kept_under_session_key and not await sync_to_async(
                self._is_referenced
            )(s.session_key, s._state.db):
                self.modified = True
            return s
        except (self.model.DoesNotExist, SuspiciousOperation) as e:
            if isinstance(e, SuspiciousOperation):
                logger = logging.getLogger("django.security.%s" % e.__class__.__name__)
                logger.warning(str(e))
            self._session_key = None

    def load(self):
        s = self._get_session_from_db()
        return self.decode(s.session_data) if s else {}

    async def aload(self):
        s = await self._aget_session_from_db()
        return self.decode(s.session_data) if s else {}

    def exists(self, session_key):
        return any(
            self.model.objects.filter(session_key=backend_key).exists()
            for backend_key in self._get_backend_keys(session_key)
        )

    async def aexists(self, session_key):
        for backend_key in self._get_backend_keys(session_key):
            if await self.model.objects.filter(session_key=backend_key).aexists():
                return True
        return False

    def create(self):
        while True:
            self._session_key = self._get_new_session_key()
            try:
                # Save immediately to ensure we have a unique entry in the
                # database.
                self.save(must_create=True)
            except CreateError:
                # Key wasn't unique. Try again.
                continue
            self.modified = True
            return

    async def acreate(self):
        while True:
            self._session_key = await self._aget_new_session_key()
            try:
                # Save immediately to ensure we have a unique entry in the
                # database.
                await self.asave(must_create=True)
            except CreateError:
                # Key wasn't unique. Try again.
                continue
            self.modified = True
            return

    def create_model_instance(self, data):
        """
        Return a new instance of the session model object, which represents the
        current session state. Intended to be used for saving the session data
        to the database.
        """
        return self.model(
            session_key=self.get_backend_key(self._get_or_create_session_key()),
            session_data=self.encode(data),
            expire_date=self.get_expiry_date(),
        )

    async def acreate_model_instance(self, data):
        """See create_model_instance()."""
        return self.model(
            session_key=self.get_backend_key(await self._aget_or_create_session_key()),
            session_data=self.encode(data),
            expire_date=await self.aget_expiry_date(),
        )

    def save(self, must_create=False):
        """
        Save the current session data to the database. If 'must_create' is
        True, raise a database error if the saving operation doesn't create a
        new entry (as opposed to possibly updating an existing entry).
        """
        if self.session_key is None:
            return self.create()
        data = self._get_session(no_load=must_create)
        obj = self.create_model_instance(data)
        using = router.db_for_write(self.model, instance=obj)
        self._kept_under_session_key = False
        self._saved_using = using
        try:
            with transaction.atomic(using=using):
                obj.save(
                    force_insert=must_create, force_update=not must_create, using=using
                )
        except IntegrityError:
            if must_create:
                raise CreateError
            raise
        except DatabaseError:
            if not must_create:
                if not self._save_kept_under_session_key(obj, using):
                    raise UpdateError
                return
            raise

    async def asave(self, must_create=False):
        """See save()."""
        if self.session_key is None:
            return await self.acreate()
        data = await self._aget_session(no_load=must_create)
        obj = await self.acreate_model_instance(data)
        using = router.db_for_write(self.model, instance=obj)
        self._kept_under_session_key = False
        self._saved_using = using
        try:
            # This code MUST run in a transaction, so it requires
            # @sync_to_async wrapping until transaction.atomic() supports
            # async.
            @sync_to_async
            def sync_transaction():
                with transaction.atomic(using=using):
                    obj.save(
                        force_insert=must_create,
                        force_update=not must_create,
                        using=using,
                    )

            await sync_transaction()
        except IntegrityError:
            if must_create:
                raise CreateError
            raise
        except DatabaseError:
            if not must_create:
                if not await sync_to_async(self._save_kept_under_session_key)(
                    obj, using
                ):
                    raise UpdateError
                return
            raise

    def delete(self, session_key=None):
        if session_key is None:
            if self.session_key is None:
                return
            session_key = self.session_key
        # The session key comes first, so that the session is found even if a
        # concurrent request is moving it to its hashed backend key.
        for backend_key in reversed(self._get_backend_keys(session_key)):
            try:
                self.model.objects.get(session_key=backend_key).delete()
            except self.model.DoesNotExist:
                pass

    async def adelete(self, session_key=None):
        if session_key is None:
            if self.session_key is None:
                return
            session_key = self.session_key
        for backend_key in reversed(self._get_backend_keys(session_key)):
            try:
                obj = await self.model.objects.aget(session_key=backend_key)
                await obj.adelete()
            except self.model.DoesNotExist:
                pass

    @classmethod
    def clear_expired(cls):
        cls.get_model_class().objects.filter(expire_date__lt=timezone.now()).delete()

    @classmethod
    async def aclear_expired(cls):
        await cls.get_model_class().objects.filter(
            expire_date__lt=timezone.now()
        ).adelete()
