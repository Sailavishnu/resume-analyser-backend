from typing import Literal

from pydantic import BaseModel, Field, field_validator


class CareerRoadmapRequest(BaseModel):
    targetRole: str = Field(min_length=2, max_length=120)
    frontendSkills: list[str] = Field(default_factory=list, max_length=30)
    backendSkills: list[str] = Field(default_factory=list, max_length=30)
    additionalSkills: list[str] = Field(default_factory=list, max_length=30)
    softSkills: dict[str, int] = Field(default_factory=dict)
    experienceLevel: Literal["beginner", "intermediate", "advanced"] = "beginner"
    hoursPerWeek: int = Field(ge=1, le=80)
    timeframeWeeks: int = Field(ge=4, le=52)

    @field_validator("targetRole")
    @classmethod
    def clean_role(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise ValueError("Target role is required")
        return value

    @field_validator("frontendSkills", "backendSkills", "additionalSkills")
    @classmethod
    def clean_skills(cls, values: list[str]) -> list[str]:
        return list(dict.fromkeys(" ".join(v.split())[:80] for v in values if v.strip()))

    @field_validator("softSkills")
    @classmethod
    def validate_soft_skills(cls, values: dict[str, int]) -> dict[str, int]:
        allowed = {"communication", "teamwork", "problemSolving", "timeManagement"}
        if set(values) - allowed or any(not isinstance(value, int) or not 1 <= value <= 5 for value in values.values()):
            raise ValueError("Soft skill ratings must use the supported fields and range from 1 to 5")
        return values


class PhaseCompletionRequest(BaseModel):
    status: Literal["completed"]
