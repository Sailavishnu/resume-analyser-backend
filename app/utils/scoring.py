"""
Deterministic scoring algorithms for resume analysis, ATS checks, and skill assessment.
"""
import re
from typing import Any


# ─── Resume Health Scoring ────────────────────────────────────────────────────

def calculate_resume_health_score(parsed_data: dict) -> tuple[int, dict]:
    """
    Calculate overall resume health score and section breakdown.
    Returns (overall_score, section_scores_dict).
    """
    section_scores = {}
    
    # Skills Score (0-100)
    skills = parsed_data.get("skills", {})
    total_skills = sum(len(skills.get(cat, [])) for cat in skills.keys())
    section_scores["skills"] = min(100, total_skills * 8)  # 12+ skills = 96+
    
    # Experience Score (0-100)
    experience = parsed_data.get("experience", [])
    exp_score = 0
    for exp in experience:
        if exp.get("key_points"):
            exp_score += 30  # Has bullet points
        if exp.get("skills"):
            exp_score += 20  # Mentions tech skills
        exp_score += 10      # Just having experience
    section_scores["experience"] = min(100, exp_score)
    
    # Projects Score (0-100)
    projects = parsed_data.get("projects", [])
    proj_score = 0
    for proj in projects:
        if proj.get("tech_stack"):
            proj_score += 25
        if proj.get("impact"):
            proj_score += 25
        proj_score += 10
    section_scores["projects"] = min(100, proj_score)
    
    # Education Score (0-100)
    education = parsed_data.get("education", [])
    section_scores["education"] = 90 if education else 40
    
    # Formatting Score (based on structure)
    format_score = 70  # Default decent
    if parsed_data.get("summary"):
        format_score += 10
    if parsed_data.get("phone"):
        format_score += 10
    if parsed_data.get("email"):
        format_score += 10
    section_scores["formatting"] = format_score
    
    # Keywords Score (skill density)
    section_scores["keywords"] = min(100, total_skills * 6)
    
    # Impact Score (quantified achievements)
    impact_score = 50
    summary_text = parsed_data.get("summary", "")
    if re.search(r'\d+\+?\s*(users?|students?|projects?)', summary_text, re.IGNORECASE):
        impact_score += 30
    for exp in experience:
        for point in exp.get("key_points", []):
            if re.search(r'\d+%|\d+\+', point):
                impact_score += 10
                break
    section_scores["impact"] = min(100, impact_score)
    
    # Completeness Score
    completeness = 0
    required_sections = ["summary", "experience", "projects", "education", "skills"]
    for section in required_sections:
        if parsed_data.get(section):
            completeness += 20
    section_scores["completeness"] = completeness
    
    # Overall score (weighted average)
    overall = int(
        section_scores["skills"] * 0.20 +
        section_scores["experience"] * 0.25 +
        section_scores["projects"] * 0.20 +
        section_scores["education"] * 0.10 +
        section_scores["formatting"] * 0.10 +
        section_scores["keywords"] * 0.10 +
        section_scores["completeness"] * 0.05
    )
    
    return overall, section_scores


# ─── ATS Scoring ──────────────────────────────────────────────────────────────

