from __future__ import annotations

import datetime

import msgspec


class _DiscordConfig(msgspec.Struct):
    token: str
    client_id: str
    client_secret: str
    redirect_uri: str


class _PatreonConfig(msgspec.Struct):
    client_id: str
    client_secret: str
    creator_access_token: str
    creator_refresh_token: str
    redirect_uri: str


class Config(msgspec.Struct):
    cookie_secret: bytes
    discord: _DiscordConfig
    patreon: _PatreonConfig


class SchemaField(msgspec.Struct):
    key: str
    name: str
    description: str
    type: int


class AccessTokenObject(msgspec.Struct):
    access_token: str
    expires_in: int
    refresh_token: str


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
