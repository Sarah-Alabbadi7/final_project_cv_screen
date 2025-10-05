# backend/nlp.py
from __future__ import annotations

import re
from typing import List, Dict, Optional

# ------------------------- Optional spaCy loading -------------------------
try:
    import spacy
    nlp = spacy.load("en_core_web_sm")
except Exception:
    nlp = None  # graceful fallback when spaCy/model is not present

# ------------------------- Skill Synonyms / Canonicals -------------------
# Map lowercased variants -> Canonical skill names (case-sensitive targets)
_SKILL_ALIASES: Dict[str, str] = {
    # Cloud
    "amazon web services": "AWS",
    "aws cloud": "AWS",
    "microsoft azure": "Azure",
    "google cloud": "GCP",
    "google cloud platform": "GCP",

    # Dev / DevOps
    "nodejs": "Node.js",
    "node js": "Node.js",
    "ci cd": "CI/CD",
    "cicd": "CI/CD",
    "continuous integration": "CI/CD",
    "continuous delivery": "CI/CD",
    "git version control": "Git",

    # Web / FE
    "js": "JavaScript",
    "reactjs": "React",
    "react js": "React",

    # Data / ML
    "sklearn": "scikit-learn",
    "scikit learn": "scikit-learn",
    "np": "NumPy",
    "pandas library": "Pandas",
    "tf": "TensorFlow",
    "torch": "PyTorch",
    "pytorch": "PyTorch",

    # Analytics / BI / Finance
    "ms excel": "Excel",
    "microsoft excel": "Excel",
    "powerbi": "Power BI",
    "ga": "Google Analytics",
    "ga4": "Google Analytics",
    "google analytics 4": "Google Analytics",
    "qb": "QuickBooks",
    "quickbooks online": "QuickBooks",
    "sap erp": "SAP",
    "sap business": "SAP",
    "financial reporting": "Financial Reporting",

    # CAD / CAE
    "auto cad": "AutoCAD",
    "autocad/cad": "AutoCAD",
    "cad/cam": "CAD",
    "solid works": "SolidWorks",
    "ansys workbench": "ANSYS",
    "sap 2000": "SAP2000",

    # PCB / EDA
    "pcb": "PCB Design",
    "altium": "Altium Designer",
    "kicad": "KiCad",

    # Design / Creative
    "photoshop": "Adobe Photoshop",
    "illustrator": "Adobe Illustrator",
    "premiere": "Adobe Premiere Pro",
    "after effects": "Adobe After Effects",
    "sketch up": "SketchUp",

    # Education / Classroom
    "ppt": "Microsoft PowerPoint",
    "google classroom app": "Google Classroom",
    "class dojo": "ClassDojo",

    # Healthcare
    "intensive care unit": "ICU",
    "clinical judgement": "Clinical Judgment",
}

# These should keep their exact casing if produced directly
_PRESERVE_CASE = {
    "AWS", "GCP", "CI/CD", "SQL", "CAD", "PLC", "RN", "ICU",
}

def _clean(s: str) -> str:
    s = (s or "").strip()
    # normalize common dashes and spacing
    s = s.replace("–", "-").replace("—", "-")
    s = re.sub(r"\s+", " ", s)
    return s

