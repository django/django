"""
    autoprogramm
    ~~~~~~~~~~~~

    ``autoprogram-modified`` (hence the two "m"s at the end of the name.)

    Documenting CLI programs.

    Adapted & simplified from https://github.com/sphinx-contrib/autoprogram

    Besides the name change, here is a summary of the changes:
    * Remove unit testing
    * Remove .lower() when processing metavar/desc
    * Add setup() return dict
    * Add :notitle:
    * Add :nodesc:
    * Add :options_title:
    * Add :options_adornment:
    * black-ification

    **WARNING:** This is custom-stripped for aiosmtpd; using this custom extension
    outside of aiosmtpd might not work. Check the code! The aiosmtpd Developers will
    NOT provide ANY kind of support with this custom extension; it is just hacked
    together in a half-day by pepoluan <== all blame goes to him!

    :copyright: Copyright 2014 by Hong Minhee
    :license: BSD

"""
import argparse
import builtins
import collections
import os
from functools import reduce
from typing import Any, Dict, Iterable, List, Optional, Tuple

import sphinx
from docutils import nodes  # pytype: disable=pyi-error
from docutils.parsers.rst import Directive  # pytype: disable=pyi-error
from docutils.parsers.rst.directives import unchanged  # pytype: disable=pyi-error
from docutils.statemachine import StringList
from sphinx.util.nodes import nested_parse_with_titles


__all__ = ("AutoprogrammDirective", "import_object", "scan_programs", "setup")


# Need to temporarily disable this particular check, because although this function
# is guaranteed to return a proper value (due to how ArgumentParser works), pytype
# doesn't really know that, and therefore raised an error  in the (to its view)
# possible fallthrough of "implicit return None" if the "for a" loop exits without
# finding the right item.
#
# pytype: disable=bad-return-type
def get_subparser_action(
    parser: argparse.ArgumentParser
) -> Optional[argparse._SubParsersAction]:
    neg1_action = parser._actions[-1]

    if isinstance(neg1_action, argparse._SubParsersAction):
        return neg1_action

    for a in parser._actions:
        if isinstance(a, argparse._SubParsersAction):
            return a
    return None
# pytype: enable=bad-return-type


def scan_programs(
    parser: argparse.ArgumentParser,
    command: Optional[List[str]] = None,
    maxdepth: int = 0,
    depth: int = 0,
    groups: bool = False,
):
    if command is None:
        command = []

    if maxdepth and depth >= maxdepth:
        return

    if groups:
        yield command, [], parser
        for group in parser._action_groups:
            options = list(scan_options(group._group_actions))
            if options:
                yield command, options, group
    else:
        options = list(scan_options(parser._actions))
        yield command, options, parser

    if parser._subparsers:
        choices: Iterable[tuple[str, int]] = ()

        subp_action = get_subparser_action(parser)

        if subp_action:
            # noinspection PyUnresolvedReferences
            choices = subp_action.choices.items()

        if not isinstance(choices, collections.OrderedDict):
            choices = sorted(choices, key=lambda pair: pair[0])

        for cmd, sub in choices:
            if isinstance(sub, argparse.ArgumentParser):
                yield from scan_programs(sub, command + [cmd], maxdepth, depth + 1)


def scan_options(actions: list):
    for arg in actions:
        if not (arg.option_strings or isinstance(arg, argparse._SubParsersAction)):
            yield format_positional_argument(arg)

    for arg in actions:
        if arg.option_strings and arg.help is not argparse.SUPPRESS:
            yield format_option(arg)


def format_positional_argument(arg: argparse.Action) -> Tuple[List[str], str]:
    desc: str = (arg.help or "") % {"default": arg.default}
    name: str
    if isinstance(arg.metavar, tuple):
        name = arg.metavar[0]
    else:
        name = arg.metavar or arg.dest or ""
    return [name], desc


def format_option(arg: argparse.Action) -> Tuple[List[str], str]:
    desc = (arg.help or "") % {"default": arg.default}

    if not isinstance(arg, (argparse._StoreAction, argparse._AppendAction)):
        names = list(arg.option_strings)
        return names, desc

    if arg.choices is not None:
        value = "{{{0}}}".format(",".join(str(c) for c in arg.choices))
    else:
        metavar = arg.metavar or arg.dest
        if not isinstance(metavar, tuple):
            metavar = (metavar,)
        value = "<{0}>".format("> <".join(metavar))

    names = [
        "{0} {1}".format(option_string, value) for option_string in arg.option_strings
    ]

    return names, desc


def import_object(import_name: str) -> Any:
    module_name, expr = import_name.split(":", 1)
    try:
        mod = __import__(module_name)
    except ImportError:
        # This happens if the file is a script with no .py extension. Here we
        # trick autoprogram to load a module in memory with the contents of
        # the script, if there is a script named module_name. Otherwise, raise
        # an ImportError as it did before.
        import glob
        import sys
        import imp

        for p in sys.path:
            f = glob.glob(os.path.join(p, module_name))
            if len(f) > 0:
                with open(f[0]) as fobj:
                    codestring = fobj.read()
                foo = imp.new_module("foo")
                # noinspection BuiltinExec
                exec(codestring, foo.__dict__)  # noqa: DUO105  # nosec

                sys.modules["foo"] = foo
                mod = __import__("foo")
                break
        else:
            raise ImportError("No module named {}".format(module_name))

    mod = reduce(getattr, module_name.split(".")[1:], mod)
    globals_ = builtins
    if not isinstance(globals_, dict):
        globals_ = globals_.__dict__  # type: ignore[assignment]
    return eval(expr, globals_, mod.__dict__)  # type: ignore[arg-type]  # noqa: DUO104  # nosec


