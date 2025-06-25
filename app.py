"""
Asynchronous client for the Sunways cloud API.

Handles:
  • Login with MD5→Base64 password
  • JWT cookie/header management
  • Automatic token refresh when expired
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
from typing import Any

import aiohttp
from aiohttp.hdrs import SET_COOKIE

from .const import (
    DEFAULT_CHANNEL,
    HEADERS_COMMON,
    LOGIN_ENDPOINT,
    STATION_MORE_ENDPOINT,
)

_LOGGER = logging.getLogger(__name__)


class SunwaysApiError(RuntimeError):
    """Raised on HTTP errors or API-level error codes."""


class SunwaysApiClient:
    """Thin wrapper around aiohttp for the Sunways endpoints."""

    def __init__(
        self,
        base_url: str,
        email: str,
        raw_password: str,
        session: aiohttp.ClientSession,
    ) -> None:
        self._base = base_url.rstrip("/")
        self._email = email
        self._password = self._encode_password(raw_password)
        self._session = session
        self._token: str | None = None
        self._lock = asyncio.Lock()
        # Each instance gets its own copy of the headers
        self._headers = HEADERS_COMMON.copy()

    async def close(self) -> None:
        """Close the underlying aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()

    # ------------------------------------------------------------------ #
    # Public API                                                         #
    # ------------------------------------------------------------------ #
    async def get_station_data(self, station_id: str) -> dict[str, Any]:
        """
        Return JSON from /station_more.

        If the stored JWT is missing or expired, refresh once automatically.
        """
        async with self._lock:
            if self._token is None:
                await self._login()

            try:
                return await self._fetch_station(station_id)
            except SunwaysApiError as exc:
                if "token" not in str(exc).lower() and "html" not in str(exc).lower():
                    raise

                _LOGGER.info("Token invalid or expired, re-logging in")
                await self._login()
                return await self._fetch_station(station_id)

    # ------------------------------------------------------------------ #
    # Internal helpers                                                   #
    # ------------------------------------------------------------------ #
    async def _login(self) -> None:
        """POST /monitor/auth/login and manually extract the JWT from the Set-Cookie header."""
        _LOGGER.info("Attempting to login to Sunways API")
        payload = {
            "email": self._email,
            "password": self._password,
            "channel": DEFAULT_CHANNEL,
        }

        # Use a temporary header without the token for the login request itself
        login_headers = self._headers.copy()
        login_headers.pop("token", None)

        async with self._session.post(
            f"{self._base}{LOGIN_ENDPOINT}",
            json=payload,
            headers=login_headers,
        ) as resp:
            text = await resp.text()
            if resp.status != 200:
                raise SunwaysApiError(f"Login HTTP {resp.status}: {text}")

            body = await resp.json(content_type=None)
            if body.get("code") != "1000000":
                raise SunwaysApiError(
                    f'Login error {body.get("code")}: {body.get("msg")}'
                )

            # Manually parse the Set-Cookie header to find the token
            token_from_cookie = None
            if SET_COOKIE in resp.headers:
                # Simple parsing: find 'token=...' and grab value before ';'
                cookie_header = resp.headers.get(SET_COOKIE, "")
                parts = cookie_header.split(';')
                for part in parts:
                    part = part.strip()
                    if part.startswith("token="):
                        token_from_cookie = part.split('=', 1)[1]
                        break
            
            self._token = token_from_cookie

            if not self._token:
                raise SunwaysApiError("Login succeeded but no 'token' cookie was set in the response header")

            # Store the token for all subsequent requests
            self._headers["token"] = self._token
            _LOGGER.info("Login successful, manually extracted token.")
            _LOGGER.debug("Obtained JWT ending in …%s", self._token[-10:])


    async def _fetch_station(self, station_id: str) -> dict[str, Any]:
        """GET /station_more?id=… and return parsed JSON."""
        url = f"{self._base}{STATION_MORE_ENDPOINT}?id={station_id}"

        # The 'token' is now manually added to the instance headers
        async with self._session.get(url, headers=self._headers) as resp:
            text = await resp.text()

            if resp.status != 200:
                raise SunwaysApiError(f"Station HTTP {resp.status}: {text}")

            if text.lstrip().startswith("<!DOCTYPE html>"):
                raise SunwaysApiError("Token invalid – got HTML instead of JSON")

            try:
                return json.loads(text)
            except ValueError as err:
                raise SunwaysApiError(f"Bad JSON: {err}") from err

    # ------------------------------------------------------------------ #
    # Static helpers                                                     #
    # ------------------------------------------------------------------ #
    @staticmethod
    def _encode_password(raw: str) -> str:
        """
        Portal JS does: md5(password) → hex → Base64.

        If the user already supplied something that *looks* Base64,
        respect it to avoid double-encoding.
        """
        if raw.endswith("=") and len(raw) >= 22:
            return raw

        md5_hex = hashlib.md5(raw.encode()).hexdigest()
        return base64.b64encode(md5_hex.encode()).decode()
