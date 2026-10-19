"""Challenge catalog, scoring, attempt persistence, and history analytics."""

from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from app.cloud import collections as C
from app.core.exceptions import NotFoundError, ProcessingError, ValidationError
from app.ml.gemini_service import gemini_interview_service


ROLES = ["Backend Developer", "Frontend Developer", "Full Stack Developer", "Software Engineer"]

CHALLENGES: dict[str, dict[str, Any]] = {
    "resume-summary-beginner": {
        "title": "Write a Resume Summary", "type": "resume", "difficulty": "beginner",
        "description": "Turn a candidate profile into a concise, evidence-based professional summary.",
        "targetRoles": ROLES, "answerType": "text",
        "instructions": "Write 2–4 sentences for the selected target role. Use only facts in the candidate profile. Do not invent skills, outcomes, or metrics.",
        "content": {"candidateProfile": {"education": "B.Sc. Computer Science, graduating 2026", "skills": ["Python", "FastAPI", "SQL", "Git"], "experience": "Six-month software engineering internship; built and documented REST endpoints", "projects": ["Course planner API using FastAPI and PostgreSQL"], "goal": "Entry-level software engineering role"}},
        "evaluation": "writing-summary",
    },
    "resume-project-improvement": {
        "title": "Improve a Project Description", "type": "resume", "difficulty": "beginner",
        "description": "Make a vague project bullet clearer without making up accomplishments.",
        "targetRoles": ROLES, "answerType": "text",
        "instructions": "Rewrite the project description as one or two resume-ready sentences. Keep every claim grounded in the source. You may identify useful details that the candidate should add, but label them as questions rather than facts.",
        "content": {"project": "Personal expense tracker", "technologies": ["React", "MongoDB"], "originalDescription": "Created a website using React and MongoDB."},
        "evaluation": "writing-project",
    },
    "resume-section-order": {
        "title": "Choose a Resume Section Order", "type": "resume", "difficulty": "beginner",
        "description": "Arrange sections for a recent computer science graduate with internship experience.",
        "targetRoles": ROLES, "answerType": "ordered-list",
        "instructions": "Move every section into a sensible order for this early-career candidate. Use the move controls to arrange the list.",
        "content": {"candidateProfile": "Recent computer science graduate with one relevant internship and two technical projects.", "sections": ["Summary", "Education", "Skills", "Projects", "Experience"]},
        "evaluation": "section-order", "answerKey": ["Summary", "Skills", "Experience", "Projects", "Education"],
    },
    "resume-skills-selection": {
        "title": "Select Relevant Skills", "type": "resume", "difficulty": "intermediate",
        "description": "Choose only skills supported by the supplied candidate profile for a backend role.",
        "targetRoles": ["Backend Developer", "Software Engineer"], "answerType": "multi-select",
        "instructions": "Select the skills and evidence that belong on this candidate's resume for the target role. Avoid unrelated or unsupported items.",
        "content": {"candidateProfile": "Built REST APIs with Python and FastAPI; queried relational databases with SQL; used Git for source control. No frontend framework or design experience is listed.", "options": ["Python", "FastAPI", "SQL", "REST APIs", "Git", "React", "Figma", "Digital marketing", "AWS certification"]},
        "evaluation": "skill-selection", "answerKey": ["Python", "FastAPI", "SQL", "REST APIs", "Git"],
    },
    "job-identify-skills": {
        "title": "Identify Job Requirements", "type": "job-readiness", "difficulty": "beginner",
        "description": "Separate required skills, preferred skills, and skills not stated in a job description.",
        "targetRoles": ROLES, "answerType": "skill-categories",
        "instructions": "Sort each skill into Required, Preferred, or Not mentioned based on the job description. Do not infer requirements that are not written.",
        "content": {"role": "Backend Developer", "jobDescription": "We need a backend developer to build and maintain Python services using FastAPI. Work with PostgreSQL databases and write tests. Docker experience is a plus. Familiarity with React is not mentioned.", "skills": ["Python", "FastAPI", "PostgreSQL", "Testing", "Docker", "React", "AWS"]},
        "evaluation": "skill-categories", "answerKey": {"required": ["Python", "FastAPI", "PostgreSQL", "Testing"], "preferred": ["Docker"], "notMentioned": ["React", "AWS"]},
    },
    "job-match-candidate": {
        "title": "Assess Candidate Skill Evidence", "type": "job-readiness", "difficulty": "intermediate",
        "description": "Classify job requirements based on what a profile documents, without assuming undocumented skills are absent.",
        "targetRoles": ROLES, "answerType": "classifications",
        "instructions": "For each requirement, select Matched, Partially matched, or Not demonstrated in this profile. 'Not demonstrated' means the profile lacks evidence; it does not prove the candidate lacks the skill.",
        "content": {"role": "Backend Developer", "candidateProfile": "Built a Python Flask REST API and queried SQL databases. Experience with cloud deployment is not included in the profile.", "requirements": ["Python", "FastAPI", "SQL", "Docker"]},
        "evaluation": "candidate-match", "answerKey": {"Python": "matched", "FastAPI": "partial", "SQL": "matched", "Docker": "not-demonstrated"},
        "explanations": {"Python": "Python is explicitly used in the candidate's project.", "FastAPI": "Flask is a different Python web framework, so the profile provides related experience but no direct FastAPI evidence.", "SQL": "The profile explicitly says the candidate queried SQL databases.", "Docker": "Docker is not documented here. This is an evidence gap, not proof that the candidate lacks the skill."},
    },
    "job-prioritize-improvements": {
        "title": "Prioritize Your Next Steps", "type": "job-readiness", "difficulty": "intermediate",
        "description": "Choose actions that close evidence gaps while separating resume edits from skill development.",
        "targetRoles": ["Backend Developer", "Software Engineer"], "answerType": "multi-select",
        "instructions": "Choose the three most useful next steps for a candidate with Python and SQL experience applying for a backend role that asks for FastAPI, PostgreSQL, Docker, and testing.",
        "content": {"candidateProfile": "Python Flask API and SQL query experience; no PostgreSQL, Docker, FastAPI, or testing evidence is shown.", "options": ["Rewrite the project bullet to clearly explain the existing Flask API and SQL work", "Build and document a small FastAPI project backed by PostgreSQL", "Practise writing automated tests for the project and document what is actually tested", "Learn Docker basics and containerize the project before claiming Docker experience", "Add FastAPI, PostgreSQL, Docker, and testing to the resume without evidence", "Change the resume template color"]},
        "evaluation": "priority-selection", "answerKey": ["Build and document a small FastAPI project backed by PostgreSQL", "Practise writing automated tests for the project and document what is actually tested", "Learn Docker basics and containerize the project before claiming Docker experience"],
        "explanations": {"Rewrite the project bullet to clearly explain the existing Flask API and SQL work": "This improves how existing experience is communicated, but does not create missing framework or deployment evidence.", "Build and document a small FastAPI project backed by PostgreSQL": "This develops and demonstrates two job requirements through real work.", "Practise writing automated tests for the project and document what is actually tested": "This creates genuine test experience that can be documented accurately.", "Learn Docker basics and containerize the project before claiming Docker experience": "This is skill development; list Docker only after you have actually used it.", "Add FastAPI, PostgreSQL, Docker, and testing to the resume without evidence": "Do not claim skills or experience that the candidate has not demonstrated.", "Change the resume template color": "Visual styling does not address the evidence gaps in the job requirements."},
    },
}

