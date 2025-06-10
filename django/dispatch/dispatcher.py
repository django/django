import asyncio
import logging
import threading
import weakref

from asgiref.sync import async_to_sync, iscoroutinefunction, sync_to_async

from django.utils.inspect import func_accepts_kwargs

logger = logging.getLogger("django.dispatch")


def _make_id(target):
    if hasattr(target, "__func__"):
        return (id(target.__self__), id(target.__func__))
    return id(target)


NONE_ID = _make_id(None)

# A marker for caching
NO_RECEIVERS = object()


class Signal:
    """
    Base class for all signals

    Internal attributes:

        receivers:
            [((id(receiver), id(sender)), ref(receiver), ref(sender), is_async)]
        sender_receivers_cache:
            WeakKeyDictionary[sender, list[receiver]]
    """

    def __init__(self, use_caching=False):
        """
        Create a new signal.
        """
        self.receivers = []
        self.lock = threading.Lock()
        self.use_caching = use_caching
        # For convenience we create empty caches even if they are not used.
        # A note about caching: if use_caching is defined, then for each
        # distinct sender we cache the receivers that sender has in
        # 'sender_receivers_cache'. The cache is cleaned when .connect() or
        # .disconnect() is called and populated on send().
        self.sender_receivers_cache = weakref.WeakKeyDictionary() if use_caching else {}
        self._dead_receivers = False

    def connect(self, receiver, sender=None, weak=True, dispatch_uid=None):
        """
        Connect receiver to sender for signal.

        Arguments:

            receiver
                A function or an instance method which is to receive signals.
                Receivers must be hashable objects. Receivers can be
                asynchronous.

                If weak is True, then receiver must be weak referenceable.

                Receivers must be able to accept keyword arguments.

                If a receiver is connected with a dispatch_uid argument, it
                will not be added if another receiver was already connected
                with that dispatch_uid.

            sender
                The sender to which the receiver should respond. Must either be
                a Python object, or None to receive events from any sender.

            weak
                Whether to use weak references to the receiver. By default, the
                module will attempt to use weak references to the receiver
                objects. If this parameter is false, then strong references will
                be used.

            dispatch_uid
                An identifier used to uniquely identify a particular instance of
                a receiver. This will usually be a string, though it may be
                anything hashable.
        """
        from django.conf import settings

        # If DEBUG is on, check that we got a good receiver
        if settings.configured and settings.DEBUG:
            if not callable(receiver):
                raise TypeError("Signal receivers must be callable.")
            # Check for **kwargs
            if not func_accepts_kwargs(receiver):
                raise ValueError(
                    "Signal receivers must accept keyword arguments (**kwargs)."
                )

        if dispatch_uid:
            lookup_key = (dispatch_uid, _make_id(sender))
        else:
            lookup_key = (_make_id(receiver), _make_id(sender))

        is_async = iscoroutinefunction(receiver)

        if weak:
            ref = weakref.ref
            receiver_object = receiver
            # Check for bound methods
            if hasattr(receiver, "__self__") and hasattr(receiver, "__func__"):
                ref = weakref.WeakMethod
                receiver_object = receiver.__self__
            receiver = ref(receiver)
            weakref.finalize(receiver_object, self._flag_dead_receivers)

        # Keep a weakref to sender if possible to ensure associated receivers
        # are cleared if it gets garbage collected. This ensures there is no
        # id(sender) collisions for distinct senders with non-overlapping
        # lifetimes.
        sender_ref = None
        if sender is not None:
            try:
                sender_ref = weakref.ref(sender, self._flag_dead_receivers)
            except TypeError:
                pass

        with self.lock:
            self._clear_dead_receivers()
            if not any(r_key == lookup_key for r_key, _, _, _ in self.receivers):
                self.receivers.append((lookup_key, receiver, sender_ref, is_async))
            self.sender_receivers_cache.clear()

    def disconnect(self, receiver=None, sender=None, dispatch_uid=None):
        """
        Disconnect receiver from sender for signal.

        If weak references are used, disconnect need not be called. The receiver
        will be removed from dispatch automatically.

        Arguments:

            receiver
                The registered receiver to disconnect. May be none if
                dispatch_uid is specified.

            sender
                The registered sender to disconnect

            dispatch_uid
                the unique identifier of the receiver to disconnect
        """
        if dispatch_uid:
            lookup_key = (dispatch_uid, _make_id(sender))
        else:
            lookup_key = (_make_id(receiver), _make_id(sender))

        disconnected = False
        with self.lock:
            self._clear_dead_receivers()
            for index in range(len(self.receivers)):
                r_key, *_ = self.receivers[index]
                if r_key == lookup_key:
                    disconnected = True
                    del self.receivers[index]
                    break
            self.sender_receivers_cache.clear()
        return disconnected

    def has_listeners(self, sender=None):
        sync_receivers, async_receivers = self._live_receivers(sender)
        return bool(sync_receivers) or bool(async_receivers)

    def send(self, sender, **named):
        """
        Send signal from sender to all connected receivers.

        If any receiver raises an error, the error propagates back through send,
        terminating the dispatch loop. So it's possible that all receivers
        won't be called if an error is raised.

        If any receivers are asynchronous, they are called after all the
        synchronous receivers via a single call to async_to_sync(). They are
        also executed concurrently with asyncio.gather().

        Arguments:

            sender
                The sender of the signal. Either a specific object or None.

            named
                Named arguments which will be passed to receivers.

        Return a list of tuple pairs [(receiver, response), ... ].
        """
        if (
            not self.receivers
            or self.sender_receivers_cache.get(sender) is NO_RECEIVERS
        ):
            return []
        responses = []
        sync_receivers, async_receivers = self._live_receivers(sender)
        for receiver in sync_receivers:
            response = receiver(signal=self, sender=sender, **named)
            responses.append((receiver, response))
        if async_receivers:

            async def asend():
                async_responses = await asyncio.gather(
                    *(
                        receiver(signal=self, sender=sender, **named)
                        for receiver in async_receivers
                    )
                )
                return zip(async_receivers, async_responses)

            responses.extend(async_to_sync(asend)())
        return responses

    async def asend(self, sender, **named):
        """
        Send signal from sender to all connected receivers in async mode.

        All sync receivers will be wrapped by sync_to_async()
        If any receiver raises an error, the error propagates back through
        send, terminating the dispatch loop. So it's possible that all
        receivers won't be called if an error is raised.

        If any receivers are synchronous, they are grouped and called behind a
        sync_to_async() adaption before executing any asynchronous receivers.

        If any receivers are asynchronous, they are grouped and executed
        concurrently with asyncio.gather().

        Arguments:

            sender
                The sender of the signal. Either a specific object or None.

            named
                Named arguments which will be passed to receivers.

        Return a list of tuple pairs [(receiver, response), ...].
        """
        if (
            not self.receivers
            or self.sender_receivers_cache.get(sender) is NO_RECEIVERS
        ):
            return []
        sync_receivers, async_receivers = self._live_receivers(sender)
        if sync_receivers:

            @sync_to_async
            def sync_send():
                responses = []
                for receiver in sync_receivers:
                    response = receiver(signal=self, sender=sender, **named)
                    responses.append((receiver, response))
                return responses

        else:

            async def sync_send():
                return []

        responses, async_responses = await asyncio.gather(
            sync_send(),
            asyncio.gather(
                *(
                    receiver(signal=self, sender=sender, **named)
                    for receiver in async_receivers
                )
            ),
        )
        responses.extend(zip(async_receivers, async_responses))
        return responses

    def _log_robust_failure(self, receiver, err):
        logger.error(
            "Error calling %s in Signal.send_robust() (%s)",
            receiver.__qualname__,
            err,
            exc_info=err,
        )

    def send_robust(self, sender, **named):
        """
        Send signal from sender to all connected receivers catching errors.

        If any receivers are asynchronous, they are called after all the
        synchronous receivers via a single call to async_to_sync(). They are
        also executed concurrently with asyncio.gather().

        Arguments:

            sender
                The sender of the signal. Can be any Python object (normally one
                registered with a connect if you actually want something to
                occur).

            named
                Named arguments which will be passed to receivers.

        Return a list of tuple pairs [(receiver, response), ... ].

        If any receiver raises an error (specifically any subclass of
        Exception), return the error instance as the result for that receiver.
        """
        if (
            not self.receivers
            or self.sender_receivers_cache.get(sender) is NO_RECEIVERS
        ):
            return []

        # Call each receiver with whatever arguments it can accept.
        # Return a list of tuple pairs [(receiver, response), ... ].
        responses = []
        sync_receivers, async_receivers = self._live_receivers(sender)
        for receiver in sync_receivers:
            try:
                response = receiver(signal=self, sender=sender, **named)
            except Exception as err:
                self._log_robust_failure(receiver, err)
                responses.append((receiver, err))
            else:
                responses.append((receiver, response))
        if async_receivers:

            async def asend_and_wrap_exception(receiver):
                try:
                    response = await receiver(signal=self, sender=sender, **named)
                except Exception as err:
                    self._log_robust_failure(receiver, err)
                    return err
                return response

            async def asend():
                async_responses = await asyncio.gather(
                    *(
                        asend_and_wrap_exception(receiver)
                        for receiver in async_receivers
                    )
                )
                return zip(async_receivers, async_responses)

            responses.extend(async_to_sync(asend)())
        return responses

    async def asend_robust(self, sender, **named):
        """
        Send signal from sender to all connected receivers catching errors.

        If any receivers are synchronous, they are grouped and called behind a
        sync_to_async() adaption before executing any asynchronous receivers.

        If any receivers are asynchronous, they are grouped and executed
        concurrently with asyncio.gather.

        Arguments:

            sender
                The sender of the signal. Can be any Python object (normally one
                registered with a connect if you actually want something to
                occur).

            named
                Named arguments which will be passed to receivers.

        Return a list of tuple pairs [(receiver, response), ... ].

        If any receiver raises an error (specifically any subclass of
        Exception), return the error instance as the result for that receiver.
        """
        if (
            not self.receivers
            or self.sender_receivers_cache.get(sender) is NO_RECEIVERS
        ):
            return []

        # Call each receiver with whatever arguments it can accept.
        # Return a list of tuple pairs [(receiver, response), ... ].
        sync_receivers, async_receivers = self._live_receivers(sender)

        if sync_receivers:

            @sync_to_async
            def sync_send():
                responses = []
                for receiver in sync_receivers:
                    try:
                        response = receiver(signal=self, sender=sender, **named)
                    except Exception as err:
                        self._log_robust_failure(receiver, err)
                        responses.append((receiver, err))
                    else:
                        responses.append((receiver, response))
                return responses

        else:

            async def sync_send():
                return []

        async def asend_and_wrap_exception(receiver):
            try:
                response = await receiver(signal=self, sender=sender, **named)
            except Exception as err:
                self._log_robust_failure(receiver, err)
                return err
            return response

        responses, async_responses = await asyncio.gather(
            sync_send(),
            asyncio.gather(
                *(asend_and_wrap_exception(receiver) for receiver in async_receivers),
            ),
        )
        responses.extend(zip(async_receivers, async_responses))
        return responses

    def _clear_dead_receivers(self):
        # Note: caller is assumed to hold self.lock.
        if self._dead_receivers:
            self._dead_receivers = False
            self.receivers = [
                r
                for r in self.receivers
                if (
                    not (isinstance(r[1], weakref.ReferenceType) and r[1]() is None)
                    and not (r[2] is not None and r[2]() is None)
                )
            ]

    def _live_receivers(self, sender):
        """
        Filter sequence of receivers to get resolved, live receivers.

        This checks for weak references and resolves them, then returning only
        live receivers.
        """
        receivers = None
        if self.use_caching and not self._dead_receivers:
            receivers = self.sender_receivers_cache.get(sender)
            # We could end up here with NO_RECEIVERS even if we do check this case in
            # .send() prior to calling _live_receivers() due to concurrent .send() call.
            if receivers is NO_RECEIVERS:
                return [], []
        if receivers is None:
            with self.lock:
                self._clear_dead_receivers()
                senderkey = _make_id(sender)
                receivers = []
                for (
                    (_receiverkey, r_senderkey),
                    receiver,
                    sender_ref,
                    is_async,
                ) in self.receivers:
                    if r_senderkey == NONE_ID or r_senderkey == senderkey:
                        receivers.append((receiver, sender_ref, is_async))
                if self.use_caching:
                    if not receivers:
                        self.sender_receivers_cache[sender] = NO_RECEIVERS
                    else:
                        # Note, we must cache the weakref versions.
                        self.sender_receivers_cache[sender] = receivers
        non_weak_sync_receivers = []
        non_weak_async_receivers = []
        for receiver, sender_ref, is_async in receivers:
            # Skip if the receiver/sender is a dead weakref
            if isinstance(receiver, weakref.ReferenceType):
                receiver = receiver()
                if receiver is None:
                    continue
            if sender_ref is not None and sender_ref() is None:
                continue
            if is_async:
                non_weak_async_receivers.append(receiver)
            else:
                non_weak_sync_receivers.append(receiver)
        return non_weak_sync_receivers, non_weak_async_receivers

    def _flag_dead_receivers(self, reference=None):
        # Mark that the self.receivers list has dead weakrefs. If so, we will
        # clean those up in connect, disconnect and _live_receivers while
        # holding self.lock. Note that doing the cleanup here isn't a good
        # idea, _flag_dead_receivers() will be called as side effect of garbage
        # collection, and so the call can happen while we are already holding
        # self.lock.
        self._dead_receivers = True


def receiver(signal, **kwargs):
    """
    A decorator for connecting receivers to signals. Used by passing in the
    signal (or list of signals) and keyword arguments to connect::

        @receiver(post_save, sender=MyModel)
        def signal_receiver(sender, **kwargs):
            ...

        @receiver([post_save, post_delete], sender=MyModel)
        def signals_receiver(sender, **kwargs):
            ...
    """

    def _decorator(func):
        if isinstance(signal, (list, tuple)):
            for s in signal:
                s.connect(func, **kwargs)
        else:
            signal.connect(func, **kwargs)
        return func

    return _decorator
