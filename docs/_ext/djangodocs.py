"""
Sphinx plugins for Django documentation.
"""

import docutils.nodes
import docutils.transforms
import sphinx
import sphinx.addnodes
try:
    from sphinx import builders
except ImportError:
    import sphinx.builder as builders
import sphinx.directives
import sphinx.environment
try:
    import sphinx.writers.html as sphinx_htmlwriter
except ImportError:
    import sphinx.htmlwriter as sphinx_htmlwriter
import sphinx.roles
from docutils import nodes

def setup(app):
    app.add_crossref_type(
        directivename = "setting",
        rolename      = "setting",
        indextemplate = "pair: %s; setting",
    )
    app.add_crossref_type(
        directivename = "templatetag",
        rolename      = "ttag",
        indextemplate = "pair: %s; template tag"
    )
    app.add_crossref_type(
        directivename = "templatefilter",
        rolename      = "tfilter",
        indextemplate = "pair: %s; template filter"
    )
    app.add_crossref_type(
        directivename = "fieldlookup",
        rolename      = "lookup",
        indextemplate = "pair: %s, field lookup type",
    )
    app.add_description_unit(
        directivename = "django-admin",
        rolename      = "djadmin",
        indextemplate = "pair: %s; django-admin command",
        parse_node    = parse_django_admin_node,
    )
    app.add_description_unit(
        directivename = "django-admin-option",
        rolename      = "djadminopt",
        indextemplate = "pair: %s; django-admin command-line option",
        parse_node    = parse_django_adminopt_node,
    )
    app.add_config_value('django_next_version', '0.0', True)
    app.add_directive('versionadded', parse_version_directive, 1, (1, 1, 1))
    app.add_directive('versionchanged', parse_version_directive, 1, (1, 1, 1))
    app.add_transform(SuppressBlockquotes)
    
    # Monkeypatch PickleHTMLBuilder so that it doesn't die in Sphinx 0.4.2
    if sphinx.__version__ == '0.4.2':
        monkeypatch_pickle_builder()

def parse_version_directive(name, arguments, options, content, lineno,
                      content_offset, block_text, state, state_machine):
    env = state.document.settings.env
    is_nextversion = env.config.django_next_version == arguments[0]
    ret = []
    node = sphinx.addnodes.versionmodified()
    ret.append(node)
    if not is_nextversion:
        if len(arguments) == 1:
            linktext = 'Please, see the release notes <releases-%s>' % (arguments[0])
            xrefs = sphinx.roles.xfileref_role('ref', linktext, linktext, lineno, state)
            node.extend(xrefs[0])
        node['version'] = arguments[0]
    else:
        node['version'] = "Development version"
    node['type'] = name
    if len(arguments) == 2:
        inodes, messages = state.inline_text(arguments[1], lineno+1)
        node.extend(inodes)
        if content:
            state.nested_parse(content, content_offset, node)
        ret = ret + messages
    env.note_versionchange(node['type'], node['version'], node, lineno)
    return ret

                
class SuppressBlockquotes(docutils.transforms.Transform):
    """
    Remove the default blockquotes that encase indented list, tables, etc.
    """
    default_priority = 300
    
    suppress_blockquote_child_nodes = (
        docutils.nodes.bullet_list, 
        docutils.nodes.enumerated_list, 
        docutils.nodes.definition_list,
        docutils.nodes.literal_block, 
        docutils.nodes.doctest_block, 
        docutils.nodes.line_block, 
        docutils.nodes.table
    )
    
    def apply(self):
        for node in self.document.traverse(docutils.nodes.block_quote):
            if len(node.children) == 1 and isinstance(node.children[0], self.suppress_blockquote_child_nodes):
                node.replace_self(node.children[0])

