from __future__ import annotations

import json
import re
from typing import Any

import httpx

from app.core.config import settings


class OpenRouterError(RuntimeError):
    pass


def _extract_text_content(value: Any) -> str:
    if isinstance(value, str):
        return value

    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            if isinstance(item, dict):
                text = item.get("text") or item.get("content")
                if text:
                    parts.append(str(text))
            elif item:
                parts.append(str(item))
        return "\n".join(parts)

    return str(value or "")


def _parse_json_content(content: str) -> dict[str, Any]:
    cleaned = content.strip()

    if cleaned.startswith("```"):
        cleaned = re.sub(
            r"^```(?:json)?\s*",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )
        cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as error:
        raise OpenRouterError(
            "La réponse OpenRouter n'est pas un JSON valide."
        ) from error

    if not isinstance(parsed, dict):
        raise OpenRouterError(
            "La réponse OpenRouter doit être un objet JSON."
        )

    return parsed


class OpenRouterClient:
    def __init__(self) -> None:
        self.api_key = str(
            getattr(settings, "OPENROUTER_API_KEY", "") or ""
        ).strip()
        self.model = str(
            getattr(settings, "OPENROUTER_MODEL", "openrouter/free")
        ).strip()
        self.base_url = str(
            getattr(
                settings,
                "OPENROUTER_BASE_URL",
                "https://openrouter.ai/api/v1",
            )
        ).rstrip("/")

        if not self.api_key:
            raise OpenRouterError(
                "OPENROUTER_API_KEY est absente."
            )

    def _headers(self) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-Title": "MaintIA ONEE",
        }

        site_url = str(
            getattr(settings, "OPENROUTER_SITE_URL", "") or ""
        ).strip()
        if site_url:
            headers["HTTP-Referer"] = site_url

        return headers

    async def _post(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(120.0),
        ) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=payload,
            )

        if response.status_code >= 400:
            detail = response.text[:1000]
            raise OpenRouterError(
                f"OpenRouter HTTP {response.status_code}: {detail}"
            )

        data = response.json()
        choices = data.get("choices") or []

        if not choices:
            raise OpenRouterError(
                "OpenRouter n'a retourné aucun choix."
            )

        message = choices[0].get("message") or {}
        content = _extract_text_content(
            message.get("content")
        )

        if not content.strip():
            raise OpenRouterError(
                "OpenRouter a retourné une réponse vide."
            )

        return {
            "content": content,
            "model": str(data.get("model") or self.model),
            "usage": data.get("usage") or {},
        }

    async def generate_structured(
        self,
        *,
        messages: list[dict[str, str]],
        json_schema: dict[str, Any],
        schema_name: str,
    ) -> tuple[dict[str, Any], str]:
        base_payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.15,
            "max_tokens": 1200,
        }

        structured_payload = {
            **base_payload,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": schema_name,
                    "strict": True,
                    "schema": json_schema,
                },
            },
            "provider": {
                "require_parameters": True,
            },
        }

        try:
            result = await self._post(structured_payload)
            return (
                _parse_json_content(result["content"]),
                result["model"],
            )
        except OpenRouterError:
            # Certains modèles gratuits ne prennent pas en charge
            # response_format=json_schema. On refait une tentative avec
            # une instruction JSON explicite.
            fallback_messages = [
                *messages,
                {
                    "role": "system",
                    "content": (
                        "Retourne uniquement un objet JSON valide, "
                        "sans bloc Markdown et sans texte avant ou après."
                    ),
                },
            ]
            fallback_payload = {
                **base_payload,
                "messages": fallback_messages,
                "response_format": {
                    "type": "json_object",
                },
            }

            result = await self._post(fallback_payload)
            return (
                _parse_json_content(result["content"]),
                result["model"],
            )
