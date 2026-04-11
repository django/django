# ------------------------------------------------------------------------------
# pycparser: c_parser.py
#
# Recursive-descent parser for the C language.
#
# Eli Bendersky [https://eli.thegreenplace.net/]
# License: BSD
# ------------------------------------------------------------------------------
from dataclasses import dataclass
from typing import (
    Any,
    Dict,
    List,
    Literal,
    NoReturn,
    Optional,
    Tuple,
    TypedDict,
    cast,
)

from . import c_ast
from .c_lexer import CLexer, _Token
from .ast_transforms import fix_switch_cases, fix_atomic_specifiers


@dataclass
class Coord:
    """Coordinates of a syntactic element. Consists of:
    - File name
    - Line number
    - Column number
    """

    file: str
    line: int
    column: Optional[int] = None

    def __str__(self) -> str:
        text = f"{self.file}:{self.line}"
        if self.column:
            text += f":{self.column}"
        return text


class ParseError(Exception):
    pass


class CParser:
    """Recursive-descent C parser.

    Usage:
        parser = CParser()
        ast = parser.parse(text, filename)

    The `lexer` parameter lets you inject a lexer class (defaults to CLexer).
    The parameters after `lexer` are accepted for backward compatibility with
    the old PLY-based parser and are otherwise unused.
    """

    def __init__(
        self,
        lex_optimize: bool = True,
        lexer: type[CLexer] = CLexer,
        lextab: str = "pycparser.lextab",
        yacc_optimize: bool = True,
        yacctab: str = "pycparser.yacctab",
        yacc_debug: bool = False,
        taboutputdir: str = "",
    ) -> None:
        self.clex: CLexer = lexer(
            error_func=self._lex_error_func,
            on_lbrace_func=self._lex_on_lbrace_func,
            on_rbrace_func=self._lex_on_rbrace_func,
            type_lookup_func=self._lex_type_lookup_func,
        )

        # Stack of scopes for keeping track of symbols. _scope_stack[-1] is
        # the current (topmost) scope. Each scope is a dictionary that
        # specifies whether a name is a type. If _scope_stack[n][name] is
        # True, 'name' is currently a type in the scope. If it's False,
        # 'name' is used in the scope but not as a type (for instance, if we
        # saw: int name;
        # If 'name' is not a key in _scope_stack[n] then 'name' was not defined
        # in this scope at all.
        self._scope_stack: List[Dict[str, bool]] = [dict()]
        self._tokens: _TokenStream = _TokenStream(self.clex)

    def parse(
        self, text: str, filename: str = "", debug: bool = False
    ) -> c_ast.FileAST:
        """Parses C code and returns an AST.

        text:
            A string containing the C source code

        filename:
            Name of the file being parsed (for meaningful
            error messages)

        debug:
            Deprecated debug flag (unused); for backwards compatibility.
        """
        self._scope_stack = [dict()]
        self.clex.input(text, filename)
        self._tokens = _TokenStream(self.clex)

        ast = self._parse_translation_unit_or_empty()
        tok = self._peek()
        if tok is not None:
            self._parse_error(f"before: {tok.value}", self._tok_coord(tok))
        return ast

    # ------------------------------------------------------------------
    # Scope and declaration helpers
    # ------------------------------------------------------------------
    def _coord(self, lineno: int, column: Optional[int] = None) -> Coord:
        return Coord(file=self.clex.filename, line=lineno, column=column)

    def _parse_error(self, msg: str, coord: Coord | str | None) -> NoReturn:
        raise ParseError(f"{coord}: {msg}")

    def _push_scope(self) -> None:
        self._scope_stack.append(dict())

    def _pop_scope(self) -> None:
        assert len(self._scope_stack) > 1
        self._scope_stack.pop()

    def _add_typedef_name(self, name: str, coord: Optional[Coord]) -> None:
        """Add a new typedef name (ie a TYPEID) to the current scope"""
        if not self._scope_stack[-1].get(name, True):
            self._parse_error(
                f"Typedef {name!r} previously declared as non-typedef in this scope",
                coord,
            )
        self._scope_stack[-1][name] = True

    def _add_identifier(self, name: str, coord: Optional[Coord]) -> None:
        """Add a new object, function, or enum member name (ie an ID) to the
        current scope
        """
        if self._scope_stack[-1].get(name, False):
            self._parse_error(
                f"Non-typedef {name!r} previously declared as typedef in this scope",
                coord,
            )
        self._scope_stack[-1][name] = False

    def _is_type_in_scope(self, name: str) -> bool:
        """Is *name* a typedef-name in the current scope?"""
        for scope in reversed(self._scope_stack):
            # If name is an identifier in this scope it shadows typedefs in
            # higher scopes.
            in_scope = scope.get(name)
            if in_scope is not None:
                return in_scope
        return False

    def _lex_error_func(self, msg: str, line: int, column: int) -> None:
        self._parse_error(msg, self._coord(line, column))

    def _lex_on_lbrace_func(self) -> None:
        self._push_scope()

    def _lex_on_rbrace_func(self) -> None:
        self._pop_scope()

    def _lex_type_lookup_func(self, name: str) -> bool:
        """Looks up types that were previously defined with
        typedef.
        Passed to the lexer for recognizing identifiers that
        are types.
        """
        return self._is_type_in_scope(name)

    # To understand what's going on here, read sections A.8.5 and
    # A.8.6 of K&R2 very carefully.
    #
    # A C type consists of a basic type declaration, with a list
    # of modifiers. For example:
    #
    # int *c[5];
    #
    # The basic declaration here is 'int c', and the pointer and
    # the array are the modifiers.
    #
    # Basic declarations are represented by TypeDecl (from module c_ast) and the
    # modifiers are FuncDecl, PtrDecl and ArrayDecl.
    #
    # The standard states that whenever a new modifier is parsed, it should be
    # added to the end of the list of modifiers. For example:
    #
    # K&R2 A.8.6.2: Array Declarators
    #
    # In a declaration T D where D has the form
    #   D1 [constant-expression-opt]
    # and the type of the identifier in the declaration T D1 is
    # "type-modifier T", the type of the
    # identifier of D is "type-modifier array of T"
    #
    # This is what this method does. The declarator it receives
    # can be a list of declarators ending with TypeDecl. It
    # tacks the modifier to the end of this list, just before
    # the TypeDecl.
    #
    # Additionally, the modifier may be a list itself. This is
    # useful for pointers, that can come as a chain from the rule
    # p_pointer. In this case, the whole modifier list is spliced
    # into the new location.
    def _type_modify_decl(self, decl: Any, modifier: Any) -> c_ast.Node:
        """Tacks a type modifier on a declarator, and returns
        the modified declarator.

        Note: the declarator and modifier may be modified
        """
        modifier_head = modifier
        modifier_tail = modifier

        # The modifier may be a nested list. Reach its tail.
        while modifier_tail.type:
            modifier_tail = modifier_tail.type

        # If the decl is a basic type, just tack the modifier onto it.
        if isinstance(decl, c_ast.TypeDecl):
            modifier_tail.type = decl
            return modifier
        else:
            # Otherwise, the decl is a list of modifiers. Reach
            # its tail and splice the modifier onto the tail,
            # pointing to the underlying basic type.
            decl_tail = decl
            while not isinstance(decl_tail.type, c_ast.TypeDecl):
                decl_tail = decl_tail.type

            modifier_tail.type = decl_tail.type
            decl_tail.type = modifier_head
            return decl

    # Due to the order in which declarators are constructed,
    # they have to be fixed in order to look like a normal AST.
    #
    # When a declaration arrives from syntax construction, it has
    # these problems:
    # * The innermost TypeDecl has no type (because the basic
    #   type is only known at the uppermost declaration level)
    # * The declaration has no variable name, since that is saved
    #   in the innermost TypeDecl
    # * The typename of the declaration is a list of type
    #   specifiers, and not a node. Here, basic identifier types
    #   should be separated from more complex types like enums
    #   and structs.
    #
    # This method fixes these problems.
    def _fix_decl_name_type(
        self,
        decl: c_ast.Decl | c_ast.Typedef | c_ast.Typename,
        typename: List[Any],
    ) -> c_ast.Decl | c_ast.Typedef | c_ast.Typename:
        """Fixes a declaration. Modifies decl."""
        # Reach the underlying basic type
        typ = decl
        while not isinstance(typ, c_ast.TypeDecl):
            typ = typ.type

        decl.name = typ.declname
        typ.quals = decl.quals[:]

        # The typename is a list of types. If any type in this
        # list isn't an IdentifierType, it must be the only
        # type in the list (it's illegal to declare "int enum ..")
        # If all the types are basic, they're collected in the
        # IdentifierType holder.
        for tn in typename:
            if not isinstance(tn, c_ast.IdentifierType):
                if len(typename) > 1:
                    self._parse_error("Invalid multiple types specified", tn.coord)
                else:
                    typ.type = tn
                    return decl

        if not typename:
            # Functions default to returning int
            if not isinstance(decl.type, c_ast.FuncDecl):
                self._parse_error("Missing type in declaration", decl.coord)
            typ.type = c_ast.IdentifierType(["int"], coord=decl.coord)
        else:
            # At this point, we know that typename is a list of IdentifierType
            # nodes. Concatenate all the names into a single list.
            typ.type = c_ast.IdentifierType(
                [name for id in typename for name in id.names], coord=typename[0].coord
            )
        return decl

    def _add_declaration_specifier(
        self,
        declspec: Optional["_DeclSpec"],
        newspec: Any,
        kind: "_DeclSpecKind",
        append: bool = False,
    ) -> "_DeclSpec":
        """See _DeclSpec for the specifier dictionary layout."""
        if declspec is None:
            spec: _DeclSpec = dict(
                qual=[], storage=[], type=[], function=[], alignment=[]
            )
        else:
            spec = declspec

        if append:
            spec[kind].append(newspec)
        else:
            spec[kind].insert(0, newspec)

        return spec

    def _build_declarations(
        self,
        spec: "_DeclSpec",
        decls: List["_DeclInfo"],
        typedef_namespace: bool = False,
    ) -> List[c_ast.Node]:
        """Builds a list of declarations all sharing the given specifiers.
        If typedef_namespace is true, each declared name is added
        to the "typedef namespace", which also includes objects,
        functions, and enum constants.
        """
        is_typedef = "typedef" in spec["storage"]
        declarations = []

        # Bit-fields are allowed to be unnamed.
        if decls[0].get("bitsize") is None:
            # When redeclaring typedef names as identifiers in inner scopes, a
            # problem can occur where the identifier gets grouped into
            # spec['type'], leaving decl as None.  This can only occur for the
            # first declarator.
            if decls[0]["decl"] is None:
                if (
                    len(spec["type"]) < 2
                    or len(spec["type"][-1].names) != 1
                    or not self._is_type_in_scope(spec["type"][-1].names[0])
                ):
                    coord = "?"
                    for t in spec["type"]:
                        if hasattr(t, "coord"):
                            coord = t.coord
                            break
                    self._parse_error("Invalid declaration", coord)

                # Make this look as if it came from "direct_declarator:ID"
                decls[0]["decl"] = c_ast.TypeDecl(
                    declname=spec["type"][-1].names[0],
                    type=None,
                    quals=None,
                    align=spec["alignment"],
                    coord=spec["type"][-1].coord,
                )
                # Remove the "new" type's name from the end of spec['type']
                del spec["type"][-1]
            # A similar problem can occur where the declaration ends up
            # looking like an abstract declarator.  Give it a name if this is
            # the case.
            elif not isinstance(
                decls[0]["decl"],
                (c_ast.Enum, c_ast.Struct, c_ast.Union, c_ast.IdentifierType),
            ):
                decls_0_tail = cast(Any, decls[0]["decl"])
                while not isinstance(decls_0_tail, c_ast.TypeDecl):
                    decls_0_tail = decls_0_tail.type
                if decls_0_tail.declname is None:
                    decls_0_tail.declname = spec["type"][-1].names[0]
                    del spec["type"][-1]

        for decl in decls:
            assert decl["decl"] is not None
            if is_typedef:
                declaration = c_ast.Typedef(
                    name=None,
                    quals=spec["qual"],
                    storage=spec["storage"],
                    type=decl["decl"],
                    coord=decl["decl"].coord,
                )
            else:
                declaration = c_ast.Decl(
                    name=None,
                    quals=spec["qual"],
                    align=spec["alignment"],
                    storage=spec["storage"],
                    funcspec=spec["function"],
                    type=decl["decl"],
                    init=decl.get("init"),
                    bitsize=decl.get("bitsize"),
                    coord=decl["decl"].coord,
                )

            if isinstance(
                declaration.type,
                (c_ast.Enum, c_ast.Struct, c_ast.Union, c_ast.IdentifierType),
            ):
                fixed_decl = declaration
            else:
                fixed_decl = self._fix_decl_name_type(declaration, spec["type"])

            # Add the type name defined by typedef to a
            # symbol table (for usage in the lexer)
            if typedef_namespace:
                if is_typedef:
                    self._add_typedef_name(fixed_decl.name, fixed_decl.coord)
                else:
                    self._add_identifier(fixed_decl.name, fixed_decl.coord)

            fixed_decl = fix_atomic_specifiers(
                cast(c_ast.Decl | c_ast.Typedef, fixed_decl)
            )
            declarations.append(fixed_decl)

        return declarations

    def _build_function_definition(
        self,
        spec: "_DeclSpec",
        decl: c_ast.Node,
        param_decls: Optional[List[c_ast.Node]],
        body: c_ast.Node,
    ) -> c_ast.Node:
        """Builds a function definition."""
        if "typedef" in spec["storage"]:
            self._parse_error("Invalid typedef", decl.coord)

        declaration = self._build_declarations(
            spec=spec,
            decls=[dict(decl=decl, init=None, bitsize=None)],
            typedef_namespace=True,
        )[0]

        return c_ast.FuncDef(
            decl=declaration, param_decls=param_decls, body=body, coord=decl.coord
        )

    def _select_struct_union_class(self, token: str) -> type:
        """Given a token (either STRUCT or UNION), selects the
        appropriate AST class.
        """
        if token == "struct":
            return c_ast.Struct
        else:
            return c_ast.Union

    # ------------------------------------------------------------------
    # Token helpers
    # ------------------------------------------------------------------
    def _peek(self, k: int = 1) -> Optional[_Token]:
        """Return the k-th next token without consuming it (1-based)."""
        return self._tokens.peek(k)

    def _peek_type(self, k: int = 1) -> Optional[str]:
        """Return the type of the k-th next token, or None if absent (1-based)."""
        tok = self._peek(k)
        return tok.type if tok is not None else None

    def _advance(self) -> _Token:
        tok = self._tokens.next()
        if tok is None:
            self._parse_error("At end of input", self.clex.filename)
        else:
            return tok

    def _accept(self, token_type: str) -> Optional[_Token]:
        """Conditionally consume next token, only if it's of token_type.

        If it is of the expected type, consume and return it.
        Otherwise, leaves the token intact and returns None.
        """
        tok = self._peek()
        if tok is not None and tok.type == token_type:
            return self._advance()
        return None

    def _expect(self, token_type: str) -> _Token:
        tok = self._advance()
        if tok.type != token_type:
            self._parse_error(f"before: {tok.value}", self._tok_coord(tok))
        return tok

    def _mark(self) -> int:
        return self._tokens.mark()

    def _reset(self, mark: int) -> None:
        self._tokens.reset(mark)

    def _tok_coord(self, tok: _Token) -> Coord:
        return self._coord(tok.lineno, tok.column)

    def _starts_declaration(self, tok: Optional[_Token] = None) -> bool:
        tok = tok or self._peek()
        if tok is None:
            return False
        return tok.type in _DECL_START

    def _starts_expression(self, tok: Optional[_Token] = None) -> bool:
        tok = tok or self._peek()
        if tok is None:
            return False
        return tok.type in _STARTS_EXPRESSION

    def _starts_statement(self) -> bool:
        tok_type = self._peek_type()
        if tok_type is None:
            return False
        if tok_type in _STARTS_STATEMENT:
            return True
        return self._starts_expression()

    def _starts_declarator(self, id_only: bool = False) -> bool:
        tok_type = self._peek_type()
        if tok_type is None:
            return False
        if tok_type in {"TIMES", "LPAREN"}:
            return True
        if id_only:
            return tok_type == "ID"
        return tok_type in {"ID", "TYPEID"}

    def _peek_declarator_name_info(self) -> Tuple[Optional[str], bool]:
        mark = self._mark()
        tok_type, saw_paren = self._scan_declarator_name_info()
        self._reset(mark)
        return tok_type, saw_paren

    def _parse_any_declarator(
        self, allow_abstract: bool = False, typeid_paren_as_abstract: bool = False
    ) -> Tuple[Optional[c_ast.Node], bool]:
        # C declarators are ambiguous without lookahead. For example:
        #   int foo(int (aa));   -> aa is a name (ID)
        #   typedef char TT;
        #   int bar(int (TT));   -> TT is a type (TYPEID) in parens
        name_type, saw_paren = self._peek_declarator_name_info()
        if name_type is None or (
            typeid_paren_as_abstract and name_type == "TYPEID" and saw_paren
        ):
            if not allow_abstract:
                tok = self._peek()
                coord = self._tok_coord(tok) if tok is not None else self.clex.filename
                self._parse_error("Invalid declarator", coord)
            decl = self._parse_abstract_declarator_opt()
            return decl, False

        if name_type == "TYPEID":
            if typeid_paren_as_abstract:
                decl = self._parse_typeid_noparen_declarator()
            else:
                decl = self._parse_typeid_declarator()
        else:
            decl = self._parse_id_declarator()
        return decl, True

    def _scan_declarator_name_info(self) -> Tuple[Optional[str], bool]:
        saw_paren = False
        while self._accept("TIMES"):
            while self._peek_type() in _TYPE_QUALIFIER:
                self._advance()

        tok = self._peek()
        if tok is None:
            return None, saw_paren
        if tok.type in {"ID", "TYPEID"}:
            self._advance()
            return tok.type, saw_paren
        if tok.type == "LPAREN":
            saw_paren = True
            self._advance()
            tok_type, nested_paren = self._scan_declarator_name_info()
            if nested_paren:
                saw_paren = True
            depth = 1
            while True:
                tok = self._peek()
                if tok is None:
                    return None, saw_paren
                if tok.type == "LPAREN":
                    depth += 1
                elif tok.type == "RPAREN":
                    depth -= 1
                    self._advance()
                    if depth == 0:
                        break
                    continue
                self._advance()
            return tok_type, saw_paren
        return None, saw_paren

    def _starts_direct_abstract_declarator(self) -> bool:
        return self._peek_type() in {"LPAREN", "LBRACKET"}

    def _is_assignment_op(self) -> bool:
        tok = self._peek()
        return tok is not None and tok.type in _ASSIGNMENT_OPS

    def _try_parse_paren_type_name(
        self,
    ) -> Optional[Tuple[c_ast.Typename, int, _Token]]:
        """Parse and return a parenthesized type name if present.

        Returns (typ, mark, lparen_tok) when the next tokens look like
        '(' type_name ')', where typ is the parsed type name, mark is the
        token-stream position before parsing, and lparen_tok is the LPAREN
        token. Returns None if no parenthesized type name is present.
        """
        mark = self._mark()
        lparen_tok = self._accept("LPAREN")
        if lparen_tok is None:
            return None
        if not self._starts_declaration():
            self._reset(mark)
            return None
        typ = self._parse_type_name()
        if self._accept("RPAREN") is None:
            self._reset(mark)
            return None
        return typ, mark, lparen_tok

    # ------------------------------------------------------------------
    # Top-level
    # ------------------------------------------------------------------
    # BNF: translation_unit_or_empty : translation_unit | empty
    def _parse_translation_unit_or_empty(self) -> c_ast.FileAST:
        if self._peek() is None:
            return c_ast.FileAST([])
        return c_ast.FileAST(self._parse_translation_unit())

    # BNF: translation_unit : external_declaration+
    def _parse_translation_unit(self) -> List[c_ast.Node]:
        ext = []
        while self._peek() is not None:
            ext.extend(self._parse_external_declaration())
        return ext

    # BNF: external_declaration : function_definition
    #                           | declaration
    #                           | pp_directive
    #                           | pppragma_directive
    #                           | static_assert
    #                           | ';'
    def _parse_external_declaration(self) -> List[c_ast.Node]:
        tok = self._peek()
        if tok is None:
            return []
        if tok.type == "PPHASH":
            self._parse_pp_directive()
            return []
        if tok.type in {"PPPRAGMA", "_PRAGMA"}:
            return [self._parse_pppragma_directive()]
        if self._accept("SEMI"):
            return []
        if tok.type == "_STATIC_ASSERT":
            return self._parse_static_assert()

        if not self._starts_declaration(tok):
            # Special handling for old-style function definitions that have an
            # implicit return type, e.g.
            #
            #   foo() {
            #    return 5;
            #   }
            #
            # These get an implicit 'int' return type.
            decl = self._parse_id_declarator()
            param_decls = None
            if self._peek_type() != "LBRACE":
                self._parse_error("Invalid function definition", decl.coord)
            spec: _DeclSpec = dict(
                qual=[],
                alignment=[],
                storage=[],
                type=[c_ast.IdentifierType(["int"], coord=decl.coord)],
                function=[],
            )
            func = self._build_function_definition(
                spec=spec,
                decl=decl,
                param_decls=param_decls,
                body=self._parse_compound_statement(),
            )
            return [func]

        # From here on, parsing a standard declatation/definition.
        spec, saw_type, spec_coord = self._parse_declaration_specifiers(
            allow_no_type=True
        )

        name_type, _ = self._peek_declarator_name_info()
        if name_type != "ID":
            decls = self._parse_decl_body_with_spec(spec, saw_type)
            self._expect("SEMI")
            return decls

        decl = self._parse_id_declarator()

        if self._peek_type() == "LBRACE" or self._starts_declaration():
            param_decls = None
            if self._starts_declaration():
                param_decls = self._parse_declaration_list()
            if self._peek_type() != "LBRACE":
                self._parse_error("Invalid function definition", decl.coord)
            if not spec["type"]:
                spec["type"] = [c_ast.IdentifierType(["int"], coord=spec_coord)]
            func = self._build_function_definition(
                spec=spec,
                decl=decl,
                param_decls=param_decls,
                body=self._parse_compound_statement(),
            )
            return [func]

        decl_dict: "_DeclInfo" = dict(decl=decl, init=None, bitsize=None)
        if self._accept("EQUALS"):
            decl_dict["init"] = self._parse_initializer()
        decls = self._parse_init_declarator_list(first=decl_dict)
        decls = self._build_declarations(spec=spec, decls=decls, typedef_namespace=True)
        self._expect("SEMI")
        return decls

    # ------------------------------------------------------------------
    # Declarations
    #
    # Declarations always come as lists (because they can be several in one
    # line). When returning parsed declarations, a list is always returned -
    # even if it contains a single element.
    # ------------------------------------------------------------------
    def _parse_declaration(self) -> List[c_ast.Node]:
        decls = self._parse_decl_body()
        self._expect("SEMI")
        return decls

    # BNF: decl_body : declaration_specifiers decl_body_with_spec
    def _parse_decl_body(self) -> List[c_ast.Node]:
        spec, saw_type, _ = self._parse_declaration_specifiers(allow_no_type=True)
        return self._parse_decl_body_with_spec(spec, saw_type)

    # BNF: decl_body_with_spec : init_declarator_list
    #                          | struct_or_union_or_enum_only
    def _parse_decl_body_with_spec(
        self, spec: "_DeclSpec", saw_type: bool
    ) -> List[c_ast.Node]:
        decls = None
        if saw_type:
            if self._starts_declarator():
                decls = self._parse_init_declarator_list()
        else:
            if self._starts_declarator(id_only=True):
                decls = self._parse_init_declarator_list(id_only=True)

        if decls is None:
            ty = spec["type"]
            s_u_or_e = (c_ast.Struct, c_ast.Union, c_ast.Enum)
            if len(ty) == 1 and isinstance(ty[0], s_u_or_e):
                decls = [
                    c_ast.Decl(
                        name=None,
                        quals=spec["qual"],
                        align=spec["alignment"],
                        storage=spec["storage"],
                        funcspec=spec["function"],
                        type=ty[0],
                        init=None,
                        bitsize=None,
                        coord=ty[0].coord,
                    )
                ]
            else:
                decls = self._build_declarations(
                    spec=spec,
                    decls=[dict(decl=None, init=None, bitsize=None)],
                    typedef_namespace=True,
                )
        else:
            decls = self._build_declarations(
                spec=spec, decls=decls, typedef_namespace=True
            )

        return decls

    # BNF: declaration_list : declaration+
    def _parse_declaration_list(self) -> List[c_ast.Node]:
        decls = []
        while self._starts_declaration():
            decls.extend(self._parse_declaration())
        return decls

    # BNF: declaration_specifiers   : (storage_class_specifier
    #                               | type_specifier
    #                               | type_qualifier
    #                               | function_specifier
    #                               | alignment_specifier)+
    def _parse_declaration_specifiers(
        self, allow_no_type: bool = False
    ) -> Tuple["_DeclSpec", bool, Optional[Coord]]:
        """Parse declaration-specifier sequence.

        allow_no_type:
            If True, allow a missing type specifier without error.

        Returns:
            (spec, saw_type, first_coord) where spec is a dict with
            qual/storage/type/function/alignment entries, saw_type is True
            if a type specifier was consumed, and first_coord is the coord
            of the first specifier token (used for diagnostics).
        """
        spec = None
        saw_type = False
        first_coord = None

        while True:
            tok = self._peek()
            if tok is None:
                break

            if tok.type == "_ALIGNAS":
                if first_coord is None:
                    first_coord = self._tok_coord(tok)
                spec = self._add_declaration_specifier(
                    spec, self._parse_alignment_specifier(), "alignment", append=True
                )
                continue

            if tok.type == "_ATOMIC" and self._peek_type(2) == "LPAREN":
                if first_coord is None:
                    first_coord = self._tok_coord(tok)
                spec = self._add_declaration_specifier(
                    spec, self._parse_atomic_specifier(), "type", append=True
                )
                saw_type = True
                continue

            if tok.type in _TYPE_QUALIFIER:
                if first_coord is None:
                    first_coord = self._tok_coord(tok)
                spec = self._add_declaration_specifier(
                    spec, self._advance().value, "qual", append=True
                )
                continue

            if tok.type in _STORAGE_CLASS:
                if first_coord is None:
                    first_coord = self._tok_coord(tok)
                spec = self._add_declaration_specifier(
                    spec, self._advance().value, "storage", append=True
                )
                continue

            if tok.type in _FUNCTION_SPEC:
                if first_coord is None:
                    first_coord = self._tok_coord(tok)
                spec = self._add_declaration_specifier(
                    spec, self._advance().value, "function", append=True
                )
                continue

            if tok.type in _TYPE_SPEC_SIMPLE:
                if first_coord is None:
                    first_coord = self._tok_coord(tok)
                tok = self._advance()
                spec = self._add_declaration_specifier(
                    spec,
                    c_ast.IdentifierType([tok.value], coord=self._tok_coord(tok)),
                    "type",
                    append=True,
                )
                saw_type = True
                continue

            if tok.type == "TYPEID":
                if saw_type:
                    break
                if first_coord is None:
                    first_coord = self._tok_coord(tok)
                tok = self._advance()
                spec = self._add_declaration_specifier(
                    spec,
                    c_ast.IdentifierType([tok.value], coord=self._tok_coord(tok)),
                    "type",
                    append=True,
                )
                saw_type = True
                continue

            if tok.type in {"STRUCT", "UNION"}:
                if first_coord is None:
                    first_coord = self._tok_coord(tok)
                spec = self._add_declaration_specifier(
                    spec, self._parse_struct_or_union_specifier(), "type", append=True
                )
                saw_type = True
                continue

            if tok.type == "ENUM":
                if first_coord is None:
                    first_coord = self._tok_coord(tok)
                spec = self._add_declaration_specifier(
                    spec, self._parse_enum_specifier(), "type", append=True
                )
                saw_type = True
                continue

            break

        if spec is None:
            self._parse_error("Invalid declaration", self.clex.filename)

        if not saw_type and not allow_no_type:
            self._parse_error("Missing type in declaration", first_coord)

        return spec, saw_type, first_coord

    # BNF: specifier_qualifier_list : (type_specifier
    #                               | type_qualifier
    #                               | alignment_specifier)+
    def _parse_specifier_qualifier_list(self) -> "_DeclSpec":
        spec = None
        saw_type = False
        saw_alignment = False
        first_coord = None

        while True:
            tok = self._peek()
            if tok is None:
                break

            if tok.type == "_ALIGNAS":
                if first_coord is None:
                    first_coord = self._tok_coord(tok)
                spec = self._add_declaration_specifier(
                    spec, self._parse_alignment_specifier(), "alignment", append=True
                )
                saw_alignment = True
                continue

            if tok.type == "_ATOMIC" and self._peek_type(2) == "LPAREN":
                if first_coord is None:
                    first_coord = self._tok_coord(tok)
                spec = self._add_declaration_specifier(
                    spec, self._parse_atomic_specifier(), "type", append=True
                )
                saw_type = True
                continue

            if tok.type in _TYPE_QUALIFIER:
                if first_coord is None:
                    first_coord = self._tok_coord(tok)
                spec = self._add_declaration_specifier(
                    spec, self._advance().value, "qual", append=True
                )
                continue

            if tok.type in _TYPE_SPEC_SIMPLE:
                if first_coord is None:
                    first_coord = self._tok_coord(tok)
                tok = self._advance()
                spec = self._add_declaration_specifier(
                    spec,
                    c_ast.IdentifierType([tok.value], coord=self._tok_coord(tok)),
                    "type",
                    append=True,
                )
                saw_type = True
                continue

            if tok.type == "TYPEID":
                if saw_type:
                    break
                if first_coord is None:
                    first_coord = self._tok_coord(tok)
                tok = self._advance()
                spec = self._add_declaration_specifier(
                    spec,
                    c_ast.IdentifierType([tok.value], coord=self._tok_coord(tok)),
                    "type",
                    append=True,
                )
                saw_type = True
                continue

            if tok.type in {"STRUCT", "UNION"}:
                if first_coord is None:
                    first_coord = self._tok_coord(tok)
                spec = self._add_declaration_specifier(
                    spec, self._parse_struct_or_union_specifier(), "type", append=True
                )
                saw_type = True
                continue

            if tok.type == "ENUM":
                if first_coord is None:
                    first_coord = self._tok_coord(tok)
                spec = self._add_declaration_specifier(
                    spec, self._parse_enum_specifier(), "type", append=True
                )
                saw_type = True
                continue

            break

        if spec is None:
            self._parse_error("Invalid specifier list", self.clex.filename)

        if not saw_type and not saw_alignment:
            self._parse_error("Missing type in declaration", first_coord)

        if spec.get("storage") is None:
            spec["storage"] = []
        if spec.get("function") is None:
            spec["function"] = []

        return spec

    # BNF: type_qualifier_list : type_qualifier+
    def _parse_type_qualifier_list(self) -> List[str]:
        quals = []
        while self._peek_type() in _TYPE_QUALIFIER:
            quals.append(self._advance().value)
        return quals

    # BNF: alignment_specifier : _ALIGNAS '(' type_name | constant_expression ')'
    def _parse_alignment_specifier(self) -> c_ast.Node:
        tok = self._expect("_ALIGNAS")
        self._expect("LPAREN")

        if self._starts_declaration():
            typ = self._parse_type_name()
            self._expect("RPAREN")
            return c_ast.Alignas(typ, self._tok_coord(tok))

        expr = self._parse_constant_expression()
        self._expect("RPAREN")
        return c_ast.Alignas(expr, self._tok_coord(tok))

    # BNF: atomic_specifier : _ATOMIC '(' type_name ')'
    def _parse_atomic_specifier(self) -> c_ast.Node:
        self._expect("_ATOMIC")
        self._expect("LPAREN")
        typ = self._parse_type_name()
        self._expect("RPAREN")
        typ.quals.append("_Atomic")
        return typ

    # BNF: init_declarator_list : init_declarator (',' init_declarator)*
    def _parse_init_declarator_list(
        self, first: Optional["_DeclInfo"] = None, id_only: bool = False
    ) -> List["_DeclInfo"]:
        decls = (
            [first]
            if first is not None
            else [self._parse_init_declarator(id_only=id_only)]
        )

        while self._accept("COMMA"):
            decls.append(self._parse_init_declarator(id_only=id_only))
        return decls

    # BNF: init_declarator : declarator ('=' initializer)?
    def _parse_init_declarator(self, id_only: bool = False) -> "_DeclInfo":
        decl = self._parse_id_declarator() if id_only else self._parse_declarator()
        init = None
        if self._accept("EQUALS"):
            init = self._parse_initializer()
        return dict(decl=decl, init=init, bitsize=None)

    # ------------------------------------------------------------------
    # Structs/unions/enums
    # ------------------------------------------------------------------
    # BNF: struct_or_union_specifier : struct_or_union ID? '{' struct_declaration_list? '}'
    #                                | struct_or_union ID
    def _parse_struct_or_union_specifier(self) -> c_ast.Node:
        tok = self._advance()
        klass = self._select_struct_union_class(tok.value)

        if self._peek_type() in {"ID", "TYPEID"}:
            name_tok = self._advance()
            if self._peek_type() == "LBRACE":
                self._advance()
                if self._accept("RBRACE"):
                    return klass(
                        name=name_tok.value, decls=[], coord=self._tok_coord(name_tok)
                    )
                decls = self._parse_struct_declaration_list()
                self._expect("RBRACE")
                return klass(
                    name=name_tok.value, decls=decls, coord=self._tok_coord(name_tok)
                )

            return klass(
                name=name_tok.value, decls=None, coord=self._tok_coord(name_tok)
            )

        if self._peek_type() == "LBRACE":
            brace_tok = self._advance()
            if self._accept("RBRACE"):
                return klass(name=None, decls=[], coord=self._tok_coord(brace_tok))
            decls = self._parse_struct_declaration_list()
            self._expect("RBRACE")
            return klass(name=None, decls=decls, coord=self._tok_coord(brace_tok))

        self._parse_error("Invalid struct/union declaration", self._tok_coord(tok))

    # BNF: struct_declaration_list : struct_declaration+
    def _parse_struct_declaration_list(self) -> List[c_ast.Node]:
        decls = []
        while self._peek_type() not in {None, "RBRACE"}:
            items = self._parse_struct_declaration()
            if items is None:
                continue
            decls.extend(items)
        return decls

    # BNF: struct_declaration   : specifier_qualifier_list struct_declarator_list? ';'
    #                           | static_assert
    #                           | pppragma_directive
    def _parse_struct_declaration(self) -> Optional[List[c_ast.Node]]:
        if self._peek_type() == "SEMI":
            self._advance()
            return None
        if self._peek_type() in {"PPPRAGMA", "_PRAGMA"}:
            return [self._parse_pppragma_directive()]

        spec = self._parse_specifier_qualifier_list()
        assert "typedef" not in spec.get("storage", [])

        decls = None
        if self._starts_declarator() or self._peek_type() == "COLON":
            decls = self._parse_struct_declarator_list()
        if decls is not None:
            self._expect("SEMI")
            return self._build_declarations(spec=spec, decls=decls)

        if len(spec["type"]) == 1:
            node = spec["type"][0]
            if isinstance(node, c_ast.Node):
                decl_type = node
            else:
                decl_type = c_ast.IdentifierType(node)
            self._expect("SEMI")
            return self._build_declarations(
                spec=spec, decls=[dict(decl=decl_type, init=None, bitsize=None)]
            )

        self._expect("SEMI")
        return self._build_declarations(
            spec=spec, decls=[dict(decl=None, init=None, bitsize=None)]
        )

    # BNF: struct_declarator_list : struct_declarator (',' struct_declarator)*
    def _parse_struct_declarator_list(self) -> List["_DeclInfo"]:
        decls = [self._parse_struct_declarator()]
        while self._accept("COMMA"):
            decls.append(self._parse_struct_declarator())
        return decls

    # BNF: struct_declarator : declarator? ':' constant_expression
    #                        | declarator (':' constant_expression)?
    def _parse_struct_declarator(self) -> "_DeclInfo":
        if self._accept("COLON"):
            bitsize = self._parse_constant_expression()
            return {
                "decl": c_ast.TypeDecl(None, None, None, None),
                "init": None,
                "bitsize": bitsize,
            }

        decl = self._parse_declarator()
        if self._accept("COLON"):
            bitsize = self._parse_constant_expression()
            return {"decl": decl, "init": None, "bitsize": bitsize}

        return {"decl": decl, "init": None, "bitsize": None}

    # BNF: enum_specifier : ENUM ID? '{' enumerator_list? '}'
    #                     | ENUM ID
    def _parse_enum_specifier(self) -> c_ast.Node:
        tok = self._expect("ENUM")
        if self._peek_type() in {"ID", "TYPEID"}:
            name_tok = self._advance()
            if self._peek_type() == "LBRACE":
                self._advance()
                enums = self._parse_enumerator_list()
                self._expect("RBRACE")
                return c_ast.Enum(name_tok.value, enums, self._tok_coord(tok))
            return c_ast.Enum(name_tok.value, None, self._tok_coord(tok))

        self._expect("LBRACE")
        enums = self._parse_enumerator_list()
        self._expect("RBRACE")
        return c_ast.Enum(None, enums, self._tok_coord(tok))

    # BNF: enumerator_list : enumerator (',' enumerator)* ','?
    def _parse_enumerator_list(self) -> c_ast.Node:
        enum = self._parse_enumerator()
        enum_list = c_ast.EnumeratorList([enum], enum.coord)
        while self._accept("COMMA"):
            if self._peek_type() == "RBRACE":
                break
            enum = self._parse_enumerator()
            enum_list.enumerators.append(enum)
        return enum_list

    # BNF: enumerator : ID ('=' constant_expression)?
    def _parse_enumerator(self) -> c_ast.Node:
        name_tok = self._expect("ID")
        if self._accept("EQUALS"):
            value = self._parse_constant_expression()
        else:
            value = None
        enum = c_ast.Enumerator(name_tok.value, value, self._tok_coord(name_tok))
        self._add_identifier(enum.name, enum.coord)
        return enum

    # ------------------------------------------------------------------
    # Declarators
    # ------------------------------------------------------------------
    # BNF: declarator : pointer? direct_declarator
    def _parse_declarator(self) -> c_ast.Node:
        decl, _ = self._parse_any_declarator(
            allow_abstract=False, typeid_paren_as_abstract=False
        )
        assert decl is not None
        return decl

    # BNF: id_declarator : declarator with ID name
    def _parse_id_declarator(self) -> c_ast.Node:
        return self._parse_declarator_kind(kind="id", allow_paren=True)

    # BNF: typeid_declarator : declarator with TYPEID name
    def _parse_typeid_declarator(self) -> c_ast.Node:
        return self._parse_declarator_kind(kind="typeid", allow_paren=True)

    # BNF: typeid_noparen_declarator : declarator without parenthesized name
    def _parse_typeid_noparen_declarator(self) -> c_ast.Node:
        return self._parse_declarator_kind(kind="typeid", allow_paren=False)

    # BNF: declarator_kind : pointer? direct_declarator(kind)
    def _parse_declarator_kind(self, kind: str, allow_paren: bool) -> c_ast.Node:
        ptr = None
        if self._peek_type() == "TIMES":
            ptr = self._parse_pointer()
        direct = self._parse_direct_declarator(kind, allow_paren=allow_paren)
        if ptr is not None:
            return self._type_modify_decl(direct, ptr)
        return direct

    # BNF: direct_declarator : ID | TYPEID | '(' declarator ')'
    #                        | direct_declarator '[' ... ']'
    #                        | direct_declarator '(' ... ')'
    def _parse_direct_declarator(
        self, kind: str, allow_paren: bool = True
    ) -> c_ast.Node:
        if allow_paren and self._accept("LPAREN"):
            decl = self._parse_declarator_kind(kind, allow_paren=True)
            self._expect("RPAREN")
        else:
            if kind == "id":
                name_tok = self._expect("ID")
            else:
                name_tok = self._expect("TYPEID")
            decl = c_ast.TypeDecl(
                declname=name_tok.value,
                type=None,
                quals=None,
                align=None,
                coord=self._tok_coord(name_tok),
            )

        return self._parse_decl_suffixes(decl)

    def _parse_decl_suffixes(self, decl: c_ast.Node) -> c_ast.Node:
        """Parse a chain of array/function suffixes and attach them to decl."""
        while True:
            if self._peek_type() == "LBRACKET":
                decl = self._type_modify_decl(decl, self._parse_array_decl(decl))
                continue
            if self._peek_type() == "LPAREN":
                func = self._parse_function_decl(decl)
                decl = self._type_modify_decl(decl, func)
                continue
            break
        return decl

    # BNF: array_decl : '[' array_specifiers? assignment_expression? ']'
    def _parse_array_decl(self, base_decl: c_ast.Node) -> c_ast.Node:
        return self._parse_array_decl_common(base_type=None, coord=base_decl.coord)

    def _parse_array_decl_common(
        self, base_type: Optional[c_ast.Node], coord: Optional[Coord] = None
    ) -> c_ast.Node:
        """Parse an array declarator suffix and return an ArrayDecl node.

        base_type:
            Base declarator node to attach (None for direct-declarator parsing,
            TypeDecl for abstract declarators).

        coord:
            Coordinate to use for the ArrayDecl. If None, uses the '[' token.
        """
        lbrack_tok = self._expect("LBRACKET")
        if coord is None:
            coord = self._tok_coord(lbrack_tok)

        def make_array_decl(dim, dim_quals):
            return c_ast.ArrayDecl(
                type=base_type, dim=dim, dim_quals=dim_quals, coord=coord
            )

        if self._accept("STATIC"):
            dim_quals = ["static"] + (self._parse_type_qualifier_list() or [])
            dim = self._parse_assignment_expression()
            self._expect("RBRACKET")
            return make_array_decl(dim, dim_quals)

        if self._peek_type() in _TYPE_QUALIFIER:
            dim_quals = self._parse_type_qualifier_list() or []
            if self._accept("STATIC"):
                dim_quals = dim_quals + ["static"]
                dim = self._parse_assignment_expression()
                self._expect("RBRACKET")
                return make_array_decl(dim, dim_quals)
            times_tok = self._accept("TIMES")
            if times_tok:
                self._expect("RBRACKET")
                dim = c_ast.ID(times_tok.value, self._tok_coord(times_tok))
                return make_array_decl(dim, dim_quals)
            dim = None
            if self._starts_expression():
                dim = self._parse_assignment_expression()
            self._expect("RBRACKET")
            return make_array_decl(dim, dim_quals)

        times_tok = self._accept("TIMES")
        if times_tok:
            self._expect("RBRACKET")
            dim = c_ast.ID(times_tok.value, self._tok_coord(times_tok))
            return make_array_decl(dim, [])

        dim = None
        if self._starts_expression():
            dim = self._parse_assignment_expression()
        self._expect("RBRACKET")
        return make_array_decl(dim, [])

    # BNF: function_decl : '(' parameter_type_list_opt | identifier_list_opt ')'
    def _parse_function_decl(self, base_decl: c_ast.Node) -> c_ast.Node:
        self._expect("LPAREN")
        if self._accept("RPAREN"):
            args = None
        else:
            args = (
                self._parse_parameter_type_list()
                if self._starts_declaration()
                else self._parse_identifier_list_opt()
            )
            self._expect("RPAREN")

        func = c_ast.FuncDecl(args=args, type=None, coord=base_decl.coord)

        if self._peek_type() == "LBRACE":
            if func.args is not None:
                for param in func.args.params:
                    if isinstance(param, c_ast.EllipsisParam):
                        break
                    name = getattr(param, "name", None)
                    if name:
                        self._add_identifier(name, param.coord)

        return func

    # BNF: pointer : '*' type_qualifier_list? pointer?
    def _parse_pointer(self) -> Optional[c_ast.Node]:
        stars = []
        times_tok = self._accept("TIMES")
        while times_tok:
            quals = self._parse_type_qualifier_list() or []
            stars.append((quals, self._tok_coord(times_tok)))
            times_tok = self._accept("TIMES")

        if not stars:
            return None

        ptr = None
        for quals, coord in stars:
            ptr = c_ast.PtrDecl(quals=quals, type=ptr, coord=coord)
        return ptr

    # BNF: parameter_type_list : parameter_list (',' ELLIPSIS)?
    def _parse_parameter_type_list(self) -> c_ast.ParamList:
        params = self._parse_parameter_list()
        if self._peek_type() == "COMMA" and self._peek_type(2) == "ELLIPSIS":
            self._advance()
            ell_tok = self._advance()
            params.params.append(c_ast.EllipsisParam(self._tok_coord(ell_tok)))
        return params

    # BNF: parameter_list : parameter_declaration (',' parameter_declaration)*
    def _parse_parameter_list(self) -> c_ast.ParamList:
        first = self._parse_parameter_declaration()
        params = c_ast.ParamList([first], first.coord)
        while self._peek_type() == "COMMA" and self._peek_type(2) != "ELLIPSIS":
            self._advance()
            params.params.append(self._parse_parameter_declaration())
        return params

    # BNF: parameter_declaration : declaration_specifiers declarator?
    #                            | declaration_specifiers abstract_declarator_opt
    def _parse_parameter_declaration(self) -> c_ast.Node:
        spec, _, spec_coord = self._parse_declaration_specifiers(allow_no_type=True)

        if not spec["type"]:
            spec["type"] = [c_ast.IdentifierType(["int"], coord=spec_coord)]

        if self._starts_declarator():
            decl, is_named = self._parse_any_declarator(
                allow_abstract=True, typeid_paren_as_abstract=True
            )
            if is_named:
                return self._build_declarations(
                    spec=spec, decls=[dict(decl=decl, init=None, bitsize=None)]
                )[0]
            return self._build_parameter_declaration(spec, decl, spec_coord)

        decl = self._parse_abstract_declarator_opt()
        return self._build_parameter_declaration(spec, decl, spec_coord)

    def _build_parameter_declaration(
        self, spec: "_DeclSpec", decl: Optional[c_ast.Node], spec_coord: Optional[Coord]
    ) -> c_ast.Node:
        if (
            len(spec["type"]) > 1
            and len(spec["type"][-1].names) == 1
            and self._is_type_in_scope(spec["type"][-1].names[0])
        ):
            return self._build_declarations(
                spec=spec, decls=[dict(decl=decl, init=None, bitsize=None)]
            )[0]

        decl = c_ast.Typename(
            name="",
            quals=spec["qual"],
            align=None,
            type=decl or c_ast.TypeDecl(None, None, None, None),
            coord=spec_coord,
        )
        return self._fix_decl_name_type(decl, spec["type"])

    # BNF: identifier_list_opt : identifier_list | empty
    def _parse_identifier_list_opt(self) -> Optional[c_ast.Node]:
        if self._peek_type() == "RPAREN":
            return None
        return self._parse_identifier_list()

    # BNF: identifier_list : identifier (',' identifier)*
    def _parse_identifier_list(self) -> c_ast.Node:
        first = self._parse_identifier()
        params = c_ast.ParamList([first], first.coord)
        while self._accept("COMMA"):
            params.params.append(self._parse_identifier())
        return params

    # ------------------------------------------------------------------
    # Abstract declarators
    # ------------------------------------------------------------------
    # BNF: type_name : specifier_qualifier_list abstract_declarator_opt
    def _parse_type_name(self) -> c_ast.Typename:
        spec = self._parse_specifier_qualifier_list()
        decl = self._parse_abstract_declarator_opt()

        coord = None
        if decl is not None:
            coord = decl.coord
        elif spec["type"]:
            coord = spec["type"][0].coord

        typename = c_ast.Typename(
            name="",
            quals=spec["qual"][:],
            align=None,
            type=decl or c_ast.TypeDecl(None, None, None, None),
            coord=coord,
        )
        return cast(c_ast.Typename, self._fix_decl_name_type(typename, spec["type"]))

    # BNF: abstract_declarator_opt : pointer? direct_abstract_declarator?
    def _parse_abstract_declarator_opt(self) -> Optional[c_ast.Node]:
        if self._peek_type() == "TIMES":
            ptr = self._parse_pointer()
            if self._starts_direct_abstract_declarator():
                decl = self._parse_direct_abstract_declarator()
            else:
                decl = c_ast.TypeDecl(None, None, None, None)
            assert ptr is not None
            return self._type_modify_decl(decl, ptr)

        if self._starts_direct_abstract_declarator():
            return self._parse_direct_abstract_declarator()

        return None

    # BNF: direct_abstract_declarator : '(' parameter_type_list_opt ')'
    #                                 | '(' abstract_declarator ')'
    #                                 | '[' ... ']'
    def _parse_direct_abstract_declarator(self) -> c_ast.Node:
        lparen_tok = self._accept("LPAREN")
        if lparen_tok:
            if self._starts_declaration() or self._peek_type() == "RPAREN":
                params = self._parse_parameter_type_list_opt()
                self._expect("RPAREN")
                decl = c_ast.FuncDecl(
                    args=params,
                    type=c_ast.TypeDecl(None, None, None, None),
                    coord=self._tok_coord(lparen_tok),
                )
            else:
                decl = self._parse_abstract_declarator_opt()
                self._expect("RPAREN")
                assert decl is not None
        elif self._peek_type() == "LBRACKET":
            decl = self._parse_abstract_array_base()
        else:
            self._parse_error("Invalid abstract declarator", self.clex.filename)

        return self._parse_decl_suffixes(decl)

    # BNF: parameter_type_list_opt : parameter_type_list | empty
    def _parse_parameter_type_list_opt(self) -> Optional[c_ast.ParamList]:
        if self._peek_type() == "RPAREN":
            return None
        return self._parse_parameter_type_list()

    # BNF: abstract_array_base : '[' array_specifiers? assignment_expression? ']'
    def _parse_abstract_array_base(self) -> c_ast.Node:
        return self._parse_array_decl_common(
            base_type=c_ast.TypeDecl(None, None, None, None), coord=None
        )

    # ------------------------------------------------------------------
    # Statements
    # ------------------------------------------------------------------
    # BNF: statement : labeled_statement | compound_statement
    #                | selection_statement | iteration_statement
    #                | jump_statement | expression_statement
    #                | static_assert | pppragma_directive
    def _parse_statement(self) -> c_ast.Node | List[c_ast.Node]:
        tok_type = self._peek_type()
        match tok_type:
            case "CASE" | "DEFAULT":
                return self._parse_labeled_statement()
            case "ID" if self._peek_type(2) == "COLON":
                return self._parse_labeled_statement()
            case "LBRACE":
                return self._parse_compound_statement()
            case "IF" | "SWITCH":
                return self._parse_selection_statement()
            case "WHILE" | "DO" | "FOR":
                return self._parse_iteration_statement()
            case "GOTO" | "BREAK" | "CONTINUE" | "RETURN":
                return self._parse_jump_statement()
            case "PPPRAGMA" | "_PRAGMA":
                return self._parse_pppragma_directive()
            case "_STATIC_ASSERT":
                return self._parse_static_assert()
            case _:
                return self._parse_expression_statement()

    # BNF: pragmacomp_or_statement : pppragma_directive* statement
    def _parse_pragmacomp_or_statement(self) -> c_ast.Node | List[c_ast.Node]:
        if self._peek_type() in {"PPPRAGMA", "_PRAGMA"}:
            pragmas = self._parse_pppragma_directive_list()
            stmt = self._parse_statement()
            return c_ast.Compound(block_items=pragmas + [stmt], coord=pragmas[0].coord)
        return self._parse_statement()

    # BNF: block_item : declaration | statement
    def _parse_block_item(self) -> c_ast.Node | List[c_ast.Node]:
        if self._starts_declaration():
            return self._parse_declaration()
        return self._parse_statement()

    # BNF: block_item_list : block_item+
    def _parse_block_item_list(self) -> List[c_ast.Node]:
        items = []
        while self._peek_type() not in {"RBRACE", None}:
            item = self._parse_block_item()
            if isinstance(item, list):
                if item == [None]:
                    continue
                items.extend(item)
            else:
                items.append(item)
        return items

    # BNF: compound_statement : '{' block_item_list? '}'
    def _parse_compound_statement(self) -> c_ast.Node:
        lbrace_tok = self._expect("LBRACE")
        if self._accept("RBRACE"):
            return c_ast.Compound(block_items=None, coord=self._tok_coord(lbrace_tok))
        block_items = self._parse_block_item_list()
        self._expect("RBRACE")
        return c_ast.Compound(
            block_items=block_items, coord=self._tok_coord(lbrace_tok)
        )

    # BNF: labeled_statement : ID ':' statement
    #                        | CASE constant_expression ':' statement
    #                        | DEFAULT ':' statement
    def _parse_labeled_statement(self) -> c_ast.Node:
        tok_type = self._peek_type()
        match tok_type:
            case "ID":
                name_tok = self._advance()
                self._expect("COLON")
                if self._starts_statement():
                    stmt = self._parse_pragmacomp_or_statement()
                else:
                    stmt = c_ast.EmptyStatement(self._tok_coord(name_tok))
                return c_ast.Label(name_tok.value, stmt, self._tok_coord(name_tok))
            case "CASE":
                case_tok = self._advance()
                expr = self._parse_constant_expression()
                self._expect("COLON")
                if self._starts_statement():
                    stmt = self._parse_pragmacomp_or_statement()
                else:
                    stmt = c_ast.EmptyStatement(self._tok_coord(case_tok))
                return c_ast.Case(expr, [stmt], self._tok_coord(case_tok))
            case "DEFAULT":
                def_tok = self._advance()
                self._expect("COLON")
                if self._starts_statement():
                    stmt = self._parse_pragmacomp_or_statement()
                else:
                    stmt = c_ast.EmptyStatement(self._tok_coord(def_tok))
                return c_ast.Default([stmt], self._tok_coord(def_tok))
            case _:
                self._parse_error("Invalid labeled statement", self.clex.filename)

    # BNF: selection_statement : IF '(' expression ')' statement (ELSE statement)?
    #                          | SWITCH '(' expression ')' statement
    def _parse_selection_statement(self) -> c_ast.Node:
        tok = self._advance()
        match tok.type:
            case "IF":
                self._expect("LPAREN")
                cond = self._parse_expression()
                self._expect("RPAREN")
                then_stmt = self._parse_pragmacomp_or_statement()
                if self._accept("ELSE"):
                    else_stmt = self._parse_pragmacomp_or_statement()
                    return c_ast.If(cond, then_stmt, else_stmt, self._tok_coord(tok))
                return c_ast.If(cond, then_stmt, None, self._tok_coord(tok))
            case "SWITCH":
                self._expect("LPAREN")
                expr = self._parse_expression()
                self._expect("RPAREN")
                stmt = self._parse_pragmacomp_or_statement()
                return fix_switch_cases(c_ast.Switch(expr, stmt, self._tok_coord(tok)))
            case _:
                self._parse_error("Invalid selection statement", self._tok_coord(tok))

    # BNF: iteration_statement : WHILE '(' expression ')' statement
    #                          | DO statement WHILE '(' expression ')' ';'
    #                          | FOR '(' (declaration | expression_opt) ';'
    #                                 expression_opt ';' expression_opt ')' statement
    def _parse_iteration_statement(self) -> c_ast.Node:
        tok = self._advance()
        match tok.type:
            case "WHILE":
                self._expect("LPAREN")
                cond = self._parse_expression()
                self._expect("RPAREN")
                stmt = self._parse_pragmacomp_or_statement()
                return c_ast.While(cond, stmt, self._tok_coord(tok))
            case "DO":
                stmt = self._parse_pragmacomp_or_statement()
                self._expect("WHILE")
                self._expect("LPAREN")
                cond = self._parse_expression()
                self._expect("RPAREN")
                self._expect("SEMI")
                return c_ast.DoWhile(cond, stmt, self._tok_coord(tok))
            case "FOR":
                self._expect("LPAREN")
                if self._starts_declaration():
                    decls = self._parse_declaration()
                    init = c_ast.DeclList(decls, self._tok_coord(tok))
                    cond = self._parse_expression_opt()
                    self._expect("SEMI")
                    next_expr = self._parse_expression_opt()
                    self._expect("RPAREN")
                    stmt = self._parse_pragmacomp_or_statement()
                    return c_ast.For(init, cond, next_expr, stmt, self._tok_coord(tok))

                init = self._parse_expression_opt()
                self._expect("SEMI")
                cond = self._parse_expression_opt()
                self._expect("SEMI")
                next_expr = self._parse_expression_opt()
                self._expect("RPAREN")
                stmt = self._parse_pragmacomp_or_statement()
                return c_ast.For(init, cond, next_expr, stmt, self._tok_coord(tok))
            case _:
                self._parse_error("Invalid iteration statement", self._tok_coord(tok))

    # BNF: jump_statement : GOTO ID ';' | BREAK ';' | CONTINUE ';'
    #                     | RETURN expression? ';'
    def _parse_jump_statement(self) -> c_ast.Node:
        tok = self._advance()
        match tok.type:
            case "GOTO":
                name_tok = self._expect("ID")
                self._expect("SEMI")
                return c_ast.Goto(name_tok.value, self._tok_coord(tok))
            case "BREAK":
                self._expect("SEMI")
                return c_ast.Break(self._tok_coord(tok))
            case "CONTINUE":
                self._expect("SEMI")
                return c_ast.Continue(self._tok_coord(tok))
            case "RETURN":
                if self._accept("SEMI"):
                    return c_ast.Return(None, self._tok_coord(tok))
                expr = self._parse_expression()
                self._expect("SEMI")
                return c_ast.Return(expr, self._tok_coord(tok))
            case _:
                self._parse_error("Invalid jump statement", self._tok_coord(tok))

    # BNF: expression_statement : expression_opt ';'
    def _parse_expression_statement(self) -> c_ast.Node:
        expr = self._parse_expression_opt()
        semi_tok = self._expect("SEMI")
        if expr is None:
            return c_ast.EmptyStatement(self._tok_coord(semi_tok))
        return expr

    # ------------------------------------------------------------------
    # Expressions
    # ------------------------------------------------------------------
    # BNF: expression_opt : expression | empty
    def _parse_expression_opt(self) -> Optional[c_ast.Node]:
        if self._starts_expression():
            return self._parse_expression()
        return None

    # BNF: expression : assignment_expression (',' assignment_expression)*
    def _parse_expression(self) -> c_ast.Node:
        expr = self._parse_assignment_expression()
        if not self._accept("COMMA"):
            return expr
        exprs = [expr, self._parse_assignment_expression()]
        while self._accept("COMMA"):
            exprs.append(self._parse_assignment_expression())
        return c_ast.ExprList(exprs, expr.coord)

    # BNF: assignment_expression : conditional_expression
    #                            | unary_expression assignment_op assignment_expression
    def _parse_assignment_expression(self) -> c_ast.Node:
        if self._peek_type() == "LPAREN" and self._peek_type(2) == "LBRACE":
            self._advance()
            comp = self._parse_compound_statement()
            self._expect("RPAREN")
            return comp

        expr = self._parse_conditional_expression()
        if self._is_assignment_op():
            op = self._advance().value
            rhs = self._parse_assignment_expression()
            return c_ast.Assignment(op, expr, rhs, expr.coord)
        return expr

    # BNF: conditional_expression : binary_expression
    #                            | binary_expression '?' expression ':' conditional_expression
    def _parse_conditional_expression(self) -> c_ast.Node:
        expr = self._parse_binary_expression()
        if self._accept("CONDOP"):
            iftrue = self._parse_expression()
            self._expect("COLON")
            iffalse = self._parse_conditional_expression()
            return c_ast.TernaryOp(expr, iftrue, iffalse, expr.coord)
        return expr

    # BNF: binary_expression : cast_expression (binary_op cast_expression)*
    def _parse_binary_expression(
        self, min_prec: int = 0, lhs: Optional[c_ast.Node] = None
    ) -> c_ast.Node:
        if lhs is None:
            lhs = self._parse_cast_expression()

        while True:
            tok = self._peek()
            if tok is None or tok.type not in _BINARY_PRECEDENCE:
                break
            prec = _BINARY_PRECEDENCE[tok.type]
            if prec < min_prec:
                break

            op = tok.value
            self._advance()
            rhs = self._parse_cast_expression()

            while True:
                next_tok = self._peek()
                if next_tok is None or next_tok.type not in _BINARY_PRECEDENCE:
                    break
                next_prec = _BINARY_PRECEDENCE[next_tok.type]
                if next_prec > prec:
                    rhs = self._parse_binary_expression(next_prec, rhs)
                else:
                    break

            lhs = c_ast.BinaryOp(op, lhs, rhs, lhs.coord)

        return lhs

    # BNF: cast_expression  : '(' type_name ')' cast_expression
    #                       | unary_expression
    def _parse_cast_expression(self) -> c_ast.Node:
        result = self._try_parse_paren_type_name()
        if result is not None:
            typ, mark, lparen_tok = result
            if self._peek_type() == "LBRACE":
                # (type){...} is a compound literal, not a cast. Examples:
                #   (int){1}      -> compound literal, handled in postfix
                #   (int) x       -> cast, handled below
                self._reset(mark)
            else:
                expr = self._parse_cast_expression()
                return c_ast.Cast(typ, expr, self._tok_coord(lparen_tok))
        return self._parse_unary_expression()

    # BNF: unary_expression : postfix_expression
    #                       | '++' unary_expression
    #                       | '--' unary_expression
    #                       | unary_op cast_expression
    #                       | 'sizeof' unary_expression
    #                       | 'sizeof' '(' type_name ')'
    #                       | '_Alignof' '(' type_name ')'
    def _parse_unary_expression(self) -> c_ast.Node:
        tok_type = self._peek_type()
        if tok_type in {"PLUSPLUS", "MINUSMINUS"}:
            tok = self._advance()
            expr = self._parse_unary_expression()
            return c_ast.UnaryOp(tok.value, expr, expr.coord)

        if tok_type in {"AND", "TIMES", "PLUS", "MINUS", "NOT", "LNOT"}:
            tok = self._advance()
            expr = self._parse_cast_expression()
            return c_ast.UnaryOp(tok.value, expr, expr.coord)

        if tok_type == "SIZEOF":
            tok = self._advance()
            result = self._try_parse_paren_type_name()
            if result is not None:
                typ, _, _ = result
                return c_ast.UnaryOp(tok.value, typ, self._tok_coord(tok))
            expr = self._parse_unary_expression()
            return c_ast.UnaryOp(tok.value, expr, self._tok_coord(tok))

        if tok_type == "_ALIGNOF":
            tok = self._advance()
            self._expect("LPAREN")
            typ = self._parse_type_name()
            self._expect("RPAREN")
            return c_ast.UnaryOp(tok.value, typ, self._tok_coord(tok))

        return self._parse_postfix_expression()

    # BNF: postfix_expression   : primary_expression postfix_suffix*
    #                           | '(' type_name ')' '{' initializer_list ','? '}'
    def _parse_postfix_expression(self) -> c_ast.Node:
        result = self._try_parse_paren_type_name()
        if result is not None:
            typ, mark, _ = result
            # Disambiguate between casts and compound literals:
            #   (int) x   -> cast
            #   (int) {1} -> compound literal
            if self._accept("LBRACE"):
                init = self._parse_initializer_list()
                self._accept("COMMA")
                self._expect("RBRACE")
                return c_ast.CompoundLiteral(typ, init)
            else:
                self._reset(mark)

        expr = self._parse_primary_expression()
        while True:
            if self._accept("LBRACKET"):
                sub = self._parse_expression()
                self._expect("RBRACKET")
                expr = c_ast.ArrayRef(expr, sub, expr.coord)
                continue
            if self._accept("LPAREN"):
                if self._peek_type() == "RPAREN":
                    self._advance()
                    args = None
                else:
                    args = self._parse_argument_expression_list()
                    self._expect("RPAREN")
                expr = c_ast.FuncCall(expr, args, expr.coord)
                continue
            if self._peek_type() in {"PERIOD", "ARROW"}:
                op_tok = self._advance()
                name_tok = self._advance()
                if name_tok.type not in {"ID", "TYPEID"}:
                    self._parse_error(
                        "Invalid struct reference", self._tok_coord(name_tok)
                    )
                field = c_ast.ID(name_tok.value, self._tok_coord(name_tok))
                expr = c_ast.StructRef(expr, op_tok.value, field, expr.coord)
                continue
            if self._peek_type() in {"PLUSPLUS", "MINUSMINUS"}:
                tok = self._advance()
                expr = c_ast.UnaryOp("p" + tok.value, expr, expr.coord)
                continue
            break
        return expr

    # BNF: primary_expression : ID | constant | string_literal
    #                        | '(' expression ')' | offsetof
    def _parse_primary_expression(self) -> c_ast.Node:
        tok_type = self._peek_type()
        if tok_type == "ID":
            return self._parse_identifier()
        if (
            tok_type in _INT_CONST
            or tok_type in _FLOAT_CONST
            or tok_type in _CHAR_CONST
        ):
            return self._parse_constant()
        if tok_type in _STRING_LITERAL:
            return self._parse_unified_string_literal()
        if tok_type in _WSTR_LITERAL:
            return self._parse_unified_wstring_literal()
        if tok_type == "LPAREN":
            self._advance()
            expr = self._parse_expression()
            self._expect("RPAREN")
            return expr
        if tok_type == "OFFSETOF":
            off_tok = self._advance()
            self._expect("LPAREN")
            typ = self._parse_type_name()
            self._expect("COMMA")
            designator = self._parse_offsetof_member_designator()
            self._expect("RPAREN")
            coord = self._tok_coord(off_tok)
            return c_ast.FuncCall(
                c_ast.ID(off_tok.value, coord),
                c_ast.ExprList([typ, designator], coord),
                coord,
            )

        self._parse_error("Invalid expression", self.clex.filename)

    # BNF: offsetof_member_designator : identifier_or_typeid
    #                                ('.' identifier_or_typeid | '[' expression ']')*
    def _parse_offsetof_member_designator(self) -> c_ast.Node:
        node = self._parse_identifier_or_typeid()
        while True:
            if self._accept("PERIOD"):
                field = self._parse_identifier_or_typeid()
                node = c_ast.StructRef(node, ".", field, node.coord)
                continue
            if self._accept("LBRACKET"):
                expr = self._parse_expression()
                self._expect("RBRACKET")
                node = c_ast.ArrayRef(node, expr, node.coord)
                continue
            break
        return node

    # BNF: argument_expression_list : assignment_expression (',' assignment_expression)*
    def _parse_argument_expression_list(self) -> c_ast.Node:
        expr = self._parse_assignment_expression()
        exprs = [expr]
        while self._accept("COMMA"):
            exprs.append(self._parse_assignment_expression())
        return c_ast.ExprList(exprs, expr.coord)

    # BNF: constant_expression : conditional_expression
    def _parse_constant_expression(self) -> c_ast.Node:
        return self._parse_conditional_expression()

    # ------------------------------------------------------------------
    # Terminals
    # ------------------------------------------------------------------
    # BNF: identifier : ID
    def _parse_identifier(self) -> c_ast.Node:
        tok = self._expect("ID")
        return c_ast.ID(tok.value, self._tok_coord(tok))

    # BNF: identifier_or_typeid : ID | TYPEID
    def _parse_identifier_or_typeid(self) -> c_ast.Node:
        tok = self._advance()
        if tok.type not in {"ID", "TYPEID"}:
            self._parse_error("Expected identifier", self._tok_coord(tok))
        return c_ast.ID(tok.value, self._tok_coord(tok))

    # BNF: constant : INT_CONST | FLOAT_CONST | CHAR_CONST
    def _parse_constant(self) -> c_ast.Node:
        tok = self._advance()
        if tok.type in _INT_CONST:
            u_count = 0
            l_count = 0
            for ch in tok.value[-3:]:
                if ch in ("l", "L"):
                    l_count += 1
                elif ch in ("u", "U"):
                    u_count += 1
            if u_count > 1:
                raise ValueError("Constant cannot have more than one u/U suffix.")
            if l_count > 2:
                raise ValueError("Constant cannot have more than two l/L suffix.")
            prefix = "unsigned " * u_count + "long " * l_count
            return c_ast.Constant(prefix + "int", tok.value, self._tok_coord(tok))

        if tok.type in _FLOAT_CONST:
            if tok.value[-1] in ("f", "F"):
                t = "float"
            elif tok.value[-1] in ("l", "L"):
                t = "long double"
            else:
                t = "double"
            return c_ast.Constant(t, tok.value, self._tok_coord(tok))

        if tok.type in _CHAR_CONST:
            return c_ast.Constant("char", tok.value, self._tok_coord(tok))

        self._parse_error("Invalid constant", self._tok_coord(tok))

    # BNF: unified_string_literal : STRING_LITERAL+
    def _parse_unified_string_literal(self) -> c_ast.Node:
        tok = self._expect("STRING_LITERAL")
        node = c_ast.Constant("string", tok.value, self._tok_coord(tok))
        while self._peek_type() == "STRING_LITERAL":
            tok2 = self._advance()
            node.value = node.value[:-1] + tok2.value[1:]
        return node

    # BNF: unified_wstring_literal : WSTRING_LITERAL+
    def _parse_unified_wstring_literal(self) -> c_ast.Node:
        tok = self._advance()
        if tok.type not in _WSTR_LITERAL:
            self._parse_error("Invalid string literal", self._tok_coord(tok))
        node = c_ast.Constant("string", tok.value, self._tok_coord(tok))
        while self._peek_type() in _WSTR_LITERAL:
            tok2 = self._advance()
            node.value = node.value.rstrip()[:-1] + tok2.value[2:]
        return node

    # ------------------------------------------------------------------
    # Initializers
    # ------------------------------------------------------------------
    # BNF: initializer : assignment_expression
    #                 | '{' initializer_list ','? '}'
    #                 | '{' '}'
    def _parse_initializer(self) -> c_ast.Node:
        lbrace_tok = self._accept("LBRACE")
        if lbrace_tok:
            if self._accept("RBRACE"):
                return c_ast.InitList([], self._tok_coord(lbrace_tok))
            init_list = self._parse_initializer_list()
            self._accept("COMMA")
            self._expect("RBRACE")
            return init_list

        return self._parse_assignment_expression()

    # BNF: initializer_list : initializer_item (',' initializer_item)* ','?
    def _parse_initializer_list(self) -> c_ast.Node:
        items = [self._parse_initializer_item()]
        while self._accept("COMMA"):
            if self._peek_type() == "RBRACE":
                break
            items.append(self._parse_initializer_item())
        return c_ast.InitList(items, items[0].coord)

    # BNF: initializer_item : designation? initializer
    def _parse_initializer_item(self) -> c_ast.Node:
        designation = None
        if self._peek_type() in {"LBRACKET", "PERIOD"}:
            designation = self._parse_designation()
        init = self._parse_initializer()
        if designation is not None:
            return c_ast.NamedInitializer(designation, init)
        return init

    # BNF: designation : designator_list '='
    def _parse_designation(self) -> List[c_ast.Node]:
        designators = self._parse_designator_list()
        self._expect("EQUALS")
        return designators

    # BNF: designator_list : designator+
    def _parse_designator_list(self) -> List[c_ast.Node]:
        designators = []
        while self._peek_type() in {"LBRACKET", "PERIOD"}:
            designators.append(self._parse_designator())
        return designators

    # BNF: designator : '[' constant_expression ']'
    #                | '.' identifier_or_typeid
    def _parse_designator(self) -> c_ast.Node:
        if self._accept("LBRACKET"):
            expr = self._parse_constant_expression()
            self._expect("RBRACKET")
            return expr
        if self._accept("PERIOD"):
            return self._parse_identifier_or_typeid()
        self._parse_error("Invalid designator", self.clex.filename)

    # ------------------------------------------------------------------
    # Preprocessor-like directives
    # ------------------------------------------------------------------
    # BNF: pp_directive : '#' ... (unsupported)
    def _parse_pp_directive(self) -> NoReturn:
        tok = self._expect("PPHASH")
        self._parse_error("Directives not supported yet", self._tok_coord(tok))

    # BNF: pppragma_directive : PPPRAGMA PPPRAGMASTR?
    #                        | _PRAGMA '(' string_literal ')'
    def _parse_pppragma_directive(self) -> c_ast.Node:
        if self._peek_type() == "PPPRAGMA":
            tok = self._advance()
            if self._peek_type() == "PPPRAGMASTR":
                str_tok = self._advance()
                return c_ast.Pragma(str_tok.value, self._tok_coord(str_tok))
            return c_ast.Pragma("", self._tok_coord(tok))

        if self._peek_type() == "_PRAGMA":
            tok = self._advance()
            lparen = self._expect("LPAREN")
            literal = self._parse_unified_string_literal()
            self._expect("RPAREN")
            return c_ast.Pragma(literal, self._tok_coord(lparen))

        self._parse_error("Invalid pragma", self.clex.filename)

    # BNF: pppragma_directive_list : pppragma_directive+
    def _parse_pppragma_directive_list(self) -> List[c_ast.Node]:
        pragmas = []
        while self._peek_type() in {"PPPRAGMA", "_PRAGMA"}:
            pragmas.append(self._parse_pppragma_directive())
        return pragmas

    # BNF: static_assert : _STATIC_ASSERT '(' constant_expression (',' string_literal)? ')'
    def _parse_static_assert(self) -> List[c_ast.Node]:
        tok = self._expect("_STATIC_ASSERT")
        self._expect("LPAREN")
        cond = self._parse_constant_expression()
        msg = None
        if self._accept("COMMA"):
            msg = self._parse_unified_string_literal()
        self._expect("RPAREN")
        return [c_ast.StaticAssert(cond, msg, self._tok_coord(tok))]


