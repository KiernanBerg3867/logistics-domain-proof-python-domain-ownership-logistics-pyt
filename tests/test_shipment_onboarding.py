from shipment_onboarding import InfraiClient, onboard_shipment


class FakeClient(InfraiClient):
    def __init__(self):
        pass

    def domain_add(self, domain):
        return {"ok": True, "data": {"zone_id": "zone-7"}, "error": None, "metadata": {}}

    def record_upsert(self, zone_id, name, content, request_id):
        assert zone_id == "zone-7"
        assert name == "acme-logistics.example"
        assert request_id == "shipment-42"
        return {"ok": True, "data": {}, "error": None, "metadata": {}}

    def domain_verify(self, domain):
        return {"ok": True, "data": {"verified": True}, "error": None, "metadata": {}}

    def user_by_email(self, email):
        return {"ok": True, "data": {"id": "user-9"}, "error": None, "metadata": {}}


def test_domain_proof_allows_shipment_onboarding():
    result = onboard_shipment(FakeClient(), {
        "shipment_id": "S-42", "company_domain": "acme-logistics.example",
        "owner_email": "ops@acme-logistics.example", "ownership_txt": "infrai-proof=abc",
        "request_id": "shipment-42",
        "events": [{"shipment_id": "S-42", "event_type": "delivered", "occurred_at": "2026-10-27T09:00:00Z", "location": "Portland"}],
        "proof": {"shipment_id": "S-42", "filename": "pod.jpg", "content_type": "image/jpeg", "checksum": "sha256:abc"},
        "exception": {"shipment_id": "S-42", "code": "WEATHER_DELAY", "note": "Delivered after a weather hold."},
    })
    assert result.user_id == "user-9"
    assert result.exception.code == "WEATHER_DELAY"
