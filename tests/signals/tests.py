from unittest import mock

from asgiref.sync import markcoroutinefunction

from django import dispatch
from django.apps.registry import Apps
from django.db import models
from django.db.models import signals
from django.dispatch import receiver
from django.test import SimpleTestCase, TestCase
from django.test.utils import isolate_apps

from .models import Author, Book, Car, Page, Person


class BaseSignalSetup:
    def setUp(self):
        # Save up the number of connected signals so that we can check at the
        # end that all the signals we register get properly unregistered (#9989)
        self.pre_signals = (
            len(signals.pre_save.receivers),
            len(signals.post_save.receivers),
            len(signals.pre_delete.receivers),
            len(signals.post_delete.receivers),
        )

    def tearDown(self):
        # All our signals got disconnected properly.
        post_signals = (
            len(signals.pre_save.receivers),
            len(signals.post_save.receivers),
            len(signals.pre_delete.receivers),
            len(signals.post_delete.receivers),
        )
        self.assertEqual(self.pre_signals, post_signals)


class SignalTests(BaseSignalSetup, TestCase):
    def test_model_pre_init_and_post_init(self):
        data = []

        def pre_init_callback(sender, args, **kwargs):
            data.append(kwargs["kwargs"])

        signals.pre_init.connect(pre_init_callback)

        def post_init_callback(sender, instance, **kwargs):
            data.append(instance)

        signals.post_init.connect(post_init_callback)

        p1 = Person(first_name="John", last_name="Doe")
        self.assertEqual(data, [{}, p1])

    def test_save_signals(self):
        data = []

        def pre_save_handler(signal, sender, instance, **kwargs):
            data.append((instance, sender, kwargs.get("raw", False)))

        def post_save_handler(signal, sender, instance, **kwargs):
            data.append(
                (instance, sender, kwargs.get("created"), kwargs.get("raw", False))
            )

        signals.pre_save.connect(pre_save_handler, weak=False)
        signals.post_save.connect(post_save_handler, weak=False)
        try:
            p1 = Person.objects.create(first_name="John", last_name="Smith")

            self.assertEqual(
                data,
                [
                    (p1, Person, False),
                    (p1, Person, True, False),
                ],
            )
            data[:] = []

            p1.first_name = "Tom"
            p1.save()
            self.assertEqual(
                data,
                [
                    (p1, Person, False),
                    (p1, Person, False, False),
                ],
            )
            data[:] = []

            # Calling an internal method purely so that we can trigger a "raw" save.
            p1.save_base(raw=True)
            self.assertEqual(
                data,
                [
                    (p1, Person, True),
                    (p1, Person, False, True),
                ],
            )
            data[:] = []

            p2 = Person(first_name="James", last_name="Jones")
            p2.id = 99999
            p2.save()
            self.assertEqual(
                data,
                [
                    (p2, Person, False),
                    (p2, Person, True, False),
                ],
            )
            data[:] = []
            p2.id = 99998
            p2.save()
            self.assertEqual(
                data,
                [
                    (p2, Person, False),
                    (p2, Person, True, False),
                ],
            )

            # The sender should stay the same when using defer().
            data[:] = []
            p3 = Person.objects.defer("first_name").get(pk=p1.pk)
            p3.last_name = "Reese"
            p3.save()
            self.assertEqual(
                data,
                [
                    (p3, Person, False),
                    (p3, Person, False, False),
                ],
            )
        finally:
            signals.pre_save.disconnect(pre_save_handler)
            signals.post_save.disconnect(post_save_handler)

    def test_delete_signals(self):
        data = []

        def pre_delete_handler(signal, sender, instance, origin, **kwargs):
            data.append((instance, sender, instance.id is None, origin))

        # #8285: signals can be any callable
        class PostDeleteHandler:
            def __init__(self, data):
                self.data = data

            def __call__(self, signal, sender, instance, origin, **kwargs):
                self.data.append((instance, sender, instance.id is None, origin))

        post_delete_handler = PostDeleteHandler(data)

        signals.pre_delete.connect(pre_delete_handler, weak=False)
        signals.post_delete.connect(post_delete_handler, weak=False)
        try:
            p1 = Person.objects.create(first_name="John", last_name="Smith")
            p1.delete()
            self.assertEqual(
                data,
                [
                    (p1, Person, False, p1),
                    (p1, Person, False, p1),
                ],
            )
            data[:] = []

            p2 = Person(first_name="James", last_name="Jones")
            p2.id = 99999
            p2.save()
            p2.id = 99998
            p2.save()
            p2.delete()
            self.assertEqual(
                data,
                [
                    (p2, Person, False, p2),
                    (p2, Person, False, p2),
                ],
            )
            data[:] = []

            self.assertQuerySetEqual(
                Person.objects.all(),
                [
                    "James Jones",
                ],
                str,
            )
        finally:
            signals.pre_delete.disconnect(pre_delete_handler)
            signals.post_delete.disconnect(post_delete_handler)

    def test_delete_signals_origin_model(self):
        data = []

        def pre_delete_handler(signal, sender, instance, origin, **kwargs):
            data.append((sender, origin))

        def post_delete_handler(signal, sender, instance, origin, **kwargs):
            data.append((sender, origin))

        person = Person.objects.create(first_name="John", last_name="Smith")
        book = Book.objects.create(name="Rayuela")
        Page.objects.create(text="Page 1", book=book)
        Page.objects.create(text="Page 2", book=book)

        signals.pre_delete.connect(pre_delete_handler, weak=False)
        signals.post_delete.connect(post_delete_handler, weak=False)
        try:
            # Instance deletion.
            person.delete()
            self.assertEqual(data, [(Person, person), (Person, person)])
            data[:] = []
            # Cascade deletion.
            book.delete()
            self.assertEqual(
                data,
                [
                    (Page, book),
                    (Page, book),
                    (Book, book),
                    (Page, book),
                    (Page, book),
                    (Book, book),
                ],
            )
        finally:
            signals.pre_delete.disconnect(pre_delete_handler)
            signals.post_delete.disconnect(post_delete_handler)

    def test_delete_signals_origin_queryset(self):
        data = []

        def pre_delete_handler(signal, sender, instance, origin, **kwargs):
            data.append((sender, origin))

        def post_delete_handler(signal, sender, instance, origin, **kwargs):
            data.append((sender, origin))

        Person.objects.create(first_name="John", last_name="Smith")
        book = Book.objects.create(name="Rayuela")
        Page.objects.create(text="Page 1", book=book)
        Page.objects.create(text="Page 2", book=book)

        signals.pre_delete.connect(pre_delete_handler, weak=False)
        signals.post_delete.connect(post_delete_handler, weak=False)
        try:
            # Queryset deletion.
            qs = Person.objects.all()
            qs.delete()
            self.assertEqual(data, [(Person, qs), (Person, qs)])
            data[:] = []
            # Cascade deletion.
            qs = Book.objects.all()
            qs.delete()
            self.assertEqual(
                data,
                [
                    (Page, qs),
                    (Page, qs),
                    (Book, qs),
                    (Page, qs),
                    (Page, qs),
                    (Book, qs),
                ],
            )
        finally:
            signals.pre_delete.disconnect(pre_delete_handler)
            signals.post_delete.disconnect(post_delete_handler)

    def test_decorators(self):
        data = []

        @receiver(signals.pre_save, weak=False)
        def decorated_handler(signal, sender, instance, **kwargs):
            data.append(instance)

        @receiver(signals.pre_save, sender=Car, weak=False)
        def decorated_handler_with_sender_arg(signal, sender, instance, **kwargs):
            data.append(instance)

        try:
            c1 = Car.objects.create(make="Volkswagen", model="Passat")
            self.assertEqual(data, [c1, c1])
        finally:
            signals.pre_save.disconnect(decorated_handler)
            signals.pre_save.disconnect(decorated_handler_with_sender_arg, sender=Car)

    def test_save_and_delete_signals_with_m2m(self):
        data = []

        def pre_save_handler(signal, sender, instance, **kwargs):
            data.append("pre_save signal, %s" % instance)
            if kwargs.get("raw"):
                data.append("Is raw")

        def post_save_handler(signal, sender, instance, **kwargs):
            data.append("post_save signal, %s" % instance)
            if "created" in kwargs:
                if kwargs["created"]:
                    data.append("Is created")
                else:
                    data.append("Is updated")
            if kwargs.get("raw"):
                data.append("Is raw")

        def pre_delete_handler(signal, sender, instance, **kwargs):
            data.append("pre_delete signal, %s" % instance)
            data.append("instance.id is not None: %s" % (instance.id is not None))

        def post_delete_handler(signal, sender, instance, **kwargs):
            data.append("post_delete signal, %s" % instance)
            data.append("instance.id is not None: %s" % (instance.id is not None))

        signals.pre_save.connect(pre_save_handler, weak=False)
        signals.post_save.connect(post_save_handler, weak=False)
        signals.pre_delete.connect(pre_delete_handler, weak=False)
        signals.post_delete.connect(post_delete_handler, weak=False)
        try:
            a1 = Author.objects.create(name="Neal Stephenson")
            self.assertEqual(
                data,
                [
                    "pre_save signal, Neal Stephenson",
                    "post_save signal, Neal Stephenson",
                    "Is created",
                ],
            )
            data[:] = []

            b1 = Book.objects.create(name="Snow Crash")
            self.assertEqual(
                data,
                [
                    "pre_save signal, Snow Crash",
                    "post_save signal, Snow Crash",
                    "Is created",
                ],
            )
            data[:] = []

            # Assigning and removing to/from m2m shouldn't generate an m2m signal.
            b1.authors.set([a1])
            self.assertEqual(data, [])
            b1.authors.set([])
            self.assertEqual(data, [])
        finally:
            signals.pre_save.disconnect(pre_save_handler)
            signals.post_save.disconnect(post_save_handler)
            signals.pre_delete.disconnect(pre_delete_handler)
            signals.post_delete.disconnect(post_delete_handler)

    def test_disconnect_in_dispatch(self):
        """
        Signals that disconnect when being called don't mess future
        dispatching.
        """

        class Handler:
            def __init__(self, param):
                self.param = param
                self._run = False

            def __call__(self, signal, sender, **kwargs):
                self._run = True
                signal.disconnect(receiver=self, sender=sender)

        a, b = Handler(1), Handler(2)
        signals.post_save.connect(a, sender=Person, weak=False)
        signals.post_save.connect(b, sender=Person, weak=False)
        Person.objects.create(first_name="John", last_name="Smith")

        self.assertTrue(a._run)
        self.assertTrue(b._run)
        self.assertEqual(signals.post_save.receivers, [])

    @mock.patch("weakref.ref")
    def test_lazy_model_signal(self, ref):
        def callback(sender, args, **kwargs):
            pass

        signals.pre_init.connect(callback)
        signals.pre_init.disconnect(callback)
        self.assertTrue(ref.called)
        ref.reset_mock()

        signals.pre_init.connect(callback, weak=False)
        signals.pre_init.disconnect(callback)
        ref.assert_not_called()

    @isolate_apps("signals", kwarg_name="apps")
    def test_disconnect_model(self, apps):
        received = []

        def receiver(**kwargs):
            received.append(kwargs)

        class Created(models.Model):
            pass

        signals.post_init.connect(receiver, sender=Created, apps=apps)
        try:
            self.assertIs(
                signals.post_init.disconnect(receiver, sender=Created, apps=apps),
                True,
            )
            self.assertIs(
                signals.post_init.disconnect(receiver, sender=Created, apps=apps),
                False,
            )
            Created()
            self.assertEqual(received, [])
        finally:
            signals.post_init.disconnect(receiver, sender=Created)


