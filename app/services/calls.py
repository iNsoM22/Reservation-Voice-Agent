"""Call registration boundary. Deliberately inert until provider setup is confirmed."""

from typing import Any


class CallService:
    def register_patient(self, arguments: dict[str, Any]) -> str:
        # No call data is persisted until confirmation and retry handling are implemented.
        return "Phone registration is not configured yet."
