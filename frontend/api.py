"""Typed, testable HTTP adapter for the existing FastAPI inspection backend.

No YOLO inference occurs here. Keep inference, business rules and persistence in backend/.
"""
from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests


class APIError(RuntimeError):
    """The API is unreachable or returned an unsuccessful response."""


def normalize_api_url(value: str) -> str:
    value = value.strip().rstrip("/")
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.path not in ("", "/"):
        raise APIError("Enter a valid API base URL, such as http://127.0.0.1:8000")
    if parsed.query or parsed.fragment or parsed.username or parsed.password:
        raise APIError("The API base URL must not contain credentials, query strings, or fragments.")
    return value


class PackageAPI:
    def __init__(self, base_url: str):
        self.base_url = normalize_api_url(base_url)

    def _call(self, method: str, path: str, *, timeout: int | tuple[int, int] = 20, **kwargs) -> requests.Response:
        if not path.startswith("/") or path.startswith("//"):
            raise APIError("Invalid API endpoint path.")
        try:
            response = requests.request(method, self.base_url + path, timeout=timeout, **kwargs)
        except requests.Timeout as exc:
            raise APIError("The backend request timed out. YOLO can take longer on the first run; retry or inspect the backend terminal.") from exc
        except requests.RequestException as exc:
            raise APIError(f"Cannot contact the FastAPI backend at {self.base_url}. Start the backend and try again. ({exc})") from exc
        if not response.ok:
            try:
                detail = response.json().get("detail", response.text)
                if isinstance(detail, (list, dict)):
                    detail = str(detail)
            except (ValueError, AttributeError):
                detail = response.text
            raise APIError(f"Backend returned HTTP {response.status_code}: {str(detail)[:500]}")
        return response

    def _json(self, method: str, path: str, **kwargs) -> Any:
        response = self._call(method, path, **kwargs)
        try:
            return response.json()
        except ValueError as exc:
            raise APIError(f"Backend response from {path} was not valid JSON.") from exc

    def health(self) -> dict:
        return self._json("GET", "/health", timeout=6)

    def checklists(self) -> list[dict]:
        return self._json("GET", "/checklists", timeout=10)

    def summary(self) -> dict:
        return self._json("GET", "/summary", timeout=10)

    def inspections(self, limit: int = 100) -> list[dict]:
        if not 1 <= limit <= 500:
            raise ValueError("limit must be between 1 and 500")
        return self._json("GET", "/inspections", params={"limit": limit}, timeout=20)

    @staticmethod
    def _file_tuple(filename: str, raw: bytes):
        # Do not pass user-supplied directories through to the API.
        safe_name = Path(filename.replace("\\", "/")).name
        mime = mimetypes.guess_type(safe_name)[0] or "application/octet-stream"
        return (safe_name, raw, mime)

    def inspect_one(self, filename: str, raw: bytes, checklist_id: str) -> dict:
        return self._json(
            "POST", "/inspect", data={"checklist_id": checklist_id},
            files={"file": self._file_tuple(filename, raw)},
            timeout=(10, 600),
        )

    def inspect_batch(self, files: list[tuple[str, bytes]], checklist_id: str) -> list[dict]:
        if not 1 <= len(files) <= 10:
            raise ValueError("The backend supports 1 to 10 images per batch.")
        return self._json(
            "POST", "/inspect/batch", data={"checklist_id": checklist_id},
            files=[("files", self._file_tuple(name, raw)) for name, raw in files],
            timeout=(10, max(600, 180 * len(files))),
        )

    def annotated_image(self, image_path: str) -> bytes:
        # The backend supplies a relative route, not an arbitrary URL.
        if (not image_path.startswith("/inspections/") or
                not image_path.endswith("/image") or
                any(part in (".", "..", "") for part in image_path.split("/")[1:])):
            raise APIError("Invalid annotated-image path returned by the backend.")
        return self._call("GET", image_path, timeout=30).content

    def export_csv(self) -> bytes:
        return self._call("GET", "/inspections/export.csv", timeout=90).content