class LazyModelRefTests(BaseSignalSetup, SimpleTestCase):
    def setUp(self):
        super().setUp()
        self.received = []

    def receiver(self, **kwargs):
        self.received.append(kwargs)

    def test_invalid_sender_model_name(self):
        msg = (
            "Invalid model reference 'invalid'. String model references must be of the "
            "form 'app_label.ModelName'."
        )
        with self.assertRaisesMessage(ValueError, msg):
            signals.post_init.connect(self.receiver, sender="invalid")

    def test_already_loaded_model(self):
        signals.post_init.connect(self.receiver, sender="signals.Book", weak=False)
        try:
            instance = Book()
            self.assertEqual(
                self.received,
                [{"signal": signals.post_init, "sender": Book, "instance": instance}],
            )
        finally:
            signals.post_init.disconnect(self.receiver, sender=Book)

    @isolate_apps("signals", kwarg_name="apps")
    def test_not_loaded_model(self, apps):
        signals.post_init.connect(
            self.receiver, sender="signals.Created", weak=False, apps=apps
        )

        try:

            class Created(models.Model):
                pass

            instance = Created()
            self.assertEqual(
                self.received,
                [
                    {
                        "signal": signals.post_init,
                        "sender": Created,
                        "instance": instance,
                    }
                ],
            )
        finally:
            signals.post_init.disconnect(self.receiver, sender=Created)

    @isolate_apps("signals", kwarg_name="apps")
    def test_disconnect_registered_model(self, apps):
        received = []

        def receiver(**kwargs):
            received.append(kwargs)

        class Created(models.Model):
            pass

        signals.post_init.connect(receiver, sender="signals.Created", apps=apps)
        try:
            self.assertIsNone(
                signals.post_init.disconnect(
                    receiver, sender="signals.Created", apps=apps
                )
            )
            self.assertIsNone(
                signals.post_init.disconnect(
                    receiver, sender="signals.Created", apps=apps
                )
            )
            Created()
            self.assertEqual(received, [])
        finally:
            signals.post_init.disconnect(receiver, sender="signals.Created")

    @isolate_apps("signals", kwarg_name="apps")
    def test_disconnect_unregistered_model(self, apps):
        received = []

        def receiver(**kwargs):
            received.append(kwargs)

        signals.post_init.connect(receiver, sender="signals.Created", apps=apps)
        try:
            self.assertIsNone(
                signals.post_init.disconnect(
                    receiver, sender="signals.Created", apps=apps
                )
            )
            self.assertIsNone(
                signals.post_init.disconnect(
                    receiver, sender="signals.Created", apps=apps
                )
            )

            class Created(models.Model):
                pass

            Created()
            self.assertEqual(received, [])
        finally:
            signals.post_init.disconnect(receiver, sender="signals.Created")

    def test_register_model_class_senders_immediately(self):
        """
        Model signals registered with model classes as senders don't use the
        Apps.lazy_model_operation() mechanism.
        """
        # Book isn't registered with apps2, so it will linger in
        # apps2._pending_operations if ModelSignal does the wrong thing.
        apps2 = Apps()
        signals.post_init.connect(self.receiver, sender=Book, apps=apps2)
        self.assertEqual(list(apps2._pending_operations), [])


