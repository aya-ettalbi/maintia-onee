from __future__ import annotations

import asyncio

import httpx

from app.core.config import settings


async def main() -> None:
    api_key = str(settings.OPENROUTER_API_KEY or "").strip()
    base_url = str(
        settings.OPENROUTER_BASE_URL
    ).rstrip("/")

    if not api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY est absente."
        )

    async with httpx.AsyncClient(
        timeout=30.0,
    ) as client:
        response = await client.get(
            f"{base_url}/key",
            headers={
                "Authorization": f"Bearer {api_key}",
            },
        )

    print("Statut HTTP :", response.status_code)

    if response.status_code >= 400:
        print(response.text[:1000])
        raise SystemExit(1)

    data = response.json().get("data") or {}

    print("Clé valide : Oui")
    print("Libellé :", data.get("label"))
    print("Offre gratuite :", data.get("is_free_tier"))
    print("Limite restante :", data.get("limit_remaining"))
    print("Expiration :", data.get("expires_at"))


if __name__ == "__main__":
    asyncio.run(main())
