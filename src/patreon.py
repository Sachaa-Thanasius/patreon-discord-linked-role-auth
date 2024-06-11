from __future__ import annotations

import datetime
import logging
import urllib.parse

import msgspec
from aiohttp import ClientSession, BasicAuth

from .config import CONFIG
from .structs import AccessTokenObject
from .verify import sign


LOGGER = logging.getLogger(__name__)

PATREON_BASE_API = "https://www.patreon.com/api"
PATREON_AUTH_URL = "https://www.patreon.com/oauth2/authorize"
PATREON_TOKEN_URL = f"{PATREON_BASE_API}/oauth2/token"

PATREON_AUTH = BasicAuth(CONFIG.patreon.client_id, CONFIG.patreon.client_secret)


def prepare_patreon_authorization_request(state: bytes) -> str:
    search_params = urllib.parse.urlencode(
        {
            "client_id": CONFIG.patreon.client_id,
            "redirect_uri": CONFIG.patreon.redirect_uri,
            "response_type": "code",
            "state": sign(state),
            "scope": "users pledges-to-me my-campaign",
        },
    )
    url = f"{PATREON_AUTH_URL}?{search_params}"
    return url


async def make_patreon_token_request(client: ClientSession, code: str) -> AccessTokenObject:
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": CONFIG.patreon.redirect_uri,
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
    }

    async with client.post(PATREON_TOKEN_URL, data=data, headers=headers, auth=PATREON_AUTH) as response:
        try:
            response.raise_for_status()
        except Exception as err:
            note = f"Error fetching OAuth tokens: [{response.status}] {response.reason}"  # pyright: ignore [reportUnknownMemberType]
            err.add_note(note)
            raise
        else:
            result = msgspec.json.decode(await response.read(), type=AccessTokenObject)
            LOGGER.debug("get_oauth_tokens result: %s", result)
            return result


async def prepare_patreon_refresh_token_request(client: ClientSession, user_id: str, tokens: AccessTokenObject) -> str:
    if tokens.expires_at and (datetime.datetime.now().astimezone() > tokens.expires_at):
        data = {
            "grant_type": "refresh_token",
            "refresh_token": tokens.refresh_token,
        }
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
        }

        async with client.post(PATREON_TOKEN_URL, data=data, headers=headers, auth=PATREON_AUTH) as response:
            try:
                response.raise_for_status()
            except Exception as err:
                note = f"Error refreshing access token: [{response.status}] {response.reason}"  # pyright: ignore [reportUnknownMemberType]
                err.add_note(note)
                raise
            else:
                new_tokens = msgspec.json.decode(await response.read(), type=AccessTokenObject)
                await store_discord_tokens(user_id, new_tokens)
                return new_tokens.access_token

    return tokens.access_token