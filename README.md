# ASSETRA - Fixed Asset Replacement Value Calculator

A web application that reads a company's **Fixed Asset Register (FAR)** in Excel and estimates the **current replacement value** of every asset, using official **Wholesale Price Index (WPI)** data and your company's valuation rules.

It works with FARs from different companies, even when column names and category wording differ. The calculation itself is plain Python and never uses AI.

---

## 1. Key terms

| Term | Meaning |
|---|---|
| **FAR** | Fixed Asset Register: a company's list of assets with cost and purchase date |
| **Acquisition value** | What the asset originally cost |
| **Book value** | Cost minus accumulated depreciation (an accounting number, not used here) |
| **Replacement value** | Estimated cost to buy the asset new today (what this app calculates) |
| **WPI** | Government price index used to estimate inflation by asset type |

Book value is never used to judge insurance adequacy, because it ignores inflation.

---

## 2. How it works

1. **Sign in** (email and password, or Google).
2. **Enter the company name** (an industry is optional and does not affect the calculation) and **upload the FAR**.
3. **Columns are detected:** description, purchase date, acquisition value and category (details in section 4).
4. **Each asset gets a WPI group** (section 5).
5. **Replacement values are calculated** (section 3).
6. **Results are saved** in MySQL under the user's account. On the next login, the last analysis opens straight away, with no recalculation.
7. **Download** the Excel report. It is built from the saved rows when you click, so no Excel files are stored.

---

## 3. Calculation rules

The rules live in the **RULES** sheet of the master dataset. The reference year (currently 2025) and the Building and Land rate (5%) are read from there.

- **WPI assets** (Plant & Machinery, Computer, Furniture & Fixture, Office Equipment, Vehicles): the asset passes through each WPI base period from its purchase year to today.
  - Rise per stage = (End index - Start index) / Start index, applied to the value carried in.
  - Only the first stage uses the index of the purchase year. Later stages start at 100.
  - **Never below cost:** a falling index is treated as zero rise.
- **Building and Land:** 5% per year, compounded, from the purchase year to the reference year (not WPI based).
- **Software:** no calculation; replacement value equals acquisition value.
- **Purchased after the reference year:** replacement value equals acquisition value.
- **Missing WPI data** for a required stage: the row is marked **Manual Review Required** with the reason. It is never marked Success.

Example (Plant & Machinery, bought 1966 for 12,496): six stages give 15,050, then 39,009, 94,363, 1,29,938, 1,61,383 and finally **2,13,349**.

---

## 4. Column detection

Needed: **asset description, purchase date (or year), acquisition value**. Recommended: a **category** column.

1. Known names, then fuzzy matching, then a content check (is it numeric, is it a date).
2. For an unfamiliar heading, **Gemini** reads the heading and a few sample values.
3. Confirmed mappings are remembered in the database, so the same heading is instant next time.

If a required column is missing, the user is told which heading to rename. If only the category is missing, the user can continue and groups are worked out from descriptions.

---

## 5. Choosing the WPI group

Valid groups are read from the master dataset at startup. Nothing is hardcoded. Order of checks:

1. **Building, Land, Software** (decided from the category columns).
2. **Category synonyms** (`backend/category_synonyms.json`): the FAR's own category text, cleaned ("and" = "&", plurals ignored).
3. **Description keywords** (same file), matched as whole words.
4. **Saved answers** from earlier uploads.
5. **Gemini**, restricted to the master's groups.
6. **Manual Review Required.**

A known group is never silently replaced by "All commodities". To teach the app new wording, edit `category_synonyms.json`. No code change is needed.

**Gemini** is used only for column detection and for descriptions the rules can't classify. If it is unavailable or over its limit, those rows go to Manual Review and everything else still calculates.

---

## 6. The WPI master dataset

`backend/data/WPI_MASTER_DATASET_CATEGORYWISE_v6.xlsx`

- **Year sheets** (names end in "base"): 2011-12, 2004-05, 1994-95, 1981-82, 1970-71, 1961-62. In the **Tier** column, the company's asset groups are "Verified" or "Candidate". Every other row is "Broad Group", which only means "official WPI series, not a company group". Do not rename these labels.
- **ASSET_GROUPS** sheet: which official series each group follows, and where data is missing.
- **RULES** sheet: the calculation rules above.
- Some groups have no data in older sheets (for example Computer before 1994). Those assets go to Manual Review.

**Yearly update:** add the new year's column to the 2011-12 sheet, update the reference year in RULES, then run the benchmark check (section 9).

---

