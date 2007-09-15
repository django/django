from django.core.management.base import AppCommand
from django.utils.encoding import force_unicode
from django.utils.text import capfirst

MODULE_TEMPLATE = '''    {%% if perms.%(app)s.%(addperm)s or perms.%(app)s.%(changeperm)s %%}
    <tr>
        <th>{%% if perms.%(app)s.%(changeperm)s %%}<a href="%(app)s/%(mod)s/">{%% endif %%}%(name)s{%% if perms.%(app)s.%(changeperm)s %%}</a>{%% endif %%}</th>
        <td class="x50">{%% if perms.%(app)s.%(addperm)s %%}<a href="%(app)s/%(mod)s/add/" class="addlink">{%% endif %%}Add{%% if perms.%(app)s.%(addperm)s %%}</a>{%% endif %%}</td>
        <td class="x75">{%% if perms.%(app)s.%(changeperm)s %%}<a href="%(app)s/%(mod)s/" class="changelink">{%% endif %%}Change{%% if perms.%(app)s.%(changeperm)s %%}</a>{%% endif %%}</td>
    </tr>
    {%% endif %%}'''

class Command(AppCommand):
    help = 'Prints the admin-index template snippet for the given app name(s).'

    def handle_app(self, app, **options):
        from django.db.models import get_models
        output = []
        app_models = get_models(app)
        app_label = app_models[0]._meta.app_label
        output.append('{%% if perms.%s %%}' % app_label)
        output.append('<div class="module"><h2>%s</h2><table>' % app_label.title())
        for model in app_models:
            if model._meta.admin:
                output.append(MODULE_TEMPLATE % {
                    'app': app_label,
                    'mod': model._meta.module_name,
                    'name': force_unicode(capfirst(model._meta.verbose_name_plural)),
                    'addperm': model._meta.get_add_permission(),
                    'changeperm': model._meta.get_change_permission(),
                })
        output.append('</table></div>')
        output.append('{% endif %}')
        return '\n'.join(output)
