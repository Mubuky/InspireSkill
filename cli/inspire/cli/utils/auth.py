"""Compatibility shims for authentication-related CLI imports."""

from __future__ import annotations


class AuthenticationError(Exception):
    """Raised when the active web session cannot authenticate a request."""


class AuthManager:
    """Compatibility facade kept for account/session cache invalidation.

    Account switching still imports this class to clear old process-local
    state, so keep the tiny facade while all real requests use Browser API
    helpers backed by the web session.
    """

    _api = None
    _token = None
    _expires_at = None
    _cache_key = None

    @classmethod
    def clear_cache(cls) -> None:
        cls._api = None
        cls._token = None
        cls._expires_at = None
        cls._cache_key = None

    @classmethod
    def get_api(cls, *args, **kwargs):  # noqa: ANN001
        del args, kwargs
        raise AuthenticationError("Token API clients have been removed; use Browser API helpers.")
