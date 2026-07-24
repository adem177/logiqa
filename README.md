# Logiqa

Full-stack app with an Angular frontend and a Flask backend (MySQL).

## Prerequisites

- **Node.js** (v20+) and npm
- **Python** 3.11+
- **MySQL** (local MySQL server)
- **Angular CLI** (optional globally: `npm install -g @angular/cli`)

## Project structure

```
logiqa/
├── backend/     # Flask API
└── frontend/    # Angular app
```

---

## Backend

### 1. Create and activate a virtual environment

```bash
cd backend
python3 -m venv venv       #  or python
source venv/bin/activate   # macOS / Linux
# venv\Scripts\activate    # Windows
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

An example file is provided: `backend/.env.example`.

1. Copy it to `.env` (same folder):

```bash
cd backend
cp .env.example .env
```

On Windows (PowerShell):

```powershell
cd backend
Copy-Item .env.example .env
```

2. Open `backend/.env` and edit the values for your machine:

| Variable | Meaning | Example |
|----------|---------|---------|
| `DB_HOST` | MySQL host | `localhost` |
| `DB_USER` | MySQL user | `root` |
| `DB_PASSWORD` | MySQL password | your password (empty `""` if none) |
| `DB_NAME` | Database name | `logiqa` |
| `DB_PORT` | MySQL port | `3306` |
| `PORT` | Flask API port | `3000` |
| `JWT_SECRET` | Secret for signing JWT tokens | long random string |
| `ADMIN_EMAIL` | Default admin email (seeded at startup) | `admin@logiqa.local` |
| `ADMIN_PASSWORD` | Default admin password | change in production |
| `ADMIN_NOM` / `ADMIN_PRENOM` | Admin display name (optional) | `Admin` / `Logiqa` |

3. Important:
   - Do **not** commit `.env` (it is in `.gitignore`).
   - Do commit `.env.example` so others know which variables are required.
   - After changing `.env`, restart `python app.py`.

Example `.env` after editing:

```env
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=logiqa
DB_PORT=3306
PORT=3000
JWT_SECRET=a_long_random_secret_phrase
ADMIN_EMAIL=admin@logiqa.local
ADMIN_PASSWORD=Admin123!
```

### 4. Start MySQL

Make sure MySQL is running (XAMPP, local MySQL, etc.).  
You do **not** need to create the database or tables by hand.

### 5. Run the API

```bash
python app.py
```

On startup, `app.py` runs `init_db.py`, which creates the `logiqa` database, the `users` / `sessions` tables if missing, and seeds a default **admin** account (`ADMIN_EMAIL` / `ADMIN_PASSWORD`). Admin accounts must not be creatable via public registration.

The API listens on **http://localhost:3000** by default.

Quick check: open http://localhost:3000/ — you should see a JSON message confirming the API is running.

---

## Frontend

### 1. Install dependencies

```bash
cd frontend
npm install
```

### 2. Run the development server

```bash
npm start
# or: ng serve
```

Open **http://localhost:4200/** in your browser.

The app calls the backend at `http://localhost:3000` (e.g. registration at `/api/register`).

### Build for production

```bash
npm run build
```

Output is written to `frontend/dist/`.

---

## Running both together

Use two terminals:

| Terminal | Commands |
|----------|----------|
| 1 – API | `cd backend` → activate venv → `python app.py` |
| 2 – UI | `cd frontend` → `npm start` |

Then open http://localhost:4200 and use the app against the API on port 3000.
