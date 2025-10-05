# backend/extraction.py
from __future__ import annotations

import re
from io import BytesIO
from functools import lru_cache
from typing import Iterable, List, Tuple

import pdfplumber
from rapidfuzz import process, fuzz

# Optional spaCy for noun-chunks (used only if available)
try:
    import spacy
    _NLP = spacy.load("en_core_web_sm")
except Exception:
    _NLP = None

# ------------------------------ Regexes ---------------------------------
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(
    r"(?:\+?\d{1,3}[\s-]?)?(?:\(?\d{2,4}\)?[\s-]?)?\d(?:[\d\s-]{6,}\d)"
)  # tries to reduce accidental matches
URL_RE = re.compile(r"https?://[^\s)>\]}]+", re.I)

# Lines to ignore when guessing names
_NAME_SKIP = re.compile(
    r"^(curriculum vitae|resume|cv|profile|summary|contacts?)$",
    re.I
)

def _char_count(text: str) -> int:
    return sum(ch.isalnum() for ch in text or "")

# ------------------------------ PDF → Text ------------------------------
def pdf_to_text(pdf_bytes: BytesIO | bytes) -> str:
    """Primary text extraction via pdfplumber."""
    buf = BytesIO(pdf_bytes) if isinstance(pdf_bytes, bytes) else pdf_bytes
    text_pages: List[str] = []
    with pdfplumber.open(buf) as pdf:
        for p in pdf.pages:
            text_pages.append(p.extract_text() or "")
    return "\n".join(text_pages)

def pdf_to_text_robust(pdf_bytes: BytesIO | bytes, ocr_dpi: int = 200, max_pages: int = 30) -> str:
    """
    Try pdfplumber. If too little text (likely scanned), fallback to OCR using PyMuPDF + pytesseract.
    """
    base = pdf_to_text(pdf_bytes)
    if _char_count(base) > 180:
        return base

    # OCR fallback
    try:
        import fitz  # PyMuPDF
        from PIL import Image
        import pytesseract

        if isinstance(pdf_bytes, bytes):
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        else:
            doc = fitz.open(stream=pdf_bytes.getvalue(), filetype="pdf")

        ocr_texts: List[str] = []
        for i, page in enumerate(doc):
            if i >= max_pages:
                break
            pix = page.get_pixmap(dpi=ocr_dpi, alpha=False)  # no alpha → simpler PIL conversion
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            # If you have a non-English corpus, pass lang="eng+XXX"
            ocr_texts.append(pytesseract.image_to_string(img))
        ocr_text = "\n".join(ocr_texts)
        return ocr_text if _char_count(ocr_text) > _char_count(base) else base

    except Exception:
        # If OCR libs unavailable, return whatever we had
        return base

# ------------------------------ Contacts --------------------------------
def extract_contacts(text: str) -> dict:
    email = EMAIL_RE.search(text or "")
    phone = PHONE_RE.search(text or "")
    urls = URL_RE.findall(text or "")
    return {
        "email": email.group(0) if email else None,
        "phone": phone.group(0) if phone else None,
        "links": urls,
    }

# ------------------------------ Name Guess ------------------------------
def guess_name(text: str) -> str | None:
    """
    Heuristic first line name guess. If spaCy is available, try PERSON entities from the top lines.
    """
    if not text:
        return None

    # Try spaCy for PERSON near top of doc
    if _NLP:
        head = "\n".join(text.splitlines()[:25])
        doc = _NLP(head)
        persons = [ent.text.strip() for ent in doc.ents if ent.label_ == "PERSON" and 3 <= len(ent.text.strip()) <= 60]
        if persons:
            return persons[0]

    # Fallback: first non-empty line with ≥2 capitalized tokens and not a boilerplate header
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if _NAME_SKIP.match(line):
            continue
        tokens = line.split()
        caps = sum(1 for t in tokens if t[:1].isupper())
        if len(tokens) >= 2 and caps >= 2 and len(line) < 80:
            return line
    return None

# ------------------------------ Skills ----------------------------------
def _tokenize_for_ngrams(text_lower: str) -> List[str]:
    # Allow alphanum plus useful tech punctuation
    return re.findall(r"[a-z0-9+#\./-]+", text_lower)

def _generate_ngrams(tokens: List[str], n_min: int = 2, n_max: int = 3) -> List[str]:
    grams: List[str] = []
    for n in range(n_min, n_max + 1):
        for i in range(0, max(0, len(tokens) - n + 1)):
            grams.append(" ".join(tokens[i:i+n]))
    return grams

def _make_skill_pattern(skill: str) -> re.Pattern:
    """
    Build a robust regex that matches:
      - Whole words for alnum skills (with flexible whitespace in multi-word skills)
      - Non-word-bounded tech tokens (Node.js, C#, SAP2000) via lookarounds
    """
    skill = skill.strip()
    if not skill:
        return re.compile(r"^$")  # never matches

    # Replace spaces with \s* to allow minor whitespace variations
    skill_escaped = re.escape(skill).replace(r"\ ", r"\s*")

    # Alphanumeric with spaces → use word boundaries
    if re.fullmatch(r"[A-Za-z0-9\s]+", skill):
        return re.compile(rf"\b{skill_escaped}\b", re.I)

    # Otherwise use non-word lookarounds to avoid partial word matches
    return re.compile(rf"(?<!\w){skill_escaped}(?!\w)", re.I)

@lru_cache(maxsize=64)
def _compiled_skill_patterns(skills_master_tuple: Tuple[str, ...]) -> Tuple[Tuple[str, re.Pattern], ...]:
    return tuple((s, _make_skill_pattern(s)) for s in skills_master_tuple)

def _exact_matches(text: str, skills_master: List[str]) -> List[str]:
    patterns = _compiled_skill_patterns(tuple(skills_master))
    found = []
    for s, pat in patterns:
        if pat.search(text):
            found.append(s)
    return found

def extract_skills_from_text(
    text: str,
    skills_master: List[str],
    scorer_threshold: int = 78,
    use_spacy_noun_chunks: bool = True
) -> List[str]:
    """
    1) Exact regex matches against the skills master (handles multi-word and dotted skills).
    2) If sparse, fuzzy-match n-grams and (optionally) noun-chunks to recover phrasing variants.
    Returns a list of canonical skill strings from skills_master.
    """
    if not text:
        return []

    # 1) Exact (case-insensitive, boundary aware)
    exact = set(_exact_matches(text, skills_master))
    if exact:
        return sorted(exact)

    # 2) Fuzzy recovery path (for phrasing/spelling variants)
    text_lower = (text or "").lower()
    tokens = _tokenize_for_ngrams(text_lower)
    grams = _generate_ngrams(tokens, 2, 3)

    # Optional: add noun chunks (spaCy) into the candidate phrases
    if use_spacy_noun_chunks and _NLP:
        try:
            doc = _NLP(text)
            grams.extend([nc.text.lower().strip() for nc in doc.noun_chunks])
        except Exception:
            pass

    # Keep unique candidates, but avoid exploding size
    candidates = list({g for g in grams if 3 <= len(g) <= 50})
    if not candidates:
        candidates = tokens  # fallback to single tokens

    # RapidFuzz: choose best matches from skills_master for the candidate phrases
    # Reverse index: find which skills in the master are hit by any candidate
    hits = process.extract(
        candidates, skills_master, scorer=fuzz.QRatio, score_cutoff=scorer_threshold, limit=500
    )

    fuzzy_found = {skill for (skill, score, idx) in hits if isinstance(skill, str)}
    return sorted(fuzzy_found)
