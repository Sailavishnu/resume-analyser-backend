"""
AI Mock Interview Engine (100% Local NLP & Semantic Analysis)

Features:
1. Dynamic Resume-Driven Question Generation (extracts real projects, skills, experience from resume)
2. Semantic & Technical Answer Evaluation (using local spaCy + Sentence-BERT embeddings)
3. Adaptive Dynamic Follow-Up Generation (tailors next question based on candidate's previous response)
"""
import re
import logging
from typing import Dict, List, Any, Optional
import numpy as np

from app.ml.nlp_processor import nlp_processor
from app.ml.embeddings import embedding_service

logger = logging.getLogger(__name__)


class AIInterviewEngine:
    """
    Intelligent HR & Technical Interview Simulator.
    Runs completely on local NLP and Sentence-BERT models with zero paid API keys.
    """
    
    def __init__(self):
        self.nlp = nlp_processor
        self.embeddings = embedding_service

    def generate_interview_questions(
        self, 
        resume_data: Dict[str, Any], 
        target_role: str = "Software Engineer",
        total_questions: int = 4
    ) -> List[Dict[str, Any]]:
        """
        Generates structured, highly customized interview questions directly from resume entities.
        """
        # Ensure models are loaded
        if not self.nlp.is_loaded:
            try:
                self.nlp.load()
            except Exception as e:
                logger.warning(f"spaCy load warning: {e}")
                
        if not self.embeddings.is_loaded:
            try:
                self.embeddings.load_model()
            except Exception as e:
                logger.warning(f"Embeddings load warning: {e}")

        # Extract Resume Assets
        projects = resume_data.get("projects", [])
        experience = resume_data.get("experience", [])
        skills_dict = resume_data.get("skills", {})
        
        all_skills = []
        if isinstance(skills_dict, dict):
            for cat, items in skills_dict.items():
                if isinstance(items, list):
                    all_skills.extend(items)
        elif isinstance(skills_dict, list):
            all_skills = skills_dict
            
        all_skills = [str(s).strip() for s in all_skills if str(s).strip()]
        if not all_skills:
            all_skills = ["JavaScript", "Python", "React", "REST APIs", "SQL"]

        questions = []
        q_idx = 1

        # ─── 1. Primary Project Deep-Dive Question ───────────────────────────
        if projects and len(projects) > 0:
            top_proj = projects[0]
            p_name = top_proj.get("title") or top_proj.get("name") or "Key Project"
            tech_stack = top_proj.get("tech_stack") or top_proj.get("technologies") or []
            if isinstance(tech_stack, str):
                tech_stack = [t.strip() for t in tech_stack.split(",") if t.strip()]
            
            tech_str = ", ".join(tech_stack[:3]) if tech_stack else (all_skills[0] if all_skills else "modern tech stack")
            
            questions.append({
                "id": f"q_{q_idx}",
                "category": "Project Architecture & Engineering",
                "question": f"In your resume, you highlighted '{p_name}' built using {tech_str}. Can you walk me through the system architecture and the biggest engineering trade-off or bottleneck you encountered while building it?",
                "context_source": f"Project: {p_name}",
                "expected_concepts": ["architecture", "data flow", "trade-off", "performance", "optimization", "database", "api", "scalability"],
                "target_skills": tech_stack if tech_stack else all_skills[:3],
                "difficulty": "Intermediate"
            })
            q_idx += 1

        # ─── 2. Core Technical Skills & Asynchronous Handling ────────────────
        top_skills_str = ", ".join(all_skills[:3])
        questions.append({
            "id": f"q_{q_idx}",
            "category": "Technical Core & Scalability",
            "question": f"As a candidate for {target_role} with strong skills in {top_skills_str}, how do you ensure high performance, error resilience, and secure state/data handling when building production services?",
            "context_source": f"Skills: {top_skills_str}",
            "expected_concepts": ["error handling", "caching", "state management", "async", "security", "jwt", "sanitization", "concurrency"],
            "target_skills": all_skills[:4],
            "difficulty": "Advanced"
        })
        q_idx += 1

        # ─── 3. Experience / Problem Solving Question ────────────────────────
        if experience and len(experience) > 0:
            top_exp = experience[0]
            company = top_exp.get("company") or "your previous company/internship"
            position = top_exp.get("position") or top_exp.get("role") or "developer"
            questions.append({
                "id": f"q_{q_idx}",
                "category": "Work Experience & Incident Resolution",
                "question": f"During your work at {company} as a {position}, describe a critical production bug or performance issue you diagnosed. What debugging tools and methodologies did you use to resolve it?",
                "context_source": f"Experience: {company} ({position})",
                "expected_concepts": ["debugging", "root cause", "logs", "monitoring", "git", "profiling", "resolution", "testing"],
                "target_skills": ["Debugging", "Problem Solving", "Monitoring"],
                "difficulty": "Intermediate"
            })
            q_idx += 1
        elif len(projects) > 1:
            second_proj = projects[1]
            p2_name = second_proj.get("title") or second_proj.get("name") or "Secondary Project"
            questions.append({
                "id": f"q_{q_idx}",
                "category": "System Design & Integration",
                "question": f"Looking at your project '{p2_name}', how did you design the API endpoints and ensure database consistency across multiple user interactions?",
                "context_source": f"Project: {p2_name}",
                "expected_concepts": ["rest api", "crud", "transactions", "indexing", "validation", "status codes", "schema"],
                "target_skills": all_skills[2:5] if len(all_skills) >= 5 else all_skills,
                "difficulty": "Intermediate"
            })
            q_idx += 1

        # ─── 4. HR Behavioral & Collaboration Question ───────────────────────
        questions.append({
            "id": f"q_{q_idx}",
            "category": "Behavioral & Engineering Leadership",
            "question": f"In a fast-paced team environment for a {target_role} role, how do you handle disagreements over code architecture during pull request reviews, and how do you prioritize technical debt versus shipping new features?",
            "context_source": f"Role Fit: {target_role}",
            "expected_concepts": ["code review", "communication", "collaboration", "technical debt", "documentation", "testing", "compromise"],
            "target_skills": ["Code Review", "Agile", "Teamwork"],
            "difficulty": "Comprehensive"
        })

        return questions[:total_questions]

    def evaluate_answer(
        self, 
        question: Dict[str, Any], 
        answer_text: str
    ) -> Dict[str, Any]:
        """
        Evaluates the candidate's answer using:
        1. Sentence-BERT semantic similarity against expected domain concepts
        2. spaCy keyword and technical token extraction
        3. Depth, structure, and STAR method markers
        """
        text = (answer_text or "").strip()
        words = text.split()
        word_count = len(words)

        if word_count == 0:
            return {
                "score": 0,
                "relevance": 0,
                "technical_depth": 0,
                "clarity": 0,
                "matched_keywords": [],
                "missed_keywords": question.get("expected_concepts", []),
                "feedback": "No answer provided. Please articulate your response with technical examples."
            }

        # 1. Semantic Similarity Calculation (Sentence-BERT)
        expected_concepts = question.get("expected_concepts", [])
        expected_context = f"Question: {question.get('question')} | Key concepts: {', '.join(expected_concepts)}"
        
        try:
            ans_emb = self.embeddings.encode_text(text)
            exp_emb = self.embeddings.encode_text(expected_context)
            similarity = float(self.embeddings.calculate_similarity(ans_emb, exp_emb))
            semantic_score = np.clip(similarity * 100, 30, 98)
        except Exception as e:
            logger.warning(f"Semantic scoring fallback: {e}")
            semantic_score = 70.0

        # 2. Keyword & Concept Matching
        text_lower = text.lower()
        matched_keywords = []
        for kw in expected_concepts + question.get("target_skills", []):
            kw_clean = str(kw).lower().strip()
            if kw_clean and (kw_clean in text_lower or re.search(r'\b' + re.escape(kw_clean) + r'\b', text_lower)):
                if kw not in matched_keywords:
                    matched_keywords.append(kw)

        missed_keywords = [kw for kw in expected_concepts if kw not in matched_keywords]

        # 3. Technical Depth & Structure Scoring
        # Bonus for structured indicators: "because", "implemented", "optimized", "reduced", "prevented", "resulted"
        star_markers = ["implemented", "optimized", "designed", "handled", "configured", "reduced", "improved", "architecture", "tradeoff", "tested"]
        star_count = sum(1 for marker in star_markers if marker in text_lower)
        
        depth_score = 50.0
        depth_score += min(25, len(matched_keywords) * 6)
        depth_score += min(15, star_count * 4)
        if word_count >= 40:
            depth_score += 10
        elif word_count < 15:
            depth_score -= 15
        depth_score = float(np.clip(depth_score, 35, 96))

        # 4. Clarity & Coherence
        clarity_score = 65.0
        if 30 <= word_count <= 180:
            clarity_score += 20
        elif word_count > 180:
            clarity_score += 10
        else:
            clarity_score -= 10
        clarity_score = float(np.clip(clarity_score, 40, 95))

        # 5. Composite Score
        overall_score = int(round(
            (semantic_score * 0.40) + 
            (depth_score * 0.40) + 
            (clarity_score * 0.20)
        ))
        overall_score = max(40, min(97, overall_score))

        # 6. Generate Actionable Feedback
        if len(matched_keywords) >= 3 and overall_score >= 78:
            feedback = f"Strong and articulate response. You clearly explained key technical aspects ({', '.join(matched_keywords[:3])}) with good engineering context."
        elif len(matched_keywords) >= 1:
            feedback = f"Solid foundation covering {', '.join(matched_keywords[:2])}. To make it stand out, discuss trade-offs and quantify performance impact (e.g., latency, throughput)."
        else:
            suggested = missed_keywords[:3] if missed_keywords else ["architecture", "error handling", "performance"]
            feedback = f"Your answer is on the right track but lacks technical specificity. Try anchoring your response with concepts like: {', '.join(suggested)}."

        return {
            "score": overall_score,
            "relevance": int(round(semantic_score)),
            "technical_depth": int(round(depth_score)),
            "clarity": int(round(clarity_score)),
            "matched_keywords": matched_keywords,
            "missed_keywords": missed_keywords,
            "feedback": feedback
        }

    def generate_adaptive_followup(
        self,
        current_question: Dict[str, Any],
        answer_text: str,
        eval_result: Dict[str, Any],
        resume_data: Dict[str, Any],
        next_question_index: int
    ) -> Dict[str, Any]:
        """
        Dynamically formulates the NEXT question adapting directly to what the candidate answered.
        """
        text_lower = (answer_text or "").lower()
        score = eval_result.get("score", 70)
        
        # Adaptive Branch 1: Drill-down on specific architectural keywords they mentioned
        tech_triggers = {
            "caching": ("Caching & Eviction", "You mentioned caching in your answer. What cache invalidation strategy (like TTL or write-through) and eviction policy (like LRU) did you use to prevent stale data?"),
            "redis": ("Redis State & Consistency", "Since you utilized Redis, how did you handle potential Redis connection failures or cache stampedes under high concurrent load?"),
            "postgresql": ("SQL Indexing & Query Tuning", "You mentioned PostgreSQL. How did you design your database indexes and analyze slow queries using EXPLAIN ANALYZE?"),
            "mongodb": ("NoSQL Data Modeling", "Regarding your use of MongoDB, how did you structure your document schemas to balance embedding vs referencing for high read/write ratios?"),
            "docker": ("Containerization & CI/CD", "You touched on Docker. How do you optimize multi-stage Docker builds to minimize final production image sizes and security vulnerabilities?"),
            "jwt": ("Authentication & Token Security", "You mentioned JWT/token authentication. How do you securely handle token expiration, refresh tokens, and revocation in distributed systems?"),
            "async": ("Concurrency & Event Loop", "You highlighted asynchronous handling. How does the event loop process microtasks vs macrotasks under heavy I/O pressure?"),
            "react": ("React State & Virtual DOM", "You discussed React components. How do you prevent unnecessary child re-renders and manage shared state across complex page trees?"),
            "microservices": ("Distributed Communication", "You mentioned microservices. How do you handle service discovery, inter-service network timeouts, and distributed tracing?")
        }

        # Check for matching trigger in candidate's response
        for trigger, (cat, follow_up_q) in tech_triggers.items():
            if trigger in text_lower:
                return {
                    "id": f"q_{next_question_index}",
                    "category": f"Adaptive Deep-Dive: {cat}",
                    "question": follow_up_q,
                    "context_source": f"Follow-up on your mention of '{trigger}'",
                    "expected_concepts": [trigger, "trade-off", "consistency", "performance", "error handling"],
                    "target_skills": [trigger.capitalize(), "System Design"],
                    "difficulty": "Advanced",
                    "is_adaptive": True
                }

        # Adaptive Branch 2: High Scorer (Scale & Stress Test)
        if score >= 82:
            return {
                "id": f"q_{next_question_index}",
                "category": "Adaptive Scaling & System Design",
                "question": "That was an impressive answer. If your system experienced a sudden 50x spike in traffic (from 1,000 to 50,000 active users), where would the primary bottleneck occur, and how would you redesign it?",
                "context_source": "Dynamic scaling scenario based on your strong response",
                "expected_concepts": ["load balancer", "horizontal scaling", "rate limiting", "caching", "replication", "message queues"],
                "target_skills": ["Scalability", "System Design"],
                "difficulty": "Advanced",
                "is_adaptive": True
            }

        # Adaptive Branch 3: Lower Scorer (Clarification & Fundamentals)
        if score < 65:
            return {
                "id": f"q_{next_question_index}",
                "category": "Adaptive Engineering Fundamentals",
                "question": "Let's break down the technical trade-offs a bit further: if you were to rebuild this feature today from scratch, what architectural mistakes would you avoid and what would you do differently?",
                "context_source": "Probing follow-up on project trade-offs",
                "expected_concepts": ["testing", "modularity", "clean code", "error handling", "documentation", "schema"],
                "target_skills": ["Architecture", "Best Practices"],
                "difficulty": "Intermediate",
                "is_adaptive": True
            }

        # Adaptive Branch 4: Fallback to next standard resume section
        std_questions = self.generate_interview_questions(resume_data, total_questions=5)
        if next_question_index - 1 < len(std_questions):
            q = std_questions[next_question_index - 1]
            q["id"] = f"q_{next_question_index}"
            return q

        # Final Wrap-up Question
        return {
            "id": f"q_{next_question_index}",
            "category": "Career Alignment & Future Vision",
            "question": "Given your technical portfolio and projects, what is an emerging technology or architectural pattern you are actively learning to elevate your software engineering craft?",
            "context_source": "Career Growth & Continuous Learning",
            "expected_concepts": ["learning", "architecture", "growth", "tooling", "scalability"],
            "target_skills": ["Continuous Learning", "Vision"],
            "difficulty": "General",
            "is_adaptive": True
        }


# Global Singleton Instance
ai_interview_engine = AIInterviewEngine()
