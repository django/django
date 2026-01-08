import asyncio
import logging
from concurrent.futures import Executor, ProcessPoolExecutor
from datetime import datetime, timezone
from functools import cache, partial
from multiprocessing import freeze_support

try:
    from aiohttp import web
    from multidict import MultiMapping

    from .middlewares import cors
except ImportError as ie:
    raise ImportError(
        f"aiohttp dependency is not installed: {ie}. "
        + "Please re-install black with the '[d]' extra install "
        + "to obtain aiohttp_cors: `pip install black[d]`"
    ) from None

import click

import black
from _black_version import version as __version__
from black.concurrency import maybe_install_uvloop
from black.mode import Preview

# This is used internally by tests to shut down the server prematurely
_stop_signal = asyncio.Event()

# Request headers
PROTOCOL_VERSION_HEADER = "X-Protocol-Version"
LINE_LENGTH_HEADER = "X-Line-Length"
PYTHON_VARIANT_HEADER = "X-Python-Variant"
SKIP_SOURCE_FIRST_LINE = "X-Skip-Source-First-Line"
SKIP_STRING_NORMALIZATION_HEADER = "X-Skip-String-Normalization"
SKIP_MAGIC_TRAILING_COMMA = "X-Skip-Magic-Trailing-Comma"
PREVIEW = "X-Preview"
UNSTABLE = "X-Unstable"
ENABLE_UNSTABLE_FEATURE = "X-Enable-Unstable-Feature"
FAST_OR_SAFE_HEADER = "X-Fast-Or-Safe"
DIFF_HEADER = "X-Diff"

BLACK_HEADERS = [
    PROTOCOL_VERSION_HEADER,
    LINE_LENGTH_HEADER,
    PYTHON_VARIANT_HEADER,
    SKIP_SOURCE_FIRST_LINE,
    SKIP_STRING_NORMALIZATION_HEADER,
    SKIP_MAGIC_TRAILING_COMMA,
    PREVIEW,
    UNSTABLE,
    ENABLE_UNSTABLE_FEATURE,
    FAST_OR_SAFE_HEADER,
    DIFF_HEADER,
]

# Response headers
BLACK_VERSION_HEADER = "X-Black-Version"


class HeaderError(Exception):
    pass


class InvalidVariantHeader(Exception):
    pass


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--bind-host",
    type=str,
    help="Address to bind the server to.",
    default="localhost",
    show_default=True,
)
@click.option(
    "--bind-port", type=int, help="Port to listen on", default=45484, show_default=True
)
@click.version_option(version=black.__version__)
def main(bind_host: str, bind_port: int) -> None:
    logging.basicConfig(level=logging.INFO)
    app = make_app()
    ver = black.__version__
    black.out(f"blackd version {ver} listening on {bind_host} port {bind_port}")
    web.run_app(app, host=bind_host, port=bind_port, handle_signals=True, print=None)


@cache
def executor() -> Executor:
    return ProcessPoolExecutor()


def make_app() -> web.Application:
    app = web.Application(
        middlewares=[cors(allow_headers=(*BLACK_HEADERS, "Content-Type"))]
    )
    app.add_routes([web.post("/", partial(handle, executor=executor()))])
    return app


async def handle(request: web.Request, executor: Executor) -> web.Response:
    headers = {BLACK_VERSION_HEADER: __version__}
    try:
        if request.headers.get(PROTOCOL_VERSION_HEADER, "1") != "1":
            return web.Response(
                status=501, text="This server only supports protocol version 1"
            )

        fast = False
        if request.headers.get(FAST_OR_SAFE_HEADER, "safe") == "fast":
            fast = True
        try:
            mode = parse_mode(request.headers)
        except HeaderError as e:
            return web.Response(status=400, text=e.args[0])
        req_bytes = await request.content.read()
        charset = request.charset if request.charset is not None else "utf8"
        req_str = req_bytes.decode(charset)
        then = datetime.now(timezone.utc)

        header = ""
        if mode.skip_source_first_line:
            first_newline_position: int = req_str.find("\n") + 1
            header = req_str[:first_newline_position]
            req_str = req_str[first_newline_position:]

        loop = asyncio.get_event_loop()
        formatted_str = await loop.run_in_executor(
            executor, partial(black.format_file_contents, req_str, fast=fast, mode=mode)
        )

        if Preview.normalize_cr_newlines not in mode:
            # Preserve CRLF line endings
            nl = req_str.find("\n")
            if nl > 0 and req_str[nl - 1] == "\r":
                formatted_str = formatted_str.replace("\n", "\r\n")
                # If, after swapping line endings, nothing changed, then say so
                if formatted_str == req_str:
                    raise black.NothingChanged

        # Put the source first line back
        req_str = header + req_str
        formatted_str = header + formatted_str

        # Only output the diff in the HTTP response
        only_diff = bool(request.headers.get(DIFF_HEADER, False))
        if only_diff:
            now = datetime.now(timezone.utc)
            src_name = f"In\t{then}"
            dst_name = f"Out\t{now}"
            loop = asyncio.get_event_loop()
            formatted_str = await loop.run_in_executor(
                executor,
                partial(black.diff, req_str, formatted_str, src_name, dst_name),
            )

        return web.Response(
            content_type=request.content_type,
            charset=charset,
            headers=headers,
            text=formatted_str,
        )
    except black.NothingChanged:
        return web.Response(status=204, headers=headers)
    except black.InvalidInput as e:
        return web.Response(status=400, headers=headers, text=str(e))
    except Exception as e:
        logging.exception("Exception during handling a request")
        return web.Response(status=500, headers=headers, text=str(e))


