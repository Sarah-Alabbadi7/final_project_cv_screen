# backend/app.py
from __future__ import annotations
from typing import Optional, List, Dict
import os, csv, io, json, re, random
from io import BytesIO

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request, Depends, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from backend.db import create_db_and_tables, get_session
from backend.models import Job, Candidate
from backend.extraction import pdf_to_text_robust, extract_contacts, guess_name, extract_skills_from_text
from backend.scoring import score_candidate
from backend.nlp import normalize_skills, jd_requirements_from_text, extract_education, extract_years_experience
from sqlmodel import select

# -------------------------- App & CORS --------------------------
app = FastAPI(title="CV Screening API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500", "http://localhost:5500",
        "http://127.0.0.1:8080", "http://localhost:8080",
        # add more dev ports if needed:
        "http://127.0.0.1:5501", "http://localhost:5501",
    ],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

# ---------------------- Optional Firebase Auth ------------------
try:
    import firebase_admin
    from firebase_admin import auth as fb_auth, credentials
except Exception:
    firebase_admin, fb_auth, credentials = None, None, None

AUTH_REQUIRED = os.getenv("AUTH_REQUIRED", "0") == "1"
FIREBASE_ENABLED = False

def _init_firebase():
    global FIREBASE_ENABLED
    if firebase_admin is None:
        FIREBASE_ENABLED = False
        if AUTH_REQUIRED:
            raise RuntimeError("Auth required but firebase_admin not installed.")
        return
    try:
        if not firebase_admin._apps:
            cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "serviceAccountKey.json")
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
        FIREBASE_ENABLED = True
    except Exception:
        FIREBASE_ENABLED = False
        if AUTH_REQUIRED:
            raise RuntimeError(
                "Firebase credentials not found. Set GOOGLE_APPLICATION_CREDENTIALS "
                "or place serviceAccountKey.json in project root."
            )

_init_firebase()
print(f"[auth] FIREBASE_ENABLED={FIREBASE_ENABLED}  AUTH_REQUIRED={AUTH_REQUIRED}")

def get_current_user(authorization: str = Header(None)) -> dict:
    # Strict mode → must verify token
    if AUTH_REQUIRED:
        if not FIREBASE_ENABLED:
            raise HTTPException(status_code=500, detail="Auth required but Firebase not initialized")
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing Authorization Bearer token")
        token = authorization.split(" ", 1)[1].strip()
        try:
            return fb_auth.verify_id_token(token)
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
    # Non-strict → try verify, else dev user
    if FIREBASE_ENABLED and authorization and authorization.startswith("Bearer "):
        try:
            token = authorization.split(" ", 1)[1].strip()
            return fb_auth.verify_id_token(token)
        except Exception:
            pass
    return {"uid": os.getenv("DEV_USER_ID", "dev_user")}

# ------------------------- DB bootstrap -------------------------
create_db_and_tables()

# ------------------------ Skills Vocabulary ---------------------
SKILLS_MASTER: List[str] = [
    # Software / Web
    "Python","SQL","Java","JavaScript","TypeScript","HTML","CSS",
    "React","Redux","Node.js","Express","FastAPI","Flask","Django",
    "REST","GraphQL","Git","CI/CD","Jest","Playwright",

    # Cloud / DevOps
    "AWS","GCP","Azure","Docker","Kubernetes","Terraform","Linux",

    # Data / ML
    "Pandas","NumPy","scikit-learn","TensorFlow","PyTorch",
    "Spark","Airflow","Matplotlib","Seaborn","Power BI","Excel",

    # Civil / Mech / Elec
    "AutoCAD","Revit","ArcGIS","SAP2000","ETABS","SAFE","Primavera P6",
    "SolidWorks","ANSYS","MATLAB","Embedded C","PCB Design","PLC",

    # Business / Finance
    "QuickBooks","SAP","Financial Reporting","Google Analytics",
    "Expense Reporting","TaxAct","BambooHR","Concur","Oracle Hyperion",
    "LibreOffice Calc","Accounts Receivable",

    # Education / Classroom / Creative (consistency with NLP aliases & demo)
    "Microsoft PowerPoint","Google Classroom","ClassDojo",
    "Adobe Photoshop","Adobe Illustrator","Adobe Premiere Pro",

    # Generic
    "Project Management","Site Supervision",
]

# ---------------------- JD parsing helper -----------------------
def _parse_job_description(jd_text: str) -> tuple[list[str], list[str]]:
    mandatory: List[str] = []; preferred: List[str] = []
    lower = (jd_text or "").lower()
    if "mandatory" in lower or "preferred" in lower:
        mand = re.search(r"(mandatory[:\-]?\s*(.*?))(?=(preferred|$))", jd_text, re.I | re.S)
        pref = re.search(r"(preferred[:\-]?\s*(.*?))(?=(mandatory|$))", jd_text, re.I | re.S)
        def split_skills(s: str) -> List[str]:
            return [x.strip() for x in re.split(r"[,\n;•\-]", s) if x.strip()]
        if mand: mandatory = split_skills(mand.group(2))
        if pref: preferred = split_skills(pref.group(2))
    else:
        all_sk = [x.strip() for x in (jd_text or "").split(",") if len(x.strip()) > 2]
        if all_sk:
            mandatory = all_sk[: min(5, len(all_sk))]
    return mandatory, preferred

