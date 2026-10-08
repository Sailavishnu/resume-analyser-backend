"""
Coding Platform API Endpoints

REST API for LeetCode-style coding problems, submissions, and user progress.
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from bson import ObjectId
import logging
from datetime import datetime, timezone

from app.cloud.mongodb import get_db
from app.cloud.coding_collections import CODING_PROBLEMS_COLLECTION, CODE_SUBMISSIONS_COLLECTION
from app.models.coding import (
    CodingProblem, CodeSubmission, DifficultyLevel, ProblemCategory, 
    LanguageSupport, SubmissionStatus
)
from app.services.code_execution_service import code_execution_service
from app.services.xp_system_service import xp_system_service
from app.core.auth import get_current_user

router = APIRouter(prefix="/api/coding", tags=["coding"])
logger = logging.getLogger(__name__)


# Request/Response Models
class ProblemListRequest(BaseModel):
    difficulty: Optional[DifficultyLevel] = None
    category: Optional[ProblemCategory] = None
    tags: Optional[List[str]] = None
    search: Optional[str] = None
    limit: int = 20
    offset: int = 0


class CodeSubmissionRequest(BaseModel):
    problem_id: str
    language: LanguageSupport
    source_code: str


class RunCodeRequest(BaseModel):
    problem_id: str
    language: LanguageSupport
    source_code: str


class ProblemResponse(BaseModel):
    problem_id: str
    title: str
    difficulty: str
    category: str
    tags: List[str]
    acceptance_rate: float
    total_submissions: int
    xp_reward: int
    is_solved: bool = False


class ProblemDetailResponse(BaseModel):
    problem_id: str
    title: str
    description: str
    difficulty: str
    category: str
    tags: List[str]
    examples: List[Dict[str, str]]
    constraints: Dict[str, Any]
    hints: List[Dict[str, Any]]
    starter_codes: List[Dict[str, str]]
    acceptance_rate: float
    total_submissions: int
    successful_submissions: int
    xp_reward: int
    is_solved: bool = False


@router.get("/problems", response_model=List[ProblemResponse])
async def get_problems(
    difficulty: Optional[DifficultyLevel] = None,
    category: Optional[ProblemCategory] = None,
    search: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    current_user: dict = Depends(get_current_user)
):
    """
    Get list of coding problems with filtering and pagination.
    """
    try:
        db = get_db()
        
        # Build filter query
        filter_query = {"is_active": True}
        
        if difficulty:
            filter_query["difficulty"] = difficulty.value
            
        if category:
            filter_query["category"] = category.value
            
        if search:
            filter_query["$or"] = [
                {"title": {"$regex": search, "$options": "i"}},
                {"description": {"$regex": search, "$options": "i"}},
                {"tags": {"$in": [search]}}
            ]
        
        # Get user's solved problems
        user_submissions = await db[CODE_SUBMISSIONS_COLLECTION].find({
            "user_id": current_user["id"],
            "status": SubmissionStatus.ACCEPTED.value
        }).distinct("problem_id")
        
        solved_problems = set(user_submissions)
        
        # Execute query
        cursor = db[CODING_PROBLEMS_COLLECTION].find(filter_query).skip(offset).limit(limit)
        
        problems = []
        async for problem_doc in cursor:
            problems.append(ProblemResponse(
                problem_id=problem_doc["problem_id"],
                title=problem_doc["title"],
                difficulty=problem_doc["difficulty"],
                category=problem_doc["category"],
                tags=problem_doc.get("tags", []),
                acceptance_rate=problem_doc.get("acceptance_rate", 0.0),
                total_submissions=problem_doc.get("total_submissions", 0),
                xp_reward=problem_doc.get("xp_reward", 10),
                is_solved=problem_doc["problem_id"] in solved_problems
            ))
        
        return problems
        
    except Exception as e:
        logger.error(f"Error getting problems: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch problems")


@router.get("/problems/{problem_id}", response_model=ProblemDetailResponse)
async def get_problem_detail(
    problem_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get detailed information about a specific problem.
    """
    try:
        db = get_db()
        
        # Get problem
        problem_doc = await db[CODING_PROBLEMS_COLLECTION].find_one({
            "problem_id": problem_id,
            "is_active": True
        })
        
        if not problem_doc:
            raise HTTPException(status_code=404, detail="Problem not found")
        
        # Check if user has solved this problem
        user_submission = await db[CODE_SUBMISSIONS_COLLECTION].find_one({
            "user_id": current_user["id"],
            "problem_id": problem_id,
            "status": SubmissionStatus.ACCEPTED.value
        })
        
        is_solved = user_submission is not None
        
        # Filter out hidden test cases from examples
        visible_examples = [
            ex for ex in problem_doc.get("examples", [])
        ]
        
        return ProblemDetailResponse(
            problem_id=problem_doc["problem_id"],
            title=problem_doc["title"],
            description=problem_doc["description"],
            difficulty=problem_doc["difficulty"],
            category=problem_doc["category"],
            tags=problem_doc.get("tags", []),
            examples=visible_examples,
            constraints=problem_doc.get("constraints", {}),
            hints=problem_doc.get("hints", []),
            starter_codes=problem_doc.get("starter_codes", []),
            acceptance_rate=problem_doc.get("acceptance_rate", 0.0),
            total_submissions=problem_doc.get("total_submissions", 0),
            successful_submissions=problem_doc.get("successful_submissions", 0),
            xp_reward=problem_doc.get("xp_reward", 10),
            is_solved=is_solved
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting problem detail: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch problem details")


@router.post("/problems/{problem_id}/run")
async def run_code(
    problem_id: str,
    request: RunCodeRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Run code against visible test cases only (not a submission).
    """
    try:
        db = get_db()
        
        # Get problem
        problem_doc = await db[CODING_PROBLEMS_COLLECTION].find_one({
            "problem_id": problem_id,
            "is_active": True
        })
        
        if not problem_doc:
            raise HTTPException(status_code=404, detail="Problem not found")
        
        # Get only visible test cases
        all_test_cases = problem_doc.get("test_cases", [])
        visible_test_cases = [tc for tc in all_test_cases if not tc.get("is_hidden", False)]
        
        if not visible_test_cases:
            raise HTTPException(status_code=400, detail="No test cases available")
        
        # Execute code
        if request.language == LanguageSupport.PYTHON:
            result = code_execution_service.execute_python_code(
                request.source_code,
                visible_test_cases,
                timeout=5
            )
        else:
            raise HTTPException(status_code=400, detail="Language not supported yet")
        
        return {
            "status": result["status"],
            "passed_tests": result["passed_tests"],
            "total_tests": result["total_tests"],
            "runtime": result["runtime"],
            "test_results": result["test_results"],
            "error_message": result.get("error_message"),
            "is_submission": False
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running code: {e}")
        raise HTTPException(status_code=500, detail="Failed to execute code")


@router.post("/problems/{problem_id}/submit")
async def submit_code(
    problem_id: str,
    request: CodeSubmissionRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """
    Submit code solution (runs against all test cases including hidden ones).
    """
    try:
        db = get_db()
        
        # Get problem
        problem_doc = await db[CODING_PROBLEMS_COLLECTION].find_one({
            "problem_id": problem_id,
            "is_active": True
        })
        
        if not problem_doc:
            raise HTTPException(status_code=404, detail="Problem not found")
        
        # Get all test cases (including hidden)
        test_cases = problem_doc.get("test_cases", [])
        
        if not test_cases:
            raise HTTPException(status_code=400, detail="No test cases available")
        
        # Execute code
        if request.language == LanguageSupport.PYTHON:
            execution_result = code_execution_service.execute_python_code(
                request.source_code,
                test_cases,
                timeout=10  # Longer timeout for submissions
            )
        else:
            raise HTTPException(status_code=400, detail="Language not supported yet")
        
        # Create submission record
        submission = CodeSubmission(
            user_id=current_user["id"],
            problem_id=problem_id,
            language=request.language,
            source_code=request.source_code,
            status=SubmissionStatus(execution_result["status"]),
            runtime=execution_result["runtime"],
            memory_used=execution_result.get("memory_used", 0),
            total_test_cases=execution_result["total_tests"],
            passed_test_cases=execution_result["passed_tests"],
            error_message=execution_result.get("error_message"),
            submitted_at=datetime.now(timezone.utc)
        )
        
        # Save submission to database
        submission_dict = submission.dict()
        submission_dict.pop('id', None)  # Remove id for insertion
        
        insert_result = await db[CODE_SUBMISSIONS_COLLECTION].insert_one(submission_dict)
        submission_id = str(insert_result.inserted_id)
        
        # Update problem statistics
        await db[CODING_PROBLEMS_COLLECTION].update_one(
            {"problem_id": problem_id},
            {
                "$inc": {
                    "total_submissions": 1,
                    "successful_submissions": 1 if submission.status == SubmissionStatus.ACCEPTED else 0
                }
            }
        )
        
        # Recalculate acceptance rate
        updated_problem = await db[CODING_PROBLEMS_COLLECTION].find_one({"problem_id": problem_id})
        if updated_problem and updated_problem["total_submissions"] > 0:
            new_acceptance_rate = updated_problem["successful_submissions"] / updated_problem["total_submissions"]
            await db[CODING_PROBLEMS_COLLECTION].update_one(
                {"problem_id": problem_id},
                {"$set": {"acceptance_rate": new_acceptance_rate}}
            )
        
        # Update user statistics in background
        if submission.status == SubmissionStatus.ACCEPTED:
            background_tasks.add_task(
                update_user_stats_background,
                current_user["id"],
                DifficultyLevel(problem_doc["difficulty"]),
                submission.status,
                request.language,
                submission.runtime or 0,
                problem_doc["category"]
            )
        
        # Prepare response (hide details of hidden test cases)
        visible_test_results = []
        for i, test_result in enumerate(execution_result.get("test_results", [])):
            if i < len([tc for tc in test_cases if not tc.get("is_hidden", False)]):
                visible_test_results.append(test_result)
            else:
                # For hidden test cases, only show pass/fail
                visible_test_results.append({
                    "test_case": test_result["test_case"],
                    "status": test_result["status"],
                    "runtime": test_result.get("runtime", 0)
                })
        
        return {
            "submission_id": submission_id,
            "status": execution_result["status"],
            "passed_tests": execution_result["passed_tests"],
            "total_tests": execution_result["total_tests"],
            "runtime": execution_result["runtime"],
            "test_results": visible_test_results,
            "error_message": execution_result.get("error_message"),
            "is_submission": True,
            "xp_gained": 0 if submission.status != SubmissionStatus.ACCEPTED else problem_doc.get("xp_reward", 10)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting code: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit code")


async def update_user_stats_background(
    user_id: str,
    difficulty: DifficultyLevel,
    status: SubmissionStatus,
    language: LanguageSupport,
    runtime: int,
    category: str
):
    """Background task to update user statistics."""
    try:
        await xp_system_service.update_stats_after_submission(
            user_id, difficulty, status, language, runtime, category
        )
    except Exception as e:
        logger.error(f"Error updating user stats in background: {e}")


@router.get("/submissions")
async def get_user_submissions(
    limit: int = 20,
    offset: int = 0,
    status_filter: Optional[SubmissionStatus] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Get user's submission history.
    """
    try:
        db = get_db()
        
        # Build filter
        filter_query = {"user_id": current_user["id"]}
        if status_filter:
            filter_query["status"] = status_filter.value
        
        # Get submissions with problem details
        pipeline = [
            {"$match": filter_query},
            {"$sort": {"submitted_at": -1}},
            {"$skip": offset},
            {"$limit": limit},
            {
                "$lookup": {
                    "from": CODING_PROBLEMS_COLLECTION,
                    "localField": "problem_id",
                    "foreignField": "problem_id",
                    "as": "problem_info"
                }
            },
            {
                "$project": {
                    "submission_id": {"$toString": "$_id"},
                    "problem_id": 1,
                    "problem_title": {"$arrayElemAt": ["$problem_info.title", 0]},
                    "difficulty": {"$arrayElemAt": ["$problem_info.difficulty", 0]},
                    "language": 1,
                    "status": 1,
                    "runtime": 1,
                    "memory_used": 1,
                    "passed_test_cases": 1,
                    "total_test_cases": 1,
                    "submitted_at": 1
                }
            }
        ]
        
        submissions = []
        async for doc in db[CODE_SUBMISSIONS_COLLECTION].aggregate(pipeline):
            submissions.append(doc)
        
        return submissions
        
    except Exception as e:
        logger.error(f"Error getting user submissions: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch submissions")


@router.get("/stats")
async def get_user_stats(current_user: dict = Depends(get_current_user)):
    """
    Get user's coding statistics and progress.
    """
    try:
        stats = await xp_system_service.get_user_stats(current_user["id"])
        
        if not stats:
            # Create new stats for new user
            stats = await xp_system_service.create_user_stats(current_user["id"])
        
        # Get user's global rank
        global_rank = await xp_system_service.get_user_rank_position(current_user["id"])
        
        return {
            "total_xp": stats.total_xp,
            "current_rank": stats.current_rank.value,
            "global_rank": global_rank,
            "problems_solved": {
                "total": stats.total_problems_solved,
                "easy": stats.easy_solved,
                "medium": stats.medium_solved,
                "hard": stats.hard_solved
            },
            "streaks": {
                "current": stats.current_streak,
                "max": stats.max_streak
            },
            "submission_stats": {
                "total_submissions": stats.total_submissions,
                "accepted_submissions": stats.accepted_submissions,
                "acceptance_rate": round(stats.acceptance_rate * 100, 1)
            },
            "languages_used": stats.languages_used,
            "favorite_language": stats.favorite_language.value if stats.favorite_language else None,
            "achievements": [
                {
                    "id": achievement.id,
                    "title": achievement.title,
                    "description": achievement.description,
                    "icon": achievement.icon,
                    "unlocked_at": achievement.unlocked_at
                }
                for achievement in stats.achievements
            ],
            "total_badges": stats.total_badges
        }
        
    except Exception as e:
        logger.error(f"Error getting user stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch user statistics")


@router.get("/leaderboard")
async def get_leaderboard(limit: int = 50):
    """
    Get global leaderboard.
    """
    try:
        leaderboard = await xp_system_service.get_leaderboard(limit)
        return leaderboard
        
    except Exception as e:
        logger.error(f"Error getting leaderboard: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch leaderboard")