_ASSIGNMENT_OPS = {
    "EQUALS",
    "XOREQUAL",
    "TIMESEQUAL",
    "DIVEQUAL",
    "MODEQUAL",
    "PLUSEQUAL",
    "MINUSEQUAL",
    "LSHIFTEQUAL",
    "RSHIFTEQUAL",
    "ANDEQUAL",
    "OREQUAL",
}

# Precedence of operators (lower number = weather binding)
# If this changes, c_generator.CGenerator.precedence_map needs to change as
# well
_BINARY_PRECEDENCE = {
    "LOR": 0,
    "LAND": 1,
    "OR": 2,
    "XOR": 3,
    "AND": 4,
    "EQ": 5,
    "NE": 5,
    "GT": 6,
    "GE": 6,
    "LT": 6,
    "LE": 6,
    "RSHIFT": 7,
    "LSHIFT": 7,
    "PLUS": 8,
    "MINUS": 8,
    "TIMES": 9,
    "DIVIDE": 9,
    "MOD": 9,
}

_STORAGE_CLASS = {"AUTO", "REGISTER", "STATIC", "EXTERN", "TYPEDEF", "_THREAD_LOCAL"}

_FUNCTION_SPEC = {"INLINE", "_NORETURN"}

_TYPE_QUALIFIER = {"CONST", "RESTRICT", "VOLATILE", "_ATOMIC"}

