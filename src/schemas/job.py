# src/schemas/job.py
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class JobListingRaw(BaseModel):
    source: str
    source_job_id: str
    job_url: str
    company_logo_url: Optional[str] = ""
    title_raw: str
    company_name_raw: Optional[str] = ""
    location_raw: Optional[str] = ""
    salary_raw: Optional[str] = ""
    experience_raw: Optional[str] = ""
    skills_raw: Optional[str] = ""
    posted_at_raw: Optional[str] = ""
    crawled_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    # --- CÁC TRƯỜNG TRACKING TRẠNG THÁI ---
    detail_status: str = "pending"        
    detail_attempts: int = 0                
    detail_http_status: Optional[int] = None
    detail_error: Optional[str] = ""        
    detail_crawled_at: Optional[str] = None 

class JobDetailRaw(BaseModel):
    detail_id: str
    source: str
    source_job_id: str
    job_url: str
    title_raw: str
    company_name_raw: Optional[str] = ""
    company_url: Optional[str] = ""
    company_size_raw: Optional[str] = ""
    company_location_raw: Optional[str] = ""
    industry_raw: Optional[str] = ""
    salary_raw: Optional[str] = ""
    experience_raw: Optional[str] = ""
    education_raw: Optional[str] = ""
    location_raw: Optional[str] = ""
    work_mode_raw: Optional[str] = ""
    employment_type_raw: Optional[str] = ""
    working_time_raw: Optional[str] = ""
    overview_raw: Optional[str] = ""
    responsibilities_raw: Optional[str] = ""
    requirements_raw: Optional[str] = ""
    benefits_raw: Optional[str] = ""
    required_skills_raw: Optional[str] = ""
    preferred_skills_raw: Optional[str] = ""
    published_at_raw: Optional[str] = ""
    updated_at_raw: Optional[str] = ""
    deadline_raw: Optional[str] = ""
    crawled_at: str = Field(default_factory=lambda: datetime.now().isoformat())
