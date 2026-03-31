"""Jarvis Lite Linux assistant package."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
from starlette.testclient import TestClient


def _patch_testclient() -> None:
    if getattr(TestClient, "_jarvis_compat_patched", False):
        return

    def _request_via_asgi_transport(
        self: TestClient,
        method: str,
        url: httpx._types.URLTypes,
        *,
        content: httpx._types.RequestContent | None = None,
        data: Any = None,
        files: httpx._types.RequestFiles | None = None,
        json: Any = None,
        params: httpx._types.QueryParamTypes | None = None,
        headers: httpx._types.HeaderTypes | None = None,
        cookies: httpx._types.CookieTypes | None = None,
        auth: httpx._types.AuthTypes | httpx._client.UseClientDefault = httpx.USE_CLIENT_DEFAULT,
        follow_redirects: bool | httpx._client.UseClientDefault = httpx.USE_CLIENT_DEFAULT,
        timeout: httpx._types.TimeoutTypes | httpx._client.UseClientDefault = httpx.USE_CLIENT_DEFAULT,
        extensions: dict[str, Any] | None = None,
    ) -> httpx.Response:
        merged_url = self._merge_url(url)
        redirect_setting = self.follow_redirects if follow_redirects is httpx.USE_CLIENT_DEFAULT else follow_redirects
        timeout_setting = None if timeout is httpx.USE_CLIENT_DEFAULT else timeout
        auth_setting = None if auth is httpx.USE_CLIENT_DEFAULT else auth

        async def _send() -> httpx.Response:
            transport = httpx.ASGITransport(app=self.app)
            async with httpx.AsyncClient(
                transport=transport,
                base_url=str(self.base_url),
                headers=self.headers,
                cookies=self.cookies,
                follow_redirects=redirect_setting,
            ) as client:
                return await client.request(
                    method=method,
                    url=str(merged_url),
                    content=content,
                    data=data,
                    files=files,
                    json=json,
                    params=params,
                    headers=headers,
                    cookies=cookies,
                    auth=auth_setting,
                    timeout=timeout_setting,
                    extensions=extensions,
                )

        return asyncio.run(_send())

    TestClient.request = _request_via_asgi_transport
    TestClient._jarvis_compat_patched = True


_patch_testclient()
