# ─── Collection name constants ────────────────────────────────────────────────
# Single source of truth for every MongoDB collection name used in the platform.

USERS                      = "users"
STUDENT_PROFILES           = "student_profiles"
RECRUITER_PROFILES         = "recruiter_profiles"
COMPANIES                  = "companies"

RESUMES                    = "resumes"
RESUME_VERSIONS            = "resume_versions"
RESUME_ANALYSES            = "resume_analyses"
RESUME_IMPROVEMENTS        = "resume_improvements"

SKILLS                     = "skills"
STUDENT_SKILLS             = "student_skills"

JOBS                       = "jobs"
JOB_MATCHES                = "job_matches"

APPLICATIONS               = "applications"
APPLICATION_EVENTS         = "application_events"
APPLICATION_NOTES          = "application_notes"

SCREENINGS                 = "screenings"

INTERVIEWS                 = "interviews"
MOCK_INTERVIEWS            = "mock_interviews"
MOCK_INTERVIEW_ANSWERS     = "mock_interview_answers"
MOCK_INTERVIEW_EVALUATIONS = "mock_interview_evaluations"

ASSESSMENTS                = "assessments"
ASSESSMENT_QUESTIONS       = "assessment_questions"
ASSESSMENT_ATTEMPTS        = "assessment_attempts"

ROADMAPS                   = "roadmaps"

NOTIFICATIONS              = "notifications"
ACTIVITIES                 = "activities"
CAREER_READINESS_HISTORY   = "career_readiness_history"

JOB_REPORTS                = "job_reports"
AUDIT_LOGS                 = "audit_logs"

# Aliases for backward compatibility
USERS_COLLECTION = USERS
USER_PROFILES_COLLECTION = STUDENT_PROFILES
RESUMES_COLLECTION = RESUMES
RESUME_ANALYSES_COLLECTION = RESUME_ANALYSES
JOBS_COLLECTION = JOBS
APPLICATIONS_COLLECTION = APPLICATIONS
INTERVIEWS_COLLECTION = INTERVIEWS
ASSESSMENTS_COLLECTION = ASSESSMENTS
NOTIFICATIONS_COLLECTION = NOTIFICATIONS
ANALYTICS_EVENTS_COLLECTION = ACTIVITIES
ROADMAPS_COLLECTION = ROADMAPS
RECOMMENDATIONS_COLLECTION = "recommendations"
CANDIDATES_COLLECTION = "candidates"
JOB_MATCHES_COLLECTION = JOB_MATCHES
SKILL_ASSESSMENTS_COLLECTION = ASSESSMENT_ATTEMPTS