# ---------------------- Demo job generator ----------------------
CATEGORIES: Dict[str, Dict] = {
    "accounting": {
        "titles": ["Financial Accountant","AP Specialist","Financial Analyst"],
        "mand_pool": ["Excel","QuickBooks","Expense Reporting","LibreOffice Calc","Accounts Receivable"],
        "pref_pool": ["Power BI","Financial Reporting","TaxAct","BambooHR","Concur","Oracle Hyperion"],
        "resp": ["Monthly close & reconciliations","Build KPI dashboards",
                 "Variance analysis and reporting","Support audits and controls"],
    },
    "software": {
        "titles": ["Backend Engineer","Full Stack Developer","Frontend Engineer"],
        "mand_pool": ["Python","SQL","JavaScript","React","Node.js","FastAPI"],
        "pref_pool": ["TypeScript","Docker","AWS","CI/CD"],
        "resp": ["Design and implement APIs","Write tests & review PRs",
                 "Improve performance & reliability","Collaborate with Product & Design"],
    },
    "data": {
        "titles": ["Data Analyst","Data Scientist","Analytics Engineer"],
        "mand_pool": ["SQL","Excel","Python","Pandas","scikit-learn"],
        "pref_pool": ["Power BI","TensorFlow"],
        "resp": ["Build dashboards and ad-hoc analyses","Clean and model data",
                 "Communicate insights","Design A/B tests"],
    },
    "civil": {
        "titles": ["Civil Engineer","Site Engineer","Project Engineer"],
        "mand_pool": ["AutoCAD","ArcGIS","SAP2000"],
        "pref_pool": ["Revit","ETABS","Primavera P6","MATLAB"],
        "resp": ["Prepare drawings and BOQs","Coordinate with contractors",
                 "Ensure code compliance","Track progress and QA/QC"],
    },
    "mechanical": {
        "titles": ["Mechanical Design Engineer","Manufacturing Engineer"],
        "mand_pool": ["SolidWorks","ANSYS","AutoCAD"],
        "pref_pool": ["MATLAB","Project Management"],
        "resp": ["Create 3D models and drawings","Define tolerances and BOM",
                 "Plan tests and reports","Support production transfers"],
    },
    "electrical": {
        "titles": ["Electrical Engineer","Firmware Engineer"],
        "mand_pool": ["Embedded C","MATLAB","PCB Design"],
        "pref_pool": ["AutoCAD","PLC","Project Management"],
        "resp": ["Design schematics and PCBs","Write firmware tests",
                 "EMC/DFM reviews","Lab bring-up and validation"],
    },
    "healthcare": {
        "titles": ["Registered Nurse","Hospital Pharmacist"],
        "mand_pool": ["Patient Safety","Clinical Judgment"],
        "pref_pool": ["Clinical documentation","Patient Advocacy"],
        "resp": ["Administer medications","Provide direct patient care",
                 "Dispense prescriptions","Collaborate with medical teams"],
    },
    "education": {
        "titles": ["STEM Teacher","Instructional Designer"],
        "mand_pool": ["Classroom Management","Microsoft PowerPoint"],
        "pref_pool": ["Google Classroom","ClassDojo"],
        "resp": ["Plan lessons and assessments","Track student performance",
                 "Create engaging materials","Support extracurricular projects"],
    },
}
def _make_demo_job(field: Optional[str] = None) -> Dict[str, str]:
    keys = list(CATEGORIES.keys())
    key = (field or "").lower()
    if key not in keys:
        key = random.choice(keys)
    cat = CATEGORIES[key]
    title = random.choice(cat["titles"])
    mand = random.sample(cat["mand_pool"], min(len(cat["mand_pool"]), random.randint(2, 3)))
    pref = random.sample(cat["pref_pool"], min(len(cat["pref_pool"]), random.randint(2, 3)))
    resp = random.sample(cat["resp"], min(3, len(cat["resp"])))
    jd = (
        f"Mandatory: {', '.join(mand)}\n"
        f"Preferred: {', '.join(pref)}\n\n"
        "Responsibilities:\n- " + "\n- ".join(resp)
    )
    return {"field": key, "title": title, "jd_text": jd}

# ---------------------- Access control helper ----------------------
def _ensure_job_access(sess, job_id: int, current_user: dict) -> Job:
    job = sess.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    # Enforce ownership only when auth is required
    if AUTH_REQUIRED:
        uid = (current_user or {}).get("uid")
        if not uid or job.user_id != uid:
            raise HTTPException(status_code=403, detail="Forbidden: job does not belong to this user")
    return job

