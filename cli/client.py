"""
BharatBuild CLI — HTTP API Client
===================================
Handles all communication with the BharatBuild backend:
  - Authenticated REST calls (GET/POST/DELETE/PATCH)
  - Server-Sent Events (SSE) streaming for code generation
  - Automatic token refresh
  - Retry with exponential back-off
"""

from __future__ import annotations

import json
import time
import asyncio
from typing import Any, AsyncGenerator, Dict, Optional
from pathlib import Path

import httpx
from rich.console import Console

from cli.config import CLIConfig

console = Console(stderr=True)

# ── retry knobs ─────────────────────────────────────────────────────────────
_MAX_RETRIES   = 3
_RETRY_BACKOFF = [1, 2, 4]          # seconds between retries
_RETRYABLE     = {408, 429, 500, 502, 503, 504}


class APIError(Exception):
    """Raised when the backend returns an error response."""
    def __init__(self, status: int, detail: str):
        self.status  = status
        self.detail  = detail
        super().__init__(f"HTTP {status}: {detail}")


class AuthError(APIError):
    """Raised on 401 / 403 — caller should re-login."""


class BharatBuildClient:
    """
    Async HTTP client for the BharatBuild backend.

    Usage
    -----
    async with BharatBuildClient(config) as client:
        me = await client.get("/users/me")
        async for event in client.stream_sse("/bolt/chat/stream", payload):
            print(event)
    """

    def __init__(self, config: CLIConfig):
        self.config  = config
        self._client: Optional[httpx.AsyncClient] = None

    # ── lifecycle ────────────────────────────────────────────────────────────

    async def __aenter__(self) -> "BharatBuildClient":
        self._client = httpx.AsyncClient(
            base_url   = self.config.api_base_url,
            timeout    = httpx.Timeout(self.config.timeout, connect=10.0),
            headers    = self._base_headers(),
            follow_redirects=True,
        )
        return self

    async def __aexit__(self, *_):
        if self._client:
            await self._client.aclose()
            self._client = None

    # ── helpers ──────────────────────────────────────────────────────────────

    def _base_headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept":        "application/json",
            "X-Client":      "bharatbuild-cli/1.0",
        }
        if self.config.auth_token:
            headers["Authorization"] = f"Bearer {self.config.auth_token}"
        if self.config.api_key:
            headers["X-API-Key"] = self.config.api_key
        return headers

    def _refresh_auth(self) -> None:
        """Reload token from config file in case it was refreshed elsewhere."""
        disk_cfg = CLIConfig.load_default()
        if disk_cfg.auth_token:
            self.config.auth_token = disk_cfg.auth_token
            if self._client:
                self._client.headers.update(
                    {"Authorization": f"Bearer {self.config.auth_token}"}
                )

    def _raise_for_status(self, resp: httpx.Response) -> None:
        if resp.status_code < 400:
            return
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text or str(resp.status_code)
        if resp.status_code in (401, 403):
            raise AuthError(resp.status_code, detail)
        raise APIError(resp.status_code, detail)

    # ── core request with retry ───────────────────────────────────────────────

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: Any  = None,
        params: Any     = None,
        data:   Any     = None,
        files:  Any     = None,
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> httpx.Response:
        assert self._client, "Client not started — use 'async with'"

        headers = {}
        if extra_headers:
            headers.update(extra_headers)
        if files:
            # Remove Content-Type so httpx sets multipart boundary
            headers["Content-Type"] = None          # type: ignore[assignment]

        for attempt, backoff in enumerate([0] + _RETRY_BACKOFF):
            if backoff:
                await asyncio.sleep(backoff)
            try:
                resp = await self._client.request(
                    method,
                    path,
                    json    = json_body,
                    params  = params,
                    data    = data,
                    files   = files,
                    headers = {k: v for k, v in headers.items() if v is not None},
                )

                # Auto-refresh token once on 401
                if resp.status_code == 401 and attempt == 0:
                    self._refresh_auth()
                    continue

                if resp.status_code in _RETRYABLE and attempt < _MAX_RETRIES:
                    continue

                self._raise_for_status(resp)
                return resp

            except (httpx.ConnectError, httpx.TimeoutException) as exc:
                if attempt < _MAX_RETRIES:
                    continue
                raise APIError(0, f"Connection error: {exc}") from exc

        raise APIError(0, "Max retries exceeded")

    # ── public REST methods ───────────────────────────────────────────────────

    async def get(self, path: str, params: Any = None) -> Dict[str, Any]:
        resp = await self._request("GET", path, params=params)
        return resp.json()

    async def post(self, path: str, body: Any = None, params: Any = None) -> Dict[str, Any]:
        resp = await self._request("POST", path, json_body=body, params=params)
        return resp.json()

    async def patch(self, path: str, body: Any = None) -> Dict[str, Any]:
        resp = await self._request("PATCH", path, json_body=body)
        return resp.json()

    async def delete(self, path: str) -> Dict[str, Any]:
        resp = await self._request("DELETE", path)
        try:
            return resp.json()
        except Exception:
            return {"ok": True}

    async def upload(self, path: str, file_path: Path, field: str = "file") -> Dict[str, Any]:
        with open(file_path, "rb") as fh:
            files = {field: (file_path.name, fh, "application/octet-stream")}
            resp  = await self._request("POST", path, files=files)
        return resp.json()

    # ── SSE streaming ─────────────────────────────────────────────────────────

    async def stream_sse(
        self,
        path: str,
        body: Any = None,
        method: str = "POST",
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Yield parsed Server-Sent Event dicts as they arrive.

        Each dict has at least a ``type`` key.  Unknown/malformed lines are
        silently skipped so the caller never has to deal with raw SSE protocol.
        """
        assert self._client, "Client not started — use 'async with'"
        headers = {
            "Accept":       "text/event-stream",
            "Content-Type": "application/json",
        }
        if self.config.auth_token:
            headers["Authorization"] = f"Bearer {self.config.auth_token}"

        buffer = ""
        async with self._client.stream(
            method,
            path,
            json    = body,
            headers = headers,
            timeout = httpx.Timeout(self.config.timeout, connect=10.0),
        ) as resp:
            self._raise_for_status(resp)
            async for raw_line in resp.aiter_lines():
                line = raw_line.strip()
                if not line:
                    # blank line = end of event; parse accumulated buffer
                    if buffer.startswith("data:"):
                        payload = buffer[5:].strip()
                        if payload == "[DONE]":
                            return
                        try:
                            yield json.loads(payload)
                        except json.JSONDecodeError:
                            yield {"type": "text", "data": payload}
                    buffer = ""
                else:
                    buffer += line

    # ── convenience wrappers ──────────────────────────────────────────────────

    async def health(self) -> bool:
        """Return True if the backend is reachable and healthy."""
        try:
            data = await self.get("/health")
            return data.get("status") == "healthy"
        except Exception:
            return False

    async def me(self) -> Dict[str, Any]:
        return await self.get("/users/me")

    async def login(self, email: str, password: str) -> Dict[str, Any]:
        return await self.post("/auth/login", {"email": email, "password": password})

    async def register(self, email: str, password: str, name: str) -> Dict[str, Any]:
        return await self.post("/auth/register", {"email": email, "password": password, "name": name})

    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        return await self.post("/auth/refresh", {"refresh_token": refresh_token})

    # projects
    async def list_projects(self, skip: int = 0, limit: int = 20) -> Dict[str, Any]:
        return await self.get("/projects/", {"skip": skip, "limit": limit})

    async def get_project(self, project_id: str) -> Dict[str, Any]:
        return await self.get(f"/projects/{project_id}")

    async def create_project(self, title: str, description: str = "", mode: str = "developer") -> Dict[str, Any]:
        return await self.post("/projects/", {"title": title, "description": description, "mode": mode})

    async def delete_project(self, project_id: str) -> Dict[str, Any]:
        return await self.delete(f"/projects/{project_id}")

    # token balance
    async def token_balance(self) -> Dict[str, Any]:
        try:
            return await self.get("/tokens/balance")
        except APIError:
            return {"balance": "N/A"}

    # classify prompt
    async def classify_prompt(self, prompt: str) -> str:
        try:
            data = await self.post("/classify/", {"prompt": prompt})
            return data.get("classification", "project_request")
        except Exception:
            return "project_request"
