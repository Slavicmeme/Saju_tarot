from datetime import date
from typing import Literal
from pydantic import BaseModel, Field, field_validator, model_validator

Orientation = Literal["upright", "reversed"]

class Profile(BaseModel):
    nickname: str = Field(default="사용자", max_length=30)
    birth_date: date
    birth_time: str | None = Field(default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    time_unknown: bool = False
    calendar_type: Literal["solar", "lunar"] = "solar"
    gender: Literal["female", "male", "other"]
    birth_place: str = Field(default="", max_length=80)

    @field_validator("birth_date")
    @classmethod
    def not_future(cls, value: date):
        if value > date.today():
            raise ValueError("생년월일은 미래일 수 없습니다.")
        return value

    @model_validator(mode="after")
    def validate_time(self):
        if not self.time_unknown and not self.birth_time:
            raise ValueError("태어난 시간을 입력하거나 시간 모름을 선택해 주세요.")
        return self

class SajuRequest(BaseModel):
    profile: Profile
    target_year: int = Field(ge=1900, le=2100)
    target_month: int = Field(ge=1, le=12)

class DrawRequest(BaseModel):
    count: Literal[1, 3, 5, 7, 10] = 3
    spread_type: str = "situation_obstacle_advice"
    seed: int | None = None

class SelectedCard(BaseModel):
    position: str = Field(max_length=40)
    card_id: str = Field(pattern=r"^[0-9]{2}_[a-z0-9_]+$")
    orientation: Orientation

class ReadingRequest(BaseModel):
    profile: Profile
    question: str = Field(default="", max_length=1000)
    category: str = Field(default="general", max_length=40)
    target_year: int = Field(ge=1900, le=2100)
    target_month: int = Field(ge=1, le=12)
    current_situation: str = Field(default="", max_length=1500)
    spread_type: str = "situation_obstacle_advice"
    cards: list[SelectedCard]
    ai_consent: Literal[True]

    @model_validator(mode="after")
    def validate_content(self):
        if not self.question.strip() and self.category == "":
            raise ValueError("질문 또는 상담 분야가 필요합니다.")
        expected = {"one_card": 1, "situation_obstacle_advice": 3, "situation_action_outcome": 3,
                    "past_present_future": 3, "self_other_relationship": 3, "five_card": 5,
                    "celtic_cross": 10, "relationship_seven": 7, "career_five": 5,
                    "money_five": 5, "study_five": 5, "decision_five": 5}.get(self.spread_type)
        if expected is None or len(self.cards) != expected:
            raise ValueError("스프레드와 카드 수가 일치하지 않습니다.")
        if len({c.card_id for c in self.cards}) != len(self.cards):
            raise ValueError("같은 카드는 중복 선택할 수 없습니다.")
        return self
