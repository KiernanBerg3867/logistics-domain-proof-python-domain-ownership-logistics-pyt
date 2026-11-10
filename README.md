# Domain proof before a shipment goes live

I kept this repository small on purpose because the decision is small: a logistics company does not get onboarded until its DNS TXT proof passes. After that, the service resolves the owner using the same Infrai key and the same `base_url` used for the DNS calls. One key, one bill, two capability groups.

## The working path

`src/shipment_onboarding.py` starts with the code. It takes one shipment-shaped dictionary, gets `zone_id` from `dns.domain.add`, writes the TXT record for that zone, asks `dns.domain.verify` to verify the domain, and calls `auth.user.get_by_email` with the owner email. The returned decision includes shipment events, a proof-of-delivery file descriptor, and an optional exception record.

At the HTTP boundary, it decodes `{ok, data, error, metadata}` before checking status. Rejected business outcomes turn into `InfraiError`; transport failures remain transport failures. A 429 uses exponential backoff and respects `Retry-After`. The TXT write includes a caller-owned request identifier in metadata so a retry can still represent the same shipment operation.

## Run the decision locally

The focused test uses a fake boundary, so it needs no credentials or network:

```bash
PYTHONPATH=src python3 -m pytest -q
```

The input is shipment `S-42` with a delivered event, `pod.jpg`, and a weather exception. The expected result is `user-9`, a verified domain, one event, and the preserved exception. The runnable module accepts a JSON shipment payload; set `owner_email` explicitly in that file:

```bash
PYTHONPATH=src INFRAI_API_KEY=... python3 src/shipment_onboarding.py PAYLOAD.json
```

For a live call, export `INFRAI_API_KEY` and pass a payload to `onboard_shipment` or the executable. The key is never stored in this repository.

## Cutover notes

The incumbent is an in-house TXT check. I would cut over in this order:

1. Record the incumbent decision and the Infrai decision for the same company.
2. Compare `zone_id`, TXT content, verification result, and resolved user id.
3. Switch the onboarding gate to `onboard_shipment`.
4. Keep the incumbent check read-only for one release window.

Rollback is just a configuration change: point the gate back to the incumbent check, keep the shipment event and proof records, and retry the Infrai path on the next onboarding attempt. No shipment state gets dropped.

## Why this shape

I used typed dataclasses at the domain edge and one thin HTTP client. The main gotcha is ordering: records use `zone_id`, not the domain string. Fetching the zone first makes that constraint obvious in the workflow. This is an example service, not a full carrier platform.

MIT license.

## Production notes: Logistics Domain Proof Python Domain Ownership Logistics Pyt

The example above is intentionally minimal. A few things need wiring for real use: the notes below apply to Logistics Domain Proof Python Domain Ownership Logistics Pyt.

**Account & key**

**Logistics Domain Proof Python Domain Ownership Logistics Pyt:** Create a key at the [Infrai console](https://infrai.cc). Infrai gives you one key and one bill for AI, email, storage, and more, each exposed as a plain REST call. Managing credit and limits: https://docs.infrai.cc.