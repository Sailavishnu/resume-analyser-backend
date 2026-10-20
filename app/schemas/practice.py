"""Request validation for student practice challenges."""

from typing import Any

from pydantic import BaseModel, Field, field_validator


class PracticeAttemptRequest(BaseModel):
    challengeId: str = Field(min_length=1, max_length=100)
    answer: dict[str, Any]
    targetRole: str | None = Field(default=None, max_length=100)

    @field_validator("answer")
    @classmethod
    def validate_answer_size(cls, answer: dict[str, Any]) -> dict[str, Any]:
        import json
        if not answer:
            raise ValueError("An answer is required")
        if len(json.dumps(answer, ensure_ascii=False, default=str)) > 20000:
            raise ValueError("Answer must be 20,000 characters or fewer")
        return answer


class CodingQuestionRequest(BaseModel):
    targetRole: str = Field(min_length=1, max_length=100)


class CodingEvaluationRequest(BaseModel):
    targetRole: str = Field(min_length=1, max_length=100)
    question: dict[str, Any]
    answer: str = Field(min_length=1, max_length=20000)

    @field_validator("question")
    @classmethod
    def validate_question_size(cls, question: dict[str, Any]) -> dict[str, Any]:
        import json
        if not question or len(json.dumps(question, ensure_ascii=False, default=str)) > 10000:
            raise ValueError("Question must be valid and 10,000 characters or fewer")
        return question
