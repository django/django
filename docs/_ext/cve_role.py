"""
An interpreted text role to link docs to CVE issues. To use: :cve:`XXXXX`
"""
from docutils import nodes, utils
from docutils.parsers.rst import roles


def cve_role(name, rawtext, text, lineno, inliner, options=None, content=None):
    if options is None:
        options = {}

    url_pattern = inliner.document.settings.env.app.config.cve_url
    if url_pattern is None:
        msg = inliner.reporter.warning("cve not configured: please configure cve_url in conf.py")
        prb = inliner.problematic(rawtext, rawtext, msg)
        return [prb], [msg]

    url = url_pattern % text
    roles.set_classes(options)
    node = nodes.reference(rawtext, utils.unescape('CVE-%s' % text), refuri=url, **options)
    return [node], []


def setup(app):
    app.add_config_value('cve_url', None, 'env')
    app.add_role('cve', cve_role)
    return {'parallel_read_safe': True}
