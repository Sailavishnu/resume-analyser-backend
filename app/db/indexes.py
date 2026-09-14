"""
Index creation for all collections.
Safe to run multiple times — pymongo ignores already-existing indexes.
Run via:  python scripts/create_indexes.py
"""

from pymongo import ASCENDING, DESCENDING, IndexModel
from pymongo.database import Database
from app.db import collections as C


def create_all_indexes(db: Database) -> None:
    # ── users ─────────────────────────────────────────────────────────────────
    db[C.USERS].create_indexes([
        IndexModel([("email", ASCENDING)], unique=True),
        IndexModel([("role", ASCENDING)]),
        IndexModel([("is_active", ASCENDING)]),
    ])

    # ── student_profiles ──────────────────────────────────────────────────────
    db[C.STUDENT_PROFILES].create_indexes([
        IndexModel([("user_id", ASCENDING)], unique=True),
    ])

    # ── recruiter_profiles ────────────────────────────────────────────────────
    db[C.RECRUITER_PROFILES].create_indexes([
        IndexModel([("user_id", ASCENDING)], unique=True),
        IndexModel([("company_id", ASCENDING)]),
    ])

    # ── companies ─────────────────────────────────────────────────────────────
    db[C.COMPANIES].create_indexes([
        IndexModel([("name", ASCENDING)], unique=True),
    ])

    # ── resumes ───────────────────────────────────────────────────────────────
    db[C.RESUMES].create_indexes([
        IndexModel([("student_id", ASCENDING)]),
        IndexModel([("student_id", ASCENDING), ("is_current", ASCENDING)]),
        IndexModel([("created_at", DESCENDING)]),
    ])

    # ── resume_analyses ───────────────────────────────────────────────────────
    db[C.RESUME_ANALYSES].create_indexes([
        IndexModel([("resume_id", ASCENDING)]),
        IndexModel([("created_at", DESCENDING)]),
    ])

    # ── resume_improvements ───────────────────────────────────────────────────
    db[C.RESUME_IMPROVEMENTS].create_indexes([
        IndexModel([("resume_id", ASCENDING)]),
        IndexModel([("student_id", ASCENDING)]),
    ])

    # ── resume_versions ───────────────────────────────────────────────────────
    db[C.RESUME_VERSIONS].create_indexes([
        IndexModel([("resume_id", ASCENDING)]),
        IndexModel([("resume_id", ASCENDING), ("version_number", DESCENDING)]),
    ])

    # ── skills ────────────────────────────────────────────────────────────────
    db[C.SKILLS].create_indexes([
        IndexModel([("name", ASCENDING)], unique=True),
        IndexModel([("category", ASCENDING)]),
    ])

    # ── student_skills ────────────────────────────────────────────────────────
    db[C.STUDENT_SKILLS].create_indexes([
        IndexModel([("student_id", ASCENDING)]),
        IndexModel([("student_id", ASCENDING), ("skill_id", ASCENDING)], unique=True),
    ])

    # ── jobs ──────────────────────────────────────────────────────────────────
    db[C.JOBS].create_indexes([
        IndexModel([("company_id", ASCENDING)]),
        IndexModel([("created_by", ASCENDING)]),
        IndexModel([("status", ASCENDING)]),
        IndexModel([("title", ASCENDING)]),
        IndexModel([("created_at", DESCENDING)]),
        IndexModel([("required_skills", ASCENDING)]),
    ])

    # ── job_matches ───────────────────────────────────────────────────────────
    db[C.JOB_MATCHES].create_indexes([
        IndexModel([("student_id", ASCENDING)]),
        IndexModel([("job_id", ASCENDING)]),
        IndexModel([("student_id", ASCENDING), ("job_id", ASCENDING)]),
        IndexModel([("resume_id", ASCENDING)]),
    ])

    # ── applications ──────────────────────────────────────────────────────────
    db[C.APPLICATIONS].create_indexes([
        IndexModel([("student_id", ASCENDING)]),
        IndexModel([("job_id", ASCENDING)]),
        IndexModel([("status", ASCENDING)]),
        IndexModel([("applied_at", DESCENDING)]),
        IndexModel(
            [("student_id", ASCENDING), ("job_id", ASCENDING)],
            unique=True,
        ),
    ])

    # ── application_events ────────────────────────────────────────────────────
    db[C.APPLICATION_EVENTS].create_indexes([
        IndexModel([("application_id", ASCENDING)]),
        IndexModel([("created_at", DESCENDING)]),
    ])

    # ── application_notes ─────────────────────────────────────────────────────
    db[C.APPLICATION_NOTES].create_indexes([
        IndexModel([("application_id", ASCENDING)]),
        IndexModel([("student_id", ASCENDING)]),
    ])

    # ── screenings ────────────────────────────────────────────────────────────
    db[C.SCREENINGS].create_indexes([
        IndexModel([("application_id", ASCENDING)]),
        IndexModel([("reviewer_id", ASCENDING)]),
    ])

    # ── interviews ────────────────────────────────────────────────────────────
    db[C.INTERVIEWS].create_indexes([
        IndexModel([("application_id", ASCENDING)]),
        IndexModel([("student_id", ASCENDING)]),
        IndexModel([("job_id", ASCENDING)]),
        IndexModel([("scheduled_at", ASCENDING)]),
    ])

    # ── mock_interviews ───────────────────────────────────────────────────────
    db[C.MOCK_INTERVIEWS].create_indexes([
        IndexModel([("student_id", ASCENDING)]),
        IndexModel([("created_at", DESCENDING)]),
    ])

    # ── assessments ───────────────────────────────────────────────────────────
    db[C.ASSESSMENTS].create_indexes([
        IndexModel([("skill_id", ASCENDING)]),
        IndexModel([("category", ASCENDING)]),
    ])

    # ── assessment_attempts ───────────────────────────────────────────────────
    db[C.ASSESSMENT_ATTEMPTS].create_indexes([
        IndexModel([("student_id", ASCENDING)]),
        IndexModel([("assessment_id", ASCENDING)]),
        IndexModel([("student_id", ASCENDING), ("assessment_id", ASCENDING)]),
        IndexModel([("created_at", DESCENDING)]),
    ])

    # ── roadmaps ──────────────────────────────────────────────────────────────
    db[C.ROADMAPS].create_indexes([
        IndexModel([("student_id", ASCENDING)], unique=True),
    ])

    # ── notifications ─────────────────────────────────────────────────────────
    db[C.NOTIFICATIONS].create_indexes([
        IndexModel([("user_id", ASCENDING)]),
        IndexModel([("user_id", ASCENDING), ("is_read", ASCENDING)]),
        IndexModel([("created_at", DESCENDING)]),
    ])

    # ── activities ────────────────────────────────────────────────────────────
    db[C.ACTIVITIES].create_indexes([
        IndexModel([("user_id", ASCENDING)]),
        IndexModel([("created_at", DESCENDING)]),
    ])

    # ── career_readiness_history ──────────────────────────────────────────────
    db[C.CAREER_READINESS_HISTORY].create_indexes([
        IndexModel([("student_id", ASCENDING)]),
        IndexModel([("created_at", DESCENDING)]),
    ])

    # ── job_reports ───────────────────────────────────────────────────────────
    db[C.JOB_REPORTS].create_indexes([
        IndexModel([("job_id", ASCENDING)]),
        IndexModel([("reported_by", ASCENDING)]),
        IndexModel([("status", ASCENDING)]),
    ])

    # ── audit_logs ────────────────────────────────────────────────────────────
    db[C.AUDIT_LOGS].create_indexes([
        IndexModel([("actor", ASCENDING)]),
        IndexModel([("entity_type", ASCENDING)]),
        IndexModel([("created_at", DESCENDING)]),
    ])

    print("✅ All indexes created successfully.")
