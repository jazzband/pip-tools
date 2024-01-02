from __future__ import annotations

import typing
from gettext import gettext

import click
import os
from typing import Union, Optional, Any


class EnhancedPath(click.Path):
    """The ``EnhancedPath`` type extends the built-in ``click.Path`` type, to
    also support URLs, for example HTTP(S). Note that ``file://`` support
    """

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)

    def convert(
        self,
        value: Union[str, os.PathLike[str]],
        param: Optional[click.Parameter],
        ctx: Optional[click.Context],
    ) -> Union[str, bytes, os.PathLike[str]]:
        if isinstance(value, os.PathLike) or not EnhancedPath.is_url(value):
            return typing.cast(
                Union[str, bytes, os.PathLike[str]], super().convert(value, param, ctx)
            )

        if EnhancedPath.is_file_scheme(value):
            super().convert(EnhancedPath.file_url_to_path(value), param, ctx)
            return value

        from urllib.request import urlopen
        from urllib.error import HTTPError, URLError

        def handle_http_error(
            http_error: HTTPError,
        ) -> None:
            if http_error.code == 404 and self.exists:
                self.fail(
                    gettext("{name} {filename!r} does not exist.").format(
                        name=self.name.title(), filename=value
                    ),
                    param,
                    ctx,
                )

            if http_error.code == 403 and self.readable:
                self.fail(
                    gettext("{name} {filename!r} is not readable.").format(
                        name=self.name.title(), filename=value
                    ),
                    param,
                    ctx,
                )
            self.fail(
                gettext(
                    "failed checking {name} {filename!r} with error code {code}."
                ).format(
                    name=self.name.title(),
                    filename=value,
                    code=http_error.code,
                ),
                param,
                ctx,
            )

        try:
            urlopen(value)
            return value
        except URLError as e:
            if isinstance(e, HTTPError):
                handle_http_error(e)

            self.fail(
                gettext("failed checking {name} {filename!r}.").format(
                    name=self.name.title(),
                    filename=value,
                ),
                param,
                ctx,
            )

    @staticmethod
    def is_url(value: str) -> bool:
        return True if "://" in value else False

    @staticmethod
    def is_file_scheme(url: str) -> bool:
        from urllib.parse import urlparse

        return urlparse(url).scheme == "file"

    @staticmethod
    def file_url_to_path(url: str) -> str:
        from urllib.parse import unquote_plus, urlparse

        return unquote_plus(urlparse(url).path)
