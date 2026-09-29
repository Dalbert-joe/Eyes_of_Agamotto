from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator


class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    email: str
    password: str = Field(min_length=8)
    role: str = "participant"
    organization: str | None = None
    orgType: str | None = None
    affiliation: str | None = None
    title: str | None = None
    specialization: str | None = None
    college: str | None = None
    degree: str | None = None
    graduationYear: str | None = None
    githubUrl: str | None = None


class LoginIn(BaseModel):
    email: str
    password: str


class RubricCriterion(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    description: str = ""
    weight: float = Field(gt=0)
    maxScore: float = Field(gt=0)
    anchors: list[dict] = []


class EventIn(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    tagline: str = ""
    description: str = ""
    eventCode: str = Field(min_length=3, max_length=64)
    accessCode: str | None = None
    status: str = "registration"
    isPublic: bool = True
    registrationMode: str = "open"
    editingPolicy: str = "allow-until-deadline"
    versioningEnabled: bool = True
    minTeamSize: int = Field(default=1, ge=1, le=20)
    maxTeamSize: int = Field(default=4, ge=1, le=20)
    participantCapacity: int | None = Field(default=None, ge=1)
    judgesPerProject: int = Field(default=3, ge=1, le=20)
    registrationStart: datetime | None = None
    registrationDeadline: datetime | None = None
    submissionDeadline: datetime | None = None
    judgingDeadline: datetime | None = None
    tracks: list[str] = []
    rubric: list[RubricCriterion] = []
    normalizationMethod: str = "z_score"
    tieBreakOrder: list[str] = ["normalized_score", "raw_score", "code_name"]
    prizes: str = ""


class EventUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str | None = None
    tagline: str | None = None
    description: str | None = None
    eventCode: str | None = None
    accessCode: str | None = None
    status: str | None = None
    isPublic: bool | None = None
    registrationMode: str | None = None
    editingPolicy: str | None = None
    versioningEnabled: bool | None = None
    minTeamSize: int | None = Field(default=None, ge=1, le=20)
    maxTeamSize: int | None = Field(default=None, ge=1, le=20)
    participantCapacity: int | None = Field(default=None, ge=1)
    judgesPerProject: int | None = Field(default=None, ge=1, le=20)
    registrationStart: datetime | None = None
    registrationDeadline: datetime | None = None
    submissionDeadline: datetime | None = None
    judgingDeadline: datetime | None = None
    tracks: list[str] | None = None
    rubric: list[RubricCriterion] | None = None
    normalizationMethod: str | None = None
    tieBreakOrder: list[str] | None = None
    prizes: str | None = None


class RegistrationIn(BaseModel):
    accessCode: str | None = None


class JoinByCodeIn(BaseModel):
    eventCode: str
    accessCode: str | None = None


class MembershipDecision(BaseModel):
    status: str


class TeamIn(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    track: str = "General"
    eventId: str


class MemberIn(BaseModel):
    userId: str
    role: str = "Team Member"
    isLeader: bool = False


class ProjectIn(BaseModel):
    eventId: str
    teamId: str
    title: str = Field(min_length=2, max_length=255)
    tagline: str = ""
    problem: str = ""
    solution: str = ""
    techStack: list[str] = []
    githubUrl: str = ""
    demoUrl: str = ""
    presentationFileName: str | None = None
    track: str = "General"


class ProjectUpdate(BaseModel):
    title: str | None = None
    tagline: str | None = None
    problem: str | None = None
    solution: str | None = None
    techStack: list[str] | None = None
    githubUrl: str | None = None
    demoUrl: str | None = None
    presentationFileName: str | None = None
    track: str | None = None
    status: str | None = None
    summary: str = "Submission update"


class AssignmentIn(BaseModel):
    projectId: str
    judgeId: str


class ConflictIn(BaseModel):
    projectId: str | None = None
    reason: str = Field(min_length=3)


class ReviewIn(BaseModel):
    projectId: str
    scores: dict[str, float]
    justifications: dict[str, str] = {}
    justification: str = ""
    status: str = "draft"


class ReopenIn(BaseModel):
    projectId: str
    judgeId: str
    reason: str = Field(min_length=3)


class ResultCalculateIn(BaseModel):
    override: bool = False
    reason: str | None = None
