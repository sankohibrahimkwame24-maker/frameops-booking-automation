import httpx


class CalendlyAPIError(RuntimeError):
    pass


class CalendlyClient:
    def __init__(self, token: str):
        if not token:
            raise ValueError("CALENDLY_API_TOKEN is not configured.")
        self._headers = {"Authorization": f"Bearer {token}"}

    @staticmethod
    def _resource(response: httpx.Response) -> dict:
        response.raise_for_status()
        payload = response.json()
        return payload.get("resource", payload)

    async def get_invitee(self, invitee_uri: str) -> dict:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(invitee_uri, headers=self._headers)
        try:
            return self._resource(response)
        except Exception as exc:
            raise CalendlyAPIError(f"Invitee lookup failed: {exc}") from exc

    async def get_scheduled_event(self, event_uri: str) -> dict:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(event_uri, headers=self._headers)
        try:
            return self._resource(response)
        except Exception as exc:
            raise CalendlyAPIError(f"Scheduled event lookup failed: {exc}") from exc
