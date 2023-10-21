from __future__ import annotations

import asyncio
import logging

from .structs import AccessTokenObject


LOGGER = logging.getLogger(__name__)


TOKEN_STORE: dict[str, AccessTokenObject] = {}

store_lock = asyncio.Lock()


async def store_discord_tokens(user_id: str, tokens: AccessTokenObject) -> None:
    LOGGER.info("Storing token: user_id=%s, tokens=%s", user_id, tokens)
    async with store_lock:
        TOKEN_STORE[f"discord-{user_id}"] = tokens


async def get_discord_tokens(user_id: str) -> AccessTokenObject | None:
    LOGGER.info("Getting token: user_id=%s", user_id)
    async with store_lock:
        tokens = TOKEN_STORE.get(f"discord-{user_id}", None)
        LOGGER.info("Gotten token: %s", tokens)
        return tokens
