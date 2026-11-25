# Carbon Footprint Tracker — Carbon_Footprint_est

A React + Vite frontend and Flask + SQLite backend for recording lifestyle information, daily activities, indicative carbon-footprint estimates and progress. This is a student/MVP application; it is not a certified emissions audit or a production-hardened public service.

## Included features

### Tracking and insights
- One-time personal profile, editable later, separated from the short daily activity check-in.
- Daily entries can be edited for the same date; each date has one current saved record.
- Car occupancy and household size are considered in the activity estimate.
- Dashboard totals and charts use saved entries; missing days are not silently treated as zero, and older entries are not displayed as today's result.
- Calendar, current-vs-previous week comparison, monthly summary, category breakdown, rule-based reduction planner and what-if scenario.
- PDF activity report and JSON account-data export.

### Engagement and local resources
- XP, streaks, badges and self-reported daily missions with duplicate-claim protection.
- Community challenges (Green Commute, Plant-Forward and Low-Waste) progress from qualifying saved check-ins and award challenge XP once.
- Challenge QR codes link to the community page; QR generation requires the `qrcode[pil]` dependency.
- Optional public leaderboard participation (off by default).
- City-based map-search links for recycling/e-waste, repair/reuse, public transport and community gardens. These are live map searches, not a vetted provider directory.
- Eco Coach uses the OpenAI Responses API when `OPENAI_API_KEY` is configured; otherwise it falls back to a local rule-based coach. Only the user's question and aggregate recent category totals are sent to the AI provider; account name/email are not sent. API usage may incur charges.

### Account, privacy and operations
- Email verification and password reset by code (SMTP required; development mode can print codes to the backend terminal).
- Account export and permanent account deletion.
- Session expiry, basic in-process per-IP throttling for sensitive endpoints, payload size limit, configurable CORS origins and input validation.
- Optional daily reminder and weekly email summary preferences with scheduler-ready scripts (`backend/send_daily_reminders.py`, `backend/send_weekly_digest.py`). SMTP and daily/weekly cron or Task Scheduler jobs must be configured.
- Light/dark appearance, page transitions, mobile layout refinements, reduced-motion support and focus-visible styles.
- Contact messages are stored in SQLite; email delivery is not claimed for contact submissions.

## Run locally

### 1. Backend (Terminal 1)

```bash
cd backend
python -m venv .venv
# Windows PowerShell:
.venv\\Scripts\\Activate.ps1
# Windows Git Bash:
source .venv/Scripts/activate
# macOS/Linux:
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

The API starts at `http://127.0.0.1:5000` by default.

### 2. Frontend (Terminal 2)

```bash
cd frontend
npm install
npm run dev
```

Open the Vite URL shown in the terminal (normally `http://localhost:5173`). If the backend is hosted elsewhere, copy `frontend/.env.example` to `frontend/.env` and set `VITE_API_URL` to the backend base URL, without `/api` at the end.

## Email verification and weekly digests

Copy `backend/.env.example` to `backend/.env`. Configure `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM`, and `SMTP_USE_TLS`. Set `FRONTEND_URL` to the public frontend origin for QR codes. To enable AI Eco Coach, optionally set `OPENAI_API_KEY` and `OPENAI_MODEL` in `backend/.env` only; never expose the key in frontend variables or commit it. API usage may be billed by the provider. For local development only, `EMAIL_DEV_MODE=true` prints verification codes to the backend terminal; this is not proof of inbox delivery. Never commit `.env` files or credentials.

Users must opt in under Profile > Account & Privacy. Schedule `python send_daily_reminders.py` from the `backend` directory once daily, and `python send_weekly_digest.py` once a week. Both scripts use SMTP and send only to verified users who opted in. Example cron schedules (server local time):

```cron
# Daily check-in reminder at 18:00
0 18 * * * cd /path/to/Carbon_Footprint_est/backend && /path/to/python send_daily_reminders.py
# Weekly summary on Monday at 09:00
0 9 * * 1 cd /path/to/Carbon_Footprint_est/backend && /path/to/python send_weekly_digest.py
```

The scripts record per-user send dates to avoid duplicate daily reminders and duplicate weekly summaries.

## Calculation methodology and limitations

The output is an indicative daily estimate. The household electricity component uses the Central Electricity Authority (CEA), Government of India, all-India grid weighted-average factor of **0.727 kg CO2/kWh** for FY 2023-24 (CEA Annual Report 2024-25). Household size is used to allocate the household electricity entry among members. The calculator also applies a user-selected renewable-electricity adjustment; this is a simplifying assumption, not a measured supplier-specific renewable share.

Motorcycle, intracity bus and non-suburban rail use older India GHG Program estimates (2014-15 technical papers). Car and metro remain illustrative because the app does not collect vehicle-specific or metro-system data. Food, shopping, waste and cooking factors remain illustrative prototype assumptions. This is not a fully current India-calibrated or independently validated factor set. The supplied `data/ghg-conversion-factors.xlsx` is a UK Government 2023 workbook retained from the original project and is not used as India-specific data. City and home type are contextual profile fields, not measured regional factors. The result should not be used for research claims, policy, regulatory reporting, corporate inventories or precise comparisons without a documented and validated methodology.

Weekly and monthly dashboard summaries sum actual saved records in their windows. They are not extrapolations from one day's value. The PDF is an activity summary, not a verified emissions certificate. Historical entries are retained as calculated at the time they were saved; editing a profile affects future estimates and does not silently rewrite past records.

Sources:
- Central Electricity Authority, Government of India, *Annual Report 2024-25*, section 2.11.1 / page 23, FY 2023-24 grid factor series: https://www.cea.nic.in/api/dashboardReports/view-pdf/en/62d073ce-f773-469e-acc7-366113cbbd5f
- CEA CDM-CO2 Baseline Database releases and user guides: https://cea.nic.in/cdm-co2-baseline-view?lang=en&mappingId=234
- India GHG Program transport factor papers: https://indiaghgp.org/transport-emission-factors

## Deployment and security notes

Set `CORS_ORIGINS` to comma-separated exact trusted frontend origins, `SESSION_DAYS` as required, and `FLASK_DEBUG=false`. Use HTTPS, a production WSGI server, persistent database storage, backups, a reverse proxy and production-grade shared rate limiting before public deployment. The included in-process throttling is a basic safeguard and is not shared across workers. Authentication currently uses bearer tokens in browser local storage; move to secure HttpOnly SameSite cookies with CSRF protection before using this for sensitive or public production workloads. Keep `.env`, database files and backups private.

## Verification

Run these checks locally after installing dependencies. Backend unit tests are included in `backend/tests/test_api.py`:

```bash
cd backend
python -m pip install -r requirements.txt
python -m py_compile app.py send_weekly_digest.py send_daily_reminders.py
python -m unittest discover -s tests
cd ../frontend
npm install
npm run build
```

In this environment, Python syntax compilation, SQLite schema/challenge-seed validation, calculation-factor smoke checks and React JSX parsing passed. The Flask API tests and Vite production build were not run because Flask/frontend dependencies could not be installed here (network access was unavailable). Run the commands above on your computer before deployment. Then manually test email verification, password reset, profile save/edit, daily save/edit, dashboard and insights, challenge progress/QR, weekly digest opt-in, PDF/JSON export, leaderboard opt-in and account deletion using a test account and test database. Do not test destructive account deletion against a live user account.
