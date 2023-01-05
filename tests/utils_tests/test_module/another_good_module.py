from . import site

content = "Another Good Module"

site._registry.update(
    {
        "lorem": "ipsum",
    }
)
