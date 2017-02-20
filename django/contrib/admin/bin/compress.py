#!/usr/bin/env python
import argparse
import os
import subprocess
import sys

try:
    import closure
except ImportError:
    closure_compiler = None
else:
    closure_compiler = os.path.join(os.path.dirname(closure.__file__), 'closure.jar')

js_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'admin', 'js')


def main():
    description = """With no file paths given this script will automatically
compress all jQuery-based files of the admin app. Requires the Google Closure
Compiler library and Java version 6 or later."""
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('file', nargs='*')
    parser.add_argument(
        "-c", dest="compiler", default="~/bin/compiler.jar",
        help="path to Closure Compiler jar file",
    )
    parser.add_argument("-v", "--verbose", action="store_true", dest="verbose")
    parser.add_argument("-q", "--quiet", action="store_false", dest="verbose")
    options = parser.parse_args()

    compiler = closure_compiler if closure_compiler else os.path.expanduser(options.compiler)
    if not os.path.exists(compiler):
        sys.exit(
            "Google Closure compiler jar file %s not found. Please use the -c "
            "option to specify the path." % compiler
        )

    if not options.file:
        if options.verbose:
            sys.stdout.write("No filenames given; defaulting to admin scripts\n")
        files = [
            os.path.join(js_path, f) for f in
            ["actions.js", "collapse.js", "inlines.js", "prepopulate.js"]
        ]
    else:
        files = options.file

    for file_name in files:
        if not file_name.endswith(".js"):
            file_name = file_name + ".js"
        to_compress = os.path.expanduser(file_name)
        if os.path.exists(to_compress):
            to_compress_min = "%s.min.js" % "".join(file_name.rsplit(".js"))
            cmd = "java -jar %s --js %s --js_output_file %s" % (compiler, to_compress, to_compress_min)
            if options.verbose:
                sys.stdout.write("Running: %s\n" % cmd)
            subprocess.call(cmd.split())
        else:
            sys.stdout.write("File %s not found. Sure it exists?\n" % to_compress)


if __name__ == '__main__':
    main()
