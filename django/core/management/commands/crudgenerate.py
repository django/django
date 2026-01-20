
'''
This is CRUD generation function for view, edit and delete fuctionality
Templates needs to be modified after generation

'''

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import List

from django.apps import apps
from django.core.management import BaseCommand, CommandError, call_command


FIELD_RE = re.compile(
    r"(?P<name>[^:]+):(?P<type>[^:]+)(?::(?P<arg>[^:]+))?(?::(?P<mods>.+))?"
)


def parse_field(spec: str) -> str:
    """Return a Django model field declaration (source) for a single field spec.

    Grammar examples:
      title:str:200
      body:text
      published:bool
      author:fk:auth.User
      name:str:100:null,blank
      slug:str:50:unique,default=untitled
    """
    m = FIELD_RE.match(spec)
    if not m:
        raise ValueError(f"Invalid field spec: {spec}")
    name = m.group("name")
    ftype = m.group("type")
    arg = m.group("arg")
    mods = m.group("mods")

    kwargs = []
    if mods:
        for part in mods.split(","):
            if "=" in part:
                k, v = part.split("=", 1)
                # naive quoting for string defaults
                if not v.isdigit() and v.lower() not in ("true", "false", "none"):
                    v = repr(v)
                kwargs.append(f"{k}={v}")
            else:
                kwargs.append(f"{part}=True")

    if ftype == "str":
        max_length = arg or "255"
        field = f"models.CharField(max_length={max_length}"
    elif ftype == "text":
        field = "models.TextField("
    elif ftype in ("int", "integer"):
        field = "models.IntegerField("
    elif ftype == "bool":
        field = "models.BooleanField("
    elif ftype == "date":
        field = "models.DateField("
    elif ftype == "datetime":
        field = "models.DateTimeField("
    elif ftype == "fk":
        if not arg:
            raise ValueError("fk requires target like app.Model")
        field = f"models.ForeignKey('{arg}', on_delete=models.CASCADE, "
    else:
        raise ValueError(f"Unknown field type: {ftype}")

    if kwargs:
        field += ", ".join(kwargs)
    field += ")"
    return f"    {name} = {field}\n"


def ensure_models_package(app_path: Path):
    models_py = app_path / "models.py"
    models_pkg = app_path / "models"
    init_file = models_pkg / "__init__.py"
    if models_pkg.exists():
        return models_pkg
    if models_py.exists():
        # Move models.py into models/__init__.py to create package
        models_pkg.mkdir()
        content = models_py.read_text()
        init_file.write_text(content)
        models_py.unlink()
        return models_pkg
    # create empty package
    models_pkg.mkdir()
    init_file.write_text("# models package\n")
    return models_pkg


