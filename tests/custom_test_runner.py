from django.test.runner import DiscoverRunner
from django.test import TestCase
import ast
import astor
import inspect
import types
import textwrap
import inspect

def state_output():
  all_vars = globals() | locals()
  exclude_sections = ['In', 'Out', 'requests', 'json', 'os', 'subprocess', 'tempfile', 'shutil', 're', 'ast']

  user_defined_vars = {
    name: value for name, value in all_vars.items()
    if not name.startswith('_') and
      name not in dir(__builtins__) and
      not callable(value) and
      not isinstance(value, type) and
      name not in exclude_sections
  }

  for var_name, var_value in user_defined_vars.items():
    print(f"{var_name}: {var_value}")


class StateOutputInjector(ast.NodeTransformer):
    def generic_visit(self, node):
        if isinstance(node, ast.stmt) and not isinstance(node, ast.FunctionDef):
            return [node, ast.Expr(ast.Call(func=ast.Name(id='state_output', ctx=ast.Load()), args=[], keywords=[]))]
        return node

class ModifiedTestLoader(DiscoverRunner.test_loader.__class__):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.testNamePatterns = None

    def loadTestsFromTestCase(self, testCaseClass):
        for name, method in inspect.getmembers(testCaseClass, predicate=inspect.isfunction):
            if name.startswith('test_'):
                try:
                    modified_method = self.modify_test_method(method, testCaseClass)
                    setattr(testCaseClass, name, modified_method)
                    # print(f"Success for  {testCaseClass.__name__}.{name}")
                except OSError as e:
                    print(f"Warning: Skipping modification for {testCaseClass.__name__}.{name} - {e}")
        return super().loadTestsFromTestCase(testCaseClass)

    def modify_test_method(self, method, testCaseClass):
        try:
            source_lines, _ = inspect.getsourcelines(method)
            print(f"Could retrieve source for method {method.__name__}")
        except OSError as e:
            raise OSError(f"Could not retrieve source for method {method.__name__}: {e}")

        source = ''.join(source_lines)
        # Remove any excess indentation
        dedented_source = textwrap.dedent(source).lstrip()

        # Parse the AST from the dedented source
        try:
            tree = ast.parse(dedented_source)
        except IndentationError as e:
            print(f"IndentationError while parsing {method.__name__}: {e}")
            raise

        # Modify the AST as needed
        modified_tree = StateOutputInjector().visit(tree)
        modified_source = astor.to_source(modified_tree)

        # Get the method's original global environment
        method_globals = method.__globals__.copy()

        # Get the module where the function is defined, to access module-level symbols
        module = inspect.getmodule(method)
        if module:
            method_globals.update(module.__dict__)

        # Include class attributes in globals
        class_attrs = {
            k: v for k, v in vars(testCaseClass).items()
            if not k.startswith('__') and not inspect.isfunction(v)
        }
        method_globals.update(class_attrs)

        # print(f"module globals: {list(method_globals.keys())}")
        # print(f"calling scope globals: {list(globals().keys())}")

        # Create a new local namespace for executing the modified source
        local_ns = {}
        try:
            exec(modified_source, method_globals, local_ns)
        except NameError as e:
            print(f"NameError while executing modified source for {method.__name__}: {e}")
            raise

        # Ensure the modified function is created
        if method.__name__ not in local_ns:
            raise ValueError(f"Modified method {method.__name__} not found in local namespace.")

        return local_ns[method.__name__]


class CustomDiscoverRunner(DiscoverRunner):
    test_loader = ModifiedTestLoader()

    def run_tests(self, test_labels, extra_tests=None, **kwargs):
        #state_output()  # Initial state before running tests
        self.setup_test_environment()
        #state_output()  # State after test environment setup
        
        # Build the test suite
        suite = self.build_suite(test_labels)
        if extra_tests:
            for test in extra_tests:
                suite.addTest(test)
        
        #state_output()  # State after building the test suite
        databases = self.get_databases(suite)
        #state_output()  # State after getting databases
        results = super().run_tests(test_labels, extra_tests, **kwargs)
        #state_output()  # Final state after running all tests
        return results

    def build_suite(self, test_labels=None, extra_tests=None):
        suite = super().build_suite(test_labels)
        if extra_tests:
            for test in extra_tests:
                suite.addTest(test)
        return suite