def normalize_skill(s: str) -> str:
    """
    Canonicalize a single skill string using aliases and light casing rules.
    """
    if not s:
        return ""
    raw = _clean(s)
    low = raw.lower()
    if low in _SKILL_ALIASES:
        return _SKILL_ALIASES[low]

    # Preserve acronyms/exact forms
    if raw.upper() in _PRESERVE_CASE:
        return raw.upper()
    if raw in _PRESERVE_CASE:
        return raw

    # Special case Node.js exact form
    if low in {"node.js", "nodejs", "node js"}:
        return "Node.js"

    # Default to title case, but keep inner punctuation as-is
    # e.g., "project management", "adobe premiere pro"
    # Preserve casing for known dotted/brand tokens
    tokens = [t for t in re.split(r"(\s+)", raw)]  # keep whitespace
    out = []
    for t in tokens:
        if not t.strip():
            out.append(t)
            continue
        if t.lower() in {"node.js", "nodejs", "ci/cd"}:
            out.append(_SKILL_ALIASES.get(t.lower(), t))
        elif re.fullmatch(r"[A-Za-z]+", t):
            out.append(t.capitalize())
        else:
            # Mixed tokens like "PowerPoint", "SAP2000", "AutoCAD"
            # If it's alnum+punct, lightly title-case alphabetic parts
            out.append(t if any(ch.isupper() for ch in t) else t.title())
    cand = "".join(out).strip()

    # Final polish for known canonical brands
    cand = re.sub(r"\bJavascript\b", "JavaScript", cand)
    cand = re.sub(r"\bPower Bi\b", "Power BI", cand)
    cand = re.sub(r"\bMs Excel\b", "Excel", cand)
    cand = re.sub(r"\bAutocad\b", "AutoCAD", cand)
    cand = re.sub(r"\bSap2000\b", "SAP2000", cand)
    return cand

def normalize_skills(skills: List[str]) -> List[str]:
    """
    Map variants to canonical skills and deduplicate (case-insensitive).
    """
    out: List[str] = []
    seen = set()
    for s in skills or []:
        c = normalize_skill(s)
        if not c:
            continue
        key = c.lower()
        if key not in seen:
            seen.add(key)
            out.append(c)
    return out

# ------------------------- Years of Experience ---------------------------
# Support formats:
# - "3-5 years", "3 – 5 years", "3 to 5 years"
# - "5+ years", "5 yrs+", "at least 4 years", "minimum 4 years"
# - "7 years experience", "7 yrs exp"
_RANGE_PAT = re.compile(
    r"\b(?P<a>\d{1,2})\s*(?:-|–|—|to)\s*(?P<b>\d{1,2})\s*(?:\+?\s*)?(?:years?|yrs?)\b",
    re.I,
)
_MIN_PAT = re.compile(
    r"\b(?:min(?:imum)?|at\s+least)\s*(?P<n>\d{1,2})\s*(?:\+?\s*)?(?:years?|yrs?)\b",
    re.I,
)
_PLUS_PAT = re.compile(
    r"\b(?P<n>\d{1,2})\s*\+\s*(?:years?|yrs?)\b",
    re.I,
)
_SIMPLE_PAT = re.compile(
    r"\b(?P<n>\d{1,2})\s*(?:years?|yrs?)\s*(?:of\s+)?(?:experience|exp)?\b",
    re.I,
)

def extract_years_experience(text: str) -> Optional[int]:
    if not text:
        return None
    t = " " + text + " "  # padding to help regex word boundaries

    # Ranges: take the upper bound (more conservative for capability)
    m = _RANGE_PAT.search(t)
    if m:
        try:
            a = int(m.group("a"))
            b = int(m.group("b"))
            return max(a, b)
        except Exception:
            pass

    # "minimum 4 years" / "at least 4 years"
    m = _MIN_PAT.search(t)
    if m:
        try:
            return int(m.group("n"))
        except Exception:
            pass

    # "5+ years"
    m = _PLUS_PAT.search(t)
    if m:
        try:
            return int(m.group("n"))
        except Exception:
            pass

    # "7 years (experience/exp)" or just "7 years"
    m = _SIMPLE_PAT.search(t)
    if m:
        try:
            return int(m.group("n"))
        except Exception:
            pass

    return None

