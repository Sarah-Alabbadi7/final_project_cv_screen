# backend/scoring.py
import json
from typing import Dict, List, Tuple, Optional

def _pct(n: int, d: int) -> float:
    return 0.0 if not d else round(100.0 * n / d, 2)

def _clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))

def score_candidate(
    job,
    candidate_skills: List[str],
    cand_years: Optional[int] = None,
    req_edu: Optional[List[str]] = None,
    cand_edu: Optional[List[str]] = None,
    requirements: Optional[Dict] = None,
    accept_threshold: float = 60.0,          # works with the 2-skill band below
    enforce_mandatory_gate: bool = False,    # set True to hard-reject low mandatory coverage
    mandatory_min_coverage: float = 0.5,     # only used if enforce_mandatory_gate=True
) -> Tuple[float, str, Dict]:
    """
    Returns (score, decision, explanation_dict).

    Rule bands (skill matches counted on union of required+preferred):
      - 0 matches: Reject (score ~0–20)
      - 1 match  : Reject
      - 2 matches: Accept, low score (60–70)
      - 3 matches: Accept, mid score (75–85)
      - 4+ matches: Accept, high score (90–100)

    Education/experience add small bonuses/penalties so the score still reflects
    more than just count, but stays within the band you expect for the web UI.
    """

    # --- Determine the job skill sets (from requirements if present else from job) ---
    mandatory = json.loads(job.mandatory_skills or "[]")
    preferred = json.loads(job.preferred_skills or "[]")

    req = requirements or {}
    req_skills_list  = req.get("required_skills",  []) or mandatory
    pref_skills_list = req.get("preferred_skills", []) or preferred

    req_skills  = set(s.lower() for s in req_skills_list)
    pref_skills = set(s.lower() for s in pref_skills_list)
    cand_set    = set(s.lower() for s in (candidate_skills or []))

    # --- Optional HARD GATE on mandatory coverage (off by default) ---
    mandatory_cov_pct = 100.0
    if mandatory:
        matched_mand = sum(1 for m in mandatory if m.lower() in cand_set)
        mandatory_cov_pct = _pct(matched_mand, len(mandatory))
        if enforce_mandatory_gate:
            if (mandatory_cov_pct / 100.0) < max(0.0, min(1.0, mandatory_min_coverage)):
                expl = {
                    "reason": "Mandatory coverage below threshold",
                    "threshold": mandatory_min_coverage,
                    "mandatory_coverage_pct": mandatory_cov_pct,
                    "missing_mandatory": [m for m in mandatory if m.lower() not in cand_set],
                    "matched_mandatory": [m for m in mandatory if m.lower() in cand_set],
                }
                return 0.0, "Reject (insufficient mandatory coverage)", expl

    # --- Matches & counts ---
    matched_req_set  = req_skills  & cand_set
    matched_pref_set = pref_skills & cand_set
    matched_all_set  = matched_req_set | matched_pref_set

    matched_count     = len(matched_all_set)
    total_declared    = len(req_skills | pref_skills) or 1  # avoid div by zero
    req_overlap_pct   = _pct(len(matched_req_set),  len(req_skills))  if req_skills  else 0.0
    pref_overlap_pct  = _pct(len(matched_pref_set), len(pref_skills)) if pref_skills else 0.0
    overall_overlap   = _pct(matched_count, total_declared)

    # --- Education & experience signals (small effect only) ---
    req_edu_list  = req.get("required_education", req_edu or [])
    cand_edu_list = cand_edu or []
    edu_match = bool(
        (not req_edu_list) or any(e.lower() in [c.lower() for c in cand_edu_list] for e in req_edu_list)
    )

    min_years = req.get("min_years_experience", None)
    exp_bonus = 0.0
    if min_years is None:
        exp_bonus = 0.0
    elif cand_years is None:
        exp_bonus = 0.0   # unknown → neutral
    else:
        if cand_years >= int(min_years):
            exp_bonus = 2.0   # small bump if meeting/exceeding req
        else:
            exp_bonus = -4.0  # small penalty if below

    edu_bonus = 2.0 if edu_match else 0.0

    # --- Banded scoring per your rules ---
    # We compute a base score from the band and nudge it slightly by overlaps/bonuses.
    if matched_count == 0:
        base = 10.0 if overall_overlap > 0 else 0.0
        decision = "Reject"
    elif matched_count == 1:
        base = 35.0   # still Reject by requirement
        decision = "Reject"
    elif matched_count == 2:
        # 60–70: favor required matches within the band
        if len(matched_req_set) == 2:
            base = 70.0
        elif len(matched_req_set) == 1:
            base = 65.0
        else:
            base = 60.0
        decision = "Accept"
    elif matched_count == 3:
        # 75–85: bias by how many are required
        base = 75.0 + min(10.0, 3.0 * len(matched_req_set) + 2.0 * len(matched_pref_set))
        base = min(base, 85.0)
        decision = "Accept"
    else:  # matched_count >= 4
        # 90–100: ramp a little with extra matches, cap at 100
        base = 90.0 + min(10.0, (matched_count - 4) * 2.5)  # 4→90, 5→92.5, 6→95, 7→97.5, 8+→100
        # Tiny push if most of them are required
        req_ratio = (len(matched_req_set) / matched_count) if matched_count else 0.0
        base += 2.0 * req_ratio   # up to +2
        decision = "Accept"

    # Small, capped adjustments so we stay in the intended band
    # (we apply a micro-overlap nudge and the edu/exp bonuses)
    micro_nudge = 0.05 * overall_overlap   # up to +5 based on overall coverage
    score = _clamp(base + micro_nudge + edu_bonus + exp_bonus)

    # Ensure decision respects the accept_threshold AND your band rules
    if matched_count <= 1:
        decision = "Reject"
    else:
        decision = "Accept" if score >= accept_threshold else "Reject"

    # --- Explanation payload for UI/inspection ---
    expl = {
        "matched_count": matched_count,
        "total_declared_skills": total_declared,
        "matched_required_skills": sorted({s for s in req_skills if s in matched_all_set}),
        "matched_preferred_skills": sorted({s for s in pref_skills if s in matched_all_set}),
        "missing_required_skills": sorted({s for s in req_skills if s not in matched_all_set}),
        "missing_preferred_skills": sorted({s for s in pref_skills if s not in matched_all_set}),
        "mandatory_coverage_pct": mandatory_cov_pct,
        "required_overlap_pct": req_overlap_pct,
        "preferred_overlap_pct": pref_overlap_pct,
        "overall_overlap_pct": overall_overlap,
        "education_required": req_edu_list,
        "education_candidate": cand_edu_list,
        "education_match": edu_match,
        "min_years_experience": min_years,
        "candidate_years_experience": cand_years,
        "score_components": {
            "base_from_band": base,
            "edu_bonus": edu_bonus,
            "exp_bonus": exp_bonus,
            "micro_overlap_nudge": round(micro_nudge, 2),
        },
        "accept_threshold": accept_threshold,
        "enforce_mandatory_gate": enforce_mandatory_gate,
        "mandatory_min_coverage": mandatory_min_coverage,
    }

    return round(score, 2), decision, expl

