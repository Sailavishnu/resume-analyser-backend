"""
Gemini LLM Service for AI Mock Interview Generation & Evaluation.

Uses the Gemini API key from .env to generate:
1. Resume-grounded interview questions from the student's primary resume.
2. Subject/domain-specific general interview questions if no resume is uploaded.
3. Deep answer evaluation and adaptive multi-turn follow-ups.
Falls back automatically to local Sentence-BERT NLP if the API key is unavailable or rate-limited.
"""
import os
import json
import logging
import requests
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class GeminiInterviewService:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY", "").strip()
        # Candidate model fallbacks
        self.models = [
            "gemini-3.5-flash-lite",
            "gemini-2.5-flash",
            "gemini-flash-latest",
            "gemini-pro-latest"
        ]

    def _call_gemini(self, prompt: str, temperature: float = 0.7) -> Optional[str]:
        """Execute a text generation call to Gemini with model fallback."""
        if not self.api_key:
            logger.warning("[GeminiService] GEMINI_API_KEY is not set.")
            return None

        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": 1024
            }
        }

        for model_name in self.models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.api_key}"
            try:
                res = requests.post(url, headers=headers, json=payload, timeout=12)
                if res.status_code == 200:
                    data = res.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        if text:
                            return text.strip()
                elif res.status_code in (429, 503):
                    # Rate limit or busy, try next model
                    continue
                else:
                    logger.warning(f"[GeminiService] Model {model_name} returned status {res.status_code}")
            except Exception as e:
                logger.warning(f"[GeminiService] Model {model_name} failed: {e}")

        return None

    def generate_resume_questions(
        self,
        resume_data: Dict[str, Any],
        target_role: str = "Software Engineer",
        total_questions: int = 3
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Generates interview questions strictly grounded in the candidate's PRIMARY resume.
        """
        projects = resume_data.get("projects", [])
        experience = resume_data.get("experience", [])
        skills = resume_data.get("skills", {})

        prompt = f"""
You are a Principal Software Engineering Interviewer conducting a technical interview for a {target_role} position.
Here is the candidate's primary resume details:
- Projects: {json.dumps(projects[:3])}
- Work History: {json.dumps(experience[:2])}
- Skills: {json.dumps(skills)}

Generate exactly {total_questions} tailored interview questions directly grounded in their primary resume:
1. Deep-dive into their most prominent project architecture, trade-offs, and how they handled data/components.
2. System reliability, debugging, or database scaling based on their work or secondary project.
3. Role alignment / architectural collaboration question for a {target_role}.

Return ONLY a valid JSON array of objects with these exact keys:
[
  {{
    "id": "q_1",
    "category": "Project Architecture & Deep Dive",
    "question": "Question text here...",
    "context_source": "Source project or experience name",
    "expected_concepts": ["concept1", "concept2", "concept3"],
    "target_skills": ["Skill1", "Skill2"],
    "difficulty": "Intermediate"
  }}
]
Do not include any markdown or code blocks around the JSON. Output only raw JSON.
"""
        response_text = self._call_gemini(prompt)
        if not response_text:
            return None

        try:
            cleaned = response_text.replace("```json", "").replace("```", "").strip()
            questions = json.loads(cleaned)
            if isinstance(questions, list) and len(questions) > 0:
                for idx, q in enumerate(questions):
                    q["id"] = f"q_{idx + 1}"
                    q["is_rag_grounded"] = True
                return questions[:total_questions]
        except Exception as e:
            logger.warning(f"[GeminiService] Failed to parse questions JSON: {e}")

        return None

    def generate_general_domain_questions(
        self,
        domain: str = "Fullstack Web Development",
        target_role: str = "Software Engineer",
        total_questions: int = 3
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Generates questions for students without an uploaded resume based on their chosen subject/domain.
        """
        prompt = f"""
You are a Principal Technical Interviewer conducting a mock interview for a candidate who has not yet uploaded a resume.
The candidate selected the domain / subject: "{domain}" for the target role: "{target_role}".

Generate exactly {total_questions} realistic, challenging interview questions:
1. Core technical concepts, internals, and execution flow in {domain}.
2. Practical system design / scenario-based problem solving in {domain}.
3. Edge case debugging, concurrency, performance optimization, or architectural trade-offs in {domain}.

Return ONLY a valid JSON array of objects with these exact keys:
[
  {{
    "id": "q_1",
    "category": "{domain} - Core Concepts",
    "question": "Question text here...",
    "context_source": "General Domain: {domain}",
    "expected_concepts": ["concept1", "concept2", "concept3"],
    "target_skills": ["Skill1", "Skill2"],
    "difficulty": "Intermediate"
  }}
]
Do not include any markdown or code blocks around the JSON. Output only raw JSON.
"""
        response_text = self._call_gemini(prompt)
        if not response_text:
            return None

        try:
            cleaned = response_text.replace("```json", "").replace("```", "").strip()
            questions = json.loads(cleaned)
            if isinstance(questions, list) and len(questions) > 0:
                for idx, q in enumerate(questions):
                    q["id"] = f"q_{idx + 1}"
                    q["is_rag_grounded"] = False
                return questions[:total_questions]
        except Exception as e:
            logger.warning(f"[GeminiService] Failed to parse domain questions JSON: {e}")

        return None

    def generate_adaptive_followup(
        self,
        previous_question: str,
        candidate_answer: str,
        eval_score: int,
        domain_or_context: str,
        next_index: int
    ) -> Optional[Dict[str, Any]]:
        """
        Generates a natural conversational follow-up question based on the candidate's exact words.
        """
        prompt = f"""
You are a Senior Technical Interviewer.
Previous Question: "{previous_question}"
Candidate's Answer: "{candidate_answer}"
Evaluation Score: {eval_score}/100
Context: {domain_or_context}

Analyze what specific technologies, libraries, or architectural patterns the candidate mentioned.
Ask a natural, probing follow-up question (Question {next_index}) that:
- Drills deeper into their claimed tools (e.g. how they handled cache invalidation, race conditions, index performance, or error boundaries).
- Tests architectural trade-offs and edge cases.

Return ONLY a valid JSON object:
{{
  "id": "q_{next_index}",
  "category": "Adaptive Deep-Dive",
  "question": "Follow-up question text here...",
  "context_source": "Follow-up on previous answer claims",
  "expected_concepts": ["trade-offs", "scalability", "error handling"],
  "target_skills": ["Architecture", "System Design"],
  "difficulty": "Advanced",
  "is_adaptive": true
}}
Do not include markdown blocks. Output only raw JSON.
"""
        response_text = self._call_gemini(prompt)
        if not response_text:
            return None

        try:
            cleaned = response_text.replace("```json", "").replace("```", "").strip()
            q = json.loads(cleaned)
            if isinstance(q, dict) and "question" in q:
                q["id"] = f"q_{next_index}"
                q["is_adaptive"] = True
                return q
        except Exception as e:
            logger.warning(f"[GeminiService] Failed to parse adaptive question JSON: {e}")

        return None


# Global singleton instance
gemini_interview_service = GeminiInterviewService()