JOB_ROLE_VARIANTS = {
    "Backend Developer": {
        "jobDescription": "We need a backend developer to build and maintain Python services using FastAPI. Work with PostgreSQL databases and write tests. Docker experience is a plus. Familiarity with React is not mentioned.",
        "required": ["Python", "FastAPI", "PostgreSQL", "Testing"], "preferred": ["Docker"], "notMentioned": ["React", "AWS"],
        "candidate": "Built a Python Flask REST API and queried SQL databases. Experience with cloud deployment is not included in the profile.",
        "requirements": ["Python", "FastAPI", "SQL", "Docker"], "matches": {"Python": "matched", "FastAPI": "partial", "SQL": "matched", "Docker": "not-demonstrated"},
        "matchExplanations": {"Python": "Python is explicitly used in the candidate's project.", "FastAPI": "Flask is a different Python web framework, so the profile provides related experience but no direct FastAPI evidence.", "SQL": "The profile explicitly says the candidate queried SQL databases.", "Docker": "Docker is not documented here. This is an evidence gap, not proof that the candidate lacks the skill."},
        "priorityProfile": "Python Flask API and SQL query experience; no PostgreSQL, Docker, FastAPI, or testing evidence is shown.",
        "priorityOptions": ["Rewrite the project bullet to clearly explain the existing Flask API and SQL work", "Build and document a small FastAPI project backed by PostgreSQL", "Practise writing automated tests for the project and document what is actually tested", "Learn Docker basics and containerize the project before claiming Docker experience", "Add FastAPI, PostgreSQL, Docker, and testing to the resume without evidence", "Change the resume template color"],
        "priorityKey": ["Build and document a small FastAPI project backed by PostgreSQL", "Practise writing automated tests for the project and document what is actually tested", "Learn Docker basics and containerize the project before claiming Docker experience"],
    },
    "Frontend Developer": {
        "jobDescription": "Build accessible web interfaces with React and TypeScript. Strong CSS fundamentals and component testing are expected. Familiarity with a design system is a plus. Python and Docker are not mentioned.",
        "required": ["React", "TypeScript", "CSS", "Component testing"], "preferred": ["Design system"], "notMentioned": ["Python", "Docker"],
        "candidate": "Built a React interface using JavaScript and CSS. The profile does not mention TypeScript, accessibility work, or component tests.",
        "requirements": ["React", "TypeScript", "CSS", "Accessibility"], "matches": {"React": "matched", "TypeScript": "partial", "CSS": "matched", "Accessibility": "not-demonstrated"},
        "matchExplanations": {"React": "React is explicitly listed in the candidate's project.", "TypeScript": "JavaScript experience is related, but the profile does not document TypeScript use.", "CSS": "CSS is explicitly listed in the project.", "Accessibility": "Accessibility work is not described. This is an evidence gap, not proof the candidate lacks the skill."},
        "priorityProfile": "React, JavaScript, and CSS experience; no TypeScript, accessibility, or testing evidence is shown.",
        "priorityOptions": ["Rewrite the project bullet to show the existing React and CSS work clearly", "Add TypeScript to the resume without using it", "Convert a project module to TypeScript and document the scope", "Audit and improve keyboard accessibility, then document verified changes", "Add component tests for key interface behavior", "Change the resume template color"],
        "priorityKey": ["Convert a project module to TypeScript and document the scope", "Audit and improve keyboard accessibility, then document verified changes", "Add component tests for key interface behavior"],
    },
    "Full Stack Developer": {
        "jobDescription": "Develop product features across a React frontend and Node.js services, integrate REST APIs, and work with PostgreSQL. Docker experience is preferred. Python is not mentioned.",
        "required": ["React", "Node.js", "REST APIs", "PostgreSQL"], "preferred": ["Docker"], "notMentioned": ["Python", "AWS"],
        "candidate": "Built a React frontend and a Python Flask REST API, and queried SQL databases. Node.js and deployment tools are not documented.",
        "requirements": ["React", "Node.js", "REST APIs", "PostgreSQL"], "matches": {"React": "matched", "Node.js": "not-demonstrated", "REST APIs": "matched", "PostgreSQL": "partial"},
        "matchExplanations": {"React": "React is explicitly documented.", "Node.js": "Node.js is not documented. This is an evidence gap, not proof the candidate lacks it.", "REST APIs": "The profile describes a Flask REST API.", "PostgreSQL": "SQL database experience is related, but PostgreSQL itself is not named."},
        "priorityProfile": "React, Python Flask REST API, and SQL experience; no Node.js, PostgreSQL, or Docker evidence is shown.",
        "priorityOptions": ["Clarify the current React and API integration work in the project description", "Build a small Node.js service and connect it to an existing frontend", "Use PostgreSQL in a project and document the schema and queries", "Learn Docker and containerize a project before claiming experience", "Add Node.js, PostgreSQL, and Docker without supporting work", "Change the resume template color"],
        "priorityKey": ["Build a small Node.js service and connect it to an existing frontend", "Use PostgreSQL in a project and document the schema and queries", "Learn Docker and containerize a project before claiming experience"],
    },
    "Software Engineer": {
        "jobDescription": "We are looking for a software engineer with Python, Git, data structures and algorithms, and automated testing experience. System design familiarity is preferred. React and AWS are not mentioned.",
        "required": ["Python", "Git", "Data structures and algorithms", "Automated testing"], "preferred": ["System design"], "notMentioned": ["React", "AWS"],
        "candidate": "Used Python and Git for coursework and built one small command-line project. Testing and data structures evidence are not described.",
        "requirements": ["Python", "Git", "Data structures and algorithms", "Automated testing"], "matches": {"Python": "matched", "Git": "matched", "Data structures and algorithms": "not-demonstrated", "Automated testing": "not-demonstrated"},
        "matchExplanations": {"Python": "Python is explicitly listed in the candidate's work.", "Git": "Git is explicitly listed in the candidate's work.", "Data structures and algorithms": "The profile does not show examples or coursework evidence for this requirement.", "Automated testing": "Automated testing is not documented. This is an evidence gap, not proof the candidate lacks the skill."},
        "priorityProfile": "Python and Git coursework with a small command-line project; no test or algorithm examples are documented.",
        "priorityOptions": ["Describe the actual command-line project and its scope clearly", "Add automated tests to the project and document the tested behavior", "Build a small project demonstrating data structures and explain the trade-offs", "Add system design, testing, and algorithm expertise without examples", "Review core data structures and solve practice problems, then capture verified learning", "Change the resume template color"],
        "priorityKey": ["Add automated tests to the project and document the tested behavior", "Build a small project demonstrating data structures and explain the trade-offs", "Review core data structures and solve practice problems, then capture verified learning"],
    },
}


