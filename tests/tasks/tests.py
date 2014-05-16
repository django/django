import unittest

from django.test import override_settings, SimpleTestCase
from django.tasks import registry, task, Task, backends

def dummy_task(*args, **kwargs):
    return args, kwargs

class DummierTask(object):
    def __call__(self, *args, **kwargs):
        return args, kwargs

dummier_task = DummierTask()

@override_settings(
    QUEUES = {
        'default': {'BACKEND': 'django.tasks.backends.DummyTaskBackend'},
    }
)
class TestDummyBackend(SimpleTestCase):
    def test_delay_runs_and_returns_result_with_status_and_result(self):
        t = Task(dummy_task)
        o = object()
        r = t.delay(1, o, 'xyz', a=42)

        self.assertIsInstance(r, backends.DummyTaskResult)
        self.assertEquals(backends.SUCCESS, r.status())
        self.assertEquals(((1, o, 'xyz'), {'a': 42}), r.get_result())

    def test_failing_task_reports_failure_and_returns_exception(self):
        e = KeyError('Nope!')
        def t():
            raise e
        t = Task(t)
        r = t.delay()

        self.assertIsInstance(r, backends.DummyTaskResult)
        self.assertEquals(backends.FAILED, r.status())
        self.assertIs(e, r.get_result())


class TestTaskDecorator(unittest.TestCase):
    def tearDown(self):
        super(TestTaskDecorator, self).tearDown()
        registry._registry.clear()

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

class TestTask(unittest.TestCase):
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
