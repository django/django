from __future__ import annotations

from virtualenv.activation.via_template import ViaTemplateActivator


class FishActivator(ViaTemplateActivator):
    def templates(self):
        yield "activate.fish"

    def replacements(self, creator, dest):
        data = super().replacements(creator, dest)
        data.update({
            "__TCL_LIBRARY__": getattr(creator.interpreter, "tcl_lib", None) or "",
            "__TK_LIBRARY__": getattr(creator.interpreter, "tk_lib", None) or "",
        })
        return data


__all__ = [
    "FishActivator",
]
