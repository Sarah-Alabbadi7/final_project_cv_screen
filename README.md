# 🧠 CV Screening System

An AI-powered web application that allows HR users to automatically screen CVs, extract skills and contact details, and rank candidates based on a job description.  
Includes optional Firebase Authentication so each HR user can securely manage their own jobs and candidates.

---

## 📑 Table of Contents

1. [Overview](#overview)  
2. [Tech Stack](#tech-stack)  
3. [Features](#features)  
4. [Project Structure](#project-structure)  
5. [Environment Variables](#environment-variables)  
6. [Setup & Installation](#setup--installation)  
   - [Backend](#backend)  
   - [Frontend](#frontend)  
7. [Firebase Setup (Optional Auth)](#firebase-setup-optional-auth)  
8. [Usage Guide](#usage-guide)  
9. [API Endpoints](#api-endpoints)  
10. [How Scoring Works](#how-scoring-works)  
11. [Troubleshooting](#troubleshooting)  
12. [License](#license)  
13. [Authors](#authors)

---

## Overview

This tool helps recruiters automatically extract and analyze information from uploaded PDF CVs, compare them to a job description, and generate ranked candidate lists with normalized scoring.  
It supports Firebase Authentication, enabling each HR user to securely access only their own data.

---

## Tech Stack

- **Backend**: FastAPI + SQLModel + SQLite  
- **Frontend**: Tailwind CSS + Chart.js (Single-page app)  
- **Authentication**: Firebase (Anonymous or Email/Password)  
- **AI/NLP**: Custom skill extraction and scoring algorithms

---

## Features

- Upload & Parse CVs (PDF + OCR fallback)  
- Extract Skills, Contacts, and Education  
- Automatic Scoring & Ranking  
- Demo Job Generator across fields (accounting, engineering, healthcare, etc.)  
- Export Candidates as CSV  
- Optional Firebase Authentication  
- Scoped Data Access — users only see their own jobs/candidates

---

## Project Structure

```
cv-screening/
├── backend/
│   ├── app.py              # FastAPI app, routes, Firebase verification
│   ├── db.py               # Database engine and session helpers
│   ├── models.py           # SQLModel definitions (Job, Candidate)
│   ├── extraction.py       # PDF → text + contact/skill extraction
│   ├── nlp.py              # Skill normalization and parsing logic
│   ├── scoring.py          # Candidate scoring and ranking
│   └── requirements.txt
├── frontend/
│   ├── index.html          # Main dashboard (protected by auth)
│   ├── login.html          # Login / Signup page
│   └── firebase.js         # Firebase config (optional split)
├── serviceAccountKey.json  # Firebase Admin SDK credentials
```

---

## Environment Variables

| Variable                     | Description                          | Example                                  |
|-----------------------------|--------------------------------------|------------------------------------------|
| `DATABASE_URL`              | DB connection string                 | `sqlite:///./cv_screening.db`            |
| `AUTH_REQUIRED`             | Require Firebase Auth (`"1"` = yes) | `1`                                      |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to Firebase Admin JSON     | `C:\cv-screening\serviceAccountKey.json` |
| `DEV_USER_ID`               | Used when auth is disabled           | `dev_user`                               |

---

## Setup & Installation

### Backend

```powershell
python -m venv .venv
. .venv/Scripts/Activate.ps1
pip install -r backend/requirements.txt

# Set environment variables
$env:AUTH_REQUIRED = "1"
$env:GOOGLE_APPLICATION_CREDENTIALS = "C:\cv-screening\serviceAccountKey.json"

# Start server
uvicorn backend.app:app --reload --port 8000
```

Visit: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

---

### Frontend

```bash
cd frontend
python -m http.server 5500
```

Then open: [http://127.0.0.1:5500/login.html](http://127.0.0.1:5500/login.html)

---

## Firebase Setup (Optional Auth)

1. In Firebase Console → Authentication → Sign-in Method, enable:
   - Anonymous
   - Email/Password (optional)

2. In Project Settings → General → Web App, copy the web config and paste it into `login.html` and `index.html`.

3. Add these Authorized Domains:
   - `localhost`
   - `127.0.0.1`
   - `cv-screening-40a27.web.app`

4. Place your `serviceAccountKey.json` in the project root and set:

```bash
GOOGLE_APPLICATION_CREDENTIALS=path/to/serviceAccountKey.json
```

---

## Usage Guide

1. Open the login page → sign in or use anonymous mode  
2. Go to `index.html` → fill a demo job or write a new job description  
3. Upload one or more CV PDFs  
4. View candidate scores and download results as CSV

---

## API Endpoints

| Endpoint                        | Method | Description                      |
|---------------------------------|--------|----------------------------------|
| `/health`                       | GET    | Check backend status             |
| `/demo_job`                     | GET    | Returns random job description   |
| `/jobs`                         | POST   | Create a new job                 |
| `/jobs/{job_id}/upload`         | POST   | Upload CVs and score candidates  |
| `/jobs/{job_id}/candidates`     | GET    | Retrieve candidates              |
| `/jobs/{job_id}/export.csv`     | GET    | Export CSV                       |

---

## How Scoring Works

The app compares skills extracted from the CV with skills required in the job:

- ≥4 matching skills → Excellent (90–100)  
- 2–3 matches → Good (60–80)  
- 1 match → Weak (Reject)  

Minor weight is given to education or experience keywords, giving a more natural ranking.

---

## Troubleshooting

| Issue                     | Solution                                                  |
|---------------------------|-----------------------------------------------------------|
| Login page flashes away   | Start from `login.html`, not `index.html`                |
| Firebase error            | Check Admin SDK path and environment variables            |
| Fill Demo not working     | Ensure backend is running on port 8000                    |
| No database entries       | Confirm `cv_screening.db` exists and is writable          |

---

## License

MIT License – free to use and modify.  
Created for academic and demo use.

---

## Authors

Developed by **Nouf Al-Rashdi** & **Sara Al-Abbadi**  
Focused on building real-world AI tools for HR automation  
Passionate about NLP, resume parsing, and full-stack development

-
