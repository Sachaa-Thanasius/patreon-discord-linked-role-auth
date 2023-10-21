from __future__ import annotations

import logging
import pathlib

import msgspec

from .structs import Config


LOGGER = logging.getLogger(__name__)

with pathlib.Path("config.toml").open(encoding="utf-8") as f:
    LOGGER.debug("Reading config file...")
    data = f.read()

CONFIG = msgspec.toml.decode(data, type=Config)
