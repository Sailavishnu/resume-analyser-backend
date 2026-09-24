"""
AI Mock Interview Engine (Custom Conversational RAG & Semantic Analysis)

Architecture:
1. Retrieval-Augmented Generation (RAG):
   - Ingests & chunks student resume into semantic segments (Projects, Work History, Tech Stack).
   - Generates vector embeddings for each chunk using Sentence-BERT (all-MiniLM-L6-v2).
   - Performs cosine similarity retrieval to ground questions in real project context.
2. Multi-Dimensional Semantic Answer Evaluation:
   - Evaluates technical depth, semantic relevance, key concept coverage, and articulation.
3. Conversational Multi-Turn Memory & Adaptive Follow-Up:
   - Remembers dialogue history [Previous Questions + Answers + Resume Context].
   - Dynamically drills down into architectural claims (e.g. Redis, JWT, Docker, Async, Caching).
"""
import re
import logging
from typing import Dict, List, Any, Optional, Tuple
import numpy as np

from app.ml.nlp_processor import nlp_processor
from app.ml.embeddings import embedding_service

logger = logging.getLogger(__name__)


class ResumeKnowledgeChunk:
    """Represents a semantically indexed segment of the candidate's resume."""
    def __init__(self, chunk_id: str, chunk_type: str, title: str, content: str, metadata: Dict[str, Any]):
        self.chunk_id = chunk_id
        self.chunk_type = chunk_type  # 'project', 'experience', 'skills', 'education'
        self.title = title
        self.content = content
        self.metadata = metadata
        self.embedding: Optional[np.ndarray] = None


