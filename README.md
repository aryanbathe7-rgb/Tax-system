# Smart Municipal Tax Collection and Payment Tracking System

A software-only Flask mini-project: citizens view property tax dues and pay online with
Razorpay (test mode); the municipal admin tracks collections, defaulters and offline payments.

**Stack:** Python 3.10+, Flask, Flask-SQLAlchemy (SQLite), Flask-Login, Razorpay SDK,
reportlab (PDF receipts), Bootstrap 5 and Chart.js (CDN), python-dotenv.

## 1. Setup

```bash
cd tax_system
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # Windows: copy .env.example .env
```

Open `.env` and set:
- `SECRET_KEY`: any long random string.
- `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET`: your **test** keys. Create a free Razorpay account,
  switch the dashboard to **Test Mode**, then go to Settings -> API Keys -> Generate Test Key.

## 2. Run

```bash
python app.py
```
Open http://127.0.0.1:5000. Tables and a default admin are created automatically on first run.

Optional demo data (a citizen with 2 properties, 3 years of bills, 2 past payments):
```bash
flask --app app seed-demo
```

| Role    | Email                  | Password     |
|---------|------------------------|--------------|
| Admin   | admin@municipal.gov    | Admin@123    |
| Citizen | citizen@example.com    | Citizen@123  (after `seed-demo`) |

## 3. How to test the whole flow

1. Log in as **admin** and press **Generate bills** on the dashboard.
2. Log out, log in as the **citizen** (or register a new one and add a property, then ask the admin to generate bills again).
3. On **My dues** press **Pay now**, then **Pay** and use Razorpay test details:
   - Card: `4111 1111 1111 1111`, any future expiry, any CVV, OTP `1234` if asked
   - UPI: `success@razorpay` (use `failure@razorpay` to test a failed payment)
4. You are redirected to the receipt. Download the PDF.
5. As admin check the **Dashboard** charts, **Defaulters**, and **Record payment** for cash/cheque entries.

## 4. Tax rules (utils/tax_calculator.py)

| Item     | Rule |
|----------|------|
| Base tax | area x rate (Residential Rs.4, Commercial Rs.12, Industrial Rs.15 per sq.ft per year) |
| Rebate   | 5% if paid on or before 30 June of the financial year |
| Due date | 30 September |
| Penalty  | 2% of base tax per month (or part of a month) after the due date |

Change the constants at the top of the file to match your own rules.

## 5. Payment flow

```
Browser                 Flask server                    Razorpay
  | POST create-order ->  compute amount (server side)
  |                       order.create()  ------------->  order_id
  | <- order_id, key
  | Checkout popup  ------------------------------------> customer pays
  | <- payment_id + signature
  | POST verify  ------>  verify_payment_signature()
  |                       mark Paid + receipt number
  | <- redirect to receipt
```
The amount is always calculated on the server, and a bill is marked paid only after the
signature check passes. `/payment/webhook` is an optional backup: set a webhook secret in the
Razorpay dashboard, put it in `RAZORPAY_WEBHOOK_SECRET`, and expose your server with a tunnel such as ngrok.

## 6. Project structure

```
app.py            app factory, blueprint registration, seed-demo command
config.py         settings read from .env
extensions.py     db and login_manager objects
models.py         User, Property, TaxDemand, Payment
routes/           auth.py, citizen.py, admin.py, payment.py
utils/            tax_calculator.py, pdf_generator.py
templates/        Jinja2 pages (base, auth/, citizen/, admin/)
static/css/       style.css
```

## 7. Known limitations (good "future scope" points for your report)

- No CSRF tokens on forms (add Flask-WTF / CSRFProtect for production).
- SQLite and Flask's dev server are for learning only; use PostgreSQL and gunicorn in production.
- No password reset, email/SMS reminders or database migrations (Flask-Migrate).
- Only Razorpay **test** keys should be used in this project.

## 8. Installable web app (PWA) and deployment

New files: `static/manifest.json`, `static/service-worker.js`, `static/offline.html`,
`static/js/pwa.js`, `static/icons/`, `tools/make_icons.py`, `render.yaml`.

Deploy to Render: push to GitHub -> Render -> New -> Blueprint -> pick the repo -> set
`ADMIN_PASSWORD`, `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET` -> Apply. Open the `https://...onrender.com`
URL on your phone in Chrome and use "Install app" (iPhone: Safari -> Share -> Add to Home Screen).

Free-tier notes: the service sleeps after 15 minutes idle (first load takes about a minute) and its disk
is temporary, so SQLite data resets on restart. `SEED_DEMO=1` re-creates the demo data each start.
Always keep Razorpay in TEST mode.
