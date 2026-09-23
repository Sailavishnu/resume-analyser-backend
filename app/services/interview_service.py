"""
AI Mock Interview Service

Handles mock interview session lifecycles, real-time NLP response grading,
and adaptive follow-up generation.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
from bson import ObjectId
from pymongo.database import Database

from app.db import collections as C
from app.core.exceptions import NotFoundError, ValidationError, ForbiddenError
from app.utils.dates import utc_now
from app.ml.interview_engine import ai_interview_engine


class AIInterviewService:
    def __init__(self, db: Database):
        self.db = db
        self.engine = ai_interview_engine

    async def start_interview(
        self,
        student_id: str,
        target_role: str = "Software Engineer",
        interview_type: str = "technical",
        resume_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Starts a new AI Interview session tailored to candidate's real resume data.
        """
        # Find candidate resume
        resume = None
        if resume_id:
            try:
                resume = self.db[C.RESUMES].find_one({"_id": ObjectId(resume_id), "student_id": ObjectId(student_id)})
            except Exception:
                pass
        
        if not resume:
            # Get latest parsed resume for student
            resume = self.db[C.RESUMES].find_one(
                {"student_id": ObjectId(student_id)},
                sort=[("created_at", -1)]
            )

        parsed_data = {}
        if resume:
            parsed_data = resume.get("parsed_data") or resume.get("parsedData") or {}

        # Fallback if no resume uploaded yet
        if not parsed_data:
            parsed_data = {
                "skills": {"languages": ["JavaScript", "Python"], "frameworks": ["React", "FastAPI"], "tools": ["Git", "Docker"]},
                "projects": [{"title": "Web Application", "tech_stack": ["React", "Node.js", "MongoDB"]}],
                "experience": []
            }

        # Generate tailored questions
        questions = self.engine.generate_interview_questions(
            resume_data=parsed_data,
            target_role=target_role,
            total_questions=3
        )

        session_doc = {
            "student_id": ObjectId(student_id),
            "target_role": target_role,
            "interview_type": interview_type,
            "resume_id": resume["_id"] if resume else None,
            "status": "in_progress",
            "current_question_index": 0,
            "total_questions": 3,
            "questions": questions,
            "answers": [],
            "overall_score": None,
            "created_at": utc_now(),
            "updated_at": utc_now()
        }

        result = self.db[C.MOCK_INTERVIEWS].insert_one(session_doc)
        session_id = str(result.inserted_id)

        # Format initial question for client
        first_question = questions[0] if questions else None

        return {
            "session_id": session_id,
            "interview_id": session_id,
            "target_role": target_role,
            "status": "in_progress",
            "current_question_index": 0,
            "total_questions": 3,
            "current_question": first_question,
            "questions": questions,
            "answers": []
        }

    async def submit_answer(
        self,
        session_id: str,
        student_id: str,
        answer_text: str
    ) -> Dict[str, Any]:
        """
        Evaluates submitted answer with local NLP and either:
        - Generates dynamic adaptive next question
        - Completes interview and outputs final performance analysis
        """
        try:
            session = self.db[C.MOCK_INTERVIEWS].find_one({"_id": ObjectId(session_id), "student_id": ObjectId(student_id)})
        except Exception:
            session = None

        if not session:
            raise NotFoundError(f"Interview session {session_id} not found.")

        if session.get("status") == "completed":
            raise ValidationError("Interview session has already been completed.")

        curr_idx = session.get("current_question_index", 0)
        questions = session.get("questions", [])

        if curr_idx >= len(questions):
            raise ValidationError("All questions already answered.")

        active_question = questions[curr_idx]

        # 1. NLP Semantic Evaluation
        eval_result = self.engine.evaluate_answer(active_question, answer_text)

        answer_record = {
            "question_id": active_question.get("id"),
            "question_text": active_question.get("question"),
            "category": active_question.get("category"),
            "answer_text": answer_text,
            "score": eval_result.get("score"),
            "relevance": eval_result.get("relevance"),
            "technical_depth": eval_result.get("technical_depth"),
            "clarity": eval_result.get("clarity"),
            "matched_keywords": eval_result.get("matched_keywords", []),
            "missed_keywords": eval_result.get("missed_keywords", []),
            "feedback": eval_result.get("feedback"),
            "submitted_at": utc_now()
        }

        updated_answers = session.get("answers", []) + [answer_record]
        next_idx = curr_idx + 1
        is_completed = (next_idx >= session.get("total_questions", 3))

        next_question = None

        if not is_completed:
            # Get Resume Data for adaptive branch
            resume_data = {}
            if session.get("resume_id"):
                resume = self.db[C.RESUMES].find_one({"_id": session["resume_id"]})
                if resume:
                    resume_data = resume.get("parsed_data") or resume.get("parsedData") or {}

            # Generate Adaptive Follow-up
            next_question = self.engine.generate_adaptive_followup(
                current_question=active_question,
                answer_text=answer_text,
                eval_result=eval_result,
                resume_data=resume_data,
                next_question_index=next_idx + 1
            )
            
            # Update questions list in session
            if next_idx < len(questions):
                questions[next_idx] = next_question
            else:
                questions.append(next_question)

        # Calculate final summary if finished
        overall_score = None
        report = None
        if is_completed:
            scores = [a.get("score", 70) for a in updated_answers]
            overall_score = int(round(sum(scores) / len(scores))) if scores else 70
            tech_depth = int(round(sum(a.get("technical_depth", 70) for a in updated_answers) / len(updated_answers)))
            clarity = int(round(sum(a.get("clarity", 70) for a in updated_answers) / len(updated_answers)))

            report = {
                "overall_score": overall_score,
                "technical_depth": tech_depth,
                "clarity": clarity,
                "total_questions_answered": len(updated_answers),
                "summary": "High Potential Candidate - Strong Technical Articulation" if overall_score >= 80 else "Good Candidate - Anchor answers with quantified engineering trade-offs",
                "completed_at": utc_now()
            }

        # Update MongoDB
        update_fields = {
            "current_question_index": next_idx,
            "answers": updated_answers,
            "questions": questions,
            "status": "completed" if is_completed else "in_progress",
            "updated_at": utc_now()
        }
        if is_completed:
            update_fields["overall_score"] = overall_score
            update_fields["completed_at"] = utc_now()
            update_fields["report"] = report

        self.db[C.MOCK_INTERVIEWS].update_one(
            {"_id": ObjectId(session_id)},
            {"$set": update_fields}
        )

        return {
            "session_id": session_id,
            "interview_id": session_id,
            "is_completed": is_completed,
            "current_question_index": next_idx,
            "latest_evaluation": eval_result,
            "next_question": next_question,
            "answers": updated_answers,
            "report": report
        }

    async def get_interview(self, session_id: str, student_id: str) -> Dict[str, Any]:
        """Get interview session details."""
        try:
            session = self.db[C.MOCK_INTERVIEWS].find_one({"_id": ObjectId(session_id), "student_id": ObjectId(student_id)})
        except Exception:
            session = None

        if not session:
            raise NotFoundError(f"Interview session {session_id} not found.")

        session["id"] = str(session["_id"])
        session["session_id"] = str(session["_id"])
        del session["_id"]
        return session

    async def get_student_interviews(self, student_id: str) -> List[Dict[str, Any]]:
        """Get all interviews for student."""
        sessions = list(self.db[C.MOCK_INTERVIEWS].find(
            {"student_id": ObjectId(student_id)},
            sort=[("created_at", -1)]
        ))
        
        result = []
        for s in sessions:
            s["id"] = str(s["_id"])
            s["session_id"] = str(s["_id"])
            del s["_id"]
            result.append(s)
        return result
