import aiohttp
from aiohttp.typedefs import StrOrURL

import black

_DEFAULT_HEADERS = {"Content-Type": "text/plain; charset=utf-8"}


class BlackDClient:
    def __init__(
        self,
        url: StrOrURL = "http://localhost:9090",
        line_length: int | None = None,
        skip_source_first_line: bool = False,
        skip_string_normalization: bool = False,
        skip_magic_trailing_comma: bool = False,
        preview: bool = False,
        fast: bool = False,
        python_variant: str | None = None,
        diff: bool = False,
        headers: dict[str, str] | None = None,
    ):
        """
        Initialize a BlackDClient object.
        :param url: The URL of the BlackD server.
        :param line_length: The maximum line length.
            Corresponds to the ``--line-length`` CLI option.
        :param skip_source_first_line: True to skip the first line of the source.
            Corresponds to the ``--skip-source-first-line`` CLI option.
        :param skip_string_normalization: True to skip string normalization.
            Corresponds to the ``--skip-string-normalization`` CLI option.
        :param skip_magic_trailing_comma: True to skip magic trailing comma.
            Corresponds to the ``--skip-magic-trailing-comma`` CLI option.
        :param preview: True to enable experimental preview mode.
            Corresponds to the ``--preview`` CLI option.
        :param fast: True to enable fast mode.
            Corresponds to the ``--fast`` CLI option.
        :param python_variant: The Python variant to use.
            Corresponds to the ``--pyi`` CLI option if this is "pyi".
            Otherwise, corresponds to the ``--target-version`` CLI option.
        :param diff: True to enable diff mode.
            Corresponds to the ``--diff`` CLI option.
        :param headers: A dictionary of additional custom headers to send with
            the request.
        """
        self.url = url
        self.headers = _DEFAULT_HEADERS.copy()

        if line_length is not None:
            self.headers["X-Line-Length"] = str(line_length)
        if skip_source_first_line:
            self.headers["X-Skip-Source-First-Line"] = "yes"
        if skip_string_normalization:
            self.headers["X-Skip-String-Normalization"] = "yes"
        if skip_magic_trailing_comma:
            self.headers["X-Skip-Magic-Trailing-Comma"] = "yes"
        if preview:
            self.headers["X-Preview"] = "yes"
        if fast:
            self.headers["X-Fast-Or-Safe"] = "fast"
        if python_variant is not None:
            self.headers["X-Python-Variant"] = python_variant
        if diff:
            self.headers["X-Diff"] = "yes"

        if headers is not None:
            self.headers.update(headers)

    async def format_code(self, unformatted_code: str) -> str:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.url, headers=self.headers, data=unformatted_code.encode("utf-8")
            ) as response:
                if response.status == 204:
                    # Input is already well-formatted
                    return unformatted_code
                elif response.status == 200:
                    # Formatting was needed
                    return await response.text()
                elif response.status == 400:
                    # Input contains a syntax error
                    error_message = await response.text()
                    raise black.InvalidInput(error_message)
                elif response.status == 500:
                    # Other kind of error while formatting
                    error_message = await response.text()
                    raise RuntimeError(f"Error while formatting: {error_message}")
                else:
                    # Unexpected response status code
                    raise RuntimeError(
                        f"Unexpected response status code: {response.status}"
                    )
