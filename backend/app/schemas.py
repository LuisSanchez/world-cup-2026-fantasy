from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserOut(BaseModel):
    id: int
    email: str
    name: str
    picture: str
    is_admin: bool
    total_points: int

    class Config:
        from_attributes = True


class MatchOut(BaseModel):
    id: int
    match_number: int
    home_team: str
    away_team: str
    home_flag: str
    away_flag: str
    kickoff: datetime | None
    lock_at: datetime | None  # kickoff minus prediction_lock_minutes; null if no kickoff
    stage: str
    group_name: str
    home_score: int | None
    away_score: int | None
    is_finished: bool
    is_placeholder: bool
    status: str  # upcoming | locked | live | finished
    can_edit: bool

    class Config:
        from_attributes = True


class PredictionOut(BaseModel):
    id: int
    match_id: int
    home_score: int
    away_score: int
    points_goals: int
    points_result: int
    points_total: int

    class Config:
        from_attributes = True


class PredictionWithMatch(BaseModel):
    prediction: PredictionOut | None
    match: MatchOut


class PredictionUpdate(BaseModel):
    home_score: int = Field(ge=0, le=20)
    away_score: int = Field(ge=0, le=20)


class LeaderboardEntry(BaseModel):
    rank: int
    user_id: int
    email: str
    name: str
    picture: str
    total_points: int
    predictions_count: int


class AdminSetScore(BaseModel):
    home_score: int = Field(ge=0, le=20)
    away_score: int = Field(ge=0, le=20)
    is_finished: bool = True


class AdminUpdateMatch(BaseModel):
    home_team: str | None = None
    away_team: str | None = None
    kickoff: datetime | None = None
    home_score: int | None = None
    away_score: int | None = None
    is_finished: bool | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class DevLoginRequest(BaseModel):
    email: EmailStr
