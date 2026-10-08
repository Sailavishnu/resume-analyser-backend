"""
XP System and User Statistics Tracking Service

Handles user progression, achievements, ranking, and gamification features.
"""
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from bson import ObjectId
import logging

from app.cloud.mongodb import get_db
from app.cloud.coding_collections import CODING_STATS_COLLECTION, CODE_SUBMISSIONS_COLLECTION
from app.models.coding import (
    CodingStats, UserRank, Achievement, SubmissionStatus, DifficultyLevel,
    XP_REWARDS, RANK_THRESHOLDS, ACHIEVEMENTS, LanguageSupport
)

logger = logging.getLogger(__name__)


class XPSystemService:
    """
    Service for managing user XP, achievements, and statistics.
    """
    
    def __init__(self):
        self.db = get_db()
    
    async def get_user_stats(self, user_id: str) -> Optional[CodingStats]:
        """Get user coding statistics."""
        try:
            stats_doc = await self.db[CODING_STATS_COLLECTION].find_one({"user_id": user_id})
            
            if stats_doc:
                # Convert MongoDB document to CodingStats model
                stats_doc.pop('_id', None)
                return CodingStats(**stats_doc)
            else:
                # Create new stats for first-time user
                return await self.create_user_stats(user_id)
                
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return None
    
    async def create_user_stats(self, user_id: str) -> CodingStats:
        """Create initial statistics for a new user."""
        try:
            new_stats = CodingStats(user_id=user_id)
            
            stats_dict = new_stats.dict()
            stats_dict['user_id'] = user_id
            
            await self.db[CODING_STATS_COLLECTION].insert_one(stats_dict)
            
            logger.info(f"Created new stats for user {user_id}")
            return new_stats
            
        except Exception as e:
            logger.error(f"Error creating user stats: {e}")
            return CodingStats(user_id=user_id)
    
    async def update_stats_after_submission(
        self, 
        user_id: str, 
        problem_difficulty: DifficultyLevel,
        submission_status: SubmissionStatus,
        language: LanguageSupport,
        runtime: int,
        problem_category: str
    ) -> Dict[str, Any]:
        """
        Update user statistics after a code submission.
        
        Returns:
            Dictionary with XP gained, achievements unlocked, rank changes
        """
        try:
            stats = await self.get_user_stats(user_id)
            if not stats:
                return {"error": "Could not load user stats"}
            
            result = {
                "xp_gained": 0,
                "achievements_unlocked": [],
                "rank_changed": False,
                "new_rank": stats.current_rank,
                "streak_updated": False
            }
            
            # Only award XP and update stats for ACCEPTED submissions
            if submission_status == SubmissionStatus.ACCEPTED:
                # Award XP based on difficulty
                xp_reward = XP_REWARDS[problem_difficulty]
                
                # Bonus XP for streaks
                streak_bonus = min(stats.current_streak * 2, 20)  # Max 20 bonus XP
                total_xp = xp_reward + streak_bonus
                
                # Update stats
                stats.total_xp += total_xp
                stats.total_problems_solved += 1
                
                # Update difficulty-specific counters
                if problem_difficulty == DifficultyLevel.EASY:
                    stats.easy_solved += 1
                elif problem_difficulty == DifficultyLevel.MEDIUM:
                    stats.medium_solved += 1
                elif problem_difficulty == DifficultyLevel.HARD:
                    stats.hard_solved += 1
                
                # Update streak
                today = datetime.now(timezone.utc).date()
                last_solved = stats.last_solved_date
                
                if last_solved and last_solved.date() == today:
                    # Already solved today, no streak change
                    pass
                elif last_solved and last_solved.date() == today - timedelta(days=1):
                    # Consecutive day, increase streak
                    stats.current_streak += 1
                    stats.max_streak = max(stats.max_streak, stats.current_streak)
                    result["streak_updated"] = True
                elif not last_solved or last_solved.date() < today - timedelta(days=1):
                    # First solve or gap in solving, reset streak
                    stats.current_streak = 1
                    result["streak_updated"] = True
                
                stats.last_solved_date = datetime.now(timezone.utc)
                
                # Update language usage
                lang_str = language.value
                stats.languages_used[lang_str] = stats.languages_used.get(lang_str, 0) + 1
                
                # Update favorite language
                most_used_lang = max(stats.languages_used.items(), key=lambda x: x[1])
                stats.favorite_language = LanguageSupport(most_used_lang[0])
                
                # Update category stats
                if problem_category not in stats.category_stats:
                    stats.category_stats[problem_category] = {"solved": 0, "total": 0, "accuracy": 0.0}
                
                stats.category_stats[problem_category]["solved"] += 1
                
                # Check for rank promotion
                old_rank = stats.current_rank
                new_rank = self._calculate_rank(stats.total_xp)
                if new_rank != old_rank:
                    stats.current_rank = new_rank
                    result["rank_changed"] = True
                    result["new_rank"] = new_rank
                
                # Check for achievements
                achievements = await self._check_achievements(stats, user_id)
                result["achievements_unlocked"] = achievements
                
                # Add achievement XP
                for achievement in achievements:
                    stats.total_xp += achievement.get("xp_bonus", 0)
                
                result["xp_gained"] = total_xp
            
            # Always update submission stats
            stats.total_submissions += 1
            if submission_status == SubmissionStatus.ACCEPTED:
                stats.accepted_submissions += 1
            
            # Recalculate acceptance rate
            if stats.total_submissions > 0:
                stats.acceptance_rate = stats.accepted_submissions / stats.total_submissions
            
            # Update timestamp
            stats.last_updated = datetime.now(timezone.utc)
            
            # Save to database
            await self.db[CODING_STATS_COLLECTION].update_one(
                {"user_id": user_id},
                {"$set": stats.dict()},
                upsert=True
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error updating stats after submission: {e}")
            return {"error": str(e)}
    
    def _calculate_rank(self, total_xp: int) -> UserRank:
        """Calculate user rank based on total XP."""
        for rank, min_xp in reversed(list(RANK_THRESHOLDS.items())):
            if total_xp >= min_xp:
                return rank
        return UserRank.NEWBIE
    
    async def _check_achievements(self, stats: CodingStats, user_id: str) -> List[Dict[str, Any]]:
        """Check and award new achievements."""
        new_achievements = []
        existing_achievement_ids = {a.id for a in stats.achievements}
        
        try:
            # First problem solved
            if "first_solve" not in existing_achievement_ids and stats.total_problems_solved >= 1:
                achievement = self._create_achievement("first_solve")
                stats.achievements.append(achievement)
                new_achievements.append(ACHIEVEMENTS["first_solve"])
            
            # Easy problems milestones
            if "easy_10" not in existing_achievement_ids and stats.easy_solved >= 10:
                achievement = self._create_achievement("easy_10")
                stats.achievements.append(achievement)
                new_achievements.append(ACHIEVEMENTS["easy_10"])
            
            # Medium problems milestones
            if "medium_5" not in existing_achievement_ids and stats.medium_solved >= 5:
                achievement = self._create_achievement("medium_5")
                stats.achievements.append(achievement)
                new_achievements.append(ACHIEVEMENTS["medium_5"])
            
            # First hard problem
            if "hard_1" not in existing_achievement_ids and stats.hard_solved >= 1:
                achievement = self._create_achievement("hard_1")
                stats.achievements.append(achievement)
                new_achievements.append(ACHIEVEMENTS["hard_1"])
            
            # Streak achievements
            if "streak_7" not in existing_achievement_ids and stats.current_streak >= 7:
                achievement = self._create_achievement("streak_7")
                stats.achievements.append(achievement)
                new_achievements.append(ACHIEVEMENTS["streak_7"])
            
            if "streak_30" not in existing_achievement_ids and stats.current_streak >= 30:
                achievement = self._create_achievement("streak_30")
                stats.achievements.append(achievement)
                new_achievements.append(ACHIEVEMENTS["streak_30"])
            
            # Language diversity
            if "language_master" not in existing_achievement_ids and len(stats.languages_used) >= 3:
                achievement = self._create_achievement("language_master")
                stats.achievements.append(achievement)
                new_achievements.append(ACHIEVEMENTS["language_master"])
            
            # Update badge count
            stats.total_badges = len(stats.achievements)
            
        except Exception as e:
            logger.error(f"Error checking achievements: {e}")
        
        return new_achievements
    
    def _create_achievement(self, achievement_id: str) -> Achievement:
        """Create an Achievement object from achievement config."""
        config = ACHIEVEMENTS[achievement_id]
        return Achievement(
            id=achievement_id,
            title=config["title"],
            description=config["description"],
            icon=config["icon"],
            xp_bonus=config["xp_bonus"],
            unlocked_at=datetime.now(timezone.utc)
        )
    
    async def get_leaderboard(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get global leaderboard."""
        try:
            pipeline = [
                {"$match": {"total_xp": {"$gt": 0}}},  # Only users with XP
                {"$sort": {"total_xp": -1, "current_streak": -1}},  # Sort by XP, then streak
                {"$limit": limit},
                {
                    "$lookup": {
                        "from": "users",  # Assuming you have a users collection
                        "localField": "user_id",
                        "foreignField": "_id",
                        "as": "user_info"
                    }
                },
                {
                    "$project": {
                        "user_id": 1,
                        "username": {"$arrayElemAt": ["$user_info.name", 0]},
                        "total_xp": 1,
                        "problems_solved": "$total_problems_solved",
                        "current_streak": 1,
                        "acceptance_rate": 1,
                        "total_badges": 1,
                        "current_rank": 1
                    }
                }
            ]
            
            cursor = self.db[CODING_STATS_COLLECTION].aggregate(pipeline)
            leaderboard = []
            
            rank = 1
            async for doc in cursor:
                leaderboard.append({
                    "rank": rank,
                    "user_id": doc["user_id"],
                    "username": doc.get("username", "Anonymous"),
                    "total_xp": doc["total_xp"],
                    "problems_solved": doc["problems_solved"],
                    "current_streak": doc["current_streak"],
                    "acceptance_rate": round(doc.get("acceptance_rate", 0) * 100, 1),
                    "total_badges": doc.get("total_badges", 0),
                    "rank_title": doc.get("current_rank", "newbie").title()
                })
                rank += 1
            
            return leaderboard
            
        except Exception as e:
            logger.error(f"Error getting leaderboard: {e}")
            return []
    
    async def get_user_rank_position(self, user_id: str) -> Optional[int]:
        """Get user's position in global ranking."""
        try:
            user_stats = await self.get_user_stats(user_id)
            if not user_stats:
                return None
            
            # Count users with higher XP
            higher_xp_count = await self.db[CODING_STATS_COLLECTION].count_documents({
                "total_xp": {"$gt": user_stats.total_xp}
            })
            
            return higher_xp_count + 1
            
        except Exception as e:
            logger.error(f"Error getting user rank position: {e}")
            return None


# Global service instance - will be initialized when needed
xp_system_service = None

def get_xp_system_service():
    global xp_system_service
    if xp_system_service is None:
        xp_system_service = XPSystemService()
    return xp_system_service