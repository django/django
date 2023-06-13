from . import site

content = "Another Bad Module"

site._registry.update(
    {
        "foo": "bar",
    }
)

raise Exception("Some random exception.")
