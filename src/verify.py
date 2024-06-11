from __future__ import annotations

import base64
import datetime
import os
from typing import Any

import msgspec
from cryptography import fernet

from .config import CONFIG
from .structs import AccessTokenObject


SECRET_KEY = base64.urlsafe_b64encode(CONFIG.cookie_secret)
FERNET_CRYPT = fernet.Fernet(SECRET_KEY)


def random_nonce(bytes_size: int = 16) -> bytes:
    return base64.urlsafe_b64encode(os.urandom(bytes_size))


def sign(payload: AccessTokenObject, expires: int = 300000) -> bytes:
    payload_dict = msgspec.convert(payload, type=dict[str, Any])
    payload_dict["expires_at"] = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=expires)
    data = msgspec.json.encode(payload_dict)
    signature = FERNET_CRYPT.encrypt(data)
    return base64.urlsafe_b64encode(data) + b"." + base64.urlsafe_b64encode(signature)


def verify(token: bytes) -> AccessTokenObject | None:
    data, _, signature = token.partition(b".")
    if not signature:
        return None

    payload_dict: dict[str, Any] = msgspec.json.decode(base64.urlsafe_b64decode(data))
    if payload_dict["expires_at"] < datetime.datetime.now(datetime.timezone.utc):
        return None

    is_valid = FERNET_CRYPT.decrypt(base64.urlsafe_b64encode(signature)) == base64.urlsafe_b64decode(data)
    return msgspec.convert(payload_dict, AccessTokenObject) if is_valid else None
