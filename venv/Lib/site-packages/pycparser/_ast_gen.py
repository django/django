# -----------------------------------------------------------------
# _ast_gen.py
#
# Generates the AST Node classes from a specification given in
# a configuration file. This module can also be run as a script to
# regenerate c_ast.py from _c_ast.cfg (from the repo root or the
# pycparser/ directory). Use 'make check' to reformat the generated
# file after running this script.
#
# The design of this module was inspired by astgen.py from the
# Python 2.5 code-base.
#
# Eli Bendersky [https://eli.thegreenplace.net/]
# License: BSD
# -----------------------------------------------------------------
from string import Template
import os
from typing import IO


class ASTCodeGenerator:
    def __init__(self, cfg_filename="_c_ast.cfg"):
        """Initialize the code generator from a configuration
        file.
        """
        self.cfg_filename = cfg_filename
        self.node_cfg = [
            NodeCfg(name, contents)
            for (name, contents) in self.parse_cfgfile(cfg_filename)
        ]

    def generate(self, file: IO[str]) -> None:
        """Generates the code into file, an open file buffer."""
        src = Template(_PROLOGUE_COMMENT).substitute(cfg_filename=self.cfg_filename)

        src += _PROLOGUE_CODE
        for node_cfg in self.node_cfg:
            src += node_cfg.generate_source() + "\n\n"

        file.write(src)

    def parse_cfgfile(self, filename):
        """Parse the configuration file and yield pairs of
        (name, contents) for each node.
        """
        with open(filename, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                colon_i = line.find(":")
                lbracket_i = line.find("[")
                rbracket_i = line.find("]")
                if colon_i < 1 or lbracket_i <= colon_i or rbracket_i <= lbracket_i:
                    raise RuntimeError(f"Invalid line in {filename}:\n{line}\n")

                name = line[:colon_i]
                val = line[lbracket_i + 1 : rbracket_i]
                vallist = [v.strip() for v in val.split(",")] if val else []
                yield name, vallist


class NodeCfg:
    """Node configuration.

    name: node name
    contents: a list of contents - attributes and child nodes
    See comment at the top of the configuration file for details.
    """

    def __init__(self, name, contents):
        self.name = name
        self.all_entries = []
        self.attr = []
        self.child = []
        self.seq_child = []

        for entry in contents:
            clean_entry = entry.rstrip("*")
            self.all_entries.append(clean_entry)

            if entry.endswith("**"):
                self.seq_child.append(clean_entry)
            elif entry.endswith("*"):
                self.child.append(clean_entry)
            else:
                self.attr.append(entry)

    def generate_source(self):
        src = self._gen_init()
        src += "\n" + self._gen_children()
        src += "\n" + self._gen_iter()
        src += "\n" + self._gen_attr_names()
        return src

    def _gen_init(self):
        src = f"class {self.name}(Node):\n"

        if self.all_entries:
            args = ", ".join(self.all_entries)
            slots = ", ".join(f"'{e}'" for e in self.all_entries)
            slots += ", 'coord', '__weakref__'"
            arglist = f"(self, {args}, coord=None)"
        else:
            slots = "'coord', '__weakref__'"
            arglist = "(self, coord=None)"

        src += f"    __slots__ = ({slots})\n"
        src += f"    def __init__{arglist}:\n"

        for name in self.all_entries + ["coord"]:
            src += f"        self.{name} = {name}\n"

        return src

    def _gen_children(self):
        src = "    def children(self):\n"

        if self.all_entries:
            src += "        nodelist = []\n"

            for child in self.child:
                src += f"        if self.{child} is not None:\n"
                src += f'            nodelist.append(("{child}", self.{child}))\n'

            for seq_child in self.seq_child:
                src += f"        for i, child in enumerate(self.{seq_child} or []):\n"
                src += f'            nodelist.append((f"{seq_child}[{{i}}]", child))\n'

            src += "        return tuple(nodelist)\n"
        else:
            src += "        return ()\n"

        return src

    def _gen_iter(self):
        src = "    def __iter__(self):\n"

        if self.all_entries:
            for child in self.child:
                src += f"        if self.{child} is not None:\n"
                src += f"            yield self.{child}\n"

            for seq_child in self.seq_child:
                src += f"        for child in (self.{seq_child} or []):\n"
                src += "            yield child\n"

            if not (self.child or self.seq_child):
                # Empty generator
                src += "        return\n" + "        yield\n"
        else:
            # Empty generator
            src += "        return\n" + "        yield\n"

        return src

    def _gen_attr_names(self):
        src = "    attr_names = (" + "".join(f"{nm!r}, " for nm in self.attr) + ")"
        return src


_PROLOGUE_COMMENT = r"""#-----------------------------------------------------------------
# ** ATTENTION **
# This code was automatically generated from _c_ast.cfg
#
# Do not modify it directly. Modify the configuration file and
# run the generator again.
# ** ** *** ** **
#
# pycparser: c_ast.py
#
# AST Node classes.
#
# Eli Bendersky [https://eli.thegreenplace.net/]
# License: BSD
#-----------------------------------------------------------------

"""
_PROLOGUE_CODE = r'''
import sys
from typing import Any, ClassVar, IO, Optional

def _repr(obj):
    """
    Get the representation of an object, with dedicated pprint-like format for lists.
    """
    if isinstance(obj, list):
        return '[' + (',\n '.join((_repr(e).replace('\n', '\n ') for e in obj))) + '\n]'
    else:
        return repr(obj)

class Node:
    __slots__ = ()
    """ Abstract base class for AST nodes.
    """
    attr_names: ClassVar[tuple[str, ...]] = ()
    coord: Optional[Any]
    def __repr__(self):
        """ Generates a python representation of the current node
        """
        result = self.__class__.__name__ + '('

        indent = ''
        separator = ''
        for name in self.__slots__[:-2]:
            result += separator
            result += indent
            result += name + '=' + (_repr(getattr(self, name)).replace('\n', '\n  ' + (' ' * (len(name) + len(self.__class__.__name__)))))

            separator = ','
            indent = '\n ' + (' ' * len(self.__class__.__name__))

        result += indent + ')'

        return result

    def children(self):
        """ A sequence of all children that are Nodes
        """
        pass

    def show(
        self,
        buf: IO[str] = sys.stdout,
        offset: int = 0,
        attrnames: bool = False,
        showemptyattrs: bool = True,
        nodenames: bool = False,
        showcoord: bool = False,
        _my_node_name: Optional[str] = None,
    ):
        """ Pretty print the Node and all its attributes and
            children (recursively) to a buffer.

            buf:
                Open IO buffer into which the Node is printed.

            offset:
                Initial offset (amount of leading spaces)

            attrnames:
                True if you want to see the attribute names in
                name=value pairs. False to only see the values.

            showemptyattrs:
                False if you want to suppress printing empty attributes.

            nodenames:
                True if you want to see the actual node names
                within their parents.

            showcoord:
                Do you want the coordinates of each Node to be
                displayed.
        """
        lead = ' ' * offset
        if nodenames and _my_node_name is not None:
            buf.write(lead + self.__class__.__name__+ ' <' + _my_node_name + '>: ')
        else:
            buf.write(lead + self.__class__.__name__+ ': ')

        if self.attr_names:
            def is_empty(v):
                v is None or (hasattr(v, '__len__') and len(v) == 0)
            nvlist = [(n, getattr(self,n)) for n in self.attr_names \
                        if showemptyattrs or not is_empty(getattr(self,n))]
            if attrnames:
                attrstr = ', '.join(f'{name}={value}' for name, value in nvlist)
            else:
                attrstr = ', '.join(f'{value}' for _, value in nvlist)
            buf.write(attrstr)

        if showcoord:
            buf.write(f' (at {self.coord})')
        buf.write('\n')

        for (child_name, child) in self.children():
            child.show(
                buf,
                offset=offset + 2,
                attrnames=attrnames,
                showemptyattrs=showemptyattrs,
                nodenames=nodenames,
                showcoord=showcoord,
                _my_node_name=child_name)


class NodeVisitor:
    """ A base NodeVisitor class for visiting c_ast nodes.
        Subclass it and define your own visit_XXX methods, where
        XXX is the class name you want to visit with these
        methods.

        For example:

        class ConstantVisitor(NodeVisitor):
            def __init__(self):
                self.values = []

            def visit_Constant(self, node):
                self.values.append(node.value)

        Creates a list of values of all the constant nodes
        encountered below the given node. To use it:

        cv = ConstantVisitor()
        cv.visit(node)

        Notes:

        *   generic_visit() will be called for AST nodes for which
            no visit_XXX method was defined.
        *   The children of nodes for which a visit_XXX was
            defined will not be visited - if you need this, call
            generic_visit() on the node.
            You can use:
                NodeVisitor.generic_visit(self, node)
        *   Modeled after Python's own AST visiting facilities
            (the ast module of Python 3.0)
    """

    _method_cache = None

    def visit(self, node: Node):
        """ Visit a node.
        """

        if self._method_cache is None:
            self._method_cache = {}

        visitor = self._method_cache.get(node.__class__.__name__, None)
        if visitor is None:
            method = 'visit_' + node.__class__.__name__
            visitor = getattr(self, method, self.generic_visit)
            self._method_cache[node.__class__.__name__] = visitor

        return visitor(node)

    def generic_visit(self, node: Node):
        """ Called if no explicit visitor function exists for a
            node. Implements preorder visiting of the node.
        """
        for _, c in node.children():
            self.visit(c)

'''


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    cfg_path = os.path.join(base_dir, "_c_ast.cfg")
    out_path = os.path.join(base_dir, "c_ast.py")
    ast_gen = ASTCodeGenerator(cfg_path)
    with open(out_path, "w") as out:
        ast_gen.generate(out)