def _public_challenge(challenge_id: str, challenge: dict[str, Any]) -> dict[str, Any]:
    return {"id": challenge_id, **{key: value for key, value in challenge.items() if key not in {"answerKey", "evaluation", "explanations"}}}


def _challenge_variant(challenge_id: str, target_role: str | None) -> dict[str, Any]:
    import copy
    challenge = copy.deepcopy(CHALLENGES[challenge_id])
    role = target_role if target_role in JOB_ROLE_VARIANTS else "Backend Developer"
    variant = JOB_ROLE_VARIANTS[role]
    if challenge_id == "job-identify-skills":
        challenge["content"].update({"role": role, "jobDescription": variant["jobDescription"], "skills": list(dict.fromkeys(variant["required"] + variant["preferred"] + variant["notMentioned"]))})
        challenge["answerKey"] = {"required": variant["required"], "preferred": variant["preferred"], "notMentioned": variant["notMentioned"]}
    elif challenge_id == "job-match-candidate":
        challenge["content"].update({"role": role, "candidateProfile": variant["candidate"], "requirements": variant["requirements"], "jobDescription": variant["jobDescription"]})
        challenge["answerKey"] = variant["matches"]
        challenge["explanations"] = variant["matchExplanations"]
    elif challenge_id == "job-prioritize-improvements":
        challenge["content"].update({"role": role, "candidateProfile": variant["priorityProfile"], "options": variant["priorityOptions"]})
        challenge["answerKey"] = variant["priorityKey"]
        challenge["explanations"] = {option: (
            "This builds and documents evidence for a real requirement. Claim it only after the work is done."
            if option in variant["priorityKey"] else
            "This improves the presentation of existing evidence but does not create a missing skill."
            if option.startswith("Rewrite") or option.startswith("Clarify") or option.startswith("Describe") else
            "Do not claim skills or experience that are not supported by completed work."
            if "without" in option else
            "Visual styling does not address the job-requirement evidence gaps."
        ) for option in variant["priorityOptions"]}
    challenge["targetRoles"] = ROLES
    return challenge


