import os
import sys
import inspect
import shlex
import subprocess
from .exceptions import FailedTestError, BadFilterError, FilterKeywordError
from .copy import copy_path
from .check import check


def run(
    options, configure, input_files, extra_args=None, filters=None, accepted_errors=None
):
    # here we find out where the test script sits
    frame = inspect.stack()[-1]
    module = inspect.getmodule(frame[0])
    caller_file = module.__file__
    caller_dir = os.path.dirname(os.path.realpath(caller_file))

    # if the work_dir is different from caller_dir
    # we copy all files under caller_dir to work_dir
    if options.work_dir != caller_dir:
        copy_path(caller_dir, options.work_dir)

    launcher, command, output_prefix, relative_reference_path = configure(
        options, input_files, extra_args
    )

    if options.launch_agent is not None:
        command = "{0} {1}".format(options.launch_agent, command)

    launch_script_path = os.path.normpath(os.path.join(options.binary_dir, launcher))

    if not options.skip_run and not os.path.exists(launch_script_path):
        sys.stderr.write(
            "ERROR: launch script/binary {0} not found in {1}\n".format(
                launcher, options.binary_dir
            )
        )
        sys.stderr.write("       have you set the correct --binary-dir (or -b)?\n")
        sys.stderr.write("       try also --help\n")
        sys.exit(-1)

    sys.stdout.write(
        "\nrunning test with input files {0} and args {1}\n".format(
            input_files, extra_args
        )
    )

    if options.skip_run:
        sys.stdout.write("(skipped run with -s|--skip-run)\n")
    else:
        if sys.platform != "win32":
            command = shlex.split(command)

        process = subprocess.Popen(
            command,
            cwd=options.work_dir,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )
        stdout, stderr = process.communicate()

        if output_prefix is None:
            _output_prefix = os.path.join(options.work_dir, "")
        else:
            _output_prefix = os.path.join(options.work_dir, output_prefix) + "."
        with open("{0}{1}".format(_output_prefix, "stdout"), "w") as f:
            try:
                _s = stdout.decode("UTF-8")
            except AttributeError:
                _s = stdout
            f.write(_s)

        with open("{0}{1}".format(_output_prefix, "stderr"), "w") as f:
            try:
                _s = stderr.decode("UTF-8")
            except AttributeError:
                _s = stderr
            f.write(_s)

        found_accepted_errors = False
        if accepted_errors is not None:
            for error in accepted_errors:
                if error in stderr:
                    # we found an error that we expect/accept
                    sys.stdout.write(
                        "found error which is expected/accepted: {0}\n".format(error)
                    )
                    found_accepted_errors = True

        if process.returncode != 0:
            if found_accepted_errors:
                return 0
            else:
                sys.stdout.write("ERROR: crash during {0}\n{1}".format(command, stderr))
                return 1

    if filters is None:
        sys.stdout.write("finished (no reference)\n")
    elif options.no_verification:
        sys.stdout.write("finished (verification skipped)\n")
    else:
        try:
            for suffix in filters:
                if output_prefix is None:
                    output = suffix
                else:
                    output = "{0}.{1}".format(output_prefix, suffix)
                check(
                    filter_list=filters[suffix],
                    out_name=os.path.join(options.work_dir, output),
                    ref_name=os.path.join(
                        options.work_dir, relative_reference_path, output
                    ),
                    log_dir=options.work_dir,
                    verbose=options.verbose,
                )
            sys.stdout.write("passed\n")
        except IOError as e:
            sys.stderr.write("ERROR: could not open file {0}\n".format(e.filename))
            sys.exit(1)
        except FailedTestError as e:
            sys.stderr.write(str(e))
            return 1
        except BadFilterError as e:
            sys.stderr.write(str(e))
            sys.exit(1)
        except FilterKeywordError as e:
            sys.stderr.write(str(e))
            sys.exit(1)
    return 0