class DjangoHTMLTranslator(sphinx_htmlwriter.SmartyPantsHTMLTranslator):
    """
    Django-specific reST to HTML tweaks.
    """

    # Don't use border=1, which docutils does by default.
    def visit_table(self, node):
        self.body.append(self.starttag(node, 'table', CLASS='docutils'))
    
    # <big>? Really?
    def visit_desc_parameterlist(self, node):
        self.body.append('(')
        self.first_param = 1
    
    def depart_desc_parameterlist(self, node):
        self.body.append(')')
        pass
        
    #
    # Don't apply smartypants to literal blocks
    #
    def visit_literal_block(self, node):
        self.no_smarty += 1
        sphinx_htmlwriter.SmartyPantsHTMLTranslator.visit_literal_block(self, node)

    def depart_literal_block(self, node):
        sphinx_htmlwriter.SmartyPantsHTMLTranslator.depart_literal_block(self, node)
        self.no_smarty -= 1
        
    #
    # Turn the "new in version" stuff (versoinadded/versionchanged) into a
    # better callout -- the Sphinx default is just a little span,
    # which is a bit less obvious that I'd like.
    #
    # FIXME: these messages are all hardcoded in English. We need to chanage 
    # that to accomodate other language docs, but I can't work out how to make
    # that work and I think it'll require Sphinx 0.5 anyway.
    #
    version_text = {
        'deprecated':       'Deprecated in Django %s',
        'versionchanged':   'Changed in Django %s',
        'versionadded':     'New in Django %s',
    }
    
    def visit_versionmodified(self, node):
        self.body.append(
            self.starttag(node, 'div', CLASS=node['type'])
        )
        title = "%s%s" % (
            self.version_text[node['type']] % node['version'],
            len(node) and ":" or "."
        )
        self.body.append('<span class="title">%s</span> ' % title)
    
    def depart_versionmodified(self, node):
        self.body.append("</div>\n")
    
    # Give each section a unique ID -- nice for custom CSS hooks
    # This is different on docutils 0.5 vs. 0.4...

    if hasattr(sphinx_htmlwriter.SmartyPantsHTMLTranslator, 'start_tag_with_title') and sphinx.__version__ == '0.4.2':
        def start_tag_with_title(self, node, tagname, **atts):
            node = {
                'classes': node.get('classes', []), 
                'ids': ['s-%s' % i for i in node.get('ids', [])]
            }
            return self.starttag(node, tagname, **atts)

    else:
        def visit_section(self, node):
            old_ids = node.get('ids', [])
            node['ids'] = ['s-' + i for i in old_ids]
            if sphinx.__version__ != '0.4.2':
                node['ids'].extend(old_ids)
            sphinx_htmlwriter.SmartyPantsHTMLTranslator.visit_section(self, node)
            node['ids'] = old_ids

def parse_django_admin_node(env, sig, signode):
    command = sig.split(' ')[0]
    env._django_curr_admin_command = command
    title = "django-admin.py %s" % sig
    signode += sphinx.addnodes.desc_name(title, title)
    return sig

def parse_django_adminopt_node(env, sig, signode):
    """A copy of sphinx.directives.CmdoptionDesc.parse_signature()"""
    from sphinx import addnodes
    from sphinx.directives.desc import option_desc_re
    count = 0
    firstname = ''
    for m in option_desc_re.finditer(sig):
        optname, args = m.groups()
        if count:
            signode += addnodes.desc_addname(', ', ', ')
        signode += addnodes.desc_name(optname, optname)
        signode += addnodes.desc_addname(args, args)
        if not count:
            firstname = optname
        count += 1
    if not firstname:
        raise ValueError
    return firstname

def monkeypatch_pickle_builder():
    import shutil
    from os import path
    try:
        import cPickle as pickle
    except ImportError:
        import pickle
    from sphinx.util.console import bold
    
    def handle_finish(self):
        # dump the global context
        outfilename = path.join(self.outdir, 'globalcontext.pickle')
        f = open(outfilename, 'wb')
        try:
            pickle.dump(self.globalcontext, f, 2)
        finally:
            f.close()

        self.info(bold('dumping search index...'))
        self.indexer.prune(self.env.all_docs)
        f = open(path.join(self.outdir, 'searchindex.pickle'), 'wb')
        try:
            self.indexer.dump(f, 'pickle')
        finally:
            f.close()

        # copy the environment file from the doctree dir to the output dir
        # as needed by the web app
        shutil.copyfile(path.join(self.doctreedir, builders.ENV_PICKLE_FILENAME),
                        path.join(self.outdir, builders.ENV_PICKLE_FILENAME))

        # touch 'last build' file, used by the web application to determine
        # when to reload its environment and clear the cache
        open(path.join(self.outdir, builders.LAST_BUILD_FILENAME), 'w').close()

    builders.PickleHTMLBuilder.handle_finish = handle_finish

