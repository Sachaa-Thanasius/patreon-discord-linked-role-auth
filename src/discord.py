from __future__ import annotations

import datetime
import logging
import urllib.parse
import uuid
from enum import IntEnum
from typing import Any

import msgspec
from aiohttp import BasicAuth, ClientSession

from .config import CONFIG
from .storage import store_discord_tokens
from .structs import AccessTokenObject, OAuth2UserInfo, SchemaField


LOGGER = logging.getLogger(__name__)

BASE_DISCORD_API = "https://discord.com/api/v10"

DISCORD_AUTH = BasicAuth(CONFIG.discord_client_id, CONFIG.discord_client_secret)


class RoleConnAttrType(IntEnum):
    NUM_LESS_THAN = 1
    NUM_GREAT_THAN = 2
    NUM_EQ = 3
    NUM_NEQ = 4
    DATETIME_LESS_THAN = 5
    DATETIME_GREAT_THAN = 6
    BOOL_EQ = 7
    BOOL_NEQ = 8


SCHEMA = [
    SchemaField(
        key="cookieseaten",
        name="Cookies Eaten",
        description="Cookies Eaten Greater Than",
        type=RoleConnAttrType.NUM_GREAT_THAN,
    ),
    SchemaField(
        key="allergictonuts",
        name="Allergic To Nuts",
        description="Is Allergic To Nuts",
        type=RoleConnAttrType.BOOL_EQ,
    ),
    SchemaField(
        key="bakingsince",
        name="Baking Since",
        description="Days since baking their first cookie",
        type=RoleConnAttrType.DATETIME_GREAT_THAN,
    ),
]


def get_oauth_url() -> tuple[uuid.UUID, str]:
    state = uuid.uuid4()
    search_params = urllib.parse.urlencode(
        {
            "client_id": CONFIG.discord_client_id,
            "redirect_uri": CONFIG.discord_redirect_uri,
            "response_type": "code",
            "state": state,
            "scope": "role_connections.write identify",
            "prompt": "consent",
        },
    )
    url = f"https://discord.com/oauth2/authorize?{search_params}"
    return (state, url)


async def get_oauth_tokens(client: ClientSession, code: str) -> AccessTokenObject:
    url = f"{BASE_DISCORD_API}/oauth2/token"
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": CONFIG.discord_redirect_uri,
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
    }

    async with client.post(url, data=data, headers=headers, auth=DISCORD_AUTH) as response:
        try:
            response.raise_for_status()
        except Exception as err:
            note = f"Error fetching OAuth tokens: [{response.status}] {response.reason}"  # pyright: ignore [reportUnknownMemberType]
            err.add_note(note)
            raise
        else:
            result = msgspec.json.decode(await response.read(), type=AccessTokenObject)
            LOGGER.info("get_oauth_tokens result: %s", result)
            return result


async def get_access_token(client: ClientSession, user_id: str, tokens: AccessTokenObject) -> str:
    if tokens.expires_at and (datetime.datetime.now().astimezone() > tokens.expires_at):
        url = f"{BASE_DISCORD_API}/oauth2/token"
        data = {
            "grant_type": "refresh_token",
            "refresh_token": tokens.refresh_token,
        }
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
        }

        async with client.post(url, data=data, headers=headers, auth=DISCORD_AUTH) as response:
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


async def get_user_data(client: ClientSession, tokens: AccessTokenObject) -> OAuth2UserInfo:
    url = f"{BASE_DISCORD_API}/oauth2/@me"
    headers = {
        "Authorization": f"Bearer {tokens.access_token}",
    }

    async with client.get(url, headers=headers) as response:
        try:
            response.raise_for_status()
        except Exception as err:
            note = f"Error fetching user data: [{response.status}] {response.reason}"  # pyright: ignore [reportUnknownMemberType]
            err.add_note(note)
            raise
        else:
            result = msgspec.json.decode(await response.read(), type=OAuth2UserInfo)
            LOGGER.info("get_user_data result: %s", result)
            return result


async def push_metadata(
    client: ClientSession,
    user_id: str,
    tokens: AccessTokenObject,
    metadata: dict[str, Any],
) -> None:
    url = f"{BASE_DISCORD_API}/users/@me/applications/{CONFIG.discord_client_id}/role-connection"
    access_token = await get_access_token(client, user_id, tokens)
    data = {
        "platform_name": "Example Linked role Discord Bot",
        "metadata": metadata,
    }
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    async with client.put(url, data=msgspec.json.encode(data), headers=headers) as response:
        try:
            response.raise_for_status()
        except Exception as err:
            note = f"Error pushing discord metadata: [{response.status}] {response.reason}"  # pyright: ignore [reportUnknownMemberType]
            err.add_note(note)
            raise


async def get_cookie_metadata(client: ClientSession, user_id: str, tokens: AccessTokenObject) -> dict[str, Any]:
    url = f"{BASE_DISCORD_API}/users/@me/applications/{CONFIG.discord_client_id}/role-connection"
    access_token = await get_access_token(client, user_id, tokens)
    headers = {
        "Authorization": f"Bearer {access_token}",
    }

    async with client.get(url, headers=headers) as response:
        try:
            response.raise_for_status()
        except Exception as err:
            note = f"Error getting discord metadata: [{response.status}] {response.reason}"  # pyright: ignore [reportUnknownMemberType]
            err.add_note(note)
            raise
        else:
            result = msgspec.json.decode(await response.read())
            LOGGER.info("get_cookie_metadata result: %s", result)
            return result


async def register_metadata_schema(client: ClientSession) -> dict[str, Any]:
    url = f"{BASE_DISCORD_API}/applications/{CONFIG.discord_client_id}/role-connections/metadata"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bot {CONFIG.discord_token}",
    }

    async with client.put(url, data=msgspec.json.encode(SCHEMA), headers=headers) as response:
        try:
            response.raise_for_status()
        except Exception as err:
            note = f"Error registering metadata schema: [{response.status}] {response.reason}"  # pyright: ignore [reportUnknownMemberType]
            text = await response.text()
            err.add_note(note)
            err.add_note(text)
            raise
        else:
            result = msgspec.json.decode(await response.read())
            LOGGER.info("register_metadata_schema result: %s", result)
            return result


async def get_metadata_schema(client: ClientSession) -> dict[str, Any]:
    url = f"{BASE_DISCORD_API}/applications/{CONFIG.discord_client_id}/role-connections/metadata"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bot {CONFIG.discord_token}",
    }

    async with client.get(url, headers=headers) as response:
        try:
            response.raise_for_status()
        except Exception as err:
            note = f"Error getting metadata schema: [{response.status}] {response.reason}"  # pyright: ignore [reportUnknownMemberType]
            err.add_note(note)
            raise
        else:
            result = msgspec.json.decode(await response.read())
            LOGGER.info("get_metadata_schema result: %s", result)
            return result
