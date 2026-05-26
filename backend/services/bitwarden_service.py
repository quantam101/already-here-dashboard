"""Bitwarden / Vaultwarden CLI integration — $0 self-hosted secret vault.

Strategy: shell out to the official `bw` CLI (single static binary, no SDK).
The operator runs once on the OCI host:

    bw config server https://vault.bitwarden.com   # or your self-hosted URL
    bw login your@email.com                         # interactive
    export BW_SESSION="$(bw unlock --raw)"          # writes to /opt/command-os/backend/.env
    docker compose restart backend

This service then uses the session token (read-only) to list/fetch items.
Falls back gracefully to environment variables if `bw` is not installed.

Zero-cost: Vaultwarden self-hosted (Docker image, Always-Free compatible)
or Bitwarden free tier (free for personal use).
"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
from typing import Any


def _bw_binary() -> str | None:
    """Locate the `bw` CLI binary, or None if not installed."""
    return shutil.which("bw")


async def _run_bw(*args: str, timeout: float = 8.0) -> tuple[int, str, str]:
    """Run `bw <args>` with the BW_SESSION env. Returns (rc, stdout, stderr)."""
    bw = _bw_binary()
    if not bw:
        return 127, "", "bw CLI not installed"
    session = os.environ.get("BW_SESSION", "")
    env = {**os.environ, "BW_SESSION": session, "NODE_NO_WARNINGS": "1"}
    proc = await asyncio.create_subprocess_exec(
        bw, *args, "--nointeraction",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, env=env,
    )
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        return 124, "", "bw command timed out"
    return proc.returncode or 0, out.decode("utf-8", errors="replace"), err.decode("utf-8", errors="replace")


class BitwardenService:
    """Async wrapper around the Bitwarden CLI."""

    async def is_available(self) -> bool:
        """True only when `bw` is installed AND a valid BW_SESSION is set."""
        if not _bw_binary():
            return False
        if not os.environ.get("BW_SESSION"):
            return False
        # `bw status` returns json with "status": "unlocked" when ready
        rc, out, _ = await _run_bw("status")
        if rc != 0 or not out:
            return False
        try:
            return json.loads(out).get("status") == "unlocked"
        except (json.JSONDecodeError, ValueError):
            return False

    async def status(self) -> dict[str, Any]:
        """Return the operator-facing status (no secrets leaked)."""
        if not _bw_binary():
            return {"installed": False, "unlocked": False, "server": None, "user": None, "reason": "bw CLI not installed"}
        if not os.environ.get("BW_SESSION"):
            return {"installed": True, "unlocked": False, "server": None, "user": None, "reason": "BW_SESSION env not set"}
        rc, out, err = await _run_bw("status")
        if rc != 0:
            return {"installed": True, "unlocked": False, "server": None, "user": None, "reason": err.strip()[:200] or "bw status failed"}
        try:
            data = json.loads(out)
        except (json.JSONDecodeError, ValueError):
            return {"installed": True, "unlocked": False, "server": None, "user": None, "reason": "bw status returned non-json"}
        return {
            "installed": True,
            "unlocked": data.get("status") == "unlocked",
            "server": data.get("serverUrl") or "https://vault.bitwarden.com",
            "user": data.get("userEmail"),
            "reason": data.get("status"),
        }

    async def list_items(self, limit: int = 200) -> list[dict[str, Any]]:
        """List items in the vault (names + ids only; never password values)."""
        rc, out, _ = await _run_bw("list", "items")
        if rc != 0:
            return []
        try:
            items = json.loads(out)
        except (json.JSONDecodeError, ValueError):
            return []
        rows = []
        for it in items[:limit]:
            login = it.get("login") or {}
            rows.append({
                "id": it.get("id"),
                "name": it.get("name"),
                "type": it.get("type"),
                "folder_id": it.get("folderId"),
                "username": login.get("username"),
                "has_password": bool(login.get("password")),
                "has_totp": bool(login.get("totp")),
                "uris": [u.get("uri") for u in (login.get("uris") or []) if u.get("uri")],
                "revision_date": it.get("revisionDate"),
            })
        return rows

    async def get_secret(self, item_name: str) -> str | None:
        """Fetch a single item's password value by name.

        Falls back to env variable lookup if Bitwarden is not configured —
        keeps existing code paths working unchanged.
        """
        if await self.is_available():
            rc, out, _ = await _run_bw("get", "password", item_name)
            if rc == 0 and out.strip():
                return out.strip()
        return os.environ.get(item_name)


_singleton: BitwardenService | None = None


def get_bitwarden_service() -> BitwardenService:
    global _singleton
    if _singleton is None:
        _singleton = BitwardenService()
    return _singleton


# Backwards-compatible alias (was `BitwartdenService` — typo in prior code)
BitwartdenService = BitwardenService
