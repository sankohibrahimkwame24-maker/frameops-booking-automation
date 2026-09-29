from typing import Any
import httpx

class CalendlyClient:
    def __init__(self, token: str):
        self.token = token

    async def get_invitee(self, invitee_uri: str) -> dict[str, Any]:
        if not self.token:
            raise RuntimeError("Calendly API token is not configured.")
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(invitee_uri, headers={"Authorization": f"Bearer {self.token}"})
            response.raise_for_status()
            return response.json()["resource"]