def _ensure_views_have_model(app_path: Path, app_label: str, model_name: str):
    """Ensure views.py contains CBVs for the model; append them if missing."""
    views_py = app_path / "views.py"
    class_marker = f"class {model_name}ListView"
    # Read existing views.py (if any)
    if views_py.exists():
        content = views_py.read_text()
    else:
        content = ""

    if class_marker in content:
        # class already present, but ensure the model is imported
        if f"from .models import {model_name}" not in content:
            # add explicit model import near top
            content = f"from .models import {model_name}\n" + content
            views_py.write_text(content)
        return

    # Build the full class block (including imports)
    classes = (
        f"from django.urls import reverse_lazy\nfrom django.views import generic\nfrom .models import {model_name}\n\n\n"
    f"class {model_name}ListView(generic.ListView):\n"
    f"    model = {model_name}\n"
    f"    template_name = '{app_label}/{model_name.lower()}/list.html'\n"
    f"\n"
    f"    def get_context_data(self, **kwargs):\n"
    f"        context = super().get_context_data(**kwargs)\n"
    f"        model = self.model\n"
    f"        headers = [(getattr(f, 'verbose_name', f.name), f.name) for f in model._meta.fields]\n"
    f"        rows = []\n"
    f"        for obj in context.get('object_list', []):\n"
    f"            row = []\n"
    f"            for f in model._meta.fields:\n"
    f"                try:\n"
    f"                    val = getattr(obj, f.name)\n"
    f"                except Exception:\n"
    f"                    val = None\n"
    f"                row.append(val)\n"
    f"            rows.append((getattr(obj, 'pk', None), row))\n"
    f"        context['headers'] = headers\n"
    f"        context['rows'] = rows\n"
    f"        return context\n\n\n"
    f"class {model_name}DetailView(generic.DetailView):\n"
    f"    model = {model_name}\n"
    f"    template_name = '{app_label}/{model_name.lower()}/detail.html'\n"
    f"\n"
    f"    def get_context_data(self, **kwargs):\n"
    f"        context = super().get_context_data(**kwargs)\n"
    f"        obj = context.get('object')\n"
    f"        fields = []\n"
    f"        if obj is not None:\n"
    f"            for f in self.model._meta.fields:\n"
    f"                try:\n"
    f"                    val = getattr(obj, f.name)\n"
    f"                except Exception:\n"
    f"                    val = None\n"
    f"                label = getattr(f, 'verbose_name', f.name)\n"
    f"                fields.append((label, val))\n"
    f"        context['fields'] = fields\n"
    f"        return context\n\n\n"
        f"class {model_name}CreateView(generic.CreateView):\n"
        f"    model = {model_name}\n"
        f"    fields = '__all__'\n"
        f"    success_url = reverse_lazy('{app_label}:{model_name.lower()}_list')\n"
        f"    template_name = '{app_label}/{model_name.lower()}/form.html'\n\n\n"
        f"class {model_name}UpdateView(generic.UpdateView):\n"
        f"    model = {model_name}\n"
        f"    fields = '__all__'\n"
        f"    success_url = reverse_lazy('{app_label}:{model_name.lower()}_list')\n"
        f"    template_name = '{app_label}/{model_name.lower()}/form.html'\n\n\n"
        f"class {model_name}DeleteView(generic.DeleteView):\n"
        f"    model = {model_name}\n"
        f"    success_url = reverse_lazy('{app_label}:{model_name.lower()}_list')\n"
        f"    template_name = '{app_label}/{model_name.lower()}/confirm_delete.html'\n"
    )

    # Determine imports to add to existing content
    imports = []
    if "from django.urls import reverse_lazy" not in content:
        imports.append("from django.urls import reverse_lazy")
    if "from django.views import generic" not in content:
        imports.append("from django.views import generic")
    # If models import exists but doesn't include this model, still add explicit import line
    if f"from .models import {model_name}" not in content:
        imports.append(f"from .models import {model_name}")

    import_block = "\n".join(imports)
    if import_block:
        import_block = import_block + "\n\n"

    # Remove the import portion from `classes` before appending (we'll add only what's missing)
    # split on first double newline to separate import header from class bodies
    parts = classes.split('\n\n', 1)
    classes_body = parts[1] if len(parts) > 1 else classes

    new_content = import_block + content + "\n\n" + classes_body
    views_py.write_text(new_content)


def _ensure_urls_have_model(app_path: Path, app_label: str, model_name: str):
    """Ensure urls.py contains patterns for the model; append if missing.
    This implementation avoids adding duplicate routes or names.
    """
    urls_py = app_path / "urls.py"
    model_lower = model_name.lower()

    desired = [
        (f"{model_lower}/", f"_views.{model_name}ListView.as_view()", f"{model_lower}_list"),
        (f"{model_lower}/<int:pk>/", f"_views.{model_name}DetailView.as_view()", f"{model_lower}_detail"),
        (f"{model_lower}/add/", f"_views.{model_name}CreateView.as_view()", f"{model_lower}_add"),
        (f"{model_lower}/<int:pk>/edit/", f"_views.{model_name}UpdateView.as_view()", f"{model_lower}_edit"),
        (f"{model_lower}/<int:pk>/delete/", f"_views.{model_name}DeleteView.as_view()", f"{model_lower}_delete"),
    ]

    legacy_names = [f"{model_lower}detail", f"{model_lower}add", f"{model_lower}edit", f"{model_lower}delete"]

    if urls_py.exists():
        content = urls_py.read_text()
        to_add_lines: List[str] = []

        if "from . import views as _views" not in content:
            content = "from . import views as _views\n\n" + content

        # ensure urlpatterns exists in the file so '+=' appends won't raise NameError
        if not re.search(r"^\s*urlpatterns\s*=", content, flags=re.M):
            content = content + "\nurlpatterns = []\n"

        existing_routes = set(re.findall(r"path\('\s*([^']+?)\s*'", content))
        existing_names = set(re.findall(r"name\s*=\s*'([^']+?)'", content))

        # Clean up legacy (no-underscore) names: if canonical exists, remove legacy entries;
        # if only legacy exists, convert legacy name to canonical to normalize the file.
        for action in ("detail", "add", "edit", "delete"):
            canon = f"{model_lower}_{action}"
            legacy = f"{model_lower}{action}"
            if canon in existing_names and legacy in existing_names:
                # remove any path lines that contain name='legacy'
                content = re.sub(r"(?m)^\s*path\(.*name\s*=\s*'" + re.escape(legacy) + r"'.*\n", "", content)
            elif canon not in existing_names and legacy in existing_names:
                # convert legacy name into canonical
                content = content.replace(f"name='{legacy}'", f"name='{canon}'")

        # Recompute existing names/routes after cleanup
        existing_routes = set(re.findall(r"path\('\s*([^']+?)\s*'", content))
        existing_names = set(re.findall(r"name\s*=\s*'([^']+?)'", content))

        for route, view_call, name in desired:
            if name in existing_names or route in existing_routes:
                continue
            to_add_lines.append(f"    path('{route}', {view_call}, name='{name}'),\n")

        if to_add_lines:
            content = content + "\n# Auto-inserted by crud command (repair)\nurlpatterns += [\n" + "".join(to_add_lines) + "]\n"
            urls_py.write_text(content)
        return

    # urls.py doesn't exist; create canonical urls
    urls_src = [
        "from django.urls import path\n",
        "from . import views as _views\n\n",
        f"app_name = '{app_label}'\n\n",
        "urlpatterns = [\n",
    ]
    for route, view_call, name in desired:
        urls_src.append(f"    path('{route}', {view_call}, name='{name}'),\n")
    urls_src.append("]\n")
    urls_py.write_text("".join(urls_src))


