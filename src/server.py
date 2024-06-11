from __future__ import annotations

import logging
from collections.abc import AsyncIterator

from aiohttp import ClientSession, web

from .discord import (
    get_cookie_metadata,
    get_metadata_schema,
    make_discord_token_request,
    prepare_discord_authorization_request,
    get_user_data,
    push_metadata,
)
from .patreon import (
    make_patreon_token_request,
)
from .storage import get_discord_tokens, store_discord_tokens
from .verify import random_nonce


LOGGER = logging.getLogger(__name__)


routes = web.RouteTableDef()


@routes.get("/")
async def hello(request: web.Request) -> web.Response:
    return web.Response(text="Hello, world")


@routes.get("/linked-role")
async def linked_role(request: web.Request) -> web.Response:
    state = random_nonce()
    url = prepare_discord_authorization_request(state)
    response = web.HTTPSeeOther(location=url)
    response.set_cookie(name="client_state", value=str(state), max_age=300000, httponly=True)
    raise response


@routes.get("/patreon/redirect")
async def patreon_oauth_callback(request: web.Request) -> web.Response:
    try:
        code = request.query["code"]
        patreon_state = request.query["state"]
        
        if not code or not patreon_state:
            raise web.HTTPForbidden(text="State verification failed.")  # noqa: TRY301

        client_state = request.cookies.get("client_state")
        if patreon_state != client_state:
            raise web.HTTPForbidden(text="State verification failed.")  # noqa: TRY301

        tokens = await make_patreon_token_request(request.app["client_session"], code)
        me_data = await get_user_data(request.app["client_session"], tokens)
        user_id = me_data.user.id
        await store_discord_tokens(user_id, tokens)
        await update_metadata_helper(request.app["client_session"], user_id)
    except Exception:
        LOGGER.exception("")
        raise web.HTTPInternalServerError from None
    else:
        return web.Response(text="You did it! Now go back to Discord.")


@routes.get("/discord/redirect")
async def discord_oauth_callback(request: web.Request) -> web.Response:
    try:
        code = request.query["code"]
        discord_state = request.query["state"]
        client_state = request.cookies.get("client_state")
        if discord_state != client_state:
            raise web.HTTPForbidden(text="State verification failed.")  # noqa: TRY301

        tokens = await make_discord_token_request(request.app["client_session"], code)
        me_data = await get_user_data(request.app["client_session"], tokens)
        user_id = me_data.user.id
        await store_discord_tokens(user_id, tokens)
        await update_metadata_helper(request.app["client_session"], user_id)
    except Exception:
        LOGGER.exception("")
        raise web.HTTPInternalServerError from None
    else:
        return web.Response(text="You did it! Now go back to Discord.")


@routes.post("/update-metadata")
async def update_metadata(request: web.Request) -> web.Response:
    try:
        user_id = request["user_id"]
        await update_metadata_helper(request.app["client_session"], user_id)
    except Exception:
        LOGGER.exception("")
        raise web.HTTPInternalServerError from None
    else:
        raise web.HTTPNoContent


async def update_metadata_helper(client: ClientSession, user_id: str) -> None:
    tokens = await get_discord_tokens(user_id)
    assert tokens

    metadata = {}
    try:
        metadata = {
            "cookieseaten": 1483,
            "allergictonuts": 0,
            "bakingsince": "2003-12-20",
        }
    except Exception as err:
        err.add_note("Error fetching external data.")
        LOGGER.exception("")

    await push_metadata(client, user_id, tokens, metadata)


@routes.get("/get-metadata")
async def get_metadata(request: web.Request) -> web.Response:
    try:
        user_id = request.query["user_id"]
        tokens = await get_discord_tokens(user_id)
        user_cookie_meta = await get_cookie_metadata(request.app["client_session"], user_id, tokens)
    except Exception:
        LOGGER.exception("")
        raise web.HTTPInternalServerError from None
    else:
        return web.Response(body=str(user_cookie_meta))


@routes.get("/get-schema")
async def get_meta_schema(request: web.Request) -> web.Response:
    result = await get_metadata_schema(request.app["client_session"])
    return web.Response(body=str(result))


async def client_session_ctx(app: web.Application) -> AsyncIterator[None]:
    user_agent = f"DiscordBot (https://github.com/Sachaa-Thanasius/patreon-discord-linked-role-auth, 0.0.1)"
    session = app["client_session"] = ClientSession(headers={"User-Agent": user_agent})
    yield
    await session.close()


def make_app() -> web.Application:
    app = web.Application()
    app.add_routes(routes)
    app.cleanup_ctx.append(client_session_ctx)
    return app
