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
    Calculate a transparent, platform-specific ATS readiness estimate.
    This is not a universal ATS vendor score or job-fit score. Job matching is
    calculated separately when the student supplies an actual job description.
    Returns (0-100 score, evidence-backed checks).
    """
    checks = []
    total_score = 0

    def add_check(name: str, score: int, maximum: int, message: str, passed: bool):
        nonlocal total_score
        score = max(0, min(maximum, int(score)))
        total_score += score
        checks.append({"check_name": name, "passed": passed, "score": score,
                       "max_score": maximum, "message": message})

    # Contact parse evidence (15). Name, email and phone are independently
    # verifiable; location is intentionally excluded as it is often optional.
    contact = sum(5 for key in ("full_name", "email", "phone") if parsed_data.get(key))
    add_check("Contact details", contact, 15,
              f"Name: {'found' if parsed_data.get('full_name') else 'not detected'}; email: {'found' if parsed_data.get('email') else 'not detected'}; phone: {'found' if parsed_data.get('phone') else 'not detected'}.",
              contact >= 10)

    # Recognized resume sections (25). Projects are useful but not required
    # when work experience is present, so use 5 standard content sections.
    headings = parsed_data.get("sections_detected") or {}
    def has_content(value):
        return any(bool(items) for items in value.values()) if isinstance(value, dict) else bool(value)
    detected = {
        "summary": bool(headings.get("summary") or parsed_data.get("summary")),
        "skills": bool(headings.get("skills") or has_content(parsed_data.get("skills"))),
        "education": bool(headings.get("education") or parsed_data.get("education")),
        "experience": bool(headings.get("experience") or parsed_data.get("experience")),
        "projects": bool(headings.get("projects") or parsed_data.get("projects")),
    }
    # Experience and projects are alternatives: a student can demonstrate work
    # through either. Summary is useful but is not a parser requirement.
    section_score = (3 * detected["summary"] + 5 * detected["skills"]
                     + 4 * detected["education"] + 13 * (detected["experience"] or detected["projects"]))
    visible = [name for name, present in detected.items() if present]
    add_check("Recognized sections", section_score, 25,
              f"Recognized: {', '.join(visible) if visible else 'no standard sections'}. Experience and projects count as alternative evidence.",
              section_score >= 17)

    # Relevant content breadth without the old arbitrary reward for listing
    # ever more skills. This is not job keyword matching.
    skill_groups = parsed_data.get("skills") or {}
    skills = [str(item).strip() for values in skill_groups.values() if isinstance(values, list) for item in values if str(item).strip()]
    skill_count = len({skill.casefold() for skill in skills})
    skill_score = min(15, skill_count * 3)
    add_check("Explicit skills list", skill_score, 15,
              f"Parsed {skill_count} distinct items from the skills section. Skills mentioned only in project prose are not counted here.",
              skill_count >= 3)

    quality = parsed_data.get("document_quality") or {}
    chars = quality.get("characters_extracted", len(parsed_data.get("raw_text", "")))
    word_count = quality.get("word_count", len(re.findall(r"\b\w+\b", parsed_data.get("raw_text", ""))))
    # This component measures analyzable text volume only; it makes no visual
    # layout claim. Short resumes are not automatically penalized as bad resumes.
    extraction_score = 20 if quality.get("has_text_layer", bool(chars)) and word_count >= 100 else min(20, round(word_count / 100 * 20))
    if not quality.get("has_text_layer", bool(chars)):
        extraction_score = 0
    format_message = f"Extracted {word_count} words ({chars} characters). Text volume supports analysis; visual layout is not assessed."
    add_check("Text available for analysis", extraction_score, 20, format_message, word_count >= 100)

    # Evidence in experience/project bullets: role details and measurable
    # outcomes are signals, not claims about an employer's ranking model.
    entries = (parsed_data.get("experience") or []) + (parsed_data.get("projects") or [])
    bullets = [str(point) for entry in entries for point in (entry.get("key_points") or [])]
    quantified = sum(1 for point in bullets if re.search(r"\b\d+(?:\.\d+)?\s*(?:%|x|users?|customers?|hours?|days?|ms|seconds?|\+)?\b", point, re.I))
    dated = sum(1 for entry in entries if entry.get("date"))
    evidence_score = min(10, len(entries) * 5) + min(10, len(bullets) * 2) + min(5, quantified)
    add_check("Experience and project details", evidence_score, 25,
              f"Parsed {len(entries)} entries, {len(bullets)} detail bullets, {dated} date ranges and {quantified} quantified outcomes.",
              bool(entries) and bool(bullets))

    return min(100, total_score), checks


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
