#!/usr/bin/env python
import sys

from django.conf import global_settings, settings
from django.core.management import execute_from_command_line


class Settings:
    def __getattr__(self, name):
        if name == "FOO":
            return "bar"
        return getattr(global_settings, name)

    def __dir__(self):
        return super().__dir__() + dir(global_settings) + ["FOO"]


if __name__ == "__main__":
    settings.configure(Settings())
    execute_from_command_line(sys.argv)