class SyncHandler:
    param = 0

    def __call__(self, **kwargs):
        self.param += 1
        return self.param


class AsyncHandler:
    param = 0

    def __init__(self):
        markcoroutinefunction(self)

    async def __call__(self, **kwargs):
        self.param += 1
        return self.param


class AsyncReceiversTests(SimpleTestCase):
    async def test_asend(self):
        sync_handler = SyncHandler()
        async_handler = AsyncHandler()
        signal = dispatch.Signal()
        signal.connect(sync_handler)
        signal.connect(async_handler)
        result = await signal.asend(self.__class__)
        self.assertEqual(result, [(sync_handler, 1), (async_handler, 1)])

    def test_send(self):
        sync_handler = SyncHandler()
        async_handler = AsyncHandler()
        signal = dispatch.Signal()
        signal.connect(sync_handler)
        signal.connect(async_handler)
        result = signal.send(self.__class__)
        self.assertEqual(result, [(sync_handler, 1), (async_handler, 1)])

    def test_send_robust(self):
        class ReceiverException(Exception):
            pass

        receiver_exception = ReceiverException()

        async def failing_async_handler(**kwargs):
            raise receiver_exception

        sync_handler = SyncHandler()
        async_handler = AsyncHandler()
        signal = dispatch.Signal()
        signal.connect(failing_async_handler)
        signal.connect(async_handler)
        signal.connect(sync_handler)
        result = signal.send_robust(self.__class__)
        # The ordering here is different than the order that signals were
        # connected in.
        self.assertEqual(
            result,
            [
                (sync_handler, 1),
                (failing_async_handler, receiver_exception),
                (async_handler, 1),
            ],
        )

    async def test_asend_robust(self):
        class ReceiverException(Exception):
            pass

        receiver_exception = ReceiverException()

        async def failing_async_handler(**kwargs):
            raise receiver_exception

        sync_handler = SyncHandler()
        async_handler = AsyncHandler()
        signal = dispatch.Signal()
        signal.connect(failing_async_handler)
        signal.connect(async_handler)
        signal.connect(sync_handler)
        result = await signal.asend_robust(self.__class__)
        # The ordering here is different than the order that signals were
        # connected in.
        self.assertEqual(
            result,
            [
                (sync_handler, 1),
                (failing_async_handler, receiver_exception),
                (async_handler, 1),
            ],
        )

    async def test_asend_only_async_receivers(self):
        async_handler = AsyncHandler()
        signal = dispatch.Signal()
        signal.connect(async_handler)

        result = await signal.asend(self.__class__)
        self.assertEqual(result, [(async_handler, 1)])

    async def test_asend_robust_only_async_receivers(self):
        async_handler = AsyncHandler()
        signal = dispatch.Signal()
        signal.connect(async_handler)

        result = await signal.asend_robust(self.__class__)
        self.assertEqual(result, [(async_handler, 1)])