def parse_mode(headers: MultiMapping[str]) -> black.Mode:
    try:
        line_length = int(headers.get(LINE_LENGTH_HEADER, black.DEFAULT_LINE_LENGTH))
    except ValueError:
        raise HeaderError("Invalid line length header value") from None

    if PYTHON_VARIANT_HEADER in headers:
        value = headers[PYTHON_VARIANT_HEADER]
        try:
            pyi, versions = parse_python_variant_header(value)
        except InvalidVariantHeader as e:
            raise HeaderError(
                f"Invalid value for {PYTHON_VARIANT_HEADER}: {e.args[0]}",
            ) from None
    else:
        pyi = False
        versions = set()

    skip_string_normalization = bool(
        headers.get(SKIP_STRING_NORMALIZATION_HEADER, False)
    )
    skip_magic_trailing_comma = bool(headers.get(SKIP_MAGIC_TRAILING_COMMA, False))
    skip_source_first_line = bool(headers.get(SKIP_SOURCE_FIRST_LINE, False))

    preview = bool(headers.get(PREVIEW, False))
    unstable = bool(headers.get(UNSTABLE, False))
    enable_features: set[black.Preview] = set()
    enable_unstable_features = headers.get(ENABLE_UNSTABLE_FEATURE, "").split(",")
    for piece in enable_unstable_features:
        piece = piece.strip()
        if piece:
            try:
                enable_features.add(black.Preview[piece])
            except KeyError:
                raise HeaderError(
                    f"Invalid value for {ENABLE_UNSTABLE_FEATURE}: {piece}",
                ) from None

    return black.FileMode(
        target_versions=versions,
        is_pyi=pyi,
        line_length=line_length,
        skip_source_first_line=skip_source_first_line,
        string_normalization=not skip_string_normalization,
        magic_trailing_comma=not skip_magic_trailing_comma,
        preview=preview,
        unstable=unstable,
        enabled_features=enable_features,
    )


def parse_python_variant_header(value: str) -> tuple[bool, set[black.TargetVersion]]:
    if value == "pyi":
        return True, set()
    else:
        versions = set()
        for version in value.split(","):
            if version.startswith("py"):
                version = version[len("py") :]
            if "." in version:
                major_str, *rest = version.split(".")
            else:
                major_str = version[0]
                rest = [version[1:]] if len(version) > 1 else []
            try:
                major = int(major_str)
                if major not in (2, 3):
                    raise InvalidVariantHeader("major version must be 2 or 3")
                if len(rest) > 0:
                    minor = int(rest[0])
                    if major == 2:
                        raise InvalidVariantHeader("Python 2 is not supported")
                else:
                    # Default to lowest supported minor version.
                    minor = 7 if major == 2 else 3
                version_str = f"PY{major}{minor}"
                if major == 3 and not hasattr(black.TargetVersion, version_str):
                    raise InvalidVariantHeader(f"3.{minor} is not supported")
                versions.add(black.TargetVersion[version_str])
            except (KeyError, ValueError):
                raise InvalidVariantHeader("expected e.g. '3.7', 'py3.5'") from None
        return False, versions


def patched_main() -> None:
    maybe_install_uvloop()
    freeze_support()
    main()


if __name__ == "__main__":
    patched_main()
