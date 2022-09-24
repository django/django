from contextlib import contextmanager

from asgiref.local import Local


def _validate_new_strategy(strategy):
    if strategy not in (None, "peers", "never", "on_demand"):
        raise ValueError(f"{strategy} is not a valid fetch_missing_fields strategy")

    return strategy


class _FetchMissingFields:
    _local = Local()
    _default_strategies = ("peers", "peers")

    def set_default(self, strategy=None, /, related=None, deferred=None):
        if strategy and (related or deferred):
            raise TypeError(
                "Specify strategy via positional argument OR keyword argument."
            )

        if strategy == "never":
            raise ValueError(
                '"never" cannot be used as default fetch_missing_strategy.'
            )

        current_related, current_deferred = self._default_strategies
        self._default_strategies = (
            _validate_new_strategy(strategy or related) or current_related,
            _validate_new_strategy(strategy or deferred) or current_deferred,
        )

    @contextmanager
    def __call__(self, strategy=None, /, related=None, deferred=None):
        if strategy and (related or deferred):
            raise TypeError(
                "Specify strategy via positional argument OR keyword argument."
            )

        current_related, current_deferred = self._get_current_strategies()
        new_strategies = (
            _validate_new_strategy(related or strategy) or current_related,
            _validate_new_strategy(deferred or strategy) or current_deferred,
        )

        if not hasattr(self._local, "stack"):
            self._local.stack = []

        self._local.stack.append(new_strategies)

        try:
            yield
        finally:
            self._local.stack.pop()

    def get_current_related_strategy(self):
        return self._get_current_strategies()[0]

    def get_current_deferred_strategy(self):
        return self._get_current_strategies()[1]

    def _get_current_strategies(self):
        stack = getattr(self._local, "stack", [])

        if not stack:
            return self._default_strategies

        return stack[-1]


fetch_missing_fields = _FetchMissingFields()
