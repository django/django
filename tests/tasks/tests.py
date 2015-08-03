import unittest

from django.tasks import (
    Task, backends, base, constants, get_backend, registry, task,
)
from django.test import SimpleTestCase, override_settings


def dummy_task(*args, **kwargs):
    return args, kwargs


class DummierTask(object):
    def __call__(self, *args, **kwargs):
        return args, kwargs


dummier_task = DummierTask()


@override_settings(
    TASKS={
        'default': {'BACKEND': 'django.tasks.backends.DummyTaskBackend'},
    }
)
class TestDummyBackend(SimpleTestCase):
    def tearDown(self):
        super(TestDummyBackend, self).tearDown()
        # clear backends cache
        base.backends.clear()

    def test_backends_are_cached(self):
        backend = get_backend()
        backend2 = get_backend()

        self.assertIs(backend, backend2)

    def test_delay_runs_and_returns_result_with_status_and_result(self):
        t = Task(dummy_task)
        o = object()
        r = t.delay(1, o, 'xyz', a=42)

        self.assertIsInstance(r, backends.DummyTaskResult)
        self.assertEquals(constants.SUCCESS, r.get_status())
        self.assertEquals(((1, o, 'xyz'), {'a': 42}), r.get_result())

    def test_failing_task_reports_failure_and_returns_exception(self):
        e = KeyError('Nope!')

        def t():
            raise e

        t = Task(t)
        r = t.delay()

        self.assertIsInstance(r, backends.DummyTaskResult)
        self.assertEquals(constants.FAILED, r.get_status())
        self.assertIs(e, r.get_result())


class TestTaskDecorator(unittest.TestCase):
    def tearDown(self):
        super(TestTaskDecorator, self).tearDown()
        registry._registry.clear()

    def test_decorating_a_task_will_extract_the_func(self):
        t = task(dummy_task)
        t2 = task(t, name='dummy_task_2')

        self.assertIs(t2.run, dummy_task)

    def test_decorator_works_without_arguments(self):
        t = task()(dummy_task)

        self.assertIsInstance(t, Task)
        self.assertIs(t.run, dummy_task)
        self.assertEqual('tasks.tests.dummy_task', t.name)

    def test_decorator_works_on_its_own(self):
        t = task(dummy_task)

        self.assertIsInstance(t, Task)
        self.assertIs(t.run, dummy_task)
        self.assertEqual('tasks.tests.dummy_task', t.name)

    def test_decortor_can_accept_name(self):
        t = task('testing')(dummy_task)

        self.assertIsInstance(t, Task)
        self.assertIs(t.run, dummy_task)
        self.assertEqual('testing', t.name)

    def test_decorator_works_with_callables(self):
        t = task(dummier_task)

        self.assertIsInstance(t, Task)
        self.assertIs(t.run, dummier_task)
        self.assertEqual('tasks.tests.DummierTask', t.name)

    def test_decorator_registers_the_task(self):
        t = task(dummy_task, name='some_name')

        self.assertIn('some_name', registry._registry)
        self.assertIs(t, registry._registry['some_name'])

    def test_decorated_task_can_be_invoked_by_name(self):
        task(dummy_task, name='some_name')

        tr = registry.delay_by_name('some_name', 1, 2, 3, answer=42)
        self.assertIsInstance(tr, backends.DummyTaskResult)
        self.assertEquals(constants.SUCCESS, tr.get_status())
        self.assertEquals(((1, 2, 3), {'answer': 42}), tr.get_result())


class TestTask(unittest.TestCase):
    def test_configure_clones_and_updates_alias_and_options(self):
        t = Task(lambda: 'XYZ', using='default', options={'priority': 1})
        t2 = t.clone(using='special', priority=3)

        self.assertEqual('default', t.alias)
        self.assertEqual({'priority': 1}, t.options)

        self.assertEqual('special', t2.alias)
        self.assertEqual({'priority': 3}, t2.options)

    def test_task_works_as_original_callable(self):
        o = object()

        def f():
            return o

        t = Task(f)
        self.assertIs(o, t())

    def test_all_args_and_kwargs_are_passed(self):
        t = Task(dummy_task)
        self.assertEqual(
            ((1, 2, 42), {'answer': 42, 'question': None}),
            t(1, 2, 42, answer=42, question=None)
        )