_TYPE_SPEC_SIMPLE = {
    "VOID",
    "_BOOL",
    "CHAR",
    "SHORT",
    "INT",
    "LONG",
    "FLOAT",
    "DOUBLE",
    "_COMPLEX",
    "SIGNED",
    "UNSIGNED",
    "__INT128",
}

_DECL_START = (
    _STORAGE_CLASS
    | _FUNCTION_SPEC
    | _TYPE_QUALIFIER
    | _TYPE_SPEC_SIMPLE
    | {"TYPEID", "STRUCT", "UNION", "ENUM", "_ALIGNAS", "_ATOMIC"}
)

_EXPR_START = {
    "ID",
    "LPAREN",
    "PLUSPLUS",
    "MINUSMINUS",
    "PLUS",
    "MINUS",
    "TIMES",
    "AND",
    "NOT",
    "LNOT",
    "SIZEOF",
    "_ALIGNOF",
    "OFFSETOF",
}

_INT_CONST = {
    "INT_CONST_DEC",
    "INT_CONST_OCT",
    "INT_CONST_HEX",
    "INT_CONST_BIN",
    "INT_CONST_CHAR",
}

_FLOAT_CONST = {"FLOAT_CONST", "HEX_FLOAT_CONST"}

_CHAR_CONST = {
    "CHAR_CONST",
    "WCHAR_CONST",
    "U8CHAR_CONST",
    "U16CHAR_CONST",
    "U32CHAR_CONST",
}

