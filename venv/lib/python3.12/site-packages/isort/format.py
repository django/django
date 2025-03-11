import re
import sys
from datetime import datetime
from difflib import unified_diff
from pathlib import Path
from typing import Optional, TextIO

try:
    import colorama
except ImportError:
    colorama_unavailable = True
else:
    colorama_unavailable = False


ADDED_LINE_PATTERN = re.compile(r"\+[^+]")
REMOVED_LINE_PATTERN = re.compile(r"-[^-]")


def format_simplified(import_line: str) -> str:
    import_line = import_line.strip()
    if import_line.startswith("from "):
        import_line = import_line.replace("from ", "")
        import_line = import_line.replace(" import ", ".")
    elif import_line.startswith("import "):
        import_line = import_line.replace("import ", "")

    return import_line


def format_natural(import_line: str) -> str:
    import_line = import_line.strip()
    if not import_line.startswith("from ") and not import_line.startswith("import "):
        if "." not in import_line:
            return f"import {import_line}"
        parts = import_line.split(".")
        end = parts.pop(-1)
        return f"from {'.'.join(parts)} import {end}"

    return import_line


def show_unified_diff(
    *,
    file_input: str,
    file_output: str,
    file_path: Optional[Path],
    output: Optional[TextIO] = None,
    color_output: bool = False,
) -> None:
    """Shows a unified_diff for the provided input and output against the provided file path.

    - **file_input**: A string that represents the contents of a file before changes.
    - **file_output**: A string that represents the contents of a file after changes.
    - **file_path**: A Path object that represents the file path of the file being changed.
    - **output**: A stream to output the diff to. If non is provided uses sys.stdout.
    - **color_output**: Use color in output if True.
    """
    printer = create_terminal_printer(color_output, output)
    file_name = "" if file_path is None else str(file_path)
    file_mtime = str(
        datetime.now() if file_path is None else datetime.fromtimestamp(file_path.stat().st_mtime)
    )
    unified_diff_lines = unified_diff(
        file_input.splitlines(keepends=True),
        file_output.splitlines(keepends=True),
        fromfile=file_name + ":before",
        tofile=file_name + ":after",
        fromfiledate=file_mtime,
        tofiledate=str(datetime.now()),
    )
    for line in unified_diff_lines:
        printer.diff_line(line)


def ask_whether_to_apply_changes_to_file(file_path: str) -> bool:
    answer = None
    while answer not in ("yes", "y", "no", "n", "quit", "q"):
        answer = input(f"Apply suggested changes to '{file_path}' [y/n/q]? ")  # nosec
        answer = answer.lower()
        if answer in ("no", "n"):
            return False
        if answer in ("quit", "q"):
            sys.exit(1)
    return True


def remove_whitespace(content: str, line_separator: str = "\n") -> str:
    content = content.replace(line_separator, "").replace(" ", "").replace("\x0c", "")
    return content


class BasicPrinter:
    ERROR = "ERROR"
    SUCCESS = "SUCCESS"

    def __init__(self, error: str, success: str, output: Optional[TextIO] = None):
        self.output = output or sys.stdout
        self.success_message = success
        self.error_message = error

    def success(self, message: str) -> None:
        print(self.success_message.format(success=self.SUCCESS, message=message), file=self.output)

    def error(self, message: str) -> None:
        print(self.error_message.format(error=self.ERROR, message=message), file=sys.stderr)

    def diff_line(self, line: str) -> None:
        self.output.write(line)


class ColoramaPrinter(BasicPrinter):
    def __init__(self, error: str, success: str, output: Optional[TextIO]):
        super().__init__(error, success, output=output)

        # Note: this constants are instance variables instead ofs class variables
        # because they refer to colorama which might not be installed.
        self.ERROR = self.style_text("ERROR", colorama.Fore.RED)
        self.SUCCESS = self.style_text("SUCCESS", colorama.Fore.GREEN)
        self.ADDED_LINE = colorama.Fore.GREEN
        self.REMOVED_LINE = colorama.Fore.RED

    @staticmethod
    def style_text(text: str, style: Optional[str] = None) -> str:
        if style is None:
            return text
        return style + text + str(colorama.Style.RESET_ALL)

    def diff_line(self, line: str) -> None:
        style = None
        if re.match(ADDED_LINE_PATTERN, line):
            style = self.ADDED_LINE
        elif re.match(REMOVED_LINE_PATTERN, line):
            style = self.REMOVED_LINE
        self.output.write(self.style_text(line, style))


def create_terminal_printer(
    color: bool, output: Optional[TextIO] = None, error: str = "", success: str = ""
) -> BasicPrinter:
    if color and colorama_unavailable:
        no_colorama_message = (
            "\n"
            "Sorry, but to use --color (color_output) the colorama python package is required.\n\n"
            "Reference: https://pypi.org/project/colorama/\n\n"
            "You can either install it separately on your system or as the colors extra "
            "for isort. Ex: \n\n"
            "$ pip install isort[colors]\n"
        )
        print(no_colorama_message, file=sys.stderr)
        sys.exit(1)

    if not colorama_unavailable:
        colorama.init(strip=False)
    return (
        ColoramaPrinter(error, success, output) if color else BasicPrinter(error, success, output)
    )
