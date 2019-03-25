# -*- coding: utf-8 -*-
"""
    sphinx.ext.todo
    ~~~~~~~~~~~~~~~

    Allow todos to be inserted into your documentation.  Inclusion of todos can
    be switched of by a configuration variable.  The todolist directive collects
    all todos of your project and lists them along with a backlink to the
    original location.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from docutils import nodes
from docutils.parsers.rst import directives
from docutils.parsers.rst.directives.admonitions import BaseAdmonition

import sphinx
from sphinx.environment import NoUri
from sphinx.locale import _, __
from sphinx.util import logging
from sphinx.util.docutils import SphinxDirective
from sphinx.util.nodes import set_source_info
from sphinx.util.texescape import tex_escape_map

if False:
    # For type annotation
    from typing import Any, Dict, Iterable, List  # NOQA
    from sphinx.application import Sphinx  # NOQA
    from sphinx.environment import BuildEnvironment  # NOQA

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
    option_spec = {
        'class': directives.class_option,
    }

    def run(self):
        # type: () -> List[nodes.Node]
        if not self.options.get('class'):
            self.options['class'] = ['admonition-todo']

        (todo,) = super(Todo, self).run()
        if isinstance(todo, nodes.system_message):
            return [todo]

        todo.insert(0, nodes.title(text=_('Todo')))
        set_source_info(self, todo)

        targetid = 'index-%s' % self.env.new_serialno('index')
        # Stash the target to be retrieved later in latex_visit_todo_node.
        todo['targetref'] = '%s:%s' % (self.env.docname, targetid)
        targetnode = nodes.target('', '', ids=[targetid])
        return [targetnode, todo]


def process_todos(app, doctree):
    # type: (Sphinx, nodes.Node) -> None
    # collect all todos in the environment
    # this is not done in the directive itself because it some transformations
    # must have already been run, e.g. substitutions
    env = app.builder.env
    if not hasattr(env, 'todo_all_todos'):
        env.todo_all_todos = []  # type: ignore
    for node in doctree.traverse(todo_node):
        app.emit('todo-defined', node)

        try:
            targetnode = node.parent[node.parent.index(node) - 1]
            if not isinstance(targetnode, nodes.target):
                raise IndexError
        except IndexError:
            targetnode = None
        newnode = node.deepcopy()
        del newnode['ids']
        env.todo_all_todos.append({  # type: ignore
            'docname': env.docname,
            'source': node.source or env.doc2path(env.docname),
            'lineno': node.line,
            'todo': newnode,
            'target': targetnode,
        })

        if env.config.todo_emit_warnings:
            logger.warning(__("TODO entry found: %s"), node[1].astext(),
                           location=node)


class TodoList(SphinxDirective):
    """
    A list of all todo entries.
    """

    has_content = False
    required_arguments = 0
    optional_arguments = 0
    final_argument_whitespace = False
    option_spec = {}  # type: Dict

    def run(self):
        # type: () -> List[todolist]
        # Simply insert an empty todolist node which will be replaced later
        # when process_todo_nodes is called
        return [todolist('')]


def process_todo_nodes(app, doctree, fromdocname):
    # type: (Sphinx, nodes.Node, unicode) -> None
    if not app.config['todo_include_todos']:
        for node in doctree.traverse(todo_node):
            node.parent.remove(node)

    # Replace all todolist nodes with a list of the collected todos.
    # Augment each todo with a backlink to the original location.
    env = app.builder.env

    if not hasattr(env, 'todo_all_todos'):
        env.todo_all_todos = []  # type: ignore

    for node in doctree.traverse(todolist):
        if node.get('ids'):
            content = [nodes.target()]
        else:
            content = []

        if not app.config['todo_include_todos']:
            node.replace_self(content)
            continue

        for todo_info in env.todo_all_todos:  # type: ignore
            para = nodes.paragraph(classes=['todo-source'])
            if app.config['todo_link_only']:
                description = _('<<original entry>>')
            else:
                description = (
                    _('(The <<original entry>> is located in %s, line %d.)') %
                    (todo_info['source'], todo_info['lineno'])
                )
            desc1 = description[:description.find('<<')]
            desc2 = description[description.find('>>') + 2:]
            para += nodes.Text(desc1, desc1)

            # Create a reference
            newnode = nodes.reference('', '', internal=True)
            innernode = nodes.emphasis(_('original entry'), _('original entry'))
            try:
                newnode['refuri'] = app.builder.get_relative_uri(
                    fromdocname, todo_info['docname'])
                if 'refid' in todo_info['target']:
                    newnode['refuri'] += '#' + todo_info['target']['refid']
                else:
                    newnode['refuri'] += '#' + todo_info['target']['ids'][0]
            except NoUri:
                # ignore if no URI can be determined, e.g. for LaTeX output
                pass
            newnode.append(innernode)
            para += newnode
            para += nodes.Text(desc2, desc2)

            todo_entry = todo_info['todo']
            # Remove targetref from the (copied) node to avoid emitting a
            # duplicate label of the original entry when we walk this node.
            if 'targetref' in todo_entry:
                del todo_entry['targetref']

            # (Recursively) resolve references in the todo content
            env.resolve_references(todo_entry, todo_info['docname'],
                                   app.builder)

            # Insert into the todolist
            content.append(todo_entry)
            content.append(para)

        node.replace_self(content)


def purge_todos(app, env, docname):
    # type: (Sphinx, BuildEnvironment, unicode) -> None
    if not hasattr(env, 'todo_all_todos'):
        return
    env.todo_all_todos = [todo for todo in env.todo_all_todos  # type: ignore
                          if todo['docname'] != docname]


def merge_info(app, env, docnames, other):
    # type: (Sphinx, BuildEnvironment, Iterable[unicode], BuildEnvironment) -> None
    if not hasattr(other, 'todo_all_todos'):
        return
    if not hasattr(env, 'todo_all_todos'):
        env.todo_all_todos = []  # type: ignore
    env.todo_all_todos.extend(other.todo_all_todos)  # type: ignore


def visit_todo_node(self, node):
    # type: (nodes.NodeVisitor, todo_node) -> None
    self.visit_admonition(node)
    # self.visit_admonition(node, 'todo')


def depart_todo_node(self, node):
    # type: (nodes.NodeVisitor, todo_node) -> None
    self.depart_admonition(node)


def latex_visit_todo_node(self, node):
    # type: (nodes.NodeVisitor, todo_node) -> None
    title = node.pop(0).astext().translate(tex_escape_map)
    self.body.append(u'\n\\begin{sphinxadmonition}{note}{')
    # If this is the original todo node, emit a label that will be referenced by
    # a hyperref in the todolist.
    target = node.get('targetref')
    if target is not None:
        self.body.append(u'\\label{%s}' % target)
    self.body.append('%s:}' % title)


def latex_depart_todo_node(self, node):
    # type: (nodes.NodeVisitor, todo_node) -> None
    self.body.append('\\end{sphinxadmonition}\n')


def setup(app):
    # type: (Sphinx) -> Dict[unicode, Any]
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
    app.connect('doctree-read', process_todos)
    app.connect('doctree-resolved', process_todo_nodes)
    app.connect('env-purge-doc', purge_todos)
    app.connect('env-merge-info', merge_info)
    return {
        'version': sphinx.__display_version__,
        'env_version': 1,
        'parallel_read_safe': True
    }