# ---------------------------- Endpoints --------------------------------
@app.get("/health")
def health():
    return {"status": "ok", "auth": {"enabled": FIREBASE_ENABLED, "required": AUTH_REQUIRED}}

@app.get("/demo_job")
def demo_job(field: Optional[str] = Query(default=None)):
    return _make_demo_job(field)

@app.post("/jobs")
async def create_job(
    request: Request,
    title: Optional[str] = Form(None),
    jd_text: Optional[str] = Form(None),
    user_id: str = Form("default_user"),
    current_user: dict = Depends(get_current_user),
):
    # JSON fallback
    if title is None or jd_text is None:
        try:
            data = await request.json()
            title = data["title"]
            jd_text = data["jd_text"]
            user_id = data.get("user_id", user_id or "default_user")
        except Exception:
            raise HTTPException(status_code=400, detail="Missing form fields or invalid JSON body.")

    # Prefer token UID if present
    if current_user and current_user.get("uid"):
        user_id = current_user["uid"]

    # Parse + NER enrich
    mandatory_raw, preferred_raw = _parse_job_description(jd_text or "")
    req = jd_requirements_from_text(jd_text or "", mandatory_raw, preferred_raw)

    mandatory_norm = normalize_skills(mandatory_raw)
    preferred_norm = normalize_skills(preferred_raw)
    req["required_skills"]  = normalize_skills(req.get("required_skills", []))
    req["preferred_skills"] = normalize_skills(req.get("preferred_skills", []))

    job = Job(
        title=title,
        user_id=user_id,
        mandatory_skills=json.dumps(mandatory_norm),
        preferred_skills=json.dumps(preferred_norm),
    )
    with get_session() as sess:
        sess.add(job); sess.commit(); sess.refresh(job)

    return {
        "job_id": job.job_id, "title": job.title, "jd_text": jd_text,
        "mandatory": mandatory_norm, "preferred": preferred_norm,
        "requirements": req,
    }

@app.post("/jobs/{job_id}/upload")
async def upload_cv(
    job_id: int,
    files: List[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user),
):
    with get_session() as sess:
        job = _ensure_job_access(sess, job_id, current_user)

        created: List[Dict] = []
        for f in files:
            content = await f.read()
            text = pdf_to_text_robust(BytesIO(content))
            contacts = extract_contacts(text)
            name = guess_name(text)

            raw_skills = extract_skills_from_text(text, SKILLS_MASTER)
            skills = normalize_skills(raw_skills)

            cand_edu = extract_education(text)
            cand_years = extract_years_experience(text)

            score, decision, expl = score_candidate(
                job,
                candidate_skills=skills,
                cand_years=cand_years,
                req_edu=None,
                cand_edu=cand_edu,
                requirements=None,
            )

            cand = Candidate(
                job_id=job.job_id,
                name=name,
                email=contacts.get("email"),
                phone=contacts.get("phone"),
                professional_links=json.dumps(contacts.get("links", [])),
                extracted_skills=json.dumps(skills),
                match_score=score,
                decision=decision,
            )
            sess.add(cand); sess.commit(); sess.refresh(cand)

            created.append({
                "candidate_id": cand.candidate_id,
                "name": cand.name,
                "email": cand.email,
                "skills": skills,
                "education": cand_edu,
                "years_experience": cand_years,
                "score": score,
                "decision": decision,
                "explain": expl,
            })
    return {"created": created}

@app.get("/jobs/{job_id}/candidates")
def list_candidates(job_id: int, sort: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    with get_session() as sess:
        _ = _ensure_job_access(sess, job_id, current_user)  # ensure ownership in strict mode
        cands = sess.exec(select(Candidate).where(Candidate.job_id == job_id)).all()
    out = [{
        "candidate_id": c.candidate_id, "name": c.name, "email": c.email,
        "skills": json.loads(c.extracted_skills or "[]"),
        "score": c.match_score, "decision": c.decision,
    } for c in cands]
    if sort == "score_desc":
        out.sort(key=lambda x: (x["score"] is not None, x["score"]), reverse=True)
    return out

@app.get("/jobs/{job_id}/export.csv")
def export_candidates_csv(job_id: int, current_user: dict = Depends(get_current_user)):
    with get_session() as sess:
        _ = _ensure_job_access(sess, job_id, current_user)  # ensure ownership in strict mode
        cands = sess.exec(select(Candidate).where(Candidate.job_id == job_id)).all()
    buf = io.StringIO(); w = csv.writer(buf)
    w.writerow(["candidate_id","name","email","phone","score","decision","skills"])
    for c in cands:
        w.writerow([c.candidate_id, c.name or "", c.email or "", c.phone or "",
                    c.match_score if c.match_score is not None else "", c.decision or "",
                    ", ".join(json.loads(c.extracted_skills or "[]"))])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="job_{job_id}_candidates.csv"'}
    )
