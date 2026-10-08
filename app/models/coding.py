"""
Coding Platform Database Models

Models for LeetCode-style coding problems, submissions, and user progress.
"""
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field
from bson import ObjectId


class DifficultyLevel(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class ProblemCategory(str, Enum):
    ARRAYS = "arrays"
    STRINGS = "strings"
    LINKED_LISTS = "linked_lists"
    TREES = "trees"
    GRAPHS = "graphs"
    DYNAMIC_PROGRAMMING = "dynamic_programming"
    GREEDY = "greedy"
    BACKTRACKING = "backtracking"
    SORTING = "sorting"
    SEARCHING = "searching"
    STACK_QUEUE = "stack_queue"
    HASH_TABLES = "hash_tables"
    MATH = "math"
    BIT_MANIPULATION = "bit_manipulation"
    TWO_POINTERS = "two_pointers"


class LanguageSupport(str, Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    JAVA = "java"
    CPP = "cpp"


class SubmissionStatus(str, Enum):
    ACCEPTED = "accepted"
    WRONG_ANSWER = "wrong_answer"
    RUNTIME_ERROR = "runtime_error"
    TIME_LIMIT_EXCEEDED = "time_limit_exceeded"
    MEMORY_LIMIT_EXCEEDED = "memory_limit_exceeded"
    COMPILATION_ERROR = "compilation_error"


class TestCase(BaseModel):
    """Individual test case for a problem"""
    input: str
    expected_output: str
    is_hidden: bool = False
    explanation: Optional[str] = None


class Constraint(BaseModel):
    """Problem constraints"""
    time_limit: int = 2000  # milliseconds
    memory_limit: int = 256  # MB
    input_constraints: List[str] = []


class Hint(BaseModel):
    """Problem hints"""
    text: str
    order: int


class StarterCode(BaseModel):
    """Starter code templates"""
    language: LanguageSupport
    code: str


class Solution(BaseModel):
    """Official solution"""
    language: LanguageSupport
    code: str
    explanation: str
    time_complexity: str
    space_complexity: str


class CodingProblem(BaseModel):
    """Main coding problem model"""
    id: Optional[str] = Field(default=None, alias="_id")
    problem_id: str  # Unique identifier like "two-sum"
    title: str
    description: str
    difficulty: DifficultyLevel
    category: ProblemCategory
    tags: List[str] = []
    
    # Problem content
    examples: List[Dict[str, str]] = []  # {"input": "...", "output": "...", "explanation": "..."}
    constraints: Constraint
    hints: List[Hint] = []
    
    # Test cases
    test_cases: List[TestCase] = []
    
    # Code templates and solutions
    starter_codes: List[StarterCode] = []
    solutions: List[Solution] = []
    
    # Metadata
    acceptance_rate: float = 0.0
    total_submissions: int = 0
    successful_submissions: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True
    
    # XP rewards
    xp_reward: int = Field(default=10)  # Based on difficulty
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class CodeSubmission(BaseModel):
    """Code submission model"""
    id: Optional[str] = Field(default=None, alias="_id")
    user_id: str
    problem_id: str
    language: LanguageSupport
    source_code: str
    
    # Execution results
    status: SubmissionStatus
    runtime: Optional[int] = None  # milliseconds
    memory_used: Optional[int] = None  # MB
    
    # Test case results
    total_test_cases: int = 0
    passed_test_cases: int = 0
    failed_test_case_index: Optional[int] = None
    error_message: Optional[str] = None
    
    # Timestamps
    submitted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # XP gained (if accepted)
    xp_gained: int = 0
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class UserRank(str, Enum):
    NEWBIE = "newbie"
    BEGINNER = "beginner"
    APPRENTICE = "apprentice"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"
    MASTER = "master"


class Achievement(BaseModel):
    """User achievement/badge"""
    id: str
    title: str
    description: str
    icon: str
    xp_bonus: int = 0
    unlocked_at: datetime


class CodingStats(BaseModel):
    """User coding statistics"""
    total_xp: int = 0
    current_rank: UserRank = UserRank.NEWBIE
    
    # Problems solved by difficulty
    easy_solved: int = 0
    medium_solved: int = 0
    hard_solved: int = 0
    total_problems_solved: int = 0
    
    # Streaks and consistency
    current_streak: int = 0
    max_streak: int = 0
    last_solved_date: Optional[datetime] = None
    
    # Submission statistics
    total_submissions: int = 0
    accepted_submissions: int = 0
    acceptance_rate: float = 0.0
    
    # Language preferences
    favorite_language: Optional[LanguageSupport] = None
    languages_used: Dict[str, int] = {}  # language -> count
    
    # Category performance
    category_stats: Dict[str, Dict[str, int]] = {}  # category -> {solved, total, accuracy}
    
    # Achievements and badges
    achievements: List[Achievement] = []
    total_badges: int = 0
    
    # Ranking
    global_rank: Optional[int] = None
    percentile: Optional[float] = None
    
    # Updated timestamp
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Contest(BaseModel):
    """Coding contest model"""
    id: Optional[str] = Field(default=None, alias="_id")
    title: str
    description: str
    start_time: datetime
    end_time: datetime
    duration_minutes: int
    
    # Contest problems
    problem_ids: List[str] = []
    
    # Participants
    participants: List[str] = []  # user_ids
    max_participants: Optional[int] = None
    
    # Prizes and rewards
    xp_multiplier: float = 1.5
    winner_xp_bonus: int = 100
    
    # Status
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class ContestSubmission(BaseModel):
    """Contest-specific submission"""
    id: Optional[str] = Field(default=None, alias="_id")
    contest_id: str
    user_id: str
    problem_id: str
    submission_id: str  # Reference to CodeSubmission
    
    # Contest scoring
    points_earned: int = 0
    penalty_minutes: int = 0  # For wrong submissions
    solved_at: Optional[datetime] = None
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class LeaderboardEntry(BaseModel):
    """Leaderboard entry model"""
    user_id: str
    username: str
    avatar_url: Optional[str] = None
    
    # Stats for ranking
    total_xp: int
    problems_solved: int
    current_streak: int
    acceptance_rate: float
    
    # Ranking
    rank: int
    previous_rank: Optional[int] = None
    rank_change: int = 0  # +1 up, -1 down, 0 same
    
    # Badges count
    total_badges: int = 0
    
    # Last activity
    last_active: datetime


class WeeklyChallenge(BaseModel):
    """Weekly coding challenge"""
    id: Optional[str] = Field(default=None, alias="_id")
    week_start: datetime
    week_end: datetime
    
    # Challenge problems (3 problems of different difficulties)
    easy_problem_id: str
    medium_problem_id: str
    hard_problem_id: str
    
    # Participants and completions
    participants: List[str] = []
    completed_users: List[str] = []
    
    # Rewards
    completion_xp_bonus: int = 50
    early_completion_bonus: int = 25  # Extra for completing in first 3 days
    
    # Status
    is_active: bool = True
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


# XP and Ranking Configuration
XP_REWARDS = {
    DifficultyLevel.EASY: 10,
    DifficultyLevel.MEDIUM: 25,
    DifficultyLevel.HARD: 50
}

RANK_THRESHOLDS = {
    UserRank.NEWBIE: 0,
    UserRank.BEGINNER: 50,
    UserRank.APPRENTICE: 150,
    UserRank.INTERMEDIATE: 400,
    UserRank.ADVANCED: 800,
    UserRank.EXPERT: 1500,
    UserRank.MASTER: 3000
}

# Achievement definitions
ACHIEVEMENTS = {
    "first_solve": {
        "title": "First Steps",
        "description": "Solved your first problem",
        "icon": "🎯",
        "xp_bonus": 10
    },
    "easy_10": {
        "title": "Getting Started",
        "description": "Solved 10 easy problems",
        "icon": "🟢",
        "xp_bonus": 25
    },
    "medium_5": {
        "title": "Stepping Up",
        "description": "Solved 5 medium problems",
        "icon": "🟡",
        "xp_bonus": 50
    },
    "hard_1": {
        "title": "Challenge Accepted",
        "description": "Solved your first hard problem",
        "icon": "🔴",
        "xp_bonus": 100
    },
    "streak_7": {
        "title": "Week Warrior",
        "description": "7 day solving streak",
        "icon": "🔥",
        "xp_bonus": 75
    },
    "streak_30": {
        "title": "Month Master",
        "description": "30 day solving streak",
        "icon": "⚡",
        "xp_bonus": 200
    },
    "perfect_10": {
        "title": "Perfect Score",
        "description": "10 consecutive accepted submissions",
        "icon": "💯",
        "xp_bonus": 150
    },
    "speed_demon": {
        "title": "Speed Demon",
        "description": "Solved a problem in under 5 minutes",
        "icon": "⚡",
        "xp_bonus": 50
    },
    "language_master": {
        "title": "Polyglot",
        "description": "Solved problems in 3+ languages",
        "icon": "🌍",
        "xp_bonus": 100
    }
}