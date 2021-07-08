from django.db import connection, models
from django.test import SimpleTestCase

from .utils import FuncTestMixin


def test_mutation(raises=True):
    def wrapper(mutation_func):
        def test(test_case_instance, *args, **kwargs):
            class TestFunc(models.Func):
                output_field = models.IntegerField()

                def __init__(self):
                    self.attribute = 'initial'
                    super().__init__('initial', ['initial'])

                def as_sql(self, *args, **kwargs):
                    mutation_func(self)
                    return '', ()

            if raises:
                msg = 'TestFunc Func was mutated during compilation.'
                with test_case_instance.assertRaisesMessage(AssertionError, msg):
                    getattr(TestFunc(), 'as_' + connection.vendor)(None, None)
            else:
                getattr(TestFunc(), 'as_' + connection.vendor)(None, None)

        return test
    return wrapper


class FuncTestMixinTests(FuncTestMixin, SimpleTestCase):
    @test_mutation()
    def test_mutated_attribute(func):
        func.attribute = 'mutated'

    @test_mutation()
    def test_mutated_expressions(func):
        func.source_expressions.clear()

    @test_mutation()
    def test_mutated_expression(func):
        func.source_expressions[0].name = 'mutated'

    @test_mutation()
    def test_mutated_expression_deep(func):
        func.source_expressions[1].value[0] = 'mutated'

    @test_mutation(raises=False)
    def test_not_mutated(func):
        pass