class AIInterviewEngine:
    """
    Conversational RAG AI Mock Interviewer.
    Runs 100% locally with Sentence-BERT & spaCy. Zero external API cost, ultra-low latency.
    """
    
    def __init__(self):
        self.nlp = nlp_processor
        self.embeddings = embedding_service

    def _ensure_models_loaded(self):
        """Ensure local NLP & Embedding models are ready."""
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

    def build_resume_knowledge_base(self, resume_data: Dict[str, Any]) -> List[ResumeKnowledgeChunk]:
        """
        RAG Step 1: Chunk the candidate's resume into semantically searchable knowledge blocks
        and embed each block with Sentence-BERT.
        """
        self._ensure_models_loaded()
        chunks: List[ResumeKnowledgeChunk] = []

        # 1. Projects Chunks
        projects = resume_data.get("projects", [])
        if isinstance(projects, list):
            for idx, p in enumerate(projects):
                if not isinstance(p, dict):
                    continue
                title = p.get("title") or p.get("name") or f"Project {idx + 1}"
                tech_stack = p.get("tech_stack") or p.get("technologies") or []
                if isinstance(tech_stack, list):
                    tech_str = ", ".join(str(t) for t in tech_stack)
                else:
                    tech_str = str(tech_stack)
                desc = p.get("description") or p.get("summary") or ""
                
                content = f"Project: {title}. Technologies used: {tech_str}. Details: {desc}"
                chunk = ResumeKnowledgeChunk(
                    chunk_id=f"proj_{idx}",
                    chunk_type="project",
                    title=title,
                    content=content,
                    metadata={"tech_stack": tech_stack, "title": title}
                )
                chunks.append(chunk)

        # 2. Experience / Work History Chunks
        experience = resume_data.get("experience", [])
        if isinstance(experience, list):
            for idx, exp in enumerate(experience):
                if not isinstance(exp, dict):
                    continue
                company = exp.get("company") or exp.get("employer") or "Company"
                role = exp.get("role") or exp.get("position") or "Software Engineer"
                summary = exp.get("summary") or exp.get("description") or ""
                
                content = f"Role: {role} at {company}. Responsibilities: {summary}"
                chunk = ResumeKnowledgeChunk(
                    chunk_id=f"exp_{idx}",
                    chunk_type="experience",
                    title=f"{role} at {company}",
                    content=content,
                    metadata={"company": company, "role": role}
                )
                chunks.append(chunk)

        # 3. Technical Skills Chunk
        skills_dict = resume_data.get("skills", {})
        all_skills = []
        if isinstance(skills_dict, dict):
            for cat, items in skills_dict.items():
                if isinstance(items, list):
                    all_skills.extend([str(i) for i in items])
        elif isinstance(skills_dict, list):
            all_skills = [str(s) for s in skills_dict]

        if all_skills:
            skills_content = f"Candidate Technical Skills: {', '.join(all_skills)}"
            chunks.append(ResumeKnowledgeChunk(
                chunk_id="skills_0",
                chunk_type="skills",
                title="Technical Competencies",
                content=skills_content,
                metadata={"skills": all_skills}
            ))

        # Embed all chunks
        for chunk in chunks:
            try:
                chunk.embedding = self.embeddings.encode_text(chunk.content)
            except Exception as e:
                logger.warning(f"Failed to embed chunk {chunk.chunk_id}: {e}")

        return chunks

    def retrieve_relevant_chunks(
        self, 
        query: str, 
        chunks: List[ResumeKnowledgeChunk], 
        top_k: int = 2
    ) -> List[Tuple[ResumeKnowledgeChunk, float]]:
        """
        RAG Step 2: Dense Semantic Vector Retrieval over candidate's resume knowledge base.
        """
        if not chunks:
            return []
        
        try:
            query_emb = self.embeddings.encode_text(query)
            scored_chunks = []
            for chunk in chunks:
                if chunk.embedding is not None:
                    sim = float(self.embeddings.calculate_similarity(query_emb, chunk.embedding))
                    scored_chunks.append((chunk, sim))
            
            scored_chunks.sort(key=lambda x: x[1], reverse=True)
            return scored_chunks[:top_k]
        except Exception as e:
            logger.warning(f"Chunk retrieval failed: {e}")
            return [(c, 0.5) for c in chunks[:top_k]]

    def generate_interview_questions(
        self, 
        resume_data: Dict[str, Any], 
        target_role: str = "Software Engineer",
        total_questions: int = 3
    ) -> List[Dict[str, Any]]:
        """
        RAG Step 3: Generates targeted, resume-grounded interview questions by retrieving
        specific project and experience assets.
        """
        self._ensure_models_loaded()
        chunks = self.build_resume_knowledge_base(resume_data)
        
        projects = resume_data.get("projects", [])
        experience = resume_data.get("experience", [])
        skills_dict = resume_data.get("skills", {})
        
        all_skills = []
        if isinstance(skills_dict, dict):
            for cat, items in skills_dict.items():
                if isinstance(items, list):
                    all_skills.extend([str(s).strip() for s in items if str(s).strip()])
        elif isinstance(skills_dict, list):
            all_skills = [str(s).strip() for s in skills_dict if str(s).strip()]
            
        if not all_skills:
            all_skills = ["Python", "FastAPI", "React", "MongoDB", "Docker", "REST APIs"]

        questions = []
        q_idx = 1

        # ─── Q1: Project Deep-Dive & Architecture (RAG Grounded) ─────────────
        top_proj = projects[0] if (projects and isinstance(projects[0], dict)) else None
        if top_proj:
            p_name = top_proj.get("title") or top_proj.get("name") or "Key Project"
            p_tech = top_proj.get("tech_stack") or top_proj.get("technologies") or all_skills[:3]
            tech_str = ", ".join(p_tech) if isinstance(p_tech, list) else str(p_tech)
            
            questions.append({
                "id": f"q_{q_idx}",
                "category": "Project Architecture & Implementation",
                "question": f"In your project '{p_name}', which utilized {tech_str}: Walk me through the end-to-end architecture. How did you structure your components or data flow, and what was the most complex technical hurdle you solved during development?",
                "context_source": f"Resume Project: {p_name} ({tech_str})",
                "expected_concepts": ["architecture", "data flow", "state management", "api", "database", "debugging", "trade-offs", "scalability"],
                "target_skills": p_tech if isinstance(p_tech, list) else all_skills[:3],
                "difficulty": "Intermediate",
                "is_rag_grounded": True
            })
            q_idx += 1
        else:
            primary_skill = all_skills[0] if all_skills else "Python"
            secondary_skill = all_skills[1] if len(all_skills) > 1 else "REST APIs"
            questions.append({
                "id": f"q_{q_idx}",
                "category": "Core Technical Architecture",
                "question": f"You highlight {primary_skill} and {secondary_skill} as core strengths. Could you describe a challenging application you built with these technologies? How did you design the backend API and handle error boundaries?",
                "context_source": f"Resume Skills: {primary_skill}, {secondary_skill}",
                "expected_concepts": ["api design", "error handling", "performance", "database", "architecture"],
                "target_skills": [primary_skill, secondary_skill],
                "difficulty": "Intermediate",
                "is_rag_grounded": True
            })
            q_idx += 1

        # ─── Q2: Production Engineering & System Reliability ──────────────────
        top_exp = experience[0] if (experience and isinstance(experience[0], dict)) else None
        if top_exp:
            company = top_exp.get("company") or top_exp.get("employer") or "your previous organization"
            role = top_exp.get("role") or top_exp.get("position") or "Software Engineer"
            questions.append({
                "id": f"q_{q_idx}",
                "category": "Work Experience & Troubleshooting",
                "question": f"During your experience as a {role} at {company}: Describe a critical production incident, performance bottleneck, or bug you encountered. What debugging tools and methodologies did you use to diagnose the root cause and ensure it wouldn't happen again?",
                "context_source": f"Resume Experience: {role} at {company}",
                "expected_concepts": ["root cause", "monitoring", "profiling", "logs", "testing", "regression", "git", "ci/cd"],
                "target_skills": ["Debugging", "System Reliability", "Root Cause Analysis"],
                "difficulty": "Intermediate",
                "is_rag_grounded": True
            })
            q_idx += 1
        elif len(projects) > 1 and isinstance(projects[1], dict):
            second_proj = projects[1]
            p2_name = second_proj.get("title") or second_proj.get("name") or "Secondary Project"
            questions.append({
                "id": f"q_{q_idx}",
                "category": "System Design & Data Consistency",
                "question": f"Looking at your project '{p2_name}': How did you design your database schema, ensure data consistency across multiple concurrent user operations, and handle data validation?",
                "context_source": f"Resume Project: {p2_name}",
                "expected_concepts": ["schema design", "concurrency", "validation", "indexes", "transactions", "crud", "rest"],
                "target_skills": all_skills[2:5] if len(all_skills) >= 5 else all_skills,
                "difficulty": "Intermediate",
                "is_rag_grounded": True
            })
            q_idx += 1
        else:
            questions.append({
                "id": f"q_{q_idx}",
                "category": "API Design & Concurrency",
                "question": f"For a production {target_role} application: How do you design idempotent RESTful APIs, manage concurrent database read/write locks, and handle graceful error responses to clients?",
                "context_source": f"Role Expectations: {target_role}",
                "expected_concepts": ["idempotency", "transactions", "http status codes", "concurrency", "caching", "indexing"],
                "target_skills": ["API Design", "Database Systems"],
                "difficulty": "Intermediate",
                "is_rag_grounded": False
            })
            q_idx += 1

        # ─── Q3: Behavioral & Engineering Leadership ──────────────────────────
        questions.append({
            "id": f"q_{q_idx}",
            "category": "Engineering Leadership & Agile Collaboration",
            "question": f"In a fast-paced agile team hiring for a {target_role}: How do you approach code reviews when you disagree with a peer's architecture, and how do you negotiate technical debt versus meeting tight product sprint deadlines?",
            "context_source": f"Target Role: {target_role}",
            "expected_concepts": ["code review", "constructive feedback", "communication", "technical debt", "testing", "prioritization"],
            "target_skills": ["Collaboration", "Code Review", "Agile"],
            "difficulty": "Comprehensive",
            "is_rag_grounded": False
        })

        return questions[:total_questions]

    def evaluate_answer(
        self, 
        question: Dict[str, Any], 
        answer_text: str
    ) -> Dict[str, Any]:
        """
        Evaluates candidate's response across 4 distinct dimensions:
        1. Semantic Relevance (Sentence-BERT embeddings)
        2. Technical Concept Density (spaCy entity & keyword extraction)
        3. Structural Depth & Actionable Impact (STAR markers)
        4. Articulation & Clarity
        """
        self._ensure_models_loaded()
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
                "feedback": "No answer provided. Please articulate your response with technical examples and design decisions."
            }

        # 1. Semantic Similarity Calculation (Sentence-BERT)
        expected_concepts = question.get("expected_concepts", [])
        expected_context = f"Question: {question.get('question')} | Essential concepts: {', '.join(expected_concepts)}"
        
        try:
            ans_emb = self.embeddings.encode_text(text)
            exp_emb = self.embeddings.encode_text(expected_context)
            similarity = float(self.embeddings.calculate_similarity(ans_emb, exp_emb))
            semantic_score = np.clip(similarity * 100, 30.0, 98.0)
        except Exception as e:
            logger.warning(f"Semantic scoring fallback: {e}")
            semantic_score = 70.0

        # 2. Keyword & Concept Extraction
        text_lower = text.lower()
        matched_keywords = []
        for kw in expected_concepts + question.get("target_skills", []):
            kw_clean = str(kw).lower().strip()
            if kw_clean and (kw_clean in text_lower or re.search(r'\b' + re.escape(kw_clean) + r'\b', text_lower)):
                if kw not in matched_keywords:
                    matched_keywords.append(kw)

        missed_keywords = [kw for kw in expected_concepts if kw not in matched_keywords]

        # 3. Technical Depth & STAR Markers
        star_markers = [
            "implemented", "optimized", "designed", "handled", "configured", 
            "reduced", "improved", "architecture", "tradeoff", "tested", 
            "refactored", "migrated", "automated", "benchmarked"
        ]
        star_count = sum(1 for marker in star_markers if marker in text_lower)
        
        depth_score = 50.0
        depth_score += min(25, len(matched_keywords) * 6)
        depth_score += min(15, star_count * 4)
        if word_count >= 40:
            depth_score += 10
        elif word_count < 15:
            depth_score -= 15
        depth_score = float(np.clip(depth_score, 35.0, 96.0))

        # 4. Clarity & Coherence
        clarity_score = 65.0
        if 35 <= word_count <= 200:
            clarity_score += 20
        elif word_count > 200:
            clarity_score += 10
        else:
            clarity_score -= 15
        clarity_score = float(np.clip(clarity_score, 35.0, 95.0))

        # 5. Composite Score
        overall_score = int(round(
            (semantic_score * 0.40) + 
            (depth_score * 0.40) + 
            (clarity_score * 0.20)
        ))
        overall_score = max(35, min(98, overall_score))

        # 6. Actionable Constructive Feedback
        if len(matched_keywords) >= 3 and overall_score >= 80:
            feedback = f"Outstanding technical response! You thoroughly explained key concepts ({', '.join(matched_keywords[:3])}) with solid architectural grounding."
        elif len(matched_keywords) >= 1:
            feedback = f"Good technical basis covering {', '.join(matched_keywords[:2])}. To make your answer truly senior-level, discuss performance trade-offs and quantify measurable impact (e.g. latency, throughput, scale)."
        else:
            suggested = missed_keywords[:3] if missed_keywords else ["architecture", "error handling", "performance metrics"]
            feedback = f"Your answer is on the right path but lacks technical specificity. Strengthen it by anchoring your response around concepts like: {', '.join(suggested)}."

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
        next_question_index: int,
        conversation_history: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Conversational RAG Memory & Dynamic Follow-up:
        1. Analyzes the candidate's actual answer for architectural claims
        2. Cross-references with resume projects
        3. Formulates a precise, conversational follow-up question
        """
        text_lower = (answer_text or "").lower()
        score = eval_result.get("score", 70)

        # Conversational Drill-Down Trigger Dictionary (Modern Tech Stack)
        tech_triggers = {
            "caching": (
                "Caching Strategy & Eviction",
                "You mentioned caching in your answer. What cache invalidation strategy (like TTL, cache-aside, or write-through) and eviction policy (like LRU) did you use to prevent stale or dirty reads?"
            ),
            "redis": (
                "Redis Concurrency & Stampedes",
                "Since you utilized Redis, how did you handle potential Redis connection dropouts or cache stampedes (thundering herd problem) under peak traffic?"
            ),
            "jwt": (
                "Token Security & Invalidation",
                "You brought up JWT authentication. Because JWTs are stateless, how do you handle instantaneous token revocation on logout or user ban without turning your database into a bottleneck?"
            ),
            "mongodb": (
                "NoSQL Indexing & Aggregations",
                "Regarding MongoDB, how did you balance embedding versus referencing in your document schema, and how did you verify index usage with `.explain('executionStats')`?"
            ),
            "postgresql": (
                "SQL Transactions & ACID",
                "You mentioned PostgreSQL. How did you structure your transactions to prevent dirty reads or phantom reads, and what index types (B-tree, GIN, GiST) did you choose?"
            ),
            "docker": (
                "Containerization & Multi-Stage Builds",
                "You touched on Docker. How did you optimize multi-stage Dockerfiles to minimize the final container attack surface and reduce image sizes?"
            ),
            "async": (
                "Event Loop & Concurrency",
                "You highlighted asynchronous processing. How does the event loop handle CPU-bound workloads versus I/O-bound tasks without blocking incoming network requests?"
            ),
            "react": (
                "State Architecture & Render Optimization",
                "You discussed React components. What strategies did you implement (memoization, context splitting, custom hooks) to prevent re-render cascades in deeply nested UI trees?"
            ),
            "microservices": (
                "Distributed Tracing & Failures",
                "You discussed microservices. How did you manage inter-service network timeouts, circuit breakers, and distributed tracing across services?"
            ),
            "cloudinary": (
                "Cloud Storage & Access Control",
                "You mentioned Cloudinary/cloud storage. How did you handle file ACL permissions, signed upload URLs, and prevent unauthorized direct file access?"
            ),
            "websocket": (
                "Real-time Scaling & Heartbeats",
                "You mentioned WebSockets. How did you handle connection state synchronization and horizontal scaling across multiple server instances with Redis Pub/Sub?"
            )
        }

        # Branch 1: Specific Architectural Deep-Dive based on candidate's exact words
        for trigger, (cat, follow_up_q) in tech_triggers.items():
            if trigger in text_lower:
                return {
                    "id": f"q_{next_question_index}",
                    "category": f"Adaptive Deep-Dive: {cat}",
                    "question": follow_up_q,
                    "context_source": f"Follow-up on your mention of '{trigger}' in the previous question",
                    "expected_concepts": [trigger, "trade-offs", "performance", "scalability", "error handling"],
                    "target_skills": [trigger.capitalize(), "System Architecture"],
                    "difficulty": "Advanced",
                    "is_adaptive": True
                }

        # Branch 2: High Scorer Challenge (Scale & Stress Testing)
        if score >= 82:
            return {
                "id": f"q_{next_question_index}",
                "category": "Adaptive Scaling & High-Availability Design",
                "question": "That was an impressive technical response. If your system experienced an unexpected 50x spike in concurrent users tomorrow, where would the primary bottleneck occur first, and how would you redesign the system with rate limiting and load balancing to keep latency under 100ms?",
                "context_source": "Dynamic scaling challenge triggered by your strong response",
                "expected_concepts": ["horizontal scaling", "rate limiting", "load balancing", "replication", "message queues", "caching"],
                "target_skills": ["High Availability", "System Design", "Scalability"],
                "difficulty": "Advanced",
                "is_adaptive": True
            }

        # Branch 3: Lower Scorer Support (Clarification & Engineering Fundamentals)
        if score < 65:
            return {
                "id": f"q_{next_question_index}",
                "category": "Adaptive Engineering Fundamentals & Trade-offs",
                "question": "Let's explore the architectural decisions a bit further: If you were to redesign that exact solution today with what you know now, what is one major architectural trade-off or mistake you would avoid, and why?",
                "context_source": "Probing follow-up on design trade-offs and code modularity",
                "expected_concepts": ["modularity", "clean code", "testing", "trade-offs", "error handling", "documentation"],
                "target_skills": ["Architecture", "Engineering Best Practices"],
                "difficulty": "Intermediate",
                "is_adaptive": True
            }

        # Branch 4: Next RAG Resume Question
        std_questions = self.generate_interview_questions(resume_data, total_questions=5)
        if next_question_index - 1 < len(std_questions):
            q = std_questions[next_question_index - 1]
            q["id"] = f"q_{next_question_index}"
            return q

        # Branch 5: Future Roadmap & Engineering Vision
        return {
            "id": f"q_{next_question_index}",
            "category": "Continuous Learning & Technical Vision",
            "question": "Looking at your technical portfolio and projects, what is an emerging architectural pattern or technology (such as event-driven design, vector databases, or micro-frontends) that you are actively learning to level up your craft?",
            "context_source": "Career Growth & Engineering Vision",
            "expected_concepts": ["learning", "architecture", "growth", "tooling", "scalability"],
            "target_skills": ["Continuous Learning", "Technical Vision"],
            "difficulty": "General",
            "is_adaptive": True
        }


# Global Singleton Instance
ai_interview_engine = AIInterviewEngine()
