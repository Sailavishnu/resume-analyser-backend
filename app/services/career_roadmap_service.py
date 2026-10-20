from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from fastapi import HTTPException
from pymongo.database import Database

from app.cloud import collections as C
from app.ml.gemini_service import gemini_interview_service


class CareerRoadmapService:
    def __init__(self, db: Database):
        self.collection = db[C.ROADMAPS]

    @staticmethod
    def _serialize(document: dict[str, Any] | None) -> dict[str, Any] | None:
        if not document:
            return None
        result = {key: value for key, value in document.items() if key != "_id"}
        result["id"] = str(document["_id"])
        if result.get("student_id") is not None:
            result["student_id"] = str(result["student_id"])
        for key in ("created_at", "updated_at"):
            if isinstance(result.get(key), datetime):
                result[key] = result[key].isoformat()
        return result

    def get(self, student_id: str) -> dict[str, Any] | None:
        return self._serialize(self.collection.find_one({"student_id": ObjectId(student_id)}))

    async def generate(self, student_id: str, intake: dict[str, Any]) -> dict[str, Any]:
        generated = await gemini_interview_service.generate_career_roadmap(intake)
        if not generated:
            raise HTTPException(status_code=503, detail="The career planning service could not create a valid roadmap. Please try again.")

        now = datetime.now(timezone.utc)
        phase_rows = []
        week = 1
        for index, phase in enumerate(generated["phases"]):
            end_week = week + phase["durationWeeks"] - 1
            phase_rows.append({
                "id": f"phase-{index + 1}",
                **phase,
                "startWeek": week,
                "endWeek": end_week,
                "status": "active" if index == 0 else "locked",
            })
            week = end_week + 1

        document = {
            "student_id": ObjectId(student_id),
            "target_role": intake["targetRole"],
            "intake": intake,
            "title": generated["title"],
            "summary": generated["summary"],
            "total_weeks": generated["totalWeeks"],
            "weekly_hours": intake["hoursPerWeek"],
            "progress": 0,
            "phases": phase_rows,
            "updated_at": now,
        }
        self.collection.update_one(
            {"student_id": ObjectId(student_id)},
            {"$set": document, "$setOnInsert": {"created_at": now}},
            upsert=True,
        )
        return self.get(student_id)  # type: ignore[return-value]

    def complete_phase(self, student_id: str, phase_id: str) -> dict[str, Any]:
        roadmap = self.collection.find_one({"student_id": ObjectId(student_id)})
        if not roadmap:
            raise HTTPException(status_code=404, detail="Generate a roadmap before completing a phase")
        phases = roadmap.get("phases", [])
        index = next((i for i, phase in enumerate(phases) if phase.get("id") == phase_id), None)
        if index is None:
            raise HTTPException(status_code=404, detail="Roadmap phase not found")
        if phases[index].get("status") == "locked":
            raise HTTPException(status_code=409, detail="Complete the active phase before unlocking this phase")
        phases[index]["status"] = "completed"
        if index + 1 < len(phases) and phases[index + 1].get("status") == "locked":
            phases[index + 1]["status"] = "active"
        completed = sum(phase.get("status") == "completed" for phase in phases)
        self.collection.update_one(
            {"_id": roadmap["_id"], "student_id": ObjectId(student_id)},
            {"$set": {"phases": phases, "progress": round(completed * 100 / len(phases)), "updated_at": datetime.now(timezone.utc)}},
        )
        return self.get(student_id)  # type: ignore[return-value]
