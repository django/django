"""The Sphinx documentation toolchain."""

import sys

from sphinx.cmd.build import main

raise SystemExit(main(sys.argv[1:]))
