"""
MongoDB Collections for Coding Platform

Collection names and database operations for coding platform.
"""

# Collection names
CODING_PROBLEMS_COLLECTION = "coding_problems"
CODE_SUBMISSIONS_COLLECTION = "code_submissions"
CODING_STATS_COLLECTION = "coding_stats"
CONTESTS_COLLECTION = "contests"
CONTEST_SUBMISSIONS_COLLECTION = "contest_submissions"
WEEKLY_CHALLENGES_COLLECTION = "weekly_challenges"
LEADERBOARD_COLLECTION = "leaderboard_cache"  # Cached leaderboard for performance

# Database indexes for optimal performance
CODING_INDEXES = {
    CODING_PROBLEMS_COLLECTION: [
        {"key": "problem_id", "unique": True},
        {"key": "difficulty"},
        {"key": "category"},
        {"key": "is_active"},
        {"key": ["difficulty", "category"]},
        {"key": ["is_active", "difficulty"]},
        {"key": "tags"},
    ],
    
    CODE_SUBMISSIONS_COLLECTION: [
        {"key": "user_id"},
        {"key": "problem_id"},
        {"key": ["user_id", "problem_id"]},
        {"key": ["user_id", "submitted_at"]},
        {"key": "status"},
        {"key": "language"},
        {"key": "submitted_at"},
    ],
    
    CODING_STATS_COLLECTION: [
        {"key": "user_id", "unique": True},
        {"key": "total_xp"},
        {"key": "current_rank"},
        {"key": "global_rank"},
        {"key": "current_streak"},
        {"key": ["total_xp", "current_streak"]},  # Compound for leaderboard
    ],
    
    CONTESTS_COLLECTION: [
        {"key": "start_time"},
        {"key": "end_time"},
        {"key": "is_active"},
        {"key": ["is_active", "start_time"]},
    ],
    
    CONTEST_SUBMISSIONS_COLLECTION: [
        {"key": "contest_id"},
        {"key": "user_id"},
        {"key": ["contest_id", "user_id"]},
        {"key": ["contest_id", "points_earned"]},
    ],
    
    WEEKLY_CHALLENGES_COLLECTION: [
        {"key": "week_start"},
        {"key": "is_active"},
        {"key": ["is_active", "week_start"]},
    ],
    
    LEADERBOARD_COLLECTION: [
        {"key": "rank", "unique": True},
        {"key": "total_xp"},
        {"key": "user_id", "unique": True},
    ]
}