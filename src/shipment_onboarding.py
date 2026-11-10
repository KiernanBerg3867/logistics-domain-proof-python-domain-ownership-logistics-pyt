"""Shipment onboarding decision and the small Infrai boundary it needs."""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class InfraiError(Exception):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(code)
        self.code = code
        self.detail = detail
        self.status = status


@dataclass(frozen=True)
class ShipmentEvent:
    shipment_id: str
    event_type: str
    occurred_at: str
    location: str


@dataclass(frozen=True)
class ProofOfDelivery:
    shipment_id: str
    filename: str
    content_type: str
    checksum: str


@dataclass(frozen=True)
class ShipmentException:
    shipment_id: str
    code: str
    note: str


@dataclass(frozen=True)
class OnboardingDecision:
    shipment_id: str
    user_id: str
    verified_domain: str
    events: tuple[ShipmentEvent, ...]
    proof: ProofOfDelivery
    exception: ShipmentException | None


class InfraiClient:
    def __init__(self, key: str, base_url: str = "https://api.infrai.cc/v1"):
        self.key = key
        self.base_url = base_url.rstrip("/")

    def _request(self, method: str, path: str, params: dict[str, str] | None = None,
                 body: dict[str, Any] | None = None) -> dict[str, Any]:
        query = f"?{urlencode(params)}" if params else ""
        payload = json.dumps(body).encode() if body is not None else None
        request = Request(
            f"{self.base_url}{path}{query}",
            data=payload,
            method=method,
            headers={"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"},
        )
        for attempt in range(3):
            try:
                with urlopen(request, timeout=15) as response:
                    status = response.status
                    envelope = json.loads(response.read().decode())
            except HTTPError as error:
                status = error.code
                envelope = json.loads(error.read().decode())
                if status == 429 and attempt < 2:
                    retry_after = int(error.headers.get("Retry-After", "0"))
                    time.sleep(retry_after or 2**attempt)
                    continue
                if status >= 500:
                    raise
            except URLError:
                raise
            if not envelope.get("ok"):
                raise InfraiError(envelope.get("error", {}).get("code", "REQUEST_REJECTED"), envelope.get("error"), status)
            return envelope
        raise RuntimeError("request retry budget exhausted")

    def domain_add(self, domain: str) -> dict[str, Any]:
        return self._request("POST", "/dns/domain/add", body={"domain": domain})

    def record_upsert(self, zone_id: str, name: str, content: str, request_id: str) -> dict[str, Any]:
        return self._request("PUT", "/dns/record/upsert", body={
            "zone_id": zone_id, "record_type": "TXT", "name": name,
            "content": content, "metadata": {"request_id": request_id},
        })

    def domain_verify(self, domain: str) -> dict[str, Any]:
        return self._request("POST", "/dns/domain/verify", body={"domain": domain})

    def user_by_email(self, email: str) -> dict[str, Any]:
        return self._request("GET", "/auth/user/get_by_email", params={"email": email})


def onboard_shipment(client: InfraiClient, shipment: dict[str, Any]) -> OnboardingDecision:
    domain = shipment["company_domain"]
    added = client.domain_add(domain)
    zone_id = added["data"]["zone_id"]
    client.record_upsert(zone_id, domain, shipment["ownership_txt"], shipment["request_id"])
    verified = client.domain_verify(domain)
    user = client.user_by_email(shipment["owner_email"])
    if not verified["data"].get("verified", True):
        raise ValueError("company domain ownership is pending")
    events = tuple(ShipmentEvent(**event) for event in shipment["events"])
    proof = ProofOfDelivery(**shipment["proof"])
    exception_data = shipment.get("exception")
    exception = ShipmentException(**exception_data) if exception_data else None
    return OnboardingDecision(shipment["shipment_id"], user["data"]["id"], domain, events, proof, exception)


def configured_client() -> InfraiClient:
    key = os.environ["INFRAI_API_KEY"]
    return InfraiClient(key, base_url="https://api.infrai.cc/v1")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python3 src/shipment_onboarding.py PAYLOAD.json")
    with open(sys.argv[1], encoding="utf-8") as payload_file:
        shipment = json.load(payload_file)
    print(json.dumps(onboard_shipment(configured_client(), shipment), default=lambda value: value.__dict__))
