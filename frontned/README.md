# Lerato Alert – frontend

Plain HTML, CSS and JS. No build step.

## Run it

The easiest way is through Django (see `backend/README.md`): run the server and open http://127.0.0.1:8000 .
The frontend then talks to the API on the same address automatically.

You can still open it on its own with `python -m http.server 5500` inside this folder. It then calls Django on port 8000,
or uses demo answers if Django isn't running. Mic and location need `localhost` or `https`, so do the phone demo on Render.

## Flow

- **First time:** `index.html` → 2s loading screen → register (name, surname, email, number) → Alert tab.
- **Returning:** `index.html` → disguise app → secret code → 2s loading screen → Alert tab.
- Default disguise: Calculator, secret sum `19×58` then `=`. Change it in Alert → crossed-eye button.
- Quick exit (top-right on every screen) locks the app and jumps to the disguise.

## Backend

The API address is worked out automatically in `assets/js/app.js`. Every call has a demo
fallback, so the app keeps working if the server is down. Endpoints the frontend expects:

| Method | Path | Body / query | Returns |
|---|---|---|---|
| POST | `/users/register/` | name, surname, email, phone | `{ id }` |
| POST | `/contacts/` | user_id, name, channel (number/email/whatsapp), value, type (kin/security/org) | `{ id }` |
| POST | `/alerts/` | user, mode, reason, location {lat,lng,accuracy}, maps_link, contacts[], sent_at | `{ ok }` → send Brevo email/SMS |
| POST | `/reports/` | anonymous, kind, area, evidence_count | `{ reference }` |
| GET | `/services/nearby/` | type, lat, lng | `{ results: [{ name, lat, lng, distance_km, open_now, address }] }` |
| POST | `/ai/referral/` | messages [{role, content}], turn, max_turns | `{ reply, options?, action?: {href,label}, done? }` |
| POST | `/ai/friend/` | messages [{role, content}] | `{ reply, options? }` |
| POST | `/ai/lesson/` | topic, id | `{ title, intro, points: [{title, body}], takeaway }` |
| POST | `/lessons/suggest/` | topic | `{ ok }` |
| POST | `/fund/apply/` | user_id, needs[], amount, phone | `{ id }` |
| POST | `/fund/donate/` | amount, last4, bank, display_name | `{ reference, status }` |
| GET | `/fund/summary/` | – | `{ total, sponsor_count, causes: [{name, amount}], sponsors: [{display_name, amount, created}] }` |
| GET | `/hotspots/` | lat, lng | `{ results: [{ lat, lng, level (clear/aware/heads/red), category, night, label, note, radius }] }` |

The Anthropic API key lives only in Django. Never put it in these JS files.
Messages sent to `/ai/*` start with an assistant greeting, so drop it (or prepend a user turn) before calling the API.
