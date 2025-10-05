# backend/models.py
from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
import json

class Job(SQLModel, table=True):
    job_id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[str] = Field(default="default_user", index=True)
    title: str
    mandatory_skills: str  # JSON encoded list
    preferred_skills: str  # JSON encoded list
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Candidate(SQLModel, table=True):
    candidate_id: Optional[int] = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="job.job_id")
    name: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    professional_links: Optional[str]  # JSON string list
    extracted_skills: str  # JSON encoded list
    match_score: float = 0.0
    decision: str = "Pending"
    submitted_at: datetime = Field(default_factory=datetime.utcnow)