def calculate_ats_score(parsed_data: dict) -> tuple[int, list[dict]]:
    """
    Calculate ATS compatibility score and detailed check results.
    Returns (overall_score, checks_list).
    """
    checks = []
    total_score = 0
    
    # Contact Information (20 points)
    contact_score = 0
    if parsed_data.get("email"):
        contact_score += 7
        checks.append({
            "check_name": "Email Present",
            "passed": True,
            "score": 7,
            "message": "Email address found"
        })
    else:
        checks.append({
            "check_name": "Email Present",
            "passed": False,
            "score": 0,
            "message": "Email address missing"
        })
    
    if parsed_data.get("phone"):
        contact_score += 7
        checks.append({
            "check_name": "Phone Present",
            "passed": True,
            "score": 7,
            "message": "Phone number found"
        })
    
    if parsed_data.get("location"):
        contact_score += 6
        checks.append({
            "check_name": "Location Present",
            "passed": True,
            "score": 6,
            "message": "Location information found"
        })
    
    total_score += contact_score
    
    # Section Detection (25 points)
    required_sections = ["summary", "experience", "projects", "education", "skills"]
    detected = sum(1 for s in required_sections if parsed_data.get(s))
    section_score = int((detected / len(required_sections)) * 25)
    total_score += section_score
    
    checks.append({
        "check_name": "Section Detection",
        "passed": detected >= 4,
        "score": section_score,
        "message": f"{detected}/{len(required_sections)} standard sections detected"
    })
    
    # Keyword Density (20 points)
    skills = parsed_data.get("skills", {})
    total_skills = sum(len(skills.get(cat, [])) for cat in skills.keys())
    keyword_score = min(20, total_skills * 2)
    total_score += keyword_score
    
    checks.append({
        "check_name": "Keyword Density",
        "passed": total_skills >= 8,
        "score": keyword_score,
        "message": f"{total_skills} technical skills/keywords identified"
    })
    
    # Formatting & Readability (20 points)
    format_score = 15  # Base score for clean parsing
    if parsed_data.get("summary") and len(parsed_data["summary"]) > 50:
        format_score += 5
    total_score += format_score
    
    checks.append({
        "check_name": "Formatting & Structure",
        "passed": format_score >= 18,
        "score": format_score,
        "message": "Resume structure is ATS-friendly"
    })
    
    # Experience Detail (15 points)
    experience = parsed_data.get("experience", [])
    exp_detail_score = 0
    for exp in experience:
        if exp.get("key_points") and len(exp["key_points"]) >= 2:
            exp_detail_score += 8
        if exp.get("company") and exp.get("position"):
            exp_detail_score += 4
    exp_detail_score = min(15, exp_detail_score)
    total_score += exp_detail_score
    
    checks.append({
        "check_name": "Experience Detail",
        "passed": exp_detail_score >= 10,
        "score": exp_detail_score,
        "message": f"Experience entries have sufficient detail"
    })
    
    return total_score, checks


# ─── Career Readiness Calculation ─────────────────────────────────────────────

def calculate_career_readiness(
    resume_health: int,
    ats_score: int,
    total_assessments: int,
    avg_assessment_score: float,
    total_applications: int,
    interview_count: int,
    profile_completion: int,
) -> int:
    """
    Calculate overall career readiness score from multiple factors.
    """
    # Weights
    weights = {
        "resume": 0.25,
        "ats": 0.15,
        "assessments": 0.20,
        "applications": 0.15,
        "interviews": 0.15,
        "profile": 0.10,
    }
    
    # Normalize assessment factor
    assessment_factor = min(100, avg_assessment_score + (total_assessments * 5))
    
    # Normalize application factor
    application_factor = min(100, (total_applications * 20) + (interview_count * 15))
    
    # Calculate weighted score
    career_readiness = int(
        resume_health * weights["resume"] +
        ats_score * weights["ats"] +
        assessment_factor * weights["assessments"] +
        application_factor * weights["applications"] +
        min(100, interview_count * 25) * weights["interviews"] +
        profile_completion * weights["profile"]
    )
    
    return min(100, career_readiness)


# ─── Skill Gap Analysis ───────────────────────────────────────────────────────

def analyze_skill_gap(resume_skills: list[str], job_required: list[str], job_preferred: list[str] = None) -> dict:
    """
    Analyze skill overlap between resume and job requirements.
    Returns categorized skill matches.
    """
    if job_preferred is None:
        job_preferred = []
    
    resume_skills_lower = [s.lower() for s in resume_skills]
    required_lower = [s.lower() for s in job_required]
    preferred_lower = [s.lower() for s in job_preferred]
    
    matched_skills = []
    missing_skills = []
    partial_skills = []
    
    # Check required skills
    for skill in job_required:
        skill_lower = skill.lower()
        if skill_lower in resume_skills_lower:
            matched_skills.append(skill)
        else:
            # Check for partial matches (e.g., "React" in "React.js")
            partial_match = False
            for resume_skill in resume_skills_lower:
                if skill_lower in resume_skill or resume_skill in skill_lower:
                    partial_skills.append(skill)
                    partial_match = True
                    break
            if not partial_match:
                missing_skills.append(skill)
    
    # Check preferred skills (add to missing if not found)
    for skill in job_preferred:
        skill_lower = skill.lower()
        if skill_lower not in resume_skills_lower:
            if skill not in missing_skills:  # Avoid duplicates
                missing_skills.append(skill)
    
    return {
        "matched_skills": matched_skills,
        "partial_skills": partial_skills,
        "missing_skills": missing_skills,
        "skill_coverage": len(matched_skills) / max(1, len(job_required)) * 100
    }