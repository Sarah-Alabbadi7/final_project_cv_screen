# 🧠 CV Screening System

An AI-powered web application that allows HR users to automatically screen CVs, extract skills and contact details, and rank candidates based on job descriptions. Includes optional Firebase Authentication for secure user management.

---

## 📑 Table of Contents

- [Overview](#overview)
- [Tech Stack](#tech-stack)
- [Features](#features)
- [Project Structure](#project-structure)
- [Environment Variables](#environment-variables)
- [Setup & Installation](#setup--installation)
- [Firebase Setup](#firebase-setup-optional-auth)
- [Usage Guide](#usage-guide)
- [API Endpoints](#api-endpoints)
- [How Scoring Works](#how-scoring-works)
- [Authors](#authors)

---

## 🎯 Overview

This intelligent tool helps recruiters automatically extract and analyze information from uploaded PDF CVs, compare them against job descriptions, and generate ranked candidate lists with normalized scoring. Supports Firebase Authentication, enabling each HR user to securely access only their own data.

---

## 🛠 Tech Stack

### Backend Technologies
- ⚡ **FastAPI** – API routes, job creation, CV upload, scoring, and CSV export
- 🧠 **SQLModel** – Database models and ORM interactions
- 🗃️ **SQLite** – Lightweight, file-based database storage
- 📄 **pdfplumber** – Text extraction from standard PDF resumes
- 🖼️ **PyMuPDF (fitz)** – Scanned PDF processing for OCR fallback
- 🔍 **pytesseract** – OCR on scanned resume images
- 🧪 **RapidFuzz** – Fuzzy logic skill matching
- 🔗 **regex** – Contact info extraction (email, phone, links)
- 🧬 **spaCy** – NLP for skill normalization
- ✅ **Pydantic** – Data validation and serialization
- 📤 **jinja2** – CSV export template rendering
- 🔐 **Firebase Admin SDK** – User identity verification
- 🚀 **Uvicorn** – Development server with hot reload

### Frontend Technologies
- 🎨 **Tailwind CSS** – Clean, responsive styling
- 📊 **Chart.js** – Candidate score visualization
- 🔐 **Firebase Auth** – User session management
- ⚡ **JavaScript (ES6+)** – Dynamic UI and API interactions

---

## ✨ Features

- 📤 **Upload & Parse CVs** – PDF support with OCR fallback for scanned documents
- 🔍 **Smart Extraction** – Automatically extracts skills, contacts, and education
- 🏆 **Automatic Scoring** – AI-powered ranking based on job requirements
- 🎭 **Demo Job Generator** – Pre-built templates across various fields
- 📥 **Export Data** – Download candidate results as CSV
- 🔒 **Secure Authentication** – Optional Firebase Auth with data scoping
- 👥 **User Isolation** – Users only access their own jobs and candidates

---

## 📁 Project Structure

```plaintext
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
└── README.md
```

---

## ⚙️ Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | Database connection string | `sqlite:///./cv_screening.db` |
| `AUTH_REQUIRED` | Require Firebase Auth (`"1"` = yes) | `1` |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to Firebase Admin JSON | `C:\cv-screening\serviceAccountKey.json` |
| `DEV_USER_ID` | Default user when auth is disabled | `dev_user` |

---

## 🚀 Setup & Installation

### Backend Setup

1. **Navigate to backend directory**
   ```bash
   cd backend
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Start the FastAPI server**
   ```bash
   uvicorn app:app --reload --port 8000
   ```
---

## 🔐 Firebase Setup (Anonymous Auth)

 **Enable Authentication Methods**
   - Go to Firebase Console → Authentication → Sign-in Method
   - Enable **Anonymous** and/or **Email/Password** authentication

---

## 📖 Usage Guide

1. **Access Application** – Start from `login.html` for proper authentication flow
2. **Authentication** – Sign in or use anonymous authentication
3. **Create Job** – Use demo templates or write custom job descriptions
4. **Upload CVs** – Drag and drop or select multiple PDF files
5. **Review Results** – View ranked candidates with detailed scoring
6. **Export Data** – Download candidate list as CSV for further analysis

---

## 🔌 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Backend status check |
| `/demo_job` | GET | Returns random job description template |
| `/jobs` | POST | Create a new job |
| `/jobs/{job_id}/upload` | POST | Upload and score CVs |
| `/jobs/{job_id}/candidates` | GET | Retrieve candidate list |
| `/jobs/{job_id}/export.csv` | GET | Export candidates as CSV |

---

## 🎯 How Scoring Works

The AI compares extracted CV skills with job requirements using intelligent matching:

| Match Level | Score Range | Description |
|-------------|-------------|-------------|
| **Excellent** | 90–100 | 4+ matching skills |
| **Good** | 60–80 | 2–3 matching skills |
| **Weak** | < 60 | 0–1 matching skills |

Additional weight is given to education and experience keywords for more natural ranking.

---

## 👥 Authors

**Developed with ❤️ by Nouf Al-Rashdi & Sara Al-Abbadi**

We're passionate about building real-world AI tools for HR automation, with expertise in NLP, resume parsing, and full-stack development.

---

<div align="center">

*⭐ Star this repo if you find it helpful! ⭐*

</div>

<script>
// Table of Contents smooth scrolling
document.addEventListener('DOMContentLoaded', function() {
    const links = document.querySelectorAll('a[href^="#"]');
    
    links.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            
            const targetId = this.getAttribute('href').substring(1);
            const targetElement = document.getElementById(targetId);
            
            if (targetElement) {
                window.scrollTo({
                    top: targetElement.offsetTop - 20,
                    behavior: 'smooth'
                });
            }
        });
    });
});
</script>

<style>
/* Beautiful styling for the README */
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    line-height: 1.6;
    color: #333;
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
}

h1, h2, h3, h4 {
    color: #2d3748;
    margin-top: 1.5em;
}

h1 {
    border-bottom: 3px solid #4299e1;
    padding-bottom: 10px;
}

h2 {
    border-left: 4px solid #4299e1;
    padding-left: 15px;
    margin-top: 2em;
}

table {
    width: 100%;
    border-collapse: collapse;
    margin: 1em 0;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

th, td {
    padding: 12px;
    text-align: left;
    border-bottom: 1px solid #e2e8f0;
}

th {
    background-color: #f7fafc;
    font-weight: 600;
}

tr:hover {
    background-color: #f8fafc;
}

code {
    background-color: #f7fafc;
    padding: 2px 6px;
    border-radius: 3px;
    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
    font-size: 0.9em;
}

pre {
    background-color: #f7fafc;
    padding: 15px;
    border-radius: 5px;
    overflow-x: auto;
    border-left: 4px solid #4299e1;
}

a {
    color: #4299e1;
    text-decoration: none;
}

a:hover {
    text-decoration: underline;
}

/* Custom styling for feature sections */
.feature-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 20px;
    margin: 20px 0;
}

.feature-card {
    background: white;
    padding: 20px;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    border-left: 4px solid #4299e1;
}

/* Responsive design */
@media (max-width: 768px) {
    body {
        padding: 10px;
    }
    
    .feature-grid {
        grid-template-columns: 1fr;
    }
}
</style>
