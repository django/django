from django.test import TestCase

from django.utils.observables import (
    ChangeNotifier, ChangeRecord, Observable
)


class Observer(object):
    def __init__(self):
        self.changes = list()

    def handle_changes(self, change_records):
        self.changes.extend(change_records)


class MockObservable(Observable):
    pass


class TestChangeNotifier(TestCase):
    def setUp(self):
        self.observer_one = Observer()
        self.observer_two = Observer()
        self.observable = MockObservable()

    def _emit_record(self, notifier):
        record = ChangeRecord('key', self.observable, 'key')
        notifier.deliver(record)
        return record

    def test_no_observers(self):
        with ChangeNotifier(self.observable) as notifier:
            self._emit_record(notifier)

        self.assertEqual(self.observer_one.changes, [])
        self.assertEqual(self.observer_two.changes, [])

    def test_single_observer(self):
        self.observable.add_observer(self.observer_one)
        with ChangeNotifier(self.observable) as notifier:
            record = self._emit_record(notifier)
            # Should not deliver changes until context has exited
            self.assertEqual(self.observer_one.changes, [])

        self.assertEqual(self.observer_one.changes, [record, ])
        self.assertEqual(self.observer_two.changes, [])

    def test_multiple_observers(self):
        self.observable.add_observer(self.observer_one)
        self.observable.add_observer(self.observer_two)

        with ChangeNotifier(self.observable) as notifier:
            record = self._emit_record(notifier)

        self.assertEqual(self.observer_one.changes, [record, ])
        self.assertEqual(self.observer_two.changes, [record, ])

    def test_exception_handling(self):
        self.observable.add_observer(self.observer_one)
        cn = ChangeNotifier(self.observable)
        try:
            with cn as notifier:
                self._emit_record(notifier)
                raise NotImplementedError()
        except NotImplementedError:
            # Changes should not have been delivered
            self.assertEqual(self.observer_one.changes, [])
        else:
            self.fail('Exception not passed out of context')

        # Can reuse a notifier
        with cn as notifier:
            record = self._emit_record(notifier)

        self.assertEqual(self.observer_one.changes, [record, ])

    def test_no_context(self):
        self.observable.add_observer(self.observer_one)
        notifier = ChangeNotifier(self.observable)
        record = self._emit_record(notifier)

        self.assertEqual(self.observer_one.changes, [record, ])