def _ensure_admin_register(app_path: Path, model_name: str):
    admin_py = app_path / "admin.py"
    reg_line = f"admin.site.register({model_name})"
    header = f"from django.contrib import admin\nfrom .models import {model_name}\n\n"
    if admin_py.exists():
        content = admin_py.read_text()
        if reg_line in content:
            return
        admin_py.write_text(content + "\n" + header + reg_line + "\n")
    else:
        admin_py.write_text(header + reg_line + "\n")


def _ensure_views_imports(app_path: Path):
    """Scan views.py for class-based views that reference a model and ensure the model
    is imported from .models. This avoids NameError when classes refer to models.
    """
    views_py = app_path / "views.py"
    if not views_py.exists():
        return
    content = views_py.read_text()
    # Find all occurrences like: model = ModelName
    # Only match simple identifiers on the RHS to avoid capturing `self` from lines
    # like `model = self.model` (which would otherwise capture 'self'). Allow an
    # optional trailing comment.
    found = set(
        re.findall(
            r"^\s*model\s*=\s*([A-Za-z_][A-Za-z0-9_]*)\s*(?:#.*)?$",
            content,
            flags=re.M,
        )
    )
    if not found:
        return
    lines = content.splitlines()
    imports = [i for i, l in enumerate(lines) if l.startswith("from .models import")]
    existing_imports = set()
    for i in imports:
        parts = lines[i].replace("from .models import", "").strip()
        for p in parts.split(","):
            existing_imports.add(p.strip())

    to_add = [m for m in sorted(found) if m and m not in existing_imports]
    if not to_add:
        return

    # Insert new import line after other imports or at top
    insert_at = 0
    for i, l in enumerate(lines):
        if (
            l.startswith("from django")
            or l.startswith("import")
            or l.startswith("from .")
        ):
            insert_at = i + 1

    new_import_line = f"from .models import {', '.join(to_add)}"
    lines.insert(insert_at, new_import_line)
    views_py.write_text("\n".join(lines) + "\n")


