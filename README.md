
# Carbon Footprint Tracker

A sustainability-focused web application built with **React.js, Vite, Flask, and SQLite** that helps users estimate their daily carbon footprint, monitor lifestyle activities, understand their environmental impact, and develop eco-friendly habits.

This is a student/MVP project. Its calculations provide indicative estimates and are not a certified emissions audit or a production-hardened public service.

## Key Features

### 1. Carbon Tracking and Insights
- One-time personal profile setup with the ability to edit profile information later.
- Separate personal profile information and daily activity check-ins.
- Daily activity records can be edited, with one current saved record per date.
- Car occupancy and household size are considered in activity estimates.
- Dashboard totals and charts are calculated from saved activity records.
- Missing days are not automatically treated as zero.
- Calendar-based activity tracking.
- Current and previous week comparisons.
- Monthly summaries and category-wise emissions breakdown.
- Rule-based carbon reduction planner.
- What-if scenarios to explore potential emission reductions.
- PDF activity reports and JSON account-data exports.

### 2. Gamification and Community
- Experience points (XP), activity streaks, badges, and daily missions.
- Duplicate-claim protection for daily missions.
- Community challenges:
  - Green Commute
  - Plant-Forward
  - Low-Waste
- Challenge progress is calculated from qualifying saved check-ins.
- Challenge XP is awarded only once.
- QR codes for accessing community challenges.
- Optional public leaderboard participation, disabled by default.

### 3. Local Sustainability Resources
- City-based map-search links for:
  - Recycling and e-waste facilities.
  - Repair and reuse services.
  - Public transportation.
  - Community gardens.
- These links open live map searches and are not a verified provider directory.

### 4. AI Eco Coach
- Optional AI-powered Eco Coach using the OpenAI Responses API.
- Uses a local rule-based fallback when an OpenAI API key is not configured.
- Only the user's question and aggregate recent category totals are sent to the AI provider.
- Account names and email addresses are not sent to the AI provider.
- OpenAI API usage may incur charges.

### 5. Account Management and Privacy
- Email verification and password reset using verification codes.
- SMTP-based email configuration.
- Development mode for displaying verification codes in the backend terminal.
- Account-data export and permanent account deletion.
- Session expiry.
- Basic in-process per-IP throttling for sensitive endpoints.
- Request payload size limits and input validation.
- Configurable CORS origins.
- Account privacy and notification preferences.
- Optional daily reminders and weekly email summaries.

### 6. User Interface
- Light and dark appearance modes.
- Page transition animations.
- Responsive mobile-friendly layout.
- Reduced-motion accessibility support.
- Focus-visible styles for keyboard navigation.

## Technology Stack

| Category | Technologies |
|---|---|
| Frontend | React.js, Vite, JavaScript, CSS |
| Backend | Python, Flask |
| Database | SQLite |
| Charts | Recharts |
| API Communication | REST APIs |
| AI Integration | OpenAI Responses API (Optional) |
| Email Services | SMTP |
| QR Code Generation | Python qrcode |
| Version Control | Git and GitHub |

## Project Structure

```text
Carbon_Footprint_est/
│
├── backend/
│   ├── app.py
│   ├── requirements.txt
│   ├── send_daily_reminders.py
│   ├── send_weekly_digest.py
│   ├── tests/
│   │   └── test_api.py
│   └── ...
│
├── frontend/
│   ├── src/
│   ├── package.json
│   ├── .env.example
│   └── ...
│
└── README.md
```

## Getting Started

### Prerequisites

- Python 3.10 or a compatible version supported by the backend dependencies.
- Node.js and npm.
- Git.
- Visual Studio Code (recommended).

### 1. Clone the Repository

```bash
git clone https://github.com/geethamuttavarapu/Carbon_Footprint_Tracker.git

cd Carbon_Footprint_Tracker
```

### 2. Backend Setup

Open Terminal 1:

```bash
cd backend

python -m venv .venv
```

Activate the virtual environment.

**Windows PowerShell:**

```powershell
.venv\Scripts\Activate.ps1
```

**Windows Git Bash:**

```bash
source .venv/Scripts/activate
```

**macOS/Linux:**

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Start the Flask backend:

```bash
python app.py
```

The backend API runs at:

```text
http://127.0.0.1:5000
```

### 3. Frontend Setup

Open Terminal 2:

```bash
cd frontend

npm install

npm run dev
```

Open the local Vite URL shown in your terminal, normally:

```text
http://localhost:5173
```

If the backend is hosted on another domain, copy `frontend/.env.example` to `frontend/.env` and configure:

```env
VITE_API_URL=https://your-backend-domain.com
```

Do not append `/api` to the URL.

Restart the Vite development server after changing environment variables.

## Email Configuration

Email verification and password reset require SMTP configuration.

Copy:

```text
backend/.env.example
```

to:

```text
backend/.env
```

Configure the following variables:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-google-app-password
SMTP_FROM=your-email@gmail.com
SMTP_USE_TLS=true
```

Configure `FRONTEND_URL` with the public frontend origin.

For local development only, `EMAIL_DEV_MODE=true` can print verification codes in the backend terminal. This does not verify actual inbox delivery.

Never upload `.env` files or credentials to GitHub.

## Optional AI Eco Coach Configuration

To enable the OpenAI-powered Eco Coach, configure the following variables in `backend/.env`:

```env
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=your-supported-model
```

If the API key is not configured, the application uses its local rule-based fallback.

Keep the API key exclusively in the backend environment. Never expose it through frontend environment variables or commit it to GitHub.

API usage may incur charges.

## Daily Reminders and Weekly Email Summaries

Users must opt in under **Profile → Account & Privacy**.

The application includes two scheduler-ready scripts:

- `backend/send_daily_reminders.py`
- `backend/send_weekly_digest.py`

Run the daily reminder script once per day:

```bash
cd backend
python send_daily_reminders.py
```

Run the weekly summary script once per week:

```bash
cd backend
python send_weekly_digest.py
```

For automated execution, configure cron jobs on Linux or Task Scheduler on Windows.

Example cron configuration:

```cron
# Daily reminder at 18:00
0 18 * * * cd /path/to/Carbon_Footprint_est/backend && /path/to/python send_daily_reminders.py

