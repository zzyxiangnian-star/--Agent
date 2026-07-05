from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx


DEFAULT_SETTINGS = {
    "llm_enabled": False,
    "llm_provider": "disabled",
    "llm_api_key": "",
    "llm_base_url": "https://api.openai.com/v1",
    "llm_model": "gpt-4.1-mini",
    "request_timeout": 20,
    "max_tokens": 2000,
    "default_mode": "Template automation",
}


def mask_secret(secret: str) -> str:
    if not secret:
        return ""
    prefix = secret[:3] if len(secret) >= 3 else "***"
    suffix = secret[-4:] if len(secret) >= 4 else secret[-1:]
    return f"{prefix}***{suffix}"


class SettingsService:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _read_raw(self) -> dict[str, Any]:
        if not self.path.exists():
            return DEFAULT_SETTINGS.copy()
        data = json.loads(self.path.read_text(encoding="utf-8"))
        return {**DEFAULT_SETTINGS, **data}

    def _write_raw(self, settings: dict[str, Any]) -> None:
        self.path.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")

    def get_llm_settings(self) -> dict[str, Any]:
        raw = self._read_raw()
        public = raw.copy()
        public["has_api_key"] = bool(raw.get("llm_api_key"))
        public["masked_api_key"] = mask_secret(raw.get("llm_api_key", ""))
        public["llm_api_key"] = ""
        public["active_mode"] = "AI-assisted" if raw.get("llm_enabled") and raw.get("llm_api_key") else "Template automation"
        return public

    def save_llm_settings(self, payload: dict[str, Any]) -> dict[str, Any]:
        raw = self._read_raw()
        for key in DEFAULT_SETTINGS:
            if key in payload:
                if key == "llm_api_key" and payload[key] == "":
                    continue
                raw[key] = payload[key]
        if not raw.get("llm_enabled"):
            raw["llm_provider"] = "disabled"
        self._write_raw(raw)
        return self.get_llm_settings()

    def test_connection(self) -> dict[str, Any]:
        raw = self._read_raw()
        if not raw.get("llm_enabled") or not raw.get("llm_api_key"):
            return {"ok": False, "mode": "Template automation", "message": "AI 未启用或 API Key 未配置。"}
        try:
            url = raw["llm_base_url"].rstrip("/") + "/models"
            response = httpx.get(url, headers={"Authorization": f"Bearer {raw['llm_api_key']}"}, timeout=float(raw["request_timeout"]))
            if response.status_code < 400:
                return {"ok": True, "mode": "AI-assisted", "message": "模型服务连接成功。"}
            return {"ok": False, "mode": "Template automation", "message": f"模型服务返回 HTTP {response.status_code}。"}
        except Exception as exc:
            return {"ok": False, "mode": "Template automation", "message": f"连接失败：{type(exc).__name__}"}