def _repair_templates_for_model(app_label: str, model_name: str):
    """Repair simple common template generation issues introduced by earlier iterations:
    - replace stray "{%%" with "{%"
    - replace triple underscores '___' used accidentally in url names with '__'
    - normalize any accidental '___add' -> '__add' for this model
    This function writes fixes in-place when needed.
    """
    templates_dir = Path("templates") / app_label / model_name.lower()
    if not templates_dir.exists():
        return []
    changed = []
    for tpl in templates_dir.glob("*.html"):
        text = tpl.read_text()
        new_text = text
        # Fix stray doubled-percent markers
        if "{%%" in new_text:
            new_text = new_text.replace("{%%", "{%")
        if "%%}" in new_text:
            new_text = new_text.replace("%%}", "%}")
        # Fix accidental triple-underscore mistakes for this model
        triple = f"{model_name.lower()}___"
        if triple in new_text:
            new_text = new_text.replace(triple, f"{model_name.lower()}__")
        # Fix generic triple underscores anywhere in url names (safe heuristic)
        if "___" in new_text:
            new_text = new_text.replace("___", "__")
        # Fix missing underscore between model and action for common url names,
        # e.g. myapp:blogmodeldetail -> myapp:blogmodel_detail
        for action in ("list", "detail", "add", "edit", "delete"):
            # patterns with single quotes
            wrong = f"'{app_label}:{model_name.lower()}{action}'"
            right = f"'{app_label}:{model_name.lower()}_{action}'"
            if wrong in new_text:
                new_text = new_text.replace(wrong, right)
            # patterns with double quotes
            wrong2 = f'"{app_label}:{model_name.lower()}{action}"'
            right2 = f'"{app_label}:{model_name.lower()}_{action}"'
            if wrong2 in new_text:
                new_text = new_text.replace(wrong2, right2)
        # Fix unprefixed names like 'blogmodeldetail' -> 'myapp:blogmodel_detail'
        for action in ("list", "detail", "add", "edit", "delete"):
            wrong_raw = f"'{model_name.lower()}{action}'"
            right_raw = f"'{app_label}:{model_name.lower()}_{action}'"
            if wrong_raw in new_text:
                new_text = new_text.replace(wrong_raw, right_raw)
            wrong_raw2 = f'"{model_name.lower()}{action}"'
            right_raw2 = f'"{app_label}:{model_name.lower()}_{action}"'
            if wrong_raw2 in new_text:
                new_text = new_text.replace(wrong_raw2, right_raw2)
        if new_text != text:
            tpl.write_text(new_text)
            changed.append(str(tpl))
    return changed


