"""
Tests for behaviour related to type annotations.
"""

from sys import version_info

from pyflakes import messages as m
from pyflakes.test.harness import TestCase, skipIf


class TestTypeAnnotations(TestCase):

    def test_typingOverload(self):
        """Allow intentional redefinitions via @typing.overload"""
        self.flakes("""
        import typing
        from typing import overload

        @overload
        def f(s: None) -> None:
            pass

        @overload
        def f(s: int) -> int:
            pass

        def f(s):
            return s

        @typing.overload
        def g(s: None) -> None:
            pass

        @typing.overload
        def g(s: int) -> int:
            pass

        def g(s):
            return s
        """)

    def test_typingExtensionsOverload(self):
        """Allow intentional redefinitions via @typing_extensions.overload"""
        self.flakes("""
        import typing_extensions
        from typing_extensions import overload

        @overload
        def f(s: None) -> None:
            pass

        @overload
        def f(s: int) -> int:
            pass

        def f(s):
            return s

        @typing_extensions.overload
        def g(s: None) -> None:
            pass

        @typing_extensions.overload
        def g(s: int) -> int:
            pass

        def g(s):
            return s
        """)

    def test_typingOverloadAsync(self):
        """Allow intentional redefinitions via @typing.overload (async)"""
        self.flakes("""
        from typing import overload

        @overload
        async def f(s: None) -> None:
            pass

        @overload
        async def f(s: int) -> int:
            pass

        async def f(s):
            return s
        """)

    def test_overload_with_multiple_decorators(self):
        self.flakes("""
            from typing import overload
            dec = lambda f: f

            @dec
            @overload
            def f(x: int) -> int:
                pass

            @dec
            @overload
            def f(x: str) -> str:
                pass

            @dec
            def f(x): return x
       """)

    def test_overload_in_class(self):
        self.flakes("""
        from typing import overload

        class C:
            @overload
            def f(self, x: int) -> int:
                pass

            @overload
            def f(self, x: str) -> str:
                pass

            def f(self, x): return x
        """)

    def test_aliased_import(self):
        """Detect when typing is imported as another name"""
        self.flakes("""
        import typing as t

        @t.overload
        def f(s: None) -> None:
            pass

        @t.overload
        def f(s: int) -> int:
            pass

        def f(s):
            return s
        """)

    def test_not_a_typing_overload(self):
        """regression test for @typing.overload detection bug in 2.1.0"""
        self.flakes("""
            def foo(x):
                return x

            @foo
            def bar():
                pass

            def bar():
                pass
        """, m.RedefinedWhileUnused)

    def test_variable_annotations(self):
        self.flakes('''
        name: str
        age: int
        ''')
        self.flakes('''
        name: str = 'Bob'
        age: int = 18
        ''')
        self.flakes('''
        class C:
            name: str
            age: int
        ''')
        self.flakes('''
        class C:
            name: str = 'Bob'
            age: int = 18
        ''')
        self.flakes('''
        def f():
            name: str
            age: int
        ''', m.UnusedAnnotation, m.UnusedAnnotation)
        self.flakes('''
        def f():
            name: str = 'Bob'
            age: int = 18
            foo: not_a_real_type = None
        ''', m.UnusedVariable, m.UnusedVariable, m.UnusedVariable, m.UndefinedName)
        self.flakes('''
        def f():
            name: str
            print(name)
        ''', m.UndefinedName)
        self.flakes('''
        from typing import Any
        def f():
            a: Any
        ''', m.UnusedAnnotation)
        self.flakes('''
        foo: not_a_real_type
        ''', m.UndefinedName)
        self.flakes('''
        foo: not_a_real_type = None
        ''', m.UndefinedName)
        self.flakes('''
        class C:
            foo: not_a_real_type
        ''', m.UndefinedName)
        self.flakes('''
        class C:
            foo: not_a_real_type = None
        ''', m.UndefinedName)
        self.flakes('''
        def f():
            class C:
                foo: not_a_real_type
        ''', m.UndefinedName)
        self.flakes('''
        def f():
            class C:
                foo: not_a_real_type = None
        ''', m.UndefinedName)
        self.flakes('''
        from foo import Bar
        bar: Bar
        ''')
        self.flakes('''
        from foo import Bar
        bar: 'Bar'
        ''')
        self.flakes('''
        import foo
        bar: foo.Bar
        ''')
        self.flakes('''
        import foo
        bar: 'foo.Bar'
        ''')
        self.flakes('''
        from foo import Bar
        def f(bar: Bar): pass
        ''')
        self.flakes('''
        from foo import Bar
        def f(bar: 'Bar'): pass
        ''')
        self.flakes('''
        from foo import Bar
        def f(bar) -> Bar: return bar
        ''')
        self.flakes('''
        from foo import Bar
        def f(bar) -> 'Bar': return bar
        ''')
        self.flakes('''
        bar: 'Bar'
        ''', m.UndefinedName)
        self.flakes('''
        bar: 'foo.Bar'
        ''', m.UndefinedName)
        self.flakes('''
        from foo import Bar
        bar: str
        ''', m.UnusedImport)
        self.flakes('''
        from foo import Bar
        def f(bar: str): pass
        ''', m.UnusedImport)
        self.flakes('''
        def f(a: A) -> A: pass
        class A: pass
        ''', m.UndefinedName, m.UndefinedName)
        self.flakes('''
        def f(a: 'A') -> 'A': return a
        class A: pass
        ''')
        self.flakes('''
        a: A
        class A: pass
        ''', m.UndefinedName)
        self.flakes('''
        a: 'A'
        class A: pass
        ''')
        self.flakes('''
        T: object
        def f(t: T): pass
        ''', m.UndefinedName)
        self.flakes('''
        T: object
        def g(t: 'T'): pass
        ''')
        self.flakes('''
        a: 'A B'
        ''', m.ForwardAnnotationSyntaxError)
        self.flakes('''
        a: 'A; B'
        ''', m.ForwardAnnotationSyntaxError)
        self.flakes('''
        a: '1 + 2'
        ''')
        self.flakes('''
        a: 'a: "A"'
        ''', m.ForwardAnnotationSyntaxError)

    def test_variable_annotation_references_self_name_undefined(self):
        self.flakes("""
        x: int = x
        """, m.UndefinedName)

    def test_TypeAlias_annotations(self):
        self.flakes("""
        from typing_extensions import TypeAlias
        from foo import Bar

        bar: TypeAlias = Bar
        """)
        self.flakes("""
        from typing_extensions import TypeAlias
        from foo import Bar

        bar: TypeAlias = 'Bar'
        """)
        self.flakes("""
        from typing_extensions import TypeAlias
        from foo import Bar

        class A:
            bar: TypeAlias = Bar
        """)
        self.flakes("""
        from typing_extensions import TypeAlias
        from foo import Bar

        class A:
            bar: TypeAlias = 'Bar'
        """)
        self.flakes("""
        from typing_extensions import TypeAlias

        bar: TypeAlias
        """)
        self.flakes("""
        from typing_extensions import TypeAlias
        from foo import Bar

        bar: TypeAlias
        """, m.UnusedImport)

    def test_annotating_an_import(self):
        self.flakes('''
            from a import b, c
            b: c
            print(b)
        ''')

    def test_unused_annotation(self):
        # Unused annotations are fine in module and class scope
        self.flakes('''
        x: int
        class Cls:
            y: int
        ''')
        self.flakes('''
        def f():
            x: int
        ''', m.UnusedAnnotation)
        # This should only print one UnusedVariable message
        self.flakes('''
        def f():
            x: int
            x = 3
        ''', m.UnusedVariable)

    def test_unused_annotation_in_outer_scope_reassigned_in_local_scope(self):
        self.flakes('''
        x: int
        x.__dict__
        def f(): x = 1
        ''', m.UndefinedName, m.UnusedVariable)

    def test_unassigned_annotation_is_undefined(self):
        self.flakes('''
        name: str
        print(name)
        ''', m.UndefinedName)

    def test_annotated_async_def(self):
        self.flakes('''
        class c: pass
        async def func(c: c) -> None: pass
        ''')

    def test_postponed_annotations(self):
        self.flakes('''
        from __future__ import annotations
        def f(a: A) -> A: pass
        class A:
            b: B
        class B: pass
        ''')

        self.flakes('''
        from __future__ import annotations
        def f(a: A) -> A: pass
        class A:
            b: Undefined
        class B: pass
        ''', m.UndefinedName)

        self.flakes('''
        from __future__ import annotations
        T: object
        def f(t: T): pass
        def g(t: 'T'): pass
        ''')

    def test_type_annotation_clobbers_all(self):
        self.flakes('''\
        from typing import TYPE_CHECKING, List

        from y import z

        if not TYPE_CHECKING:
            __all__ = ("z",)
        else:
            __all__: List[str]
        ''')

    def test_return_annotation_is_class_scope_variable(self):
        self.flakes("""
        from typing import TypeVar
        class Test:
            Y = TypeVar('Y')

            def t(self, x: Y) -> Y:
                return x
        """)

    def test_return_annotation_is_function_body_variable(self):
        self.flakes("""
        class Test:
            def t(self) -> Y:
                Y = 2
                return Y
        """, m.UndefinedName)

    def test_positional_only_argument_annotations(self):
        self.flakes("""
        from x import C

        def f(c: C, /): ...
        """)

    def test_partially_quoted_type_annotation(self):
        self.flakes("""
        from queue import Queue
        from typing import Optional

        def f() -> Optional['Queue[str]']:
            return None
        """)

    def test_partially_quoted_type_assignment(self):
        self.flakes("""
        from queue import Queue
        from typing import Optional

        MaybeQueue = Optional['Queue[str]']
        """)

    def test_nested_partially_quoted_type_assignment(self):
        self.flakes("""
        from queue import Queue
        from typing import Callable

        Func = Callable[['Queue[str]'], None]
        """)

    def test_quoted_type_cast(self):
        self.flakes("""
        from typing import cast, Optional

        maybe_int = cast('Optional[int]', 42)
        """)

    def test_type_cast_literal_str_to_str(self):
        # Checks that our handling of quoted type annotations in the first
        # argument to `cast` doesn't cause issues when (only) the _second_
        # argument is a literal str which looks a bit like a type annotation.
        self.flakes("""
        from typing import cast

        a_string = cast(str, 'Optional[int]')
        """)

    def test_quoted_type_cast_renamed_import(self):
        self.flakes("""
        from typing import cast as tsac, Optional as Maybe

        maybe_int = tsac('Maybe[int]', 42)
        """)

    def test_quoted_TypeVar_constraints(self):
        self.flakes("""
        from typing import TypeVar, Optional

        T = TypeVar('T', 'str', 'Optional[int]', bytes)
        """)

    def test_quoted_TypeVar_bound(self):
        self.flakes("""
        from typing import TypeVar, Optional, List

        T = TypeVar('T', bound='Optional[int]')
        S = TypeVar('S', int, bound='List[int]')
        """)

    def test_literal_type_typing(self):
        self.flakes("""
        from typing import Literal

        def f(x: Literal['some string']) -> None:
            return None
        """)

    def test_literal_type_typing_extensions(self):
        self.flakes("""
        from typing_extensions import Literal

        def f(x: Literal['some string']) -> None:
            return None
        """)

    def test_annotated_type_typing_missing_forward_type(self):
        self.flakes("""
        from typing import Annotated

        def f(x: Annotated['integer']) -> None:
            return None
        """, m.UndefinedName)

    def test_annotated_type_typing_missing_forward_type_multiple_args(self):
        self.flakes("""
        from typing import Annotated

        def f(x: Annotated['integer', 1]) -> None:
            return None
        """, m.UndefinedName)

    def test_annotated_type_typing_with_string_args(self):
        self.flakes("""
        from typing import Annotated

        def f(x: Annotated[int, '> 0']) -> None:
            return None
        """)

    def test_annotated_type_typing_with_string_args_in_union(self):
        self.flakes("""
        from typing import Annotated, Union

        def f(x: Union[Annotated['int', '>0'], 'integer']) -> None:
            return None
        """, m.UndefinedName)

    def test_literal_type_some_other_module(self):
        """err on the side of false-negatives for types named Literal"""
        self.flakes("""
        from my_module import compat
        from my_module.compat import Literal

        def f(x: compat.Literal['some string']) -> None:
            return None
        def g(x: Literal['some string']) -> None:
            return None
        """)

    def test_literal_union_type_typing(self):
        self.flakes("""
        from typing import Literal

        def f(x: Literal['some string', 'foo bar']) -> None:
            return None
        """)

    def test_deferred_twice_annotation(self):
        self.flakes("""
            from queue import Queue
            from typing import Optional


            def f() -> "Optional['Queue[str]']":
                return None
        """)

    def test_partial_string_annotations_with_future_annotations(self):
        self.flakes("""
            from __future__ import annotations

            from queue import Queue
            from typing import Optional


            def f() -> Optional['Queue[str]']:
                return None
        """)

    def test_forward_annotations_for_classes_in_scope(self):
        # see #749
        self.flakes("""
        from typing import Optional

        def f():
            class C:
                a: "D"
                b: Optional["D"]
                c: "Optional[D]"

            class D: pass
        """)

    def test_idomiatic_typing_guards(self):
        # typing.TYPE_CHECKING: python3.5.3+
        self.flakes("""
            from typing import TYPE_CHECKING

            if TYPE_CHECKING:
                from t import T

            def f() -> T:
                pass
        """)
        # False: the old, more-compatible approach
        self.flakes("""
            if False:
                from t import T

            def f() -> T:
                pass
        """)
        # some choose to assign a constant and do it that way
        self.flakes("""
            MYPY = False

            if MYPY:
                from t import T

            def f() -> T:
                pass
        """)

    def test_typing_guard_for_protocol(self):
        self.flakes("""
            from typing import TYPE_CHECKING

            if TYPE_CHECKING:
                from typing import Protocol
            else:
                Protocol = object

            class C(Protocol):
                def f() -> int:
                    pass
        """)

    def test_typednames_correct_forward_ref(self):
        self.flakes("""
            from typing import TypedDict, List, NamedTuple

            List[TypedDict("x", {})]
            List[TypedDict("x", x=int)]
            List[NamedTuple("a", a=int)]
            List[NamedTuple("a", [("a", int)])]
        """)
        self.flakes("""
            from typing import TypedDict, List, NamedTuple, TypeVar

            List[TypedDict("x", {"x": "Y"})]
            List[TypedDict("x", x="Y")]
            List[NamedTuple("a", [("a", "Y")])]
            List[NamedTuple("a", a="Y")]
            List[TypedDict("x", {"x": List["a"]})]
            List[TypeVar("A", bound="C")]
            List[TypeVar("A", List["C"])]
        """, *[m.UndefinedName]*7)
        self.flakes("""
            from typing import NamedTuple, TypeVar, cast
            from t import A, B, C, D, E

            NamedTuple("A", [("a", A["C"])])
            TypeVar("A", bound=A["B"])
            TypeVar("A", A["D"])
            cast(A["E"], [])
        """)

    def test_namedtypes_classes(self):
        self.flakes("""
            from typing import TypedDict, NamedTuple
            class X(TypedDict):
                y: TypedDict("z", {"zz":int})

            class Y(NamedTuple):
                y: NamedTuple("v", [("vv", int)])
        """)

    @skipIf(version_info < (3, 11), 'new in Python 3.11')
    def test_variadic_generics(self):
        self.flakes("""
            from typing import Generic
            from typing import TypeVarTuple

            Ts = TypeVarTuple('Ts')

            class Shape(Generic[*Ts]): pass

            def f(*args: *Ts) -> None: ...

            def g(x: Shape[*Ts]) -> Shape[*Ts]: ...
        """)

    @skipIf(version_info < (3, 12), 'new in Python 3.12')
    def test_type_statements(self):
        self.flakes("""
            type ListOrSet[T] = list[T] | set[T]

            def f(x: ListOrSet[str]) -> None: ...

            type RecursiveType = int | list[RecursiveType]

            type ForwardRef = int | C

            type ForwardRefInBounds[T: C] = T

            class C: pass
        """)

    @skipIf(version_info < (3, 12), 'new in Python 3.12')
    def test_type_parameters_functions(self):
        self.flakes("""
            def f[T](t: T) -> T: return t

            async def g[T](t: T) -> T: return t

            def with_forward_ref[T: C](t: T) -> T: return t

            def can_access_inside[T](t: T) -> T:
                print(T)
                return t

            class C: pass
        """)

    @skipIf(version_info < (3, 12), 'new in Python 3.12')
    def test_type_parameters_do_not_escape_function_scopes(self):
        self.flakes("""
            from x import g

            @g(T)  # not accessible in decorators
            def f[T](t: T) -> T: return t

            T  # not accessible afterwards
        """, m.UndefinedName, m.UndefinedName)

    @skipIf(version_info < (3, 12), 'new in Python 3.12')
    def test_type_parameters_classes(self):
        self.flakes("""
            class C[T](list[T]): pass

            class UsesForward[T: Forward](list[T]): pass

            class Forward: pass

            class WithinBody[T](list[T]):
                t = T
        """)

    @skipIf(version_info < (3, 12), 'new in Python 3.12')
    def test_type_parameters_do_not_escape_class_scopes(self):
        self.flakes("""
            from x import g

            @g(T)  # not accessible in decorators
            class C[T](list[T]): pass

            T  # not accessible afterwards
        """, m.UndefinedName, m.UndefinedName)

    @skipIf(version_info < (3, 12), 'new in Python 3.12')
    def test_type_parameters_TypeVarTuple(self):
        self.flakes("""
        def f[*T](*args: *T) -> None: ...
        """)

    @skipIf(version_info < (3, 12), 'new in Python 3.12')
    def test_type_parameters_ParamSpec(self):
        self.flakes("""
        from typing import Callable

        def f[R, **P](f: Callable[P, R]) -> Callable[P, R]:
            def g(*args: P.args, **kwargs: P.kwargs) -> R:
                return f(*args, **kwargs)
            return g
        """)