class AutoprogrammDirective(Directive):

    has_content = False
    required_arguments = 1
    option_spec = {
        "prog": unchanged,
        "maxdepth": unchanged,
        "start_command": unchanged,
        "strip_usage": unchanged,
        "no_usage_codeblock": unchanged,
        "groups": unchanged,
        "notitle": unchanged,
        "nodesc": unchanged,
        "options_title": unchanged,
        "options_adornment": unchanged,
    }

    def make_rst(self):
        (import_name,) = self.arguments
        parser = import_object(import_name or "__undefined__")
        prog = self.options.get("prog")
        original_prog = None
        if prog:
            original_prog = parser.prog
            parser.prog = prog
        start_command = self.options.get("start_command", "").split(" ")
        strip_usage = "strip_usage" in self.options
        usage_codeblock = "no_usage_codeblock" not in self.options
        maxdepth = int(self.options.get("maxdepth", 0))
        groups = "groups" in self.options
        options_title = self.options.get("options_title")
        options_adornment = self.options.get("options_adornment", "~")

        if start_command[0] == "":
            start_command.pop(0)

        if start_command:

            def get_start_cmd_parser(
                p: argparse.ArgumentParser,
            ) -> argparse.ArgumentParser:
                looking_for = start_command.pop(0)
                action = get_subparser_action(p)

                if not action:
                    raise ValueError("No actions for command " + looking_for)

                # noinspection PyUnresolvedReferences
                subp = action.choices[looking_for]

                if start_command:
                    return get_start_cmd_parser(subp)

                return subp

            parser = get_start_cmd_parser(parser)
            if prog and parser.prog.startswith(original_prog):
                parser.prog = parser.prog.replace(original_prog, prog, 1)

        for commands, options, group_or_parser in scan_programs(
            parser, maxdepth=maxdepth, groups=groups
        ):
            if isinstance(group_or_parser, argparse._ArgumentGroup):
                title = group_or_parser.title
                description = group_or_parser.description
                usage = None
                epilog = None
                is_subgroup = True
                is_program = False
            else:
                cmd_parser = group_or_parser
                if prog and cmd_parser.prog.startswith(original_prog):
                    cmd_parser.prog = cmd_parser.prog.replace(original_prog, prog, 1)
                title = cmd_parser.prog.rstrip()
                description = cmd_parser.description
                usage = cmd_parser.format_usage()
                epilog = cmd_parser.epilog
                is_subgroup = bool(commands)
                is_program = True

            if "notitle" in self.options:
                title = None

            if "nodesc" in self.options:
                description = None

            yield from render_rst(
                title,
                options,
                is_program=is_program,
                is_subgroup=is_subgroup,
                description=description,
                usage=usage,
                usage_strip=strip_usage,
                usage_codeblock=usage_codeblock,
                epilog=epilog,
                options_title=options_title,
                options_adornment=options_adornment,
            )

    def run(self) -> list:
        node = nodes.section()
        node.document = self.state.document
        result = StringList()
        for line in self.make_rst():
            result.append(line, "<autoprogram>")
        nested_parse_with_titles(self.state, result, node)
        return node.children


def render_rst(
    title: Optional[str],
    options: List[Tuple[List[str], str]],
    is_program: bool,
    is_subgroup: bool,
    description: Optional[str],
    usage: Optional[str],
    usage_strip: bool,
    usage_codeblock: bool,
    epilog: Optional[str],
    options_title: str,
    options_adornment: str,
):
    if usage_strip:
        assert usage is not None
        to_strip = (title or "").rsplit(" ", 1)[0]

        len_to_strip = len(to_strip) - 4
        usage_lines: List[str] = usage.splitlines()

        usage = os.linesep.join(
            [
                usage_lines[0].replace(to_strip, "..."),
            ]
            + [line[len_to_strip:] for line in usage_lines[1:]]
        )

    yield ""

    if title is not None:
        if is_program:
            yield ".. program:: " + title
            yield ""

        yield title
        yield ("!" if is_subgroup else "?") * len(title)
        yield ""

    yield from (description or "").splitlines()
    yield ""

    if usage is None:
        pass
    elif usage_codeblock:
        yield ".. code-block:: console"
        yield ""
        for usage_line in usage.splitlines():
            yield "   " + usage_line
    else:
        yield usage

    yield ""

    if options_title:
        yield options_title
        yield options_adornment * len(options_title)

    for option_strings, help_ in options:
        yield ".. option:: {0}".format(", ".join(option_strings))
        yield ""
        yield "   " + help_.replace("\n", "   \n")
        yield ""

    for line in (epilog or "").splitlines():
        yield line or ""


def setup(app: sphinx.application.Sphinx) -> Dict[str, Any]:
    app.add_directive("autoprogramm", AutoprogrammDirective)
    return {
        "version": "0.2a0",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