# ------------------------------ Education --------------------------------
# Map many variations to canonical degree labels
_DEGREE_CANON: Dict[str, List[str]] = {
    "BSc": ["b.sc", "bsc", "bs", "b.s", "bachelor of science", "bachelor’s of science", "bachelors of science"],
    "BA": ["ba", "b.a", "bachelor of arts", "bachelor’s of arts", "bachelors of arts"],
    "BEng": ["beng", "b.eng", "bachelor of engineering"],
    "BE": ["be"],
    "BPharm": ["bpharm", "b.pharm", "bachelor of pharmacy"],
    "MSc": ["msc", "m.sc", "ms", "m.s", "master of science", "master’s of science", "masters of science"],
    "MA": ["ma", "m.a", "master of arts", "master’s of arts", "masters of arts"],
    "MEng": ["meng", "m.eng", "master of engineering"],
    "MBA": ["mba", "master of business administration"],
    "PhD": ["phd", "ph.d", "doctorate", "d.phil", "doctor of philosophy"],
    "MD":  ["md", "doctor of medicine"],
    "PharmD": ["pharmd", "doctor of pharmacy"],
    "RN": ["registered nurse", r"\brn\b"],
}

# Pre-compile a finder regex for all variants
_deg_patterns: List[re.Pattern] = []
for canon, variants in _DEGREE_CANON.items():
    for v in variants:
        # treat entries with \b literally as regex; else escape and word-boundary wrap
        if r"\b" in v:
            pat = re.compile(v, re.I)
        else:
            pat = re.compile(r"\b" + re.escape(v) + r"\b", re.I)
        _deg_patterns.append((canon, pat))

def extract_education(text: str) -> List[str]:
    """
    Return a list of canonical degree labels found in the text, e.g. ["BSc", "MBA"].
    """
    if not text:
        return []
    found = []
    seen = set()
    for canon, pat in _deg_patterns:
        if pat.search(text):
            if canon not in seen:
                seen.add(canon)
                found.append(canon)
    return found

# ------------------------------ Job Titles --------------------------------
_TITLE_WORDS = [
    "engineer", "developer", "scientist", "analyst", "manager",
    "consultant", "architect", "specialist", "lead", "head",
    "designer", "teacher", "nurse", "pharmacist", "coordinator",
]

def extract_job_titles(text: str) -> List[str]:
    """
    Very naive: collect lines that contain a known title word.
    """
    titles = set()
    for line in (text or "").splitlines():
        l = line.strip()
        if not l:
            continue
        low = l.lower()
        if any(w in low for w in _TITLE_WORDS) and 3 <= len(l) <= 80:
            titles.add(l)
    return list(titles)

# ------------------------------ Noun Chunks --------------------------------
def spacy_chunks(text: str) -> List[str]:
    """
    Return SpaCy noun chunks if spaCy is available; otherwise empty list.
    """
    if not nlp or not text:
        return []
    doc = nlp(text)
    chunks = []
    for nc in doc.noun_chunks:
        s = nc.text.strip()
        if 2 <= len(s) <= 40 and any(ch.isalpha() for ch in s):
            chunks.append(s)
    return chunks

# ------------------------------ JD Requirements ----------------------------
def jd_requirements_from_text(
    jd_text: str,
    fallback_mandatory: List[str],
    fallback_preferred: List[str],
) -> Dict:
    """
    Extract structured requirements from JD:
      - required skills (fallback lists + noun chunks if available)
      - required education (regex)
      - minimum years of experience (regex)
    """
    jd_text = jd_text or ""
    req_edu = extract_education(jd_text)
    req_years = extract_years_experience(jd_text)

    # Expand skills from noun chunks (when spaCy is available), then normalize
    chunk_skills = spacy_chunks(jd_text) if nlp else []
    # Merge fallbacks + chunks, small cap & dedupe, then normalize
    all_required = normalize_skills(list({*(fallback_mandatory or []), *chunk_skills}))
    all_preferred = normalize_skills(list({*(fallback_preferred or [])}))

    # Keep tidy
    all_required = all_required[:30]
    all_preferred = all_preferred[:30]

    return {
        "required_skills": all_required,
        "preferred_skills": all_preferred,
        "required_education": req_edu,      # list of canonical degrees
        "min_years_experience": req_years,  # int or None
    }
