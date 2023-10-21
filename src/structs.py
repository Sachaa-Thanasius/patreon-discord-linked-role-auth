from __future__ import annotations

import datetime
from typing import Self

import msgspec


class Config(msgspec.Struct):
    discord_token: str
    discord_client_id: str
    discord_client_secret: str
    discord_redirect_uri: str
    cookie_secret: str


class SchemaField(msgspec.Struct):
    key: str
    name: str
    description: str
    type: int


class AccessTokenObject(msgspec.Struct):
    access_token: str
    token_type: str
    expires_in: int
    refresh_token: str
    scope: str
    expires_at: datetime.datetime | None = None

    def __post_init__(self: Self) -> None:
        self.expires_at = datetime.datetime.now().astimezone() + datetime.timedelta(seconds=self.expires_in)


class _ApplicationInfo(msgspec.Struct):
    id: str
    name: str
    description: str
    summary: str
    hook: bool
    bot_public: bool
    bot_require_code_grant: bool
    verify_key: str
    flags: int
    icon: str | None = None
    type: str | None = None


class _UserInfo(msgspec.Struct):
    id: str
    username: str
    avatar: str
    discriminator: str
    public_flags: int
    avatar_decoration: str | None = None


class OAuth2UserInfo(msgspec.Struct):
    application: _ApplicationInfo
    scopes: list[str]
    expires: datetime.datetime
    user: _UserInfo
