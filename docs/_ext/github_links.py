import ast
import functools
import importlib.util
import pathlib

BASE_PATH = pathlib.Path(__file__).parents[2]


class CodeLocator(ast.NodeVisitor):
    def __init__(self):
        self.current_path = []
        self.node_line_numbers = {}
        self.import_locations = {}

    @classmethod
    def from_code(cls, code):
        tree = ast.parse(code)
        locator = cls()
        locator.visit(tree)
        return locator

    def visit_node(self, node):
        self.current_path.append(node.name)
        self.node_line_numbers[".".join(self.current_path)] = node.lineno
        ast.NodeVisitor.generic_visit(self, node)
        self.current_path.pop()

    def visit_FunctionDef(self, node):
        self.visit_node(node)

    def visit_ClassDef(self, node):
        self.visit_node(node)

    def visit_ImportFrom(self, node):
        for alias in node.names:
            if alias.asname:
                # Exclude linking aliases (`import x as y`) to avoid confusion when
                # clicking a source link to a differently named entity.
                continue
            self.import_locations[alias.name] = ("." * node.level) + (node.module or "")


@functools.lru_cache(maxsize=1024)
def get_locator(file):
    file_contents = file.read_text(encoding="utf-8")
    return CodeLocator.from_code(file_contents)


class CodeNotFound(Exception):
    pass


def module_name_to_file_path(module_name):
    # Avoid importlib machinery as locating a module involves importing its
    # parent, which would trigger import side effects.

    for suffix in [".py", "/__init__.py"]:
        file_path = BASE_PATH / (module_name.replace(".", "/") + suffix)
        if file_path.exists():
            return file_path

    raise CodeNotFound


def get_path_and_line(module, fullname):
    path = module_name_to_file_path(module_name=module)

    locator = get_locator(path)

    lineno = locator.node_line_numbers.get(fullname)

    if lineno is not None:
        return path, lineno

    imported_object = fullname.split(".", maxsplit=1)[0]
    try:
        imported_path = locator.import_locations[imported_object]
    except KeyError:
        raise CodeNotFound

    # From a statement such as:
    # from . import y.z
    # - either y.z might be an object in the parent module
    # - or y might be a module, and z be an object in y
    # also:
    # - either the current file is x/__init__.py, and z would be in x.y
    # - or the current file is x/a.py, and z would be in x.a.y
    if path.name != "__init__.py":
        # Look in parent module
        module = module.rsplit(".", maxsplit=1)[0]
    imported_module = importlib.util.resolve_name(name=imported_path, package=module)
    try:
        return get_path_and_line(module=imported_module, fullname=fullname)
    except CodeNotFound:
        if "." not in fullname:
            raise

        first_element, remainder = fullname.rsplit(".", maxsplit=1)
        # Retrying, assuming the first element of of the fullname is a module
        return get_path_and_line(
            module=f"{imported_module}.{first_element}", fullname=remainder
        )


def get_branch(version, next_version):
    if version == next_version:
        return "main"
    else:
        return f"stable/{version}.x"


def github_linkcode_resolve(domain, info, *, version, next_version):
    """ """
    if domain != "py":
        return None

    if not info.get("module", None):
        return None

    module: str = info["module"]
    fullname: str = info["fullname"]

    try:
        path, lineno = get_path_and_line(module=module, fullname=fullname)
    except CodeNotFound:
        return None

    linespec = f"#L{lineno}"

    branch = get_branch(version=version, next_version=next_version)

    relative_path = path.relative_to(BASE_PATH)
    # Use a /-separated path otherwise on windows, str(file) returns \-separated path.
    url_path = "/".join(relative_path.parts)

    return f"https://github.com/django/django/blob/{branch}/{url_path}{linespec}"