# Weekly summary on Monday at 09:00
0 9 * * 1 cd /path/to/Carbon_Footprint_est/backend && /path/to/python send_weekly_digest.py
```

The scripts record per-user send dates to prevent duplicate daily reminders and weekly summaries.

## Carbon Calculation Methodology

The application provides an indicative daily carbon-footprint estimate based on user-entered lifestyle activities.

### Electricity

The household electricity component uses the Central Electricity Authority (CEA), Government of India, all-India grid weighted-average emission factor of **0.727 kg CO2/kWh** for FY 2023-24, as reported in the CEA Annual Report 2024-25.

Household size is used to allocate the household electricity entry among members.

A user-selected renewable-electricity adjustment is also applied. This is a simplifying assumption and does not represent a measured supplier-specific renewable share.

### Transportation

Motorcycle, intracity bus, and non-suburban rail calculations use older India GHG Program estimates from 2014-15 technical papers.

Car and metro calculations remain illustrative because the application does not collect vehicle-specific or metro-system data.

### Food, Shopping, Waste and Cooking

Food, shopping, waste, and cooking emission factors are illustrative prototype assumptions.

The supplied `data/ghg-conversion-factors.xlsx` workbook is a UK Government 2023 workbook retained from the original project. It is not used as India-specific emissions data.

City and home type are contextual profile fields and are not measured regional emission factors.

### Calculation Limitations

- The factors do not represent a fully current India-calibrated dataset.
- The methodology has not been independently validated.
- Results should not be used for research claims, policy decisions, regulatory reporting, or corporate emissions inventories.
- Precise comparisons require a documented and validated emissions methodology.

Weekly and monthly summaries use actual saved records within their respective date ranges. They are not extrapolations from a single day's emissions.

The PDF report is an activity summary, not a verified emissions certificate.

Historical entries retain the calculation values saved at the time of entry. Editing a profile affects future estimates and does not automatically rewrite historical records.

## Data Sources

1. Central Electricity Authority, Government of India, *Annual Report 2024-25*, Section 2.11.1, page 23, FY 2023-24 grid emission factor series.  
   https://www.cea.nic.in/api/dashboardReports/view-pdf/en/62d073ce-f773-469e-acc7-366113cbbd5f

2. Central Electricity Authority, CDM-CO2 Baseline Database releases and user guides.  
   https://cea.nic.in/cdm-co2-baseline-view?lang=en&mappingId=234

3. India GHG Program, Transport Emission Factor Technical Papers.  
   https://indiaghgp.org/transport-emission-factors

## Deployment and Security Considerations

Before using this application as a public production service, configure:

- HTTPS for all public connections.
- A production WSGI server.
- Persistent database storage.
- Database backups and recovery procedures.
- Trusted frontend origins through `CORS_ORIGINS`.
- `FLASK_DEBUG=false`.
- Appropriate session expiry through `SESSION_DAYS`.
- Production-grade shared rate limiting.
- Secure storage of SMTP credentials and API keys.

The current implementation has the following limitations:

- Rate limiting is in-process and is not shared across multiple workers.
- Authentication uses bearer tokens stored in browser local storage.
- Production use with sensitive or public user data should migrate to secure HttpOnly, SameSite cookies with CSRF protection.

Keep `.env` files, database files, backups, passwords, and API credentials private.

## Verification and Testing

The backend includes unit tests in:

```text
backend/tests/test_api.py
```

Run the backend checks:

```bash
cd backend

python -m pip install -r requirements.txt

python -m py_compile app.py send_weekly_digest.py send_daily_reminders.py

python -m unittest discover -s tests
```

Run the frontend production build:

```bash
cd frontend

npm install

npm run build
```

### Verification Status

The following checks passed in the development environment:

- Python syntax compilation.
- SQLite schema and challenge-seed validation.
- Calculation-factor smoke checks.
- React JSX parsing.

The Flask API unit tests and Vite production build were not run in that environment because dependencies could not be installed due to network restrictions.

Run the verification commands above locally before deployment.

### Recommended Manual Testing

Test the following features using a test account and test database:

- Email verification and password reset.
- Profile creation and editing.
- Daily activity creation and editing.
- Dashboard and insights.
- Community challenge progress and QR codes.
- Weekly digest and daily reminder opt-in.
- PDF and JSON exports.
- Leaderboard opt-in.
- Account deletion.

Do not test destructive account deletion against a live user account.

## Project Status

This project is developed as a student/MVP application to demonstrate full-stack development, REST API integration, database management, data visualization, sustainability tracking, and optional AI integration.

It is not a certified carbon accounting platform or a production-hardened service.

## Author

**Geetha M.**

GitHub: https://github.com/geethamuttavarapu

LinkedIn: https://www.linkedin.com/in/geetha-muttavarapu-b31460343/

---

If you find this project useful, feel free to explore the repository and share your feedback.