_STRING_LITERAL = {"STRING_LITERAL"}

_WSTR_LITERAL = {
    "WSTRING_LITERAL",
    "U8STRING_LITERAL",
    "U16STRING_LITERAL",
    "U32STRING_LITERAL",
}

_STARTS_EXPRESSION = (
    _EXPR_START
    | _INT_CONST
    | _FLOAT_CONST
    | _CHAR_CONST
    | _STRING_LITERAL
    | _WSTR_LITERAL
)

_STARTS_STATEMENT = {
    "LBRACE",
    "IF",
    "SWITCH",
    "WHILE",
    "DO",
    "FOR",
    "GOTO",
    "BREAK",
    "CONTINUE",
    "RETURN",
    "CASE",
    "DEFAULT",
    "PPPRAGMA",
    "_PRAGMA",
    "_STATIC_ASSERT",
    "SEMI",
}


class _TokenStream:
    """Wraps a lexer to provide convenient, buffered access to the underlying
    token stream. The lexer is expected to be initialized with the input
    string already.
    """

    def __init__(self, lexer: CLexer) -> None:
        self._lexer = lexer
        self._buffer: List[Optional[_Token]] = []
        self._index = 0

    def peek(self, k: int = 1) -> Optional[_Token]:
        """Peek at the k-th next token in the stream, without consuming it.

        Examples:
            k=1 returns the immediate next token.
            k=2 returns the token after that.
        """
        if k <= 0:
            return None
        self._fill(k)
        return self._buffer[self._index + k - 1]

    def next(self) -> Optional[_Token]:
        """Consume a single token and return it."""
        self._fill(1)
        tok = self._buffer[self._index]
        self._index += 1
        return tok

    # The 'mark' and 'reset' methods are useful for speculative parsing with
    # backtracking; when the parser needs to examine a sequence of tokens
    # and potentially decide to try a different path on the same sequence, it
    # can call 'mark' to obtain the current token position, and if the first
    # path fails restore the position with `reset(pos)`.
    def mark(self) -> int:
        return self._index

    def reset(self, mark: int) -> None:
        self._index = mark

    def _fill(self, n: int) -> None:
        while len(self._buffer) < self._index + n:
            tok = self._lexer.token()
            self._buffer.append(tok)
            if tok is None:
                break


# Declaration specifiers are represented by a dictionary with entries:
# - qual: a list of type qualifiers
# - storage: a list of storage class specifiers
# - type: a list of type specifiers
# - function: a list of function specifiers
# - alignment: a list of alignment specifiers
class _DeclSpec(TypedDict):
    qual: List[Any]
    storage: List[Any]
    type: List[Any]
    function: List[Any]
    alignment: List[Any]


_DeclSpecKind = Literal["qual", "storage", "type", "function", "alignment"]


class _DeclInfo(TypedDict):
    # Declarator payloads used by declaration/initializer parsing:
    # - decl: the declarator node (may be None for abstract/implicit cases)
    # - init: optional initializer expression
    # - bitsize: optional bit-field width expression (for struct declarators)
    decl: Optional[c_ast.Node]
    init: Optional[c_ast.Node]
    bitsize: Optional[c_ast.Node]
