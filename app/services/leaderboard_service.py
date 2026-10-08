"""
Leaderboard and Competitive Features Service

Handles global rankings, contests, weekly challenges, and competitive analytics.
"""
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from bson import ObjectId
import logging

from app.cloud.mongodb import get_db
from app.cloud.coding_collections import (
    CODING_STATS_COLLECTION, CONTESTS_COLLECTION, CONTEST_SUBMISSIONS_COLLECTION,
    WEEKLY_CHALLENGES_COLLECTION, LEADERBOARD_COLLECTION
)
from app.models.coding import Contest, ContestSubmission, WeeklyChallenge, LeaderboardEntry

logger = logging.getLogger(__name__)


class LeaderboardService:
    """
    Service for managing leaderboards, contests, and competitive features.
    """
    
    def __init__(self):
        self.db = get_db()
    
    async def get_global_leaderboard(
        self, 
        limit: int = 50, 
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get global leaderboard with optional user position.
        """
        try:
            pipeline = [
                {"$match": {"total_xp": {"$gt": 0}}},
                {
                    "$lookup": {
                        "from": "users",
                        "localField": "user_id", 
                        "foreignField": "_id",
                        "as": "user_info"
                    }
                },
                {
                    "$addFields": {
                        "username": {"$arrayElemAt": ["$user_info.name", 0]},
                        "avatar": {"$arrayElemAt": ["$user_info.avatar", 0]}
                    }
                },
                {
                    "$sort": {
                        "total_xp": -1,
                        "current_streak": -1,
                        "total_problems_solved": -1
                    }
                },
                {"$limit": limit},
                {
                    "$project": {
                        "user_id": 1,
                        "username": {"$ifNull": ["$username", "Anonymous"]},
                        "avatar": 1,
                        "total_xp": 1,
                        "problems_solved": "$total_problems_solved",
                        "current_streak": 1,
                        "acceptance_rate": {"$multiply": ["$acceptance_rate", 100]},
                        "current_rank": 1,
                        "total_badges": 1,
                        "easy_solved": 1,
                        "medium_solved": 1,
                        "hard_solved": 1
                    }
                }
            ]
            
            leaderboard_data = []
            rank = 1
            user_position = None
            
            async for doc in self.db[CODING_STATS_COLLECTION].aggregate(pipeline):
                entry = {
                    "rank": rank,
                    "user_id": doc["user_id"],
                    "username": doc["username"],
                    "avatar": doc.get("avatar"),
                    "total_xp": doc["total_xp"],
                    "problems_solved": doc["problems_solved"],
                    "current_streak": doc["current_streak"],
                    "acceptance_rate": round(doc.get("acceptance_rate", 0), 1),
                    "rank_title": doc.get("current_rank", "newbie").title(),
                    "total_badges": doc.get("total_badges", 0),
                    "difficulty_breakdown": {
                        "easy": doc.get("easy_solved", 0),
                        "medium": doc.get("medium_solved", 0),
                        "hard": doc.get("hard_solved", 0)
                    }
                }
                
                if user_id and doc["user_id"] == user_id:
                    user_position = entry.copy()
                
                leaderboard_data.append(entry)
                rank += 1
            
            # If user not in top N but requested, find their position
            if user_id and not user_position:
                user_position = await self._get_user_position(user_id)
            
            return {
                "leaderboard": leaderboard_data,
                "user_position": user_position,
                "total_users": await self._get_total_ranked_users()
            }
            
        except Exception as e:
            logger.error(f"Error getting global leaderboard: {e}")
            return {"leaderboard": [], "user_position": None, "total_users": 0}
    
    async def get_weekly_leaderboard(self) -> Dict[str, Any]:
        """
        Get leaderboard for current week's activity.
        """
        try:
            # Calculate week boundaries
            now = datetime.now(timezone.utc)
            week_start = now - timedelta(days=now.weekday())
            week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
            
            pipeline = [
                {
                    "$lookup": {
                        "from": "code_submissions",
                        "let": {"user_id": "$user_id"},
                        "pipeline": [
                            {
                                "$match": {
                                    "$expr": {"$eq": ["$user_id", "$$user_id"]},
                                    "status": "accepted",
                                    "submitted_at": {"$gte": week_start}
                                }
                            },
                            {
                                "$group": {
                                    "_id": None,
                                    "weekly_solves": {"$sum": 1},
                                    "weekly_xp": {"$sum": 10}  # Simplified XP calculation
                                }
                            }
                        ],
                        "as": "weekly_stats"
                    }
                },
                {
                    "$addFields": {
                        "weekly_solves": {"$arrayElemAt": ["$weekly_stats.weekly_solves", 0]},
                        "weekly_xp": {"$arrayElemAt": ["$weekly_stats.weekly_xp", 0]}
                    }
                },
                {"$match": {"weekly_solves": {"$gt": 0}}},
                {"$sort": {"weekly_xp": -1, "weekly_solves": -1}},
                {"$limit": 20},
                {
                    "$lookup": {
                        "from": "users",
                        "localField": "user_id",
                        "foreignField": "_id", 
                        "as": "user_info"
                    }
                },
                {
                    "$project": {
                        "user_id": 1,
                        "username": {"$arrayElemAt": ["$user_info.name", 0]},
                        "weekly_solves": {"$ifNull": ["$weekly_solves", 0]},
                        "weekly_xp": {"$ifNull": ["$weekly_xp", 0]},
                        "current_streak": 1,
                        "total_xp": 1
                    }
                }
            ]
            
            weekly_leaders = []
            rank = 1
            
            async for doc in self.db[CODING_STATS_COLLECTION].aggregate(pipeline):
                weekly_leaders.append({
                    "rank": rank,
                    "user_id": doc["user_id"],
                    "username": doc.get("username", "Anonymous"),
                    "weekly_solves": doc["weekly_solves"],
                    "weekly_xp": doc["weekly_xp"],
                    "current_streak": doc.get("current_streak", 0),
                    "total_xp": doc.get("total_xp", 0)
                })
                rank += 1
            
            return {
                "weekly_leaderboard": weekly_leaders,
                "week_start": week_start.isoformat(),
                "week_end": (week_start + timedelta(days=7)).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting weekly leaderboard: {e}")
            return {"weekly_leaderboard": [], "week_start": None, "week_end": None}
    
    async def get_streak_leaderboard(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get leaderboard sorted by current streak.
        """
        try:
            pipeline = [
                {"$match": {"current_streak": {"$gt": 0}}},
                {"$sort": {"current_streak": -1, "total_xp": -1}},
                {"$limit": limit},
                {
                    "$lookup": {
                        "from": "users",
                        "localField": "user_id",
                        "foreignField": "_id",
                        "as": "user_info"
                    }
                },
                {
                    "$project": {
                        "user_id": 1,
                        "username": {"$arrayElemAt": ["$user_info.name", 0]},
                        "current_streak": 1,
                        "max_streak": 1,
                        "total_xp": 1,
                        "problems_solved": "$total_problems_solved",
                        "last_solved_date": 1
                    }
                }
            ]
            
            streak_leaders = []
            rank = 1
            
            async for doc in self.db[CODING_STATS_COLLECTION].aggregate(pipeline):
                streak_leaders.append({
                    "rank": rank,
                    "user_id": doc["user_id"],
                    "username": doc.get("username", "Anonymous"),
                    "current_streak": doc["current_streak"],
                    "max_streak": doc.get("max_streak", 0),
                    "total_xp": doc["total_xp"],
                    "problems_solved": doc["problems_solved"],
                    "last_solved": doc.get("last_solved_date")
                })
                rank += 1
            
            return streak_leaders
            
        except Exception as e:
            logger.error(f"Error getting streak leaderboard: {e}")
            return []
    
    async def create_weekly_challenge(
        self,
        easy_problem_id: str,
        medium_problem_id: str,
        hard_problem_id: str
    ) -> Optional[str]:
        """
        Create a new weekly challenge.
        """
        try:
            now = datetime.now(timezone.utc)
            week_start = now - timedelta(days=now.weekday())
            week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
            week_end = week_start + timedelta(days=7)
            
            # Check if challenge already exists for this week
            existing = await self.db[WEEKLY_CHALLENGES_COLLECTION].find_one({
                "week_start": week_start,
                "is_active": True
            })
            
            if existing:
                return str(existing["_id"])
            
            challenge = WeeklyChallenge(
                week_start=week_start,
                week_end=week_end,
                easy_problem_id=easy_problem_id,
                medium_problem_id=medium_problem_id,
                hard_problem_id=hard_problem_id,
                completion_xp_bonus=50,
                early_completion_bonus=25,
                is_active=True
            )
            
            challenge_dict = challenge.dict()
            challenge_dict.pop('id', None)
            
            result = await self.db[WEEKLY_CHALLENGES_COLLECTION].insert_one(challenge_dict)
            
            logger.info(f"Created weekly challenge: {result.inserted_id}")
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"Error creating weekly challenge: {e}")
            return None
    
    async def get_current_weekly_challenge(self) -> Optional[Dict[str, Any]]:
        """
        Get the current week's challenge.
        """
        try:
            now = datetime.now(timezone.utc)
            
            challenge = await self.db[WEEKLY_CHALLENGES_COLLECTION].find_one({
                "week_start": {"$lte": now},
                "week_end": {"$gte": now},
                "is_active": True
            })
            
            if not challenge:
                return None
            
            # Get problem details
            problem_ids = [
                challenge["easy_problem_id"],
                challenge["medium_problem_id"],
                challenge["hard_problem_id"]
            ]
            
            problems = []
            async for problem in self.db["coding_problems"].find({"problem_id": {"$in": problem_ids}}):
                problems.append({
                    "problem_id": problem["problem_id"],
                    "title": problem["title"],
                    "difficulty": problem["difficulty"],
                    "xp_reward": problem.get("xp_reward", 10)
                })
            
            return {
                "challenge_id": str(challenge["_id"]),
                "week_start": challenge["week_start"],
                "week_end": challenge["week_end"],
                "problems": problems,
                "participants": len(challenge.get("participants", [])),
                "completed_users": len(challenge.get("completed_users", [])),
                "completion_xp_bonus": challenge.get("completion_xp_bonus", 50),
                "early_completion_bonus": challenge.get("early_completion_bonus", 25)
            }
            
        except Exception as e:
            logger.error(f"Error getting current weekly challenge: {e}")
            return None
    
    async def join_weekly_challenge(self, user_id: str) -> bool:
        """
        Join the current weekly challenge.
        """
        try:
            now = datetime.now(timezone.utc)
            
            result = await self.db[WEEKLY_CHALLENGES_COLLECTION].update_one(
                {
                    "week_start": {"$lte": now},
                    "week_end": {"$gte": now},
                    "is_active": True,
                    "participants": {"$ne": user_id}
                },
                {"$push": {"participants": user_id}}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Error joining weekly challenge: {e}")
            return False
    
    async def get_user_challenge_progress(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user's progress on current weekly challenge.
        """
        try:
            challenge = await self.get_current_weekly_challenge()
            if not challenge:
                return None
            
            problem_ids = [p["problem_id"] for p in challenge["problems"]]
            
            # Check which problems user has solved this week
            week_start = challenge["week_start"]
            
            solved_problems = []
            async for submission in self.db["code_submissions"].find({
                "user_id": user_id,
                "problem_id": {"$in": problem_ids},
                "status": "accepted",
                "submitted_at": {"$gte": week_start}
            }):
                solved_problems.append(submission["problem_id"])
            
            progress = {
                "challenge_id": challenge["challenge_id"],
                "problems_solved": len(solved_problems),
                "total_problems": len(problem_ids),
                "is_completed": len(solved_problems) == len(problem_ids),
                "solved_problem_ids": solved_problems
            }
            
            # Check if eligible for early completion bonus
            if progress["is_completed"]:
                early_deadline = datetime.fromisoformat(challenge["week_start"]) + timedelta(days=3)
                latest_submission = await self.db["code_submissions"].find_one(
                    {
                        "user_id": user_id,
                        "problem_id": {"$in": problem_ids},
                        "status": "accepted",
                        "submitted_at": {"$gte": week_start}
                    },
                    sort=[("submitted_at", -1)]
                )
                
                if latest_submission and latest_submission["submitted_at"] <= early_deadline:
                    progress["early_completion_eligible"] = True
                else:
                    progress["early_completion_eligible"] = False
            
            return progress
            
        except Exception as e:
            logger.error(f"Error getting user challenge progress: {e}")
            return None
    
    async def _get_user_position(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get specific user's position in global ranking.
        """
        try:
            # Count users with higher XP
            user_stats = await self.db[CODING_STATS_COLLECTION].find_one({"user_id": user_id})
            if not user_stats:
                return None
            
            higher_xp_count = await self.db[CODING_STATS_COLLECTION].count_documents({
                "total_xp": {"$gt": user_stats["total_xp"]}
            })
            
            # Get user info
            user_info = await self.db["users"].find_one({"_id": user_id})
            
            return {
                "rank": higher_xp_count + 1,
                "user_id": user_id,
                "username": user_info.get("name", "Anonymous") if user_info else "Anonymous",
                "total_xp": user_stats["total_xp"],
                "problems_solved": user_stats.get("total_problems_solved", 0),
                "current_streak": user_stats.get("current_streak", 0),
                "acceptance_rate": round(user_stats.get("acceptance_rate", 0) * 100, 1),
                "rank_title": user_stats.get("current_rank", "newbie").title(),
                "total_badges": user_stats.get("total_badges", 0)
            }
            
        except Exception as e:
            logger.error(f"Error getting user position: {e}")
            return None
    
    async def _get_total_ranked_users(self) -> int:
        """
        Get total number of users with XP > 0.
        """
        try:
            return await self.db[CODING_STATS_COLLECTION].count_documents({"total_xp": {"$gt": 0}})
        except Exception as e:
            logger.error(f"Error getting total ranked users: {e}")
            return 0


# Global service instance - will be initialized when needed  
leaderboard_service = None

def get_leaderboard_service():
    global leaderboard_service
    if leaderboard_service is None:
        leaderboard_service = LeaderboardService()
    return leaderboard_service