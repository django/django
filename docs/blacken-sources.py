import sys
from os.path import abspath, dirname

from _utils import find_sphinx_sources
from blacken_docs import main

if __name__ == "__main__":
    directory = dirname(abspath(__file__))
    params = sys.argv[1:] if len(sys.argv) > 1 else []

    source_files = find_sphinx_sources(directory)
    print(f"Running blacken-docs on {len(source_files)} source files...")

    args = ["--rst-literal-blocks", *params, *source_files]
    sys.exit(main(args))
