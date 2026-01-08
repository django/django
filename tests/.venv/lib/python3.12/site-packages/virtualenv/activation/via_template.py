from __future__ import annotations

import os
import shlex
import sys
from abc import ABC, abstractmethod

from .activator import Activator

if sys.version_info >= (3, 10):
    from importlib.resources import files

    def read_binary(module_name: str, filename: str) -> bytes:
        return (files(module_name) / filename).read_bytes()

else:
    from importlib.resources import read_binary


class ViaTemplateActivator(Activator, ABC):
    @abstractmethod
    def templates(self):
        raise NotImplementedError

    @staticmethod
    def quote(string):
        """
        Quote strings in the activation script.

        :param string: the string to quote
        :return: quoted string that works in the activation script
        """
        return shlex.quote(string)

    def generate(self, creator):
        dest_folder = creator.bin_dir
        replacements = self.replacements(creator, dest_folder)
        generated = self._generate(replacements, self.templates(), dest_folder, creator)
        if self.flag_prompt is not None:
            creator.pyenv_cfg["prompt"] = self.flag_prompt
        return generated

    def replacements(self, creator, dest_folder):  # noqa: ARG002
        return {
            "__VIRTUAL_PROMPT__": "" if self.flag_prompt is None else self.flag_prompt,
            "__VIRTUAL_ENV__": str(creator.dest),
            "__VIRTUAL_NAME__": creator.env_name,
            "__BIN_NAME__": str(creator.bin_dir.relative_to(creator.dest)),
            "__PATH_SEP__": os.pathsep,
            "__TCL_LIBRARY__": getattr(creator.interpreter, "tcl_lib", None) or "",
            "__TK_LIBRARY__": getattr(creator.interpreter, "tk_lib", None) or "",
        }

    def _generate(self, replacements, templates, to_folder, creator):
        generated = []
        for template in templates:
            text = self.instantiate_template(replacements, template, creator)
            dest = to_folder / self.as_name(template)
            # remove the file if it already exists - this prevents permission
            # errors when the dest is not writable
            if dest.exists():
                dest.unlink()
            # Powershell assumes Windows 1252 encoding when reading files without BOM
            encoding = "utf-8-sig" if str(template).endswith(".ps1") else "utf-8"
            # use write_bytes to avoid platform specific line normalization (\n -> \r\n)
            dest.write_bytes(text.encode(encoding))
            generated.append(dest)
        return generated

    def as_name(self, template):
        return template

    def instantiate_template(self, replacements, template, creator):
        # read content as binary to avoid platform specific line normalization (\n -> \r\n)
        binary = read_binary(self.__module__, template)
        text = binary.decode("utf-8", errors="strict")
        for key, value in replacements.items():
            value_uni = self._repr_unicode(creator, value)
            text = text.replace(key, self.quote(value_uni))
        return text

    @staticmethod
    def _repr_unicode(creator, value):  # noqa: ARG004
        return value  # by default, we just let it be unicode


__all__ = [
    "ViaTemplateActivator",
]
