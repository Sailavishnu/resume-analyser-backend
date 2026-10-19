"""
Gemini LLM Service for AI Mock Interview Generation & Evaluation.

Uses the Gemini API key from .env to generate:
1. Resume-grounded interview questions from the student's primary resume.
2. Subject/domain-specific general interview questions if no resume is uploaded.
3. Deep answer evaluation and adaptive multi-turn follow-ups.
Falls back automatically to local Sentence-BERT NLP if the API key is unavailable or rate-limited.
"""
import asyncio
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

    def generate_resume_enhancements(self, target_role: str, source_bullets: List[Dict[str, str]]) -> Optional[List[Dict[str, str]]]:
        """Rewrite only supplied resume bullets for the user's chosen target role."""
        prompt = f"""
You are a careful resume editor. Tailor the supplied candidate statements to this target role: {target_role!r}.
Return JSON only, as an array of objects with keys: section, original_text, suggested_text, reason.
Return at most six suggestions. Every original_text must exactly match one supplied source bullet.
Preserve the candidate's actual experience, technologies, scope, and numbers. Never add tools, skills,
metrics, responsibilities, employers, certifications, or outcomes that do not appear in the source.
Improve clarity, action verbs, specificity, and alignment to the target role using only supported facts.
If a source bullet cannot be improved honestly, omit it. Do not add generic summary text.

Source bullets:
{json.dumps(source_bullets[:20], ensure_ascii=False)}
"""
        response_text = self._call_gemini(prompt, temperature=0.2)
        if not response_text:
            return None
        try:
            cleaned = response_text.replace("```json", "").replace("```", "").strip()
            suggestions = json.loads(cleaned)
            if not isinstance(suggestions, list):
                return None
            allowed = {item["original_text"].strip() for item in source_bullets}
            validated = []
            for item in suggestions[:6]:
                if not isinstance(item, dict):
                    continue
                original = str(item.get("original_text", "")).strip()
                suggested = str(item.get("suggested_text", "")).strip()
                if original not in allowed or not suggested:
                    continue
                validated.append({
                    "section": str(item.get("section", "Experience"))[:120],
                    "original_text": original,
                    "suggested_text": suggested[:2000],
                    "reason": str(item.get("reason", "Improves clarity for the selected target role."))[:500],
                })
            return validated
        except (ValueError, TypeError, KeyError) as e:
            logger.warning("[GeminiService] Failed to parse resume enhancements: %s", e)
            return None

    async def evaluate_practice_writing(
        self, challenge_name: str, instructions: str, candidate_profile: Any, answer: str,
        target_role: str | None = None,
    ) -> Optional[Dict[str, Any]]:
        """Score a writing exercise against its supplied facts and rubric."""
        prompt = f"""
Evaluate a student's resume-writing practice response. This is feedback for learning, not hiring.
Challenge: {challenge_name}
Instructions: {instructions}
Target role: {target_role or 'Use the role named in the challenge context'}
Candidate facts (the only facts the student may claim): {json.dumps(candidate_profile, ensure_ascii=False)}
Student response: {json.dumps(answer, ensure_ascii=False)}

Score 0-100 using these criteria (each 0-100): clarity, relevance, specificity, evidence_fidelity.
Reward useful detail only when supported by the candidate facts. Do not reward invented metrics,
skills, results, seniority, or responsibilities. Treat omissions as opportunities for improvement,
not proof the candidate lacks a skill. Give concise, actionable strengths and improvements.
An optional suggestedAnswer must use only supported facts and must not add metrics or achievements.
Return only valid JSON in this shape:
{{"score": 0, "criteriaScores": {{"clarity": 0, "relevance": 0, "specificity": 0, "evidence_fidelity": 0}},
"feedback": {{"strengths": ["..."], "improvements": ["..."], "explanation": "..."}}, "suggestedAnswer": "..."}}
"""
        response_text = await asyncio.to_thread(self._call_gemini, prompt, temperature=0.2)
        if not response_text:
            return None
        try:
            cleaned = response_text.replace("```json", "").replace("```", "").strip()
            result = json.loads(cleaned)
            if not isinstance(result, dict):
                return None
            return result
        except (ValueError, TypeError) as exc:
            logger.warning("[GeminiService] Failed to parse practice writing evaluation: %s", exc)
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
