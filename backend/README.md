# Lerato Alert – backend (Django)

One Django app runs the API at `/api/`, the admin at `/admin/`, and serves the
`frontned` folder at `/`. So you open the whole app from one address.

## 1. Run it locally (Windows, VS Code terminal)

```
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env          # then fill in the keys you have
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_demo      # optional: sample hotspots + donations, tagged DEMO
python manage.py runserver
```

Open **http://127.0.0.1:8000**. Admin: http://127.0.0.1:8000/admin.
Check what's connected: http://127.0.0.1:8000/api/health/

Everything works with no keys at all: alerts are saved but not sent, and the AI
chats and lessons use the built-in answers. Add keys one at a time.

Run the tests: `python manage.py test api`

## 2. Keys

| Key | Where to get it | What it powers |
|---|---|---|
| `DATABASE_URL` | Supabase → Connect → **Session pooler** URI (replace `[YOUR-PASSWORD]`) | Database. Empty = local SQLite |
| `ANTHROPIC_API_KEY` | console.anthropic.com → API keys | Get referred, Help a friend, AI lessons |
| `BREVO_API_KEY` + `BREVO_SENDER_EMAIL` | Brevo → SMTP & API → API keys. Verify the sender email under Senders | Alert emails (free, 300/day) |
| SMS (later) | Buy Brevo SA SMS credits, then set `SMS_ENABLED=true` and re-enable the SMS button in `alert/contacts.html` | Alert SMS. Email only for now |
| `GOOGLE_MAPS_API_KEY` | Google Cloud → enable **Places API (New)** → create API key | Nearest care centres, police, shelters |
| `CLOUDINARY_URL` | Cloudinary → Dashboard → copy the **API environment variable** (`cloudinary://...`) | Private backup of vault photos, voice notes and videos |

The keys stay on the server. The browser never sees them.

## 3. Deploy on Render

1. Push the whole `Lerato` folder to GitHub. `.gitignore` keeps `.env` out.
2. Render → **New → Blueprint** → choose the repo. It reads `render.yaml`.
3. Paste your keys when asked, then deploy.
4. Create an admin login: Render → your service → **Shell** → `cd backend && python manage.py createsuperuser`
5. Optional demo data: `python manage.py seed_demo --lat <your lat> --lng <your lng>`
   (remove later with `python manage.py seed_demo --clear`)

You get an `https://lerato-alert.onrender.com` link. HTTPS means the mic works on your iPhone.
The free plan sleeps after 15 minutes idle, so open the link a minute before you record or present.

## 4. API

All JSON. Endpoints marked 🔑 need the `X-Lerato-Token` header (the app sends it automatically after registering).

| Method | Path | Notes |
|---|---|---|
| GET | `/api/health/` | Which services are configured |
| POST | `/api/users/register/` | Returns `{ id, token }` |
| POST | `/api/contacts/` 🔑 | Save a trusted contact |
| POST | `/api/alerts/` 🔑 | Saves the alert and sends Brevo email/SMS with a Google Maps link. Home mode skips next of kin when other contacts exist |
| POST | `/api/reports/` | Anonymous. Returns `{ reference }` |
| GET | `/api/services/nearby/?type=care\|police\|shelter\|hospital&lat=&lng=` | Google Places, sorted by distance |
| POST | `/api/ai/referral/` | 3 questions, then a referral with an action button |
| POST | `/api/ai/friend/` | Live advice chat |
| POST | `/api/ai/lesson/` | `{ topic }` → lesson. Cached for 1 hour per topic |
| POST | `/api/lessons/suggest/` | Saves suggestions (see admin) |
| POST | `/api/fund/apply/` 🔑 | One request in review at a time |
| POST | `/api/fund/donate/` | Sandbox donation. Only the last 4 card digits are sent |
| GET | `/api/fund/summary/` | Totals, spending by cause, sponsors |
| GET | `/api/hotspots/?lat=&lng=` | Active hotspots within about 15 km |
| GET / POST | `/api/vault/` 🔑 | List backed-up evidence (10-minute signed links) / upload a file or note |
| DELETE | `/api/vault/<id>/` 🔑 | Delete from the backup too |

## 5. Running the admin

- **Fund allocations**: add payouts by cause. The transparency page updates automatically.
- **Fund applications**: change status (In review → Approved → Paid).
- **Hotspots**: add or switch off hotspots for the safety map.
- **Alerts**: see who was notified and whether each message was delivered.