## 7. Accounts, saved analyses and admin

- **Sign-up** with email verification (6-digit code, 15 minutes, 5 attempts). **Google sign-in** needs no code. **Password reset** also uses a 6-digit code (no links).
- Rate limiting, CAPTCHA (Cloudflare Turnstile) and a unique-email check (Gmail dots and "+tag" are ignored).
- **Delete account** removes the user's analyses and data, and anonymizes login and audit records.
- **Saved analyses:** each user sees only their own.
- **Admin dashboard:** users, login activity, analyses (who uploaded which file), usage and limits. Roles are checked on the server for every request. The first admin is created only with `python seed_admin.py`. There are no default accounts.
- **Limits** (set in `.env`): upload size, rows per file, analyses per day, Gemini calls per month.

---

## 8. Tools, technologies & setup

**Requirements:** Python 3.9+, Node.js 18+, MySQL 8.0.
*(Verified running in this environment: Python 3.14, Node.js v24, MySQL 8.0)*

- **Backend:** Python, FastAPI, Uvicorn (ASGI server), SQLAlchemy 2.0 (ORM), Alembic (database migrations), PyMySQL, Pandas & NumPy (data processing & calculation math), OpenPyXL & PyXLSB (Excel parsing), Bcrypt (password hashing), PyJWT (tokens), Google GenAI SDK (Gemini 3.8 Flash), Cloudflare Turnstile (CAPTCHA).
- **Frontend:** React 18, Vite 5, Lucide React (icons), SheetJS `xlsx` (client-side Excel reading), responsive CSS.
- **Database:** MySQL 8 (`far_app` for production, `far_app_test` for automated tests).

**Backend**
```bash
cd backend
py -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env      # then fill in .env
alembic upgrade head        # creates the database tables
python seed_admin.py        # creates the first admin (asks for details)
python -m uvicorn main:app --port 8001
```

**Frontend**
```bash
cd frontend
npm install
npm run dev                 # opens at the address Vite prints
```

API docs are at `http://localhost:8001/docs`. Health check: `/health`.

**Main `.env` settings** (the full list is in `backend/.env.example`):

| Setting | Purpose |
|---|---|
| `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` | MySQL connection (use `far_user`, never root) |
| `JWT_SECRET` | Signs login tokens (long and random) |
| `GEMINI_API_KEY`, `GEMINI_MODEL` | Gemini access and model name |
| `SMTP_*`, `MAIL_FROM`, `MAIL_SENDER_NAME`, `MAIL_REPLY_TO` | Sending verification and reset codes |
| `GOOGLE_CLIENT_ID` (and `VITE_GOOGLE_CLIENT_ID` in `frontend/.env`) | Google sign-in |
| `TURNSTILE_SECRET` | CAPTCHA |
| `FRONTEND_URL`, `ENV` | Allowed website address; development or production |

---

## 9. Testing

- Tests run only on the separate database `far_app_test` and refuse to run on `far_app`.
  ```powershell
  $env:DB_NAME="far_app_test"
  python -m unittest discover tests
  python scripts/clean_test_db.py     # empties the test database
  ```
- **Benchmark check before every release:** compares four reference FARs with saved results and must show **0 differing rows**.
  ```powershell
  python scripts/verify_benchmarks.py
  ```

**Scripts:** `backend/seed_admin.py` (first admin), `scripts/cleanup_test_data.py` (removes test accounts after a backup and a typed YES), `scripts/clean_test_db.py`, `scripts/verify_benchmarks.py`, `scripts/list_aliases.py`.

---

## 10. Deployment

Use `docs/DEPLOY.md`. In short: set `ENV=production`, run **one worker** without `--reload`, serve over **HTTPS**, set `FRONTEND_URL` to the real site address, keep MySQL private, back it up with `mysqldump`, and set a budget alert on the Gemini key. Large FARs can take minutes the first time, so allow long request timeouts.

---

## 11. Security

- Never commit `.env`, and never paste passwords, keys or screenshots of `.env` into chats or tickets.
- Uploaded files are processed from temporary storage and deleted afterwards.
- Results contain client financial data: keep backups private and set a retention period.
- Use a paid Gemini project for client data.

---

## 12. Limits and open decisions

- WPI is a general price index, so replacement value is an estimate, not a vendor quotation.
- Index values are yearly averages.
- **To confirm with the valuation team:** whether Building and Land should use simple or compound 5%; which group networking and telephone equipment should follow; what to do for assets older than the first year with data for their group; and the Office Equipment series, which is a "Candidate".
