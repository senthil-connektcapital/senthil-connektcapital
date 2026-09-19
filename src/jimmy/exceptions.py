"""Jimmy SDK exceptions (OpenAI-style names)."""

from __future__ import annotations


class JimmyError(Exception):
    """Base error for the Jimmy SDK."""


class APIError(JimmyError):
    """Raised when the API returns an error payload or unexpected body."""

    def __init__(self, message: str, *, request_id: str | None = None, body: object = None):
        super().__init__(message)
        self.message = message
        self.request_id = request_id
        self.body = body


class APIStatusError(APIError):
    """Raised when the HTTP status is not 2xx."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int,
        request_id: str | None = None,
        body: object = None,
    ):
        super().__init__(message, request_id=request_id, body=body)
        self.status_code = status_code


class APIConnectionError(JimmyError):
    """Raised when a network / transport error occurs."""

    def __init__(self, message: str = "Connection error.", *, request: object = None):
        super().__init__(message)
        self.request = request
