from __future__ import annotations

import logging

from aiohttp import web

from src.server import make_app


def setup_logging() -> None:
    dt_fmt = "%Y-%m-%d %H:%M:%S"
    fmt = "[{asctime}] [{levelname:<8}] {name}: {message}"
    logging.basicConfig(format=fmt, datefmt=dt_fmt, style="{", level=logging.INFO)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)


def main() -> None:
    setup_logging()
    app = make_app()
    web.run_app(app, port=80)  # pyright: ignore [reportUnknownMemberType]


if __name__ == "__main__":
    raise SystemExit(main())
