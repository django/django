"""All isort specific exception classes should be defined here"""

from functools import partial
from pathlib import Path
from typing import Any, Dict, List, Type, Union

from .profiles import profiles


class ISortError(Exception):
    """Base isort exception object from which all isort sourced exceptions should inherit"""

    def __reduce__(self):  # type: ignore
        return (partial(type(self), **self.__dict__), ())


class InvalidSettingsPath(ISortError):
    """Raised when a settings path is provided that is neither a valid file or directory"""

    def __init__(self, settings_path: str):
        super().__init__(
            f"isort was told to use the settings_path: {settings_path} as the base directory or "
            "file that represents the starting point of config file discovery, but it does not "
            "exist."
        )
        self.settings_path = settings_path


class ExistingSyntaxErrors(ISortError):
    """Raised when isort is told to sort imports within code that has existing syntax errors"""

    def __init__(self, file_path: str):
        super().__init__(
            f"isort was told to sort imports within code that contains syntax errors: "
            f"{file_path}."
        )
        self.file_path = file_path


class IntroducedSyntaxErrors(ISortError):
    """Raised when isort has introduced a syntax error in the process of sorting imports"""

    def __init__(self, file_path: str):
        super().__init__(
            f"isort introduced syntax errors when attempting to sort the imports contained within "
            f"{file_path}."
        )
        self.file_path = file_path


class FileSkipped(ISortError):
    """Should be raised when a file is skipped for any reason"""

    def __init__(self, message: str, file_path: str):
        super().__init__(message)
        self.message = message
        self.file_path = file_path


class FileSkipComment(FileSkipped):
    """Raised when an entire file is skipped due to a isort skip file comment"""

    def __init__(self, file_path: str, **kwargs: str):
        super().__init__(
            f"{file_path} contains a file skip comment and was skipped.", file_path=file_path
        )


class FileSkipSetting(FileSkipped):
    """Raised when an entire file is skipped due to provided isort settings"""

    def __init__(self, file_path: str, **kwargs: str):
        super().__init__(
            f"{file_path} was skipped as it's listed in 'skip' setting"
            " or matches a glob in 'skip_glob' setting",
            file_path=file_path,
        )


class ProfileDoesNotExist(ISortError):
    """Raised when a profile is set by the user that doesn't exist"""

    def __init__(self, profile: str):
        super().__init__(
            f"Specified profile of {profile} does not exist. "
            f"Available profiles: {','.join(profiles)}."
        )
        self.profile = profile


class SortingFunctionDoesNotExist(ISortError):
    """Raised when the specified sorting function isn't available"""

    def __init__(self, sort_order: str, available_sort_orders: List[str]):
        super().__init__(
            f"Specified sort_order of {sort_order} does not exist. "
            f"Available sort_orders: {','.join(available_sort_orders)}."
        )
        self.sort_order = sort_order
        self.available_sort_orders = available_sort_orders


class FormattingPluginDoesNotExist(ISortError):
    """Raised when a formatting plugin is set by the user that doesn't exist"""

    def __init__(self, formatter: str):
        super().__init__(f"Specified formatting plugin of {formatter} does not exist. ")
        self.formatter = formatter


class LiteralParsingFailure(ISortError):
    """Raised when one of isorts literal sorting comments is used but isort can't parse the
    the given data structure.
    """

    def __init__(self, code: str, original_error: Union[Exception, Type[Exception]]):
        super().__init__(
            f"isort failed to parse the given literal {code}. It's important to note "
            "that isort literal sorting only supports simple literals parsable by "
            f"ast.literal_eval which gave the exception of {original_error}."
        )
        self.code = code
        self.original_error = original_error


class LiteralSortTypeMismatch(ISortError):
    """Raised when an isort literal sorting comment is used, with a type that doesn't match the
    supplied data structure's type.
    """

    def __init__(self, kind: type, expected_kind: type):
        super().__init__(
            f"isort was told to sort a literal of type {expected_kind} but was given "
            f"a literal of type {kind}."
        )
        self.kind = kind
        self.expected_kind = expected_kind


class AssignmentsFormatMismatch(ISortError):
    """Raised when isort is told to sort assignments but the format of the assignment section
    doesn't match isort's expectation.
    """

    def __init__(self, code: str):
        super().__init__(
            "isort was told to sort a section of assignments, however the given code:\n\n"
            f"{code}\n\n"
            "Does not match isort's strict single line formatting requirement for assignment "
            "sorting:\n\n"
            "{variable_name} = {value}\n"
            "{variable_name2} = {value2}\n"
            "...\n\n"
        )
        self.code = code


class UnsupportedSettings(ISortError):
    """Raised when settings are passed into isort (either from config, CLI, or runtime)
    that it doesn't support.
    """

    @staticmethod
    def _format_option(name: str, value: Any, source: str) -> str:
        return f"\t- {name} = {value}  (source: '{source}')"

    def __init__(self, unsupported_settings: Dict[str, Dict[str, str]]):
        errors = "\n".join(
            self._format_option(name, **option) for name, option in unsupported_settings.items()
        )

        super().__init__(
            "isort was provided settings that it doesn't support:\n\n"
            f"{errors}\n\n"
            "For a complete and up-to-date listing of supported settings see: "
            "https://pycqa.github.io/isort/docs/configuration/options.\n"
        )
        self.unsupported_settings = unsupported_settings


class UnsupportedEncoding(ISortError):
    """Raised when isort encounters an encoding error while trying to read a file"""

    def __init__(self, filename: Union[str, Path]):
        super().__init__(f"Unknown or unsupported encoding in {filename}")
        self.filename = filename


class MissingSection(ISortError):
    """Raised when isort encounters an import that matches a section that is not defined"""

    def __init__(self, import_module: str, section: str):
        super().__init__(
            f"Found {import_module} import while parsing, but {section} was not included "
            "in the `sections` setting of your config. Please add it before continuing\n"
            "See https://pycqa.github.io/isort/#custom-sections-and-ordering "
            "for more info."
        )
