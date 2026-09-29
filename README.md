# Piki Ora Medical Center

A Django appointment booking application for ISCG7420 Assignment 1.

## Live website

https://iscg7420-2026-s2-assignment1-pikiora.onrender.com/

## Features

Patients can:
- Register, log in and log out.
- Browse doctors and available consultation slots.
- Book, reschedule and cancel their own appointments.
- View their booking history.

Staff can:
- Access a custom administration dashboard.
- Create and edit doctor profiles and consultation slots.
- View patient bookings and cancel eligible appointments.
- Activate and deactivate patient accounts.

Appointment times use the Pacific/Auckland time zone.

## Technology

- Python 3.12 and Django 5.2
- SQLite for local development
- PostgreSQL on Render
- Gunicorn and WhiteNoise
- Django templates and CSS

## Run locally

The following commands are for macOS/Linux:

```bash
git clone https://github.com/karsonYe0129/ISCG7420-2026-S2-Assignment1.git
cd ISCG7420-2026-S2-Assignment1
python3.12 -m venv .venv
source .venv/bin/activate
cd "Assignment 1"
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open http://127.0.0.1:8000/.

A new local database starts without doctors or consultation slots.
Log in with the superuser account and use Admin dashboard to add them.
Accounts created through the registration page are ordinary patient accounts.

## Tests

From the directory containing manage.py:

```bash
python manage.py test clinic
```

The suite contains 18 tests covering booking constraints, staff access,
patient account status, cancellation and booking ownership permissions.

Manual desktop checks were also performed on the deployed application.
Mobile layout testing was not performed.

## Render deployment

- Runtime: Python 3
- Root Directory: Assignment 1
- Build Command: bash build.sh
- Start Command: python -m gunicorn config.wsgi:application --bind 0.0.0.0:$PORT

Environment variables:
- DATABASE_URL: Render PostgreSQL internal connection URL
- SECRET_KEY: a private randomly generated Django secret
- PYTHON_VERSION: 3.12.10

Render supplies the RENDER environment variable used by the project
to select production settings.

The build script installs dependencies, collects static files and
applies database migrations.

Local and deployed databases are separate. Local accounts and sample
data are not automatically transferred to Render.

Do not commit database credentials, secret keys or account passwords.