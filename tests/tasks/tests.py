import unittest

from django.tasks import registry, task, Task

def dummy_task(*args, **kwargs):
    return args, kwargs

class DummierTask(object):
    def __call__(self, *args, **kwargs):
        return args, kwargs

dummier_task = DummierTask()

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


