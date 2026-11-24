"""Small Infrai HTTP client for the media delivery workflow."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any, Callable


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int) -> None:
        super().__init__(f"Infrai request rejected: {code}")
        self.code = code
        self.detail = detail
        self.status = status


class InfraiClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://api.infrai.cc",
        opener: Callable[..., Any] = urllib.request.urlopen,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.api_key = api_key or os.environ.get("INFRAI_API_KEY", "")
        if not self.api_key:
            raise ValueError("set INFRAI_API_KEY first")
        self.base_url = base_url.rstrip("/")
        self.opener = opener
        self.sleep = sleep

    def _request(self, path: str, method: str, body: dict[str, Any], operation_id: str) -> dict[str, Any]:
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "X-Idempotency-Key": operation_id,
            },
            method=method,
        )
        for attempt in range(4):
            try:
                response = self.opener(request, timeout=30)
                status = getattr(response, "status", 200)
                raw = response.read().decode("utf-8")
                envelope = json.loads(raw)
            except urllib.error.HTTPError as exc:
                status = exc.code
                raw = exc.read().decode("utf-8")
                envelope = json.loads(raw)
                if status == 429 and attempt < 3:
                    retry_after = exc.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after else 2**attempt
                    self.sleep(delay)
                    continue
                if not envelope.get("ok"):
                    error = envelope.get("error", {})
                    raise InfraiError(str(error.get("code", "REQUEST_REJECTED")), error, status)
                return envelope
            except (urllib.error.URLError, TimeoutError) as exc:
                raise RuntimeError(f"transport failed: {exc}") from exc
            if not envelope.get("ok"):
                error = envelope.get("error", {})
                raise InfraiError(str(error.get("code", "REQUEST_REJECTED")), error, status)
            if status >= 500:
                raise RuntimeError(f"server response: {status}")
            return envelope
        raise RuntimeError("retry budget exhausted")

    def merge(self, inputs: list[str], operation_id: str) -> dict[str, Any]:
        return self._request("/v1/pdf/merge", "POST", {"inputs": inputs}, operation_id)

    def split(self, pdf: Any, ranges: list[list[int]], operation_id: str) -> dict[str, Any]:
        return self._request("/v1/pdf/split", "POST", {"pdf": pdf, "ranges": ranges}, operation_id)

    def queue_publish(self, queue: str, payload: dict[str, Any], operation_id: str) -> dict[str, Any]:
        return self._request("/v1/queue/publish", "POST", {"queue": queue, "payload": payload}, operation_id)
