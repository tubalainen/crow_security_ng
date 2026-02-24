# CLAUDE.md — Crow Security NG

## Project Purpose
Async Python library for the Crow Cloud API (Shepherd alarm panels).
Intended as the backend for a Home Assistant custom component.

## Source of Truth
The **only** confirmed-working source for production API behaviour is
`crow_security` 0.3.0 (PyPI, github.com/shprota/crow).

The staging docs at `https://api-doc-stage.crowcloud.xyz/` describe a **future**
API version not yet deployed to production:
- `/auth/login/` → 404 on production (staging only)
- Staging schema details (ZoneState, AreaState fields) are still useful for data models

When production migrates to the new auth endpoint, update `constants.py` and
the `login()` method in `client.py`. The change will be minimal.

## Authentication — OAuth2 ROPC
- Endpoint: `POST /o/token/` — form-encoded body, **not** JSON
- `grant_type`: `password`
- `CLIENT_ID` / `CLIENT_SECRET` are baked into `constants.py` (same for all users)
- Response: `{access_token, token_type="Bearer", refresh_token}`
- Header: `Authorization: Bearer {access_token}`
- Refresh: `POST /o/token/` with `grant_type=refresh_token`

## CRITICAL: Panel ID vs MAC
Two different identifiers are used by the API:

| Purpose | Field | Example |
|---------|-------|---------|
| Panel lookup | `mac` (12-char hex) | `GET /panels/0013a1250a45/` |
| Sub-resources | `id` (numeric int) | `GET /panels/42/zones/` |

`Panel.mac` and `Panel.id` are **both** populated from `GET /panels/{mac}/`.
Always use `Panel.id` for zones, areas, outputs, and measurements calls.

## Control Operation Headers
Arming/disarming/output-control operations require these HTTP headers:
```
X-Crow-CP-Remote: panel.remote_access_password   (from API response)
X-Crow-CP-User:   panel.user_code                (from API response, may be None)
```
These are **headers**, not query parameters.

## WebSocket
- URL: `wss://websocket.crowcloud.xyz/sockjs/websocket`
- Handshake:
  1. Send: `{"type": "authentication", "value": raw_access_token}`
  2. Recv: `{"status": "OK"}`
  3. Send: `{"type": "subscribe", "value": panel_mac}`
  4. Recv: `{"status": "OK"}`
  5. Recv: continuous event messages

## Confirmed Production Endpoints
```
POST /o/token/
GET  /panels/
GET  /panels/{mac}/
GET  /panels/{id}/areas/
GET  /panels/{id}/areas/{area_id}/
PATCH /panels/{id}/areas/{area_id}/        body: {state, force}
GET  /panels/{id}/zones/
GET  /panels/{id}/zones/{zone_id}/
PATCH /panels/{id}/zones/{zone_id}/        body: {bypass}
GET  /panels/{id}/outputs/
GET  /panels/{id}/outputs/{output_id}/
PATCH /panels/{id}/outputs/{output_id}/    body: {state}
GET  /panels/{id}/dect/measurements/latest/by_zone/
GET  /panels/{id}/zones/{zone_id}/pictures/
POST /panels/{id}/zones/{zone_id}/pictures/
```

## Files
| File | Purpose |
|------|---------|
| `crow_security_ng/constants.py` | BASE_URL, WS_URL, OAuth2 credentials |
| `crow_security_ng/client.py` | `CrowClient` — all HTTP + WebSocket |
| `crow_security_ng/models.py` | Dataclass models (Panel, Area, Zone, …) |
| `crow_security_ng/exceptions.py` | Exception hierarchy |
| `crow_security_ng/session.py` | `Session` — backward-compat wrapper |
| `crow_security_ng/utils.py` | MAC address helpers (do not modify) |

## Running Tests
```
pytest tests/ --asyncio-mode=auto
```
Use `aioresponses` for mocking. Never use real credentials in tests.

## Key Design Notes
- **MAC normalization**: Always normalize to lowercase 12-char hex before API calls.
  `normalize_mac()` from `utils.py` handles all formats (`AA:BB:CC`, `aa-bb-cc`, `AABBCC`).
- **`panel.user_code`**: May be `None` — control operations still work if the panel
  does not require a user code.
- **Picture download**: `picture.url` is a pre-signed URL; download without
  `Authorization` header (no auth needed).
- **Measurements**: Raw values from the DECT sensor endpoint are integer milliUnits.
  `Measurement.from_api()` pre-divides temperature, humidity, and air_pressure by 1000.
- **Zone.state**: Boolean in the production API (not a string enum).
