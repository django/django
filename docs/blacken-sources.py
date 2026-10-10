import sys
from pathlib import Path

from _utils import find_sphinx_sources
from blacken_docs import main

if __name__ == "__main__":
    docs_dir = Path(__file__).resolve().parent
    source_files = find_sphinx_sources(docs_dir)
    print(f"Running blacken-docs on {len(source_files)} source files...")

    params = sys.argv[1:] if len(sys.argv) > 1 else []
    args = ["--rst-literal-blocks", *params, *source_files]
    sys.exit(main(args))
