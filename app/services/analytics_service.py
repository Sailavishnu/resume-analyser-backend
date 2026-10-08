"""
Submission History and Analytics Service

Provides detailed analytics for user submissions, progress tracking, and performance insights.
"""
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from bson import ObjectId
import logging
from collections import defaultdict

from app.cloud.mongodb import get_db
from app.cloud.coding_collections import CODE_SUBMISSIONS_COLLECTION, CODING_PROBLEMS_COLLECTION, CODING_STATS_COLLECTION
from app.models.coding import SubmissionStatus, DifficultyLevel, ProblemCategory

logger = logging.getLogger(__name__)


class AnalyticsService:
    """
    Service for submission analytics and user progress insights.
    """
    
    def __init__(self):
        self.db = None
    
    def _get_db(self):
        if self.db is None:
            self.db = get_db()
        return self.db
    
    async def get_user_submission_history(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
        status_filter: Optional[SubmissionStatus] = None,
        problem_id_filter: Optional[str] = None,
        language_filter: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get detailed submission history with filtering and analytics.
        """
        try:
            # Build filter query
            filter_query = {"user_id": user_id}
            
            if status_filter:
                filter_query["status"] = status_filter.value
            
            if problem_id_filter:
                filter_query["problem_id"] = problem_id_filter
            
            if language_filter:
                filter_query["language"] = language_filter
            
            if date_from or date_to:
                date_filter = {}
                if date_from:
                    date_filter["$gte"] = date_from
                if date_to:
                    date_filter["$lte"] = date_to
                filter_query["submitted_at"] = date_filter
            
            # Get submissions with problem details
            pipeline = [
                {"$match": filter_query},
                {"$sort": {"submitted_at": -1}},
                {
                    "$facet": {
                        "submissions": [
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
                                    "category": {"$arrayElemAt": ["$problem_info.category", 0]},
                                    "language": 1,
                                    "status": 1,
                                    "runtime": 1,
                                    "memory_used": 1,
                                    "passed_test_cases": 1,
                                    "total_test_cases": 1,
                                    "error_message": 1,
                                    "submitted_at": 1,
                                    "xp_gained": 1
                                }
                            }
                        ],
                        "total_count": [{"$count": "count"}],
                        "analytics": [
                            {
                                "$group": {
                                    "_id": None,
                                    "total_submissions": {"$sum": 1},
                                    "accepted_submissions": {
                                        "$sum": {"$cond": [{"$eq": ["$status", "accepted"]}, 1, 0]}
                                    },
                                    "avg_runtime": {"$avg": "$runtime"},
                                    "languages_used": {"$addToSet": "$language"},
                                    "problems_attempted": {"$addToSet": "$problem_id"}
                                }
                            }
                        ]
                    }
                }
            ]
            
            result = await self.db[CODE_SUBMISSIONS_COLLECTION].aggregate(pipeline).to_list(1)
            
            if not result:
                return {
                    "submissions": [],
                    "total_count": 0,
                    "analytics": {
                        "total_submissions": 0,
                        "accepted_submissions": 0,
                        "acceptance_rate": 0.0,
                        "avg_runtime": 0,
                        "languages_used": [],
                        "problems_attempted": 0
                    }
                }
            
            data = result[0]
            submissions = data["submissions"]
            total_count = data["total_count"][0]["count"] if data["total_count"] else 0
            analytics_data = data["analytics"][0] if data["analytics"] else {}
            
            # Calculate analytics
            total_subs = analytics_data.get("total_submissions", 0)
            accepted_subs = analytics_data.get("accepted_submissions", 0)
            acceptance_rate = (accepted_subs / total_subs * 100) if total_subs > 0 else 0.0
            
            analytics = {
                "total_submissions": total_subs,
                "accepted_submissions": accepted_subs,
                "acceptance_rate": round(acceptance_rate, 1),
                "avg_runtime": round(analytics_data.get("avg_runtime", 0), 2),
                "languages_used": analytics_data.get("languages_used", []),
                "problems_attempted": len(analytics_data.get("problems_attempted", []))
            }
            
            return {
                "submissions": submissions,
                "total_count": total_count,
                "analytics": analytics,
                "filters_applied": {
                    "status": status_filter.value if status_filter else None,
                    "problem_id": problem_id_filter,
                    "language": language_filter,
                    "date_from": date_from.isoformat() if date_from else None,
                    "date_to": date_to.isoformat() if date_to else None
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting submission history: {e}")
            return {"submissions": [], "total_count": 0, "analytics": {}}
    
    async def get_user_progress_analytics(self, user_id: str) -> Dict[str, Any]:
        """
        Get comprehensive progress analytics for a user.
        """
        try:
            # Get user stats
            user_stats = await self.db[CODING_STATS_COLLECTION].find_one({"user_id": user_id})
            if not user_stats:
                return {"error": "User stats not found"}
            
            # Get submission data for last 30 days
            thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
            
            pipeline = [
                {
                    "$match": {
                        "user_id": user_id,
                        "submitted_at": {"$gte": thirty_days_ago}
                    }
                },
                {
                    "$lookup": {
                        "from": CODING_PROBLEMS_COLLECTION,
                        "localField": "problem_id",
                        "foreignField": "problem_id",
                        "as": "problem_info"
                    }
                },
                {
                    "$addFields": {
                        "difficulty": {"$arrayElemAt": ["$problem_info.difficulty", 0]},
                        "category": {"$arrayElemAt": ["$problem_info.category", 0]}
                    }
                },
                {
                    "$facet": {
                        "daily_activity": [
                            {
                                "$group": {
                                    "_id": {
                                        "date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$submitted_at"}},
                                        "status": "$status"
                                    },
                                    "count": {"$sum": 1}
                                }
                            },
                            {"$sort": {"_id.date": 1}}
                        ],
                        "difficulty_breakdown": [
                            {
                                "$group": {
                                    "_id": {"difficulty": "$difficulty", "status": "$status"},
                                    "count": {"$sum": 1}
                                }
                            }
                        ],
                        "category_performance": [
                            {
                                "$group": {
                                    "_id": {"category": "$category", "status": "$status"},
                                    "count": {"$sum": 1},
                                    "avg_runtime": {"$avg": "$runtime"}
                                }
                            }
                        ],
                        "language_usage": [
                            {
                                "$group": {
                                    "_id": {"language": "$language", "status": "$status"},
                                    "count": {"$sum": 1}
                                }
                            }
                        ],
                        "runtime_trends": [
                            {
                                "$match": {"status": "accepted"}
                            },
                            {
                                "$group": {
                                    "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$submitted_at"}},
                                    "avg_runtime": {"$avg": "$runtime"},
                                    "submissions": {"$sum": 1}
                                }
                            },
                            {"$sort": {"_id": 1}}
                        ]
                    }
                }
            ]
            
            result = await self.db[CODE_SUBMISSIONS_COLLECTION].aggregate(pipeline).to_list(1)
            
            if not result:
                return {"error": "No submission data found"}
            
            data = result[0]
            
            # Process daily activity
            daily_activity = self._process_daily_activity(data["daily_activity"])
            
            # Process difficulty breakdown
            difficulty_stats = self._process_difficulty_breakdown(data["difficulty_breakdown"])
            
            # Process category performance
            category_stats = self._process_category_performance(data["category_performance"])
            
            # Process language usage
            language_stats = self._process_language_usage(data["language_usage"])
            
            # Process runtime trends
            runtime_trends = data["runtime_trends"]
            
            # Calculate overall metrics
            total_problems_solved = user_stats.get("total_problems_solved", 0)
            current_streak = user_stats.get("current_streak", 0)
            max_streak = user_stats.get("max_streak", 0)
            
            return {
                "overview": {
                    "total_xp": user_stats.get("total_xp", 0),
                    "current_rank": user_stats.get("current_rank", "newbie"),
                    "problems_solved": total_problems_solved,
                    "current_streak": current_streak,
                    "max_streak": max_streak,
                    "acceptance_rate": round(user_stats.get("acceptance_rate", 0) * 100, 1)
                },
                "daily_activity": daily_activity,
                "difficulty_breakdown": difficulty_stats,
                "category_performance": category_stats,
                "language_usage": language_stats,
                "runtime_trends": runtime_trends,
                "achievements": [
                    {
                        "id": achievement["id"],
                        "title": achievement["title"],
                        "description": achievement["description"],
                        "icon": achievement["icon"],
                        "unlocked_at": achievement["unlocked_at"]
                    }
                    for achievement in user_stats.get("achievements", [])
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting user progress analytics: {e}")
            return {"error": str(e)}
    
    async def get_problem_analytics(self, problem_id: str) -> Dict[str, Any]:
        """
        Get analytics for a specific problem.
        """
        try:
            # Get problem details
            problem = await self.db[CODING_PROBLEMS_COLLECTION].find_one({"problem_id": problem_id})
            if not problem:
                return {"error": "Problem not found"}
            
            # Get submission analytics
            pipeline = [
                {"$match": {"problem_id": problem_id}},
                {
                    "$facet": {
                        "status_breakdown": [
                            {
                                "$group": {
                                    "_id": "$status",
                                    "count": {"$sum": 1}
                                }
                            }
                        ],
                        "language_performance": [
                            {
                                "$group": {
                                    "_id": "$language",
                                    "total_submissions": {"$sum": 1},
                                    "accepted_submissions": {
                                        "$sum": {"$cond": [{"$eq": ["$status", "accepted"]}, 1, 0]}
                                    },
                                    "avg_runtime": {"$avg": "$runtime"}
                                }
                            }
                        ],
                        "runtime_distribution": [
                            {"$match": {"status": "accepted"}},
                            {
                                "$bucket": {
                                    "groupBy": "$runtime",
                                    "boundaries": [0, 100, 500, 1000, 2000, 5000, float('inf')],
                                    "default": "Other",
                                    "output": {"count": {"$sum": 1}}
                                }
                            }
                        ],
                        "daily_submissions": [
                            {
                                "$group": {
                                    "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$submitted_at"}},
                                    "submissions": {"$sum": 1},
                                    "accepted": {"$sum": {"$cond": [{"$eq": ["$status", "accepted"]}, 1, 0]}}
                                }
                            },
                            {"$sort": {"_id": -1}},
                            {"$limit": 30}
                        ]
                    }
                }
            ]
            
            result = await self.db[CODE_SUBMISSIONS_COLLECTION].aggregate(pipeline).to_list(1)
            
            if not result:
                analytics_data = {
                    "status_breakdown": [],
                    "language_performance": [],
                    "runtime_distribution": [],
                    "daily_submissions": []
                }
            else:
                analytics_data = result[0]
            
            # Calculate overall stats
            total_submissions = problem.get("total_submissions", 0)
            successful_submissions = problem.get("successful_submissions", 0)
            acceptance_rate = (successful_submissions / total_submissions * 100) if total_submissions > 0 else 0.0
            
            return {
                "problem_info": {
                    "problem_id": problem["problem_id"],
                    "title": problem["title"],
                    "difficulty": problem["difficulty"],
                    "category": problem["category"],
                    "tags": problem.get("tags", []),
                    "total_submissions": total_submissions,
                    "successful_submissions": successful_submissions,
                    "acceptance_rate": round(acceptance_rate, 1)
                },
                "status_breakdown": analytics_data["status_breakdown"],
                "language_performance": [
                    {
                        "language": lang_data["_id"],
                        "total_submissions": lang_data["total_submissions"],
                        "accepted_submissions": lang_data["accepted_submissions"],
                        "acceptance_rate": round(
                            (lang_data["accepted_submissions"] / lang_data["total_submissions"] * 100)
                            if lang_data["total_submissions"] > 0 else 0, 1
                        ),
                        "avg_runtime": round(lang_data["avg_runtime"], 2) if lang_data["avg_runtime"] else 0
                    }
                    for lang_data in analytics_data["language_performance"]
                ],
                "runtime_distribution": analytics_data["runtime_distribution"],
                "daily_submissions": analytics_data["daily_submissions"]
            }
            
        except Exception as e:
            logger.error(f"Error getting problem analytics: {e}")
            return {"error": str(e)}
    
    def _process_daily_activity(self, daily_data: List[Dict]) -> List[Dict[str, Any]]:
        """Process daily activity data for visualization."""
        activity_map = defaultdict(lambda: {"date": "", "accepted": 0, "failed": 0, "total": 0})
        
        for item in daily_data:
            date = item["_id"]["date"]
            status = item["_id"]["status"]
            count = item["count"]
            
            activity_map[date]["date"] = date
            if status == "accepted":
                activity_map[date]["accepted"] = count
            else:
                activity_map[date]["failed"] += count
            activity_map[date]["total"] += count
        
        return sorted(list(activity_map.values()), key=lambda x: x["date"])
    
    def _process_difficulty_breakdown(self, difficulty_data: List[Dict]) -> Dict[str, Any]:
        """Process difficulty breakdown data."""
        stats = {
            "easy": {"attempted": 0, "solved": 0, "accuracy": 0.0},
            "medium": {"attempted": 0, "solved": 0, "accuracy": 0.0},
            "hard": {"attempted": 0, "solved": 0, "accuracy": 0.0}
        }
        
        for item in difficulty_data:
            difficulty = item["_id"]["difficulty"]
            status = item["_id"]["status"]
            count = item["count"]
            
            if difficulty in stats:
                stats[difficulty]["attempted"] += count
                if status == "accepted":
                    stats[difficulty]["solved"] += count
        
        # Calculate accuracy
        for difficulty in stats:
            if stats[difficulty]["attempted"] > 0:
                stats[difficulty]["accuracy"] = round(
                    stats[difficulty]["solved"] / stats[difficulty]["attempted"] * 100, 1
                )
        
        return stats
    
    def _process_category_performance(self, category_data: List[Dict]) -> Dict[str, Any]:
        """Process category performance data."""
        category_stats = defaultdict(lambda: {"attempted": 0, "solved": 0, "avg_runtime": 0})
        
        for item in category_data:
            category = item["_id"]["category"]
            status = item["_id"]["status"]
            count = item["count"]
            avg_runtime = item.get("avg_runtime", 0)
            
            if category:
                category_stats[category]["attempted"] += count
                if status == "accepted":
                    category_stats[category]["solved"] += count
                    category_stats[category]["avg_runtime"] = avg_runtime
        
        # Convert to list format with accuracy calculation
        result = []
        for category, stats in category_stats.items():
            accuracy = (stats["solved"] / stats["attempted"] * 100) if stats["attempted"] > 0 else 0
            result.append({
                "category": category,
                "attempted": stats["attempted"],
                "solved": stats["solved"],
                "accuracy": round(accuracy, 1),
                "avg_runtime": round(stats["avg_runtime"], 2)
            })
        
        return sorted(result, key=lambda x: x["solved"], reverse=True)
    
    def _process_language_usage(self, language_data: List[Dict]) -> List[Dict[str, Any]]:
        """Process language usage data."""
        language_stats = defaultdict(lambda: {"attempted": 0, "solved": 0})
        
        for item in language_data:
            language = item["_id"]["language"]
            status = item["_id"]["status"]
            count = item["count"]
            
            language_stats[language]["attempted"] += count
            if status == "accepted":
                language_stats[language]["solved"] += count
        
        # Convert to list format
        result = []
        for language, stats in language_stats.items():
            accuracy = (stats["solved"] / stats["attempted"] * 100) if stats["attempted"] > 0 else 0
            result.append({
                "language": language,
                "attempted": stats["attempted"],
                "solved": stats["solved"],
                "accuracy": round(accuracy, 1)
            })
        
        return sorted(result, key=lambda x: x["attempted"], reverse=True)


# Global service instance - will be initialized when needed
analytics_service = None

def get_analytics_service():
    global analytics_service
    if analytics_service is None:
        analytics_service = AnalyticsService()
    return analytics_service