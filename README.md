# Lerato Alert

**Hands-free safety for gender-based violence response.**
Built by **Tshireletso Tech** for the FNB App of the Year Hackathon 2026, Safer Communities challenge.

**Live app:** https://lerato-alert.onrender.com

> The live demo runs on a free server that sleeps when idle. The first visit can take up to a minute to wake up.

> *Lerato* means love in Setswana. Many people are hurt by someone who says they love them.
> Lerato Alert is built on a simple belief: everyone deserves to be loved without being hurt.

---

## The problem

- Most safety apps expect a victim to unlock their phone and press a button **during** an attack. In real life that rarely happens.
- An app that looks like a safety app can put someone at **greater risk** if an abuser finds it.
- Many survivors stay because they **depend on the abuser financially**.
- Many safety platforms shut down because they have **no lasting funding**.

## The solution

Lerato Alert works **without touching your phone**. Start a safe session when you feel unsafe: jogging, commuting, or when an abuser comes home. The app listens quietly for:

- your **personal safe word**
- distress phrases like *"leave me alone"* or *"help me"*
- a **scream** or sudden loud noise

After a **5-second silent cancel window** (so false alarms can be stopped), it emails your **live location** to trusted contacts and starts recording evidence.

## Features

| Tab | What it does |
|---|---|
| **Alert** | Hands-free detection, safe modes (Jogging, Commute, At home), live location, trusted contacts. In *At home* mode, security companies and organisations are alerted instead of family the abuser may know. |
| **Vault** | PIN-locked evidence: voice recordings, photos, videos and written incident notes, timestamped and **backed up privately to the cloud**, so evidence survives if the phone is taken or broken. Includes anonymous reporting. |
| **Help** | Verified services near you (Thuthuzela Care Centres, police, shelters, hospitals) and an **AI referral chat** that finds the right help in three questions. |
| **Fund** | A **survivor fund** for emergency transport, shelter, essentials and legal help, plus a public transparency page showing where every rand goes, by cause only, never by name. |
| **Learn** | AI-written prevention lessons, a live **"Help a friend"** guide, lesson suggestions, and a **community safety map** of hotspots (All clear, Stay aware, Heads up, Red zone). |

## Built to keep survivors safe

- **Disguise mode:** the app opens as a working **Calculator**, **Messages** or **Internet** screen. Only the user's **own secret code** opens Lerato Alert. There is no shared default code.
- **Disguised home screen icon:** once registered, the app is added to the home screen as "Calculator", "Chats" or "Search", with a matching icon.
- **Quick exit** on every screen instantly locks the app and returns to the disguise.
- **Private evidence:** cloud files can't be opened by a plain link, only through short-lived signed links.
- **Anonymous reports** are never linked to an account.
- **POPIA consent** is asked for at registration. All API keys stay on the server, never in the browser.

## Sustainability: how it stays alive

Lerato Alert is **free for individuals**. Revenue comes from:

- **API licensing** to ride-hailing and transport platforms (e.g. Uber, Bolt, public transport)
- **Licences** for employers and campuses that protect staff and students
- **Partnerships** with insurers and security companies
- **Corporate social investment** into the survivor fund

## Tech stack

| Area | Technology |
|---|---|
| Frontend | HTML, CSS, JavaScript (installable PWA) |
| Detection | Web Speech API and Web Audio API |
| Backend | Django, Django REST Framework |
| Database | Supabase (PostgreSQL) |
| Hosting | Render |
| Alerts | Brevo (email) |
| AI | Claude API (Anthropic), Claude Sonnet 5.5 with structured outputs |
| Evidence backup | Cloudinary (private, authenticated uploads) |
| Maps | Google Maps and Places API (nearest help), Leaflet with Esri satellite imagery (safety map) |
| Payments | PayFast (sandbox) |

## Run it locally

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
copy .env.example .env         # Mac/Linux: cp .env.example .env, then add your keys
python manage.py migrate
python manage.py runserver
```

Open http://127.0.0.1:8000. The app runs without any keys; each service switches on as its key is added.
Details: [`backend/README.md`](backend/README.md) · Tests: `python manage.py test api`

## Project structure

```
backend/     Django API, admin and integrations (Brevo, Claude, Cloudinary, Google Places)
frontned/    The app: alert, vault, help, fund, learn, disguise and onboarding screens
render.yaml  One-click deployment to Render
```

## Roadmap

- SMS and WhatsApp alerts
- Native Android and iOS apps for background listening with the screen locked
- Restoring vault evidence on a new phone
- Partner API for transport platforms
- Live payouts for the survivor fund

## Get help now (South Africa)

- **GBV Command Centre:** 0800 428 428 (free, 24/7)
- **SAPS:** 10111
- **Childline:** 116