class Command(BaseCommand):
    help = "Bind a simple CRUD set for an app and model: python manage.py crud <app> <ModelName> <field:type>... \n" \
              "Or create only templates for an existing app/model with --templates-only" \
              "python manage.py crud myapp Publication title:str:255 body:text --create-base --force\n" \
              "python manage.py crud myapp Publication --templates-only --create-base --force" \
              " migrate after the generation to create database tables"  
                

    def add_arguments(self, parser):
        parser.add_argument("app")
        parser.add_argument("model")
        parser.add_argument("fields", nargs="*", help="Field specifications")
        parser.add_argument(
            "--templates-only",
            action="store_true",
            dest="templates_only",
            help="Only create templates for an existing app/model (do not create model)",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            dest="force",
            help="Overwrite existing templates if present",
        )
        parser.add_argument(
            "--create-base",
            action="store_true",
            dest="create_base",
            help="Create a shared templates/crud_base.html file (default: False)",
        )

    def handle(self, *args, **options):
        app_label = options["app"]
        model_name = options["model"]
        fields: List[str] = options.get("fields") or []

        templates_only = bool(options.get("templates_only"))
        force = bool(options.get("force"))
        create_base = bool(options.get("create_base"))

        try:
            app_config = apps.get_app_config(app_label)
            app_path = Path(app_config.path)
        except LookupError:
            if templates_only:
                raise CommandError(
                    f"App '{app_label}' not found; cannot create templates for unknown app"
                )
            # try to create the app in cwd via startapp
            self.stdout.write(
                self.style.NOTICE(
                    f"App '{app_label}' not found — creating with startapp"
                )
            )
            call_command("startapp", app_label)
            try:
                app_config = apps.get_app_config(app_label)
                app_path = Path(app_config.path)
            except LookupError:
                # fallback: assume created in cwd
                app_path = Path(os.getcwd()) / app_label

        # If templates-only mode is requested, ensure the model exists and then only create templates
        if templates_only:
            try:
                model_cls = apps.get_model(app_label, model_name)
            except LookupError:
                raise CommandError(
                    f"Model '{model_name}' not found in app '{app_label}'; cannot create templates"
                )

            # Create model-specific templates directory: templates/<app_label>/<model_lower>/
            templates_dir = Path("templates") / app_label / model_name.lower()
            templates_dir.mkdir(parents=True, exist_ok=True)
            # Optionally create a shared base template for generated templates
            base_tpl = Path("templates") / "crud_base.html"
            if create_base:
                base_tpl.parent.mkdir(parents=True, exist_ok=True)
                base_content = (
                    "<!doctype html>\n"
                    '<html lang="en">\n'
                    "<head>\n"
                    '  <meta charset="utf-8">\n'
                    '  <meta name="viewport" content="width=device-width,initial-scale=1">\n'
                    "  <title>{% block title %}My Site{% endblock %}</title>\n"
                    "  <style>\n"
                    '    body { font-family: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial; margin: 1.5rem; }\n'
                    "    nav { margin-bottom: 1rem; }\n"
                    "    main { max-width: 800px; }\n"
                    "  </style>\n"
                    "</head>\n"
                    "<body>\n"
                    "  <nav>\n"
                    "    <a href=\"{% url 'admin:index' %}\">Admin</a>\n"
                    "  </nav>\n\n"
                    "  <main>\n"
                    "    {% block content %}{% endblock %}\n"
                    "  </main>\n\n"
                    '  <footer style="margin-top:2rem;color:#666;font-size:.9rem;">\n'
                    "    Generated by crud command\n"
                    "  </footer>\n"
                    "</body>\n"
                    "</html>\n"
                )
                if not base_tpl.exists() or force:
                    base_tpl.write_text(base_content)
                    self.stdout.write(
                        self.style.SUCCESS(f"Created base template {base_tpl}")
                    )
                else:
                    self.stdout.write(
                        self.style.NOTICE(
                            "Base template exists; use --force to overwrite."
                        )
                    )
            names = ["list", "detail", "form", "confirm_delete"]
            created = []
            for n in names:
                tpl = templates_dir / f"{n}.html"
                # produce same richer content as the full command
                if n == "list":
                    template_tpl = (
                        "{% extends 'crud_base.html' %}\n\n"
                        "{% block title %}__MODEL__ — list{% endblock %}\n\n"
                        "{% block content %}\n"
                        "<!-- Template: __APP__/__TPL__ -->\n"
                        "<h1>__MODEL__ list</h1>\n"
                        "<p><a href=\"{% url '__APP__:__MODEL_LOWER__add' %}\">Add __MODEL__</a></p>\n"
                        "{% if rows %}\n"
                        "<table>\n"
                        "  <thead>\n"
                        "    <tr>\n"
                        "      {% for label, fname in headers %}\n"
                        "      <th>{{ label }}</th>\n"
                        "      {% endfor %}\n"
                        "      <th>Actions</th>\n"
                        "    </tr>\n"
                        "  </thead>\n"
                        "  <tbody>\n"
                        "    {% for pk, rowvals in rows %}\n"
                        "    <tr>\n"
                        "      {% for val in rowvals %}\n"
                        "      <td>{{ val }}</td>\n"
                        "      {% endfor %}\n"
                        "      <td><a href=\"{% url '__APP__:__MODEL_LOWER__detail' pk %}\">View</a></td>\n"
                        "    </tr>\n"
                        "    {% endfor %}\n"
                        "  </tbody>\n"
                        "</table>\n"
                        "{% else %}\n  <p>No items</p>\n{% endif %}\n"
                        "{% endblock %}\n"
                    )
                elif n == "detail":
                    template_tpl = (
                        "{% extends 'crud_base.html' %}\n\n"
                        "{% block title %}__MODEL__ — detail{% endblock %}\n\n"
                        "{% block content %}\n"
                        "<!-- Template: __APP__/__TPL__ -->\n"
                        "<h1>__MODEL__ detail</h1>\n"
                        "<table>\n"
                        "{% for label, value in fields %}\n"
                        "  <tr>\n"
                        "    <th>{{ label }}</th>\n"
                        "    <td>{{ value }}</td>\n"
                        "  </tr>\n"
                        "{% endfor %}\n"
                        "</table>\n"
                        "<p><a href=\"{% url '__APP__:__MODEL_LOWER__edit' object.pk %}\">Edit</a> | "
                        "<a href=\"{% url '__APP__:__MODEL_LOWER__delete' object.pk %}\">Delete</a></p>\n"
                        "<p><a href=\"{% url '__APP__:__MODEL_LOWER__list' %}\">Back to list</a></p>\n"
                        "{% endblock %}\n"
                    )
                elif n == "form":
                    template_tpl = (
                        "{% extends 'crud_base.html' %}\n\n"
                        "{% block title %}__MODEL__ — form{% endblock %}\n\n"
                        "{% block content %}\n"
                        "<!-- Template: __APP__/__TPL__ -->\n"
                        "<h1>__MODEL__ form</h1>\n"
                        '<form method="post">{% csrf_token %}\n  {{ form.as_p }}\n  <button type="submit">Save</button>\n</form>\n'
                        "{% endblock %}\n"
                    )
                else:  # confirm_delete
                    template_tpl = (
                        "{% extends 'crud_base.html' %}\n\n"
                        "{% block title %}Confirm delete — __MODEL__{% endblock %}\n\n"
                        "{% block content %}\n"
                        "<!-- Template: __APP__/__TPL__ -->\n"
                        "<h1>Confirm delete __MODEL__</h1>\n"
                        '<form method="post">{% csrf_token %}\n  <p>Are you sure you want to delete {{ object }}?</p>\n'
                        '  <button type="submit">Yes, delete</button>\n'
                        "  <a href=\"{% url '__APP__:__MODEL_LOWER__list' %}\">Cancel</a>\n</form>\n"
                        "{% endblock %}\n"
                    )
                content = (
                    template_tpl.replace("__APP__", app_label)
                    .replace("__TPL__", tpl.name)
                    .replace("__MODEL__", model_name)
                    .replace("__MODEL_LOWER__", model_name.lower())
                )
                if tpl.exists() and not force:
                    continue
                tpl.write_text(content)
                created.append(str(tpl))
                # remove any old wrapper file if --force was used (we only use folder structure)
                if force:
                    wrapper_file = (
                        Path("templates") / app_label / f"{model_name.lower()}_{n}.html"
                    )
                    if wrapper_file.exists():
                        try:
                            wrapper_file.unlink()
                        except Exception:
                            pass
            if created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Created/updated templates: {', '.join(created)}"
                    )
                )
            else:
                self.stdout.write(
                    self.style.NOTICE(
                        "No templates created (already exist). Use --force to overwrite."
                    )
                )
            # Repair templates for any obvious generator issues
            try:
                changed = _repair_templates_for_model(app_label, model_name)
                if changed:
                    self.stdout.write(
                        self.style.SUCCESS(f"Repaired templates: {', '.join(changed)}")
                    )
            except Exception:
                pass
            return

        # Ensure models package exists (and move existing models.py if present)
        models_pkg = ensure_models_package(app_path)

        model_file = models_pkg / f"{model_name.lower()}.py"
        model_created = False
        if model_file.exists():
            self.stdout.write(
                self.style.NOTICE(
                    f"Model file {model_file} already exists — skipping model creation"
                )
            )

        # Build model source
        src = [
            "from django.db import models\n\n\n",
            f"class {model_name}(models.Model):\n",
        ]
        if not fields:
            src.append("    # TODO: add fields\n    pass\n")
        else:
            for spec in fields:
                try:
                    src.append(parse_field(spec))
                except ValueError as exc:
                    raise CommandError(str(exc))

        src.append(
            "\n    def __str__(self):\n        pk = getattr(self, 'id', None)\n        if pk is not None:\n            return str(pk)\n        return super().__str__()\n"
        )
        model_file.write_text("".join(src))
        model_created = True
        self.stdout.write(self.style.SUCCESS(f"Created model file {model_file}"))

        # Ensure models/__init__.py imports the new model
        init_file = models_pkg / "__init__.py"
        content = init_file.read_text()
        import_line = f"from .{model_name.lower()} import {model_name}\n"
        if import_line not in content:
            content += import_line
            init_file.write_text(content)

        # Ensure admin registration (idempotent)
        try:
            _ensure_admin_register(app_path, model_name)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Ensured admin registration for {model_name} in {app_label}"
                )
            )
        except Exception:
            pass

        # Create basic views.py if missing
        # Ensure views contain CBVs for the model (append if needed)
        try:
            # make sure views have necessary model imports for any classes that reference models
            try:
                _ensure_views_imports(app_path)
            except Exception:
                pass
            _ensure_views_have_model(app_path, app_label, model_name)
            self.stdout.write(
                self.style.SUCCESS(f"Ensured views for {model_name} in {app_label}")
            )
        except Exception:
            pass

        # Create app urls.py
        # Ensure urls contain patterns for the model (append if needed)
        try:
            _ensure_urls_have_model(app_path, app_label, model_name)
            self.stdout.write(
                self.style.SUCCESS(f"Ensured urls for {model_name} in {app_label}")
            )
        except Exception:
            pass

        # Templates: create model-specific template directory under templates/<app>/<model>/
        templates_dir = Path("templates") / app_label / model_name.lower()
        templates_dir.mkdir(parents=True, exist_ok=True)

        # Optionally create a shared base template for generated templates (honor --create-base
        # in the full command path as well as in --templates-only mode)
        base_tpl = Path("templates") / "crud_base.html"
        if create_base:
            base_tpl.parent.mkdir(parents=True, exist_ok=True)
            base_content = (
                "<!doctype html>\n"
                "<html lang=\"en\">\n"
                "<head>\n"
                "  <meta charset=\"utf-8\">\n"
                "  <meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">\n"
                "  <title>{% block title %}My Site{% endblock %}</title>\n"
                "  <style>\n"
                "    body { font-family: system-ui, -apple-system, \"Segoe UI\", Roboto, \"Helvetica Neue\", Arial; margin: 1.5rem; }\n"
                "    nav { margin-bottom: 1rem; }\n"
                "    main { max-width: 800px; }\n"
                "  </style>\n"
                "</head>\n"
                "<body>\n"
                "  <nav>\n"
                "    <a href=\"{% url 'admin:index' %}\">Admin</a>\n"
                "  </nav>\n\n"
                "  <main>\n"
                "    {% block content %}{% endblock %}\n"
                "  </main>\n\n"
                "  <footer style=\"margin-top:2rem;color:#666;font-size:.9rem;\">\n"
                "    Generated by crud command\n"
                "  </footer>\n"
                "</body>\n"
                "</html>\n"
            )
            if not base_tpl.exists() or force:
                base_tpl.write_text(base_content)
                self.stdout.write(
                    self.style.SUCCESS(f"Created base template {base_tpl}")
                )
            else:
                self.stdout.write(
                    self.style.NOTICE(
                        "Base template exists; use --force to overwrite."
                    )
                )
        names = ["list", "detail", "form", "confirm_delete"]
        names = ["list", "detail", "form", "confirm_delete"]
        for n in names:
            tpl = templates_dir / f"{n}.html"
            if n == "list":
                template_tpl = (
                    "{% extends 'crud_base.html' %}\n\n"
                    "{% block title %}__MODEL__ — list{% endblock %}\n\n"
                    "{% block content %}\n"
                    "<!-- Template: __APP__/__TPL__ -->\n"
                    "<h1>__MODEL__ list</h1>\n"
                    "<p><a href=\"{% url '__APP__:__MODEL_LOWER__add' %}\">Add __MODEL__</a></p>\n"
                    "{% if rows %}\n"
                    "<table>\n"
                    "  <thead>\n"
                    "    <tr>\n"
                    "      {% for label, fname in headers %}\n"
                    "      <th>{{ label }}</th>\n"
                    "      {% endfor %}\n"
                    "      <th>Actions</th>\n"
                    "    </tr>\n"
                    "  </thead>\n"
                    "  <tbody>\n"
                    "    {% for pk, rowvals in rows %}\n"
                    "    <tr>\n"
                    "      {% for val in rowvals %}\n"
                    "      <td>{{ val }}</td>\n"
                    "      {% endfor %}\n"
                    "      <td><a href=\"{% url '__APP__:__MODEL_LOWER__detail' pk %}\">View</a></td>\n"
                    "    </tr>\n"
                    "    {% endfor %}\n"
                    "  </tbody>\n"
                    "</table>\n"
                    "{% else %}\n  <p>No items</p>\n{% endif %}\n"
                    "{% endblock %}\n"
                )
            elif n == "detail":
                template_tpl = (
                    "{% extends 'crud_base.html' %}\n\n"
                    "{% block title %}__MODEL__ — detail{% endblock %}\n\n"
                    "{% block content %}\n"
                    "<!-- Template: __APP__/__TPL__ -->\n"
                    "<h1>__MODEL__ detail</h1>\n"
                    "<table>\n"
                    "{% for label, value in fields %}\n"
                    "  <tr>\n"
                    "    <th>{{ label }}</th>\n"
                    "    <td>{{ value }}</td>\n"
                    "  </tr>\n"
                    "{% endfor %}\n"
                    "</table>\n"
                    "<p><a href=\"{% url '__APP__:__MODEL_LOWER__edit' object.pk %}\">Edit</a> | "
                    "<a href=\"{% url '__APP__:__MODEL_LOWER__delete' object.pk %}\">Delete</a></p>\n"
                    "<p><a href=\"{% url '__APP__:__MODEL_LOWER__list' %}\">Back to list</a></p>\n"
                    "{% endblock %}\n"
                )
            elif n == "form":
                template_tpl = (
                    "{% extends 'crud_base.html' %}\n\n"
                    "{% block title %}__MODEL__ — form{% endblock %}\n\n"
                    "{% block content %}\n"
                    "<!-- Template: __APP__/__TPL__ -->\n"
                    "<h1>__MODEL__ form</h1>\n"
                    '<form method="post">{% csrf_token %}\n  {{ form.as_p }}\n  <button type="submit">Save</button>\n</form>\n'
                    "{% endblock %}\n"
                )
            else:  # confirm_delete
                template_tpl = (
                    "{% extends 'crud_base.html' %}\n\n"
                    "{% block title %}Confirm delete — __MODEL__{% endblock %}\n\n"
                    "{% block content %}\n"
                    "<!-- Template: __APP__/__TPL__ -->\n"
                    "<h1>Confirm delete __MODEL__</h1>\n"
                    '<form method="post">{% csrf_token %}\n  <p>Are you sure you want to delete {{ object }}?</p>\n'
                    '  <button type="submit">Yes, delete</button>\n'
                    "  <a href=\"{% url '__APP__:__MODEL_LOWER__list' %}\">Cancel</a>\n</form>\n"
                    "{% endblock %}\n"
                )
            content = (
                template_tpl.replace("__APP__", app_label)
                .replace("__TPL__", tpl.name)
                .replace("__MODEL__", model_name)
                .replace("__MODEL_LOWER__", model_name.lower())
            )
            if not tpl.exists() or force:
                tpl.write_text(content)
                # remove any old wrapper file if --force was used (we only use folder structure)
                if force:
                    wrapper_file = (
                        Path("templates") / app_label / f"{model_name.lower()}_{n}.html"
                    )
                    if wrapper_file.exists():
                        try:
                            wrapper_file.unlink()
                        except Exception:
                            pass
        self.stdout.write(
            self.style.SUCCESS(f"Created templates under {templates_dir}")
        )
        # Repair templates that may have been created with earlier generator bugs
        try:
            changed = _repair_templates_for_model(app_label, model_name)
            if changed:
                self.stdout.write(
                    self.style.SUCCESS(f"Repaired templates: {', '.join(changed)}")
                )
        except Exception:
            pass

        # Run makemigrations and migrate for the app
        try:
            call_command("makemigrations", app_label)
            call_command("migrate")
            self.stdout.write(self.style.SUCCESS("Ran makemigrations and migrate"))
        except Exception as exc:
            self.stdout.write(
                self.style.WARNING(f"Finished Binding but migrations failed: {exc}")
            )

    if __name__ == "__main__":
        # Standalone repair runner: allows running this file directly to fix views/templates
        # without invoking Django's management (avoids import-time URL/view errors).
        import sys

        def _print_usage():
            print("Usage: python crud.py repair <app_label> <ModelName>")

        if len(sys.argv) < 4 or sys.argv[1] != "repair":
            _print_usage()
            sys.exit(2)

        _, _, app_label, model_name = sys.argv[:4]
        cwd = Path.cwd()
        # locate app path: prefer ./<app_label> then search cwd
        app_path = cwd / app_label
        if not app_path.exists():
            # try to find directory with that name under cwd
            found = None
            for p in cwd.iterdir():
                if p.is_dir() and p.name == app_label:
                    found = p
                    break
            if found:
                app_path = found

        if not app_path.exists():
            print(f"App directory for '{app_label}' not found under {cwd}")
            sys.exit(1)

        print(
            f"Running standalone repair for app={app_label} model={model_name} at {app_path}"
        )
        try:
            _ensure_views_imports(app_path)
            print("Ensured model imports in views.py")
        except Exception as exc:
            print(f"_ensure_views_imports failed: {exc}")

        try:
            changed = _repair_templates_for_model(app_label, model_name)
            if changed:
                print("Repaired templates:")
                for c in changed:
                    print(" - ", c)
            else:
                print("No template repairs needed")
        except Exception as exc:
            print(f"_repair_templates_for_model failed: {exc}")

        try:
            _ensure_views_have_model(app_path, app_label, model_name)
            print("Ensured CBV classes present in views.py")
        except Exception as exc:
            print(f"_ensure_views_have_model failed: {exc}")

        try:
            _ensure_urls_have_model(app_path, app_label, model_name)
            print("Ensured urls.py contains patterns for model")
        except Exception as exc:
            print(f"_ensure_urls_have_model failed: {exc}")

        try:
            _ensure_admin_register(app_path, model_name)
            print("Ensured admin registration")
        except Exception as exc:
            print(f"_ensure_admin_register failed: {exc}")

        print("Standalone repair complete")