def _as_set(values: Any, field: str, allowed: list[str]) -> set[str]:
    if not isinstance(values, list) or any(not isinstance(item, str) for item in values):
        raise ValidationError(f"{field} must be a list of strings")
    if len(values) > len(allowed) or len(values) != len(set(values)) or any(item not in allowed for item in values):
        raise ValidationError(f"{field} contains an invalid or repeated option")
    return set(values)


def _score_set_selection(selected: set[str], expected: set[str]) -> tuple[int, dict[str, int]]:
    correct = len(selected & expected)
    incorrect = len(selected - expected)
    score = round(100 * max(0, correct - incorrect) / max(len(expected), 1))
    return max(0, min(score, 100)), {"correctSelections": correct, "missedSelections": len(expected - selected), "incorrectSelections": incorrect}


class PracticeService:
    def __init__(self, db):
        self.db = db
        self.attempts = db[C.PRACTICE_ATTEMPTS]

    def list_challenges(self, challenge_type: str | None = None, difficulty: str | None = None, target_role: str | None = None) -> list[dict[str, Any]]:
        return [
            _public_challenge(challenge_id, _challenge_variant(challenge_id, target_role))
            for challenge_id in CHALLENGES
            for challenge in [_challenge_variant(challenge_id, target_role)]
            if (not challenge_type or challenge["type"] == challenge_type)
            and (not difficulty or challenge["difficulty"] == difficulty)
        ]

    def get_challenge(self, challenge_id: str, target_role: str | None = None) -> dict[str, Any]:
        if challenge_id not in CHALLENGES:
            raise NotFoundError("Practice challenge not found")
        challenge = _challenge_variant(challenge_id, target_role)
        return _public_challenge(challenge_id, challenge)

    async def submit_attempt(self, student_id: str, challenge_id: str, answer: dict[str, Any], target_role: str | None, submission_id: str | None) -> dict[str, Any]:
        if challenge_id not in CHALLENGES:
            raise NotFoundError("Practice challenge not found")
        challenge = _challenge_variant(challenge_id, target_role)
        if target_role and target_role not in challenge["targetRoles"]:
            raise ValidationError("Select a target role supported by this challenge")
        if submission_id:
            existing = self.attempts.find_one({"user_id": ObjectId(student_id), "submission_id": submission_id})
            if existing:
                return self._serialize(existing)

        score, criteria, feedback, suggested = await self._evaluate(challenge, answer, target_role)
        created = datetime.now(timezone.utc)
        attempt_number = self.attempts.count_documents({
            "user_id": ObjectId(student_id), "challenge_id": challenge_id, "status": "completed",
        }) + 1
        doc = {
            "user_id": ObjectId(student_id),
            "challenge_id": challenge_id,
            "challenge_type": challenge["type"],
            "challenge_name": challenge["title"],
            "challenge_version": 1,
            "attempt_number": attempt_number,
            "target_role": target_role or (challenge["targetRoles"][0] if challenge["targetRoles"] else None),
            "submitted_answer": answer,
            "score": score,
            "criteria_scores": criteria,
            "feedback": feedback,
            "suggested_answer": suggested,
            "status": "completed",
            "submission_id": submission_id,
            "created_at": created,
            "completed_at": created,
        }
        try:
            result = self.attempts.insert_one(doc)
        except DuplicateKeyError:
            existing = self.attempts.find_one({"user_id": ObjectId(student_id), "submission_id": submission_id})
            if existing:
                return self._serialize(existing)
            raise
        doc["_id"] = result.inserted_id
        return self._serialize(doc)

    async def _evaluate(self, challenge: dict[str, Any], answer: dict[str, Any], target_role: str | None = None):
        evaluation = challenge["evaluation"]
        if evaluation in ("writing-summary", "writing-project"):
            field = "summary" if evaluation == "writing-summary" else "description"
            answer_text = answer.get(field)
            if not isinstance(answer_text, str) or not answer_text.strip() or len(answer_text) > 5000:
                raise ValidationError(f"{field} must contain between 1 and 5,000 characters")
            result = await self._run_ai_evaluation(challenge, answer_text, target_role)
            return result["score"], result["criteriaScores"], result["feedback"], result.get("suggestedAnswer")

        if evaluation == "section-order":
            sections = answer.get("sections")
            expected = challenge["content"]["sections"]
            if not isinstance(sections, list) or len(sections) != len(expected) or set(sections) != set(expected):
                raise ValidationError("sections must contain every displayed section exactly once")
            answer_key = challenge["answerKey"]
            pairs = [(a, b) for i, a in enumerate(answer_key) for b in answer_key[i + 1:]]
            positions = {item: index for index, item in enumerate(sections)}
            correct = sum(positions[a] < positions[b] for a, b in pairs)
            score = round(100 * correct / len(pairs))
            feedback = {"strengths": ["You submitted a complete section order."], "improvements": ["Consider placing the most relevant evidence near the top; ordering can vary with the candidate's experience."], "explanation": "For this early-career profile, skills and relevant experience should be easy to find, while the candidate's education and projects remain visible."}
            return score, {"relativeOrdering": score}, feedback, answer_key

        if evaluation == "skill-selection":
            selected = _as_set(answer.get("skills"), "skills", challenge["content"]["options"])
            score, criteria = _score_set_selection(selected, set(challenge["answerKey"]))
            feedback = {"strengths": sorted(selected & set(challenge["answerKey"])), "improvements": sorted(set(challenge["answerKey"]) - selected), "explanation": "Choose skills directly supported by the candidate profile. Unsupported skills should not be added to a resume."}
            return score, criteria, feedback, challenge["answerKey"]

        if evaluation == "skill-categories":
            key = challenge["answerKey"]
            allowed = challenge["content"]["skills"]
            answers = {"required": answer.get("required"), "preferred": answer.get("preferred"), "notMentioned": answer.get("notMentioned")}
            selected = {name: _as_set(values, name, allowed) for name, values in answers.items()}
            flattened = [item for values in selected.values() for item in values]
            if len(flattened) != len(set(flattened)) or set(flattened) != set(allowed):
                raise ValidationError("Every listed skill must be assigned to exactly one category")
            total = len(allowed)
            correct = sum(len(selected[name] & set(key[name])) for name in key)
            score = round(100 * correct / total)
            criteria = {name: round(100 * len(selected[name] & set(key[name])) / max(len(key[name]), 1)) for name in key}
            feedback = {"strengths": sorted(selected["required"] & set(key["required"])), "improvements": sorted(item for name in key for item in set(key[name]) - selected[name]), "explanation": "Required means explicitly expected in the description; preferred means listed as a plus; not mentioned means the description does not state it."}
            return score, criteria, feedback, key

        if evaluation == "candidate-match":
            key = challenge["answerKey"]
            allowed_values = {"matched", "partial", "not-demonstrated"}
            values = answer.get("classifications")
            if not isinstance(values, dict) or set(values) != set(key) or any(value not in allowed_values for value in values.values()):
                raise ValidationError("Provide one valid classification for each requirement")
            correct = sum(values[item] == expected for item, expected in key.items())
            score = round(100 * correct / len(key))
            feedback = {"strengths": [name for name in key if values[name] == key[name]], "improvements": [name for name in key if values[name] != key[name]], "explanations": challenge["explanations"], "explanation": "A missing resume detail is an evidence gap; it is not proof the candidate lacks that skill."}
            return score, {name: 100 if values[name] == expected else 0 for name, expected in key.items()}, feedback, key

        if evaluation == "priority-selection":
            options = challenge["content"]["options"]
            selected = _as_set(answer.get("actions"), "actions", options)
            if len(selected) != 3:
                raise ValidationError("Choose exactly three next steps")
            expected = set(challenge["answerKey"])
            score, criteria = _score_set_selection(selected, expected)
            feedback = {"strengths": sorted(selected & expected), "improvements": sorted(expected - selected), "explanations": {key: challenge["explanations"][key] for key in selected}, "nextSteps": list(challenge["answerKey"]), "explanation": "Resume wording makes existing evidence clearer. Learning activities build new experience; only claim the skill after you have demonstrated it."}
            return score, criteria, feedback, challenge["answerKey"]

        raise ValidationError("This challenge has no supported evaluator")

    async def _run_ai_evaluation(self, challenge: dict[str, Any], answer: str, target_role: str | None) -> dict[str, Any]:
        profile = challenge["content"].get("candidateProfile", challenge["content"])
        result = await gemini_interview_service.evaluate_practice_writing(
            challenge["title"], challenge["instructions"], profile, answer, target_role
        )
        if not isinstance(result, dict):
            raise ProcessingError("AI evaluation is unavailable. Check GEMINI_API_KEY and try again.")
        try:
            score = int(result["score"])
            criteria = result["criteriaScores"]
            feedback = result["feedback"]
            if not 0 <= score <= 100 or not isinstance(criteria, dict) or not criteria or not isinstance(feedback, dict):
                raise ValueError
            criteria_scores = {str(key)[:60]: max(0, min(100, int(value))) for key, value in criteria.items()}
            if any(not isinstance(feedback.get(key), list) for key in ("strengths", "improvements")):
                raise ValueError
            validated_feedback = {
                "strengths": [str(item)[:500] for item in feedback["strengths"][:6]],
                "improvements": [str(item)[:500] for item in feedback["improvements"][:6]],
                "explanation": str(feedback.get("explanation", ""))[:1000],
            }
            suggested = result.get("suggestedAnswer")
            return {"score": score, "criteriaScores": criteria_scores, "feedback": validated_feedback,
                    "suggestedAnswer": str(suggested)[:3000] if suggested else None}
        except (KeyError, TypeError, ValueError):
            raise ProcessingError("AI returned an invalid evaluation. The attempt was not saved; please retry.")

    def list_attempts(self, student_id: str, challenge_type: str | None, limit: int, offset: int) -> dict[str, Any]:
        query: dict[str, Any] = {"user_id": ObjectId(student_id), "status": "completed"}
        if challenge_type:
            query["challenge_type"] = challenge_type
        total = self.attempts.count_documents(query)
        items = [self._serialize(doc) for doc in self.attempts.find(query).sort("created_at", -1).skip(offset).limit(limit)]
        return {"items": items, "total": total, "limit": limit, "offset": offset}

    def get_attempt(self, student_id: str, attempt_id: str) -> dict[str, Any]:
        if not ObjectId.is_valid(attempt_id):
            raise NotFoundError("Practice attempt not found")
        attempt = self.attempts.find_one({"_id": ObjectId(attempt_id), "user_id": ObjectId(student_id), "status": "completed"})
        if not attempt:
            raise NotFoundError("Practice attempt not found")
        return self._serialize(attempt)

    def get_stats(self, student_id: str, challenge_type: str | None) -> dict[str, Any]:
        query: dict[str, Any] = {"user_id": ObjectId(student_id), "status": "completed"}
        if challenge_type:
            query["challenge_type"] = challenge_type
        docs = list(self.attempts.find(query).sort("created_at", 1))
        resume_scores = [doc["score"] for doc in docs if doc["challenge_type"] == "resume"]
        readiness_scores = [doc["score"] for doc in docs if doc["challenge_type"] == "job-readiness"]
        scores = [doc["score"] for doc in docs]
        average = lambda values: round(sum(values) / len(values), 1) if values else None
        chart = [{
            "attemptId": str(doc["_id"]), "date": doc["created_at"].isoformat(),
            "type": doc["challenge_type"], "challengeName": doc["challenge_name"], "score": doc["score"],
        } for doc in docs]
        return {"summary": {"totalAttempts": len(docs), "resumeAverage": average(resume_scores),
                            "jobReadinessAverage": average(readiness_scores), "overallAverage": average(scores)}, "chart": chart}

    @staticmethod
    def _serialize(doc: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(doc["_id"]), "challengeId": doc["challenge_id"],
            "challengeType": doc["challenge_type"], "challengeName": doc["challenge_name"],
            "challengeVersion": doc.get("challenge_version", 1), "attemptNumber": doc.get("attempt_number", 1),
            "targetRole": doc.get("target_role"),
            "submittedAnswer": doc["submitted_answer"], "score": doc["score"],
            "criteriaScores": doc.get("criteria_scores", {}), "feedback": doc.get("feedback", {}),
            "suggestedAnswer": doc.get("suggested_answer"), "status": doc["status"],
            "createdAt": doc["created_at"].isoformat(), "completedAt": doc["completed_at"].isoformat(),
        }
