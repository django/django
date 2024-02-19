"""Utility functions for math."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from docutils import nodes

    from sphinx.builders.html import HTML5Translator


def get_node_equation_number(writer: HTML5Translator, node: nodes.math_block) -> str:
    if writer.builder.config.math_numfig and writer.builder.config.numfig:
        figtype = 'displaymath'
        if writer.builder.name == 'singlehtml':
            key = f"{writer.docnames[-1]}/{figtype}"  # type: ignore[has-type]
        else:
            key = figtype

        id = node['ids'][0]
        number = writer.builder.fignumbers.get(key, {}).get(id, ())
        return '.'.join(map(str, number))
    else:
        return node['number']


def wrap_displaymath(text: str, label: str | None, numbering: bool) -> str:
    def is_equation(part: str) -> str:
        return part.strip()

    if label is None:
        labeldef = ''
    else:
        labeldef = r'\label{%s}' % label
        numbering = True

    parts = list(filter(is_equation, text.split('\n\n')))
    equations = []
    if len(parts) == 0:
        return ''
    elif len(parts) == 1:
        if numbering:
            begin = r'\begin{equation}' + labeldef
            end = r'\end{equation}'
        else:
            begin = r'\begin{equation*}' + labeldef
            end = r'\end{equation*}'
        equations.append('\\begin{split}%s\\end{split}\n' % parts[0])
    else:
        if numbering:
            begin = r'\begin{align}%s\!\begin{aligned}' % labeldef
            end = r'\end{aligned}\end{align}'
        else:
            begin = r'\begin{align*}%s\!\begin{aligned}' % labeldef
            end = r'\end{aligned}\end{align*}'
        for part in parts:
            equations.append('%s\\\\\n' % part.strip())

    concatenated_equations = ''.join(equations)
    return f'{begin}\n{concatenated_equations}{end}'
