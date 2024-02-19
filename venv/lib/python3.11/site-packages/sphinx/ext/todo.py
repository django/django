"""Allow todos to be inserted into your documentation.

Inclusion of todos can be switched of by a configuration variable.
The todolist directive collects all todos of your project and lists them along
with a backlink to the original location.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from docutils import nodes
from docutils.parsers.rst import directives
from docutils.parsers.rst.directives.admonitions import BaseAdmonition

import sphinx
from sphinx import addnodes
from sphinx.domains import Domain
from sphinx.errors import NoUri
from sphinx.locale import _, __
from sphinx.util import logging, texescape
from sphinx.util.docutils import SphinxDirective, new_document

if TYPE_CHECKING:
    from docutils.nodes import Element, Node

    from sphinx.application import Sphinx
    from sphinx.environment import BuildEnvironment
    from sphinx.util.typing import OptionSpec
    from sphinx.writers.html import HTML5Translator
    from sphinx.writers.latex import LaTeXTranslator

logger = logging.getLogger(__name__)


class todo_node(nodes.Admonition, nodes.Element):
    pass


class todolist(nodes.General, nodes.Element):
    pass


class Todo(BaseAdmonition, SphinxDirective):
    """
    A todo entry, displayed (if configured) in the form of an admonition.
    """

    node_class = todo_node
    has_content = True
    required_arguments = 0
    optional_arguments = 0
    final_argument_whitespace = False
    option_spec: OptionSpec = {
        'class': directives.class_option,
        'name': directives.unchanged,
    }

    def run(self) -> list[Node]:
        if not self.options.get('class'):
            self.options['class'] = ['admonition-todo']

        (todo,) = super().run()
        if isinstance(todo, nodes.system_message):
            return [todo]
        elif isinstance(todo, todo_node):
            todo.insert(0, nodes.title(text=_('Todo')))
            todo['docname'] = self.env.docname
            self.add_name(todo)
            self.set_source_info(todo)
            self.state.document.note_explicit_target(todo)
            return [todo]
        else:
            raise RuntimeError  # never reached here


class TodoDomain(Domain):
    name = 'todo'
    label = 'todo'

    @property
    def todos(self) -> dict[str, list[todo_node]]:
        return self.data.setdefault('todos', {})

    def clear_doc(self, docname: str) -> None:
        self.todos.pop(docname, None)

    def merge_domaindata(self, docnames: list[str], otherdata: dict) -> None:
        for docname in docnames:
            self.todos[docname] = otherdata['todos'][docname]

    def process_doc(self, env: BuildEnvironment, docname: str,
                    document: nodes.document) -> None:
        todos = self.todos.setdefault(docname, [])
        for todo in document.findall(todo_node):
            env.app.emit('todo-defined', todo)
            todos.append(todo)

            if env.config.todo_emit_warnings:
                logger.warning(__("TODO entry found: %s"), todo[1].astext(),
                               location=todo)


class TodoList(SphinxDirective):
    """
    A list of all todo entries.
    """

    has_content = False
    required_arguments = 0
    optional_arguments = 0
    final_argument_whitespace = False
    option_spec: OptionSpec = {}

    def run(self) -> list[Node]:
        # Simply insert an empty todolist node which will be replaced later
        # when process_todo_nodes is called
        return [todolist('')]


class TodoListProcessor:
    def __init__(self, app: Sphinx, doctree: nodes.document, docname: str) -> None:
        self.builder = app.builder
        self.config = app.config
        self.env = app.env
        self.domain = cast(TodoDomain, app.env.get_domain('todo'))
        self.document = new_document('')

        self.process(doctree, docname)

    def process(self, doctree: nodes.document, docname: str) -> None:
        todos: list[todo_node] = sum(self.domain.todos.values(), [])
        for node in list(doctree.findall(todolist)):
            if not self.config.todo_include_todos:
                node.parent.remove(node)
                continue

            if node.get('ids'):
                content: list[Element] = [nodes.target()]
            else:
                content = []

            for todo in todos:
                # Create a copy of the todo node
                new_todo = todo.deepcopy()
                new_todo['ids'].clear()

                self.resolve_reference(new_todo, docname)
                content.append(new_todo)

                todo_ref = self.create_todo_reference(todo, docname)
                content.append(todo_ref)

            node.replace_self(content)

    def create_todo_reference(self, todo: todo_node, docname: str) -> nodes.paragraph:
        if self.config.todo_link_only:
            description = _('<<original entry>>')
        else:
            description = (_('(The <<original entry>> is located in %s, line %d.)') %
                           (todo.source, todo.line))

        prefix = description[:description.find('<<')]
        suffix = description[description.find('>>') + 2:]

        para = nodes.paragraph(classes=['todo-source'])
        para += nodes.Text(prefix)

        # Create a reference
        linktext = nodes.emphasis(_('original entry'), _('original entry'))
        reference = nodes.reference('', '', linktext, internal=True)
        try:
            reference['refuri'] = self.builder.get_relative_uri(docname, todo['docname'])
            reference['refuri'] += '#' + todo['ids'][0]
        except NoUri:
            # ignore if no URI can be determined, e.g. for LaTeX output
            pass

        para += reference
        para += nodes.Text(suffix)

        return para

    def resolve_reference(self, todo: todo_node, docname: str) -> None:
        """Resolve references in the todo content."""
        for node in todo.findall(addnodes.pending_xref):
            if 'refdoc' in node:
                node['refdoc'] = docname

        # Note: To resolve references, it is needed to wrap it with document node
        self.document += todo
        self.env.resolve_references(self.document, docname, self.builder)
        self.document.remove(todo)


def visit_todo_node(self: HTML5Translator, node: todo_node) -> None:
    if self.config.todo_include_todos:
        self.visit_admonition(node)
    else:
        raise nodes.SkipNode


def depart_todo_node(self: HTML5Translator, node: todo_node) -> None:
    self.depart_admonition(node)


def latex_visit_todo_node(self: LaTeXTranslator, node: todo_node) -> None:
    if self.config.todo_include_todos:
        self.body.append('\n\\begin{sphinxadmonition}{note}{')
        self.body.append(self.hypertarget_to(node))

        title_node = cast(nodes.title, node[0])
        title = texescape.escape(title_node.astext(), self.config.latex_engine)
        self.body.append('%s:}' % title)
        node.pop(0)
    else:
        raise nodes.SkipNode


def latex_depart_todo_node(self: LaTeXTranslator, node: todo_node) -> None:
    self.body.append('\\end{sphinxadmonition}\n')


def setup(app: Sphinx) -> dict[str, Any]:
    app.add_event('todo-defined')
    app.add_config_value('todo_include_todos', False, 'html')
    app.add_config_value('todo_link_only', False, 'html')
    app.add_config_value('todo_emit_warnings', False, 'html')

    app.add_node(todolist)
    app.add_node(todo_node,
                 html=(visit_todo_node, depart_todo_node),
                 latex=(latex_visit_todo_node, latex_depart_todo_node),
                 text=(visit_todo_node, depart_todo_node),
                 man=(visit_todo_node, depart_todo_node),
                 texinfo=(visit_todo_node, depart_todo_node))

    app.add_directive('todo', Todo)
    app.add_directive('todolist', TodoList)
    app.add_domain(TodoDomain)
    app.connect('doctree-resolved', TodoListProcessor)
    return {
        'version': sphinx.__display_version__,
        'env_version': 2,
        'parallel_read_safe': True,
    }
