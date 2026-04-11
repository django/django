""" Module containing the RetryingClient wrapper class. """

from time import sleep


def _ensure_tuple_argument(argument_name, argument_value):
    """
    Helper function to ensure the given arguments are tuples of Exceptions (or
    subclasses), or can at least be converted to such.

    Args:
      argument_name: str, name of the argument we're checking, only used for
        raising meaningful exceptions.
      argument: any, the argument itself.

    Returns:
      tuple[Exception]: A tuple with the elements from the argument if they are
        valid.

    Exceptions:
      ValueError: If the argument was not None, tuple or Iterable.
      ValueError: If any of the elements of the argument is not a subclass of
        Exception.
    """

    # Ensure the argument is a tuple, set or list.
    if argument_value is None:
        return tuple()
    elif not isinstance(argument_value, (tuple, set, list)):
        raise ValueError("%s must be either a tuple, a set or a list." % argument_name)

    # Convert the argument before checking contents.
    argument_tuple = tuple(argument_value)

    # Check that all the elements are actually inherited from Exception.
    # (Catchable)
    if not all([issubclass(arg, Exception) for arg in argument_tuple]):
        raise ValueError(
            "%s is only allowed to contain elements that are subclasses of "
            "Exception." % argument_name
        )

    return argument_tuple


class RetryingClient(object):
    """
    Client that allows retrying calls for the other clients.
    """

    def __init__(
        self, client, attempts=2, retry_delay=0, retry_for=None, do_not_retry_for=None
    ):
        """
        Constructor for RetryingClient.

        Args:
          client: Client|PooledClient|HashClient, inner client to use for
            performing actual work.
          attempts: optional int, how many times to attempt an action before
            failing. Must be 1 or above. Defaults to 2.
          retry_delay: optional int|float, how many seconds to sleep between
            each attempt.
            Defaults to 0.

          retry_for: optional None|tuple|set|list, what exceptions to
            allow retries for. Will allow retries for all exceptions if None.
            Example:
                `(MemcacheClientError, MemcacheUnexpectedCloseError)`
            Accepts any class that is a subclass of Exception.
            Defaults to None.

          do_not_retry_for: optional None|tuple|set|list, what
            exceptions should be retried. Will not block retries for any
            Exception if None.
            Example:
                `(IOError, MemcacheIllegalInputError)`
            Accepts any class that is a subclass of Exception.
            Defaults to None.

        Exceptions:
          ValueError: If `attempts` is not 1 or above.
          ValueError: If `retry_for` or `do_not_retry_for` is not None, tuple or
            Iterable.
          ValueError: If any of the elements of `retry_for` or
            `do_not_retry_for` is not a subclass of Exception.
          ValueError: If there is any overlap between `retry_for` and
            `do_not_retry_for`.
        """

        if attempts < 1:
            raise ValueError(
                "`attempts` argument must be at least 1. "
                "Otherwise no attempts are made."
            )

        self._client = client
        self._attempts = attempts
        self._retry_delay = retry_delay
        self._retry_for = _ensure_tuple_argument("retry_for", retry_for)
        self._do_not_retry_for = _ensure_tuple_argument(
            "do_not_retry_for", do_not_retry_for
        )

        # Verify no overlap in the go/no-go exception collections.
        for exc_class in self._retry_for:
            if exc_class in self._do_not_retry_for:
                raise ValueError(
                    'Exception class "%s" was present in both `retry_for` '
                    "and `do_not_retry_for`. Any exception class is only "
                    "allowed in a single argument." % repr(exc_class)
                )

        # Take dir from the client to speed up future checks.
        self._client_dir = dir(self._client)

    def _retry(self, name, func, *args, **kwargs):
        """
        Workhorse function, handles retry logic.

        Args:
          name: str, Name of the function called.
          func: callable, the function to retry.
          *args: args, array arguments to pass to the function.
          **kwargs: kwargs, keyword arguments to pass to the function.
        """
        for attempt in range(self._attempts):
            try:
                result = func(*args, **kwargs)
                return result

            except Exception as exc:
                # Raise the exception to caller if either is met:
                # - We've used the last attempt.
                # - self._retry_for is set, and we do not match.
                # - self._do_not_retry_for is set, and we do match.
                # - name is not actually a member of the client class.
                if (
                    attempt >= self._attempts - 1
                    or (self._retry_for and not isinstance(exc, self._retry_for))
                    or (
                        self._do_not_retry_for
                        and isinstance(exc, self._do_not_retry_for)
                    )
                    or name not in self._client_dir
                ):
                    raise exc

                # Sleep and try again.
                sleep(self._retry_delay)

    # This is the real magic soup of the class, we catch anything that isn't
    # strictly defined for ourselves and pass it on to whatever client we've
    # been given.
    def __getattr__(self, name):

        return lambda *args, **kwargs: self._retry(
            name, self._client.__getattribute__(name), *args, **kwargs
        )

    # We implement these explicitly because they're "magic" functions and won't
    # get passed on by __getattr__.

    def __dir__(self):
        return self._client_dir

    # These magics are copied from the base client.
    def __setitem__(self, key, value):
        self.set(key, value, noreply=True)

    def __getitem__(self, key):
        value = self.get(key)
        if value is None:
            raise KeyError
        return value

    def __delitem__(self, key):
        self.delete(key, noreply=True)
