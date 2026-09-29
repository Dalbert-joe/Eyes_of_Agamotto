from __future__ import annotations

from datetime import datetime, timezone
from math import sqrt
from statistics import mean, pstdev
from uuid import uuid4

import os

from fastapi import Cookie, Depends, FastAPI, HTTPException, Response, status
from fastapi.routing import APIRoute
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .database import get_db
from .models import (
    AuditLog,
    Event,
    EventStatus,
    JudgeAssignment,
    JudgeConflict,
    Membership,
    NormalizationSnapshot,
    Notification,
    Project,
    ProjectVersion,
    Result,
    Review,
    ReviewCriterionScore,
    ReviewStatus,
    Role,
    Team,
    TeamMember,
    User,
)
from .schemas import (
    AssignmentIn,
    ConflictIn,
    EventIn,
    EventUpdate,
    JoinByCodeIn,
    LoginIn,
    MemberIn,
    MembershipDecision,
    ProjectIn,
    ProjectUpdate,
    RegistrationIn,
    RegisterIn,
    ReopenIn,
    ResultCalculateIn,
    ReviewIn,
    TeamIn,
)
from .security import create_refresh_token, create_token, current_user, decode_refresh_token, hash_password, require_role, verify_password

app = FastAPI(title="AGAMOTTO API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------- common helpers ----------------------------

def now() -> datetime:
    return datetime.now(timezone.utc)


def audit(db: Session, actor: User | None, event_id: str | None, action: str, entity_type: str, entity_id: str, details: dict | None = None) -> None:
    db.add(
        AuditLog(
            actor_id=actor.id if actor else None,
            event_id=event_id,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id),
            details=details or {},
        )
    )


def fail(status_code: int, detail: str) -> None:
    raise HTTPException(status_code=status_code, detail=detail)


def get_event_or_404(db: Session, event_id: str) -> Event:
    event = db.get(Event, event_id)
    if not event:
        fail(404, "Event not found")
    return event


def require_event_owner(db: Session, event_id: str, user: User) -> Event:
    event = get_event_or_404(db, event_id)
    if event.organizer_id != user.id:
        fail(403, "You do not own this event")
    return event


def membership_for(db: Session, event_id: str, user_id: str) -> Membership | None:
    return db.scalar(select(Membership).where(Membership.event_id == event_id, Membership.user_id == user_id))


def team_members(db: Session, team_id: str) -> list[TeamMember]:
    return list(db.scalars(select(TeamMember).where(TeamMember.team_id == team_id)).all())


def team_member_count(db: Session, team_id: str) -> int:
    return db.scalar(select(func.count()).select_from(TeamMember).where(TeamMember.team_id == team_id)) or 0


def participant_team(db: Session, event_id: str, user_id: str) -> Team | None:
    return db.scalar(
        select(Team)
        .join(TeamMember, TeamMember.team_id == Team.id)
        .where(Team.event_id == event_id, TeamMember.user_id == user_id)
    )


def rubric_valid(rubric: list[dict]) -> None:
    if not rubric:
        fail(422, "Event requires at least one rubric criterion")
    ids: set[str] = set()
    total = 0.0
    for criterion in rubric:
        cid = str(criterion.get("id", "")).strip()
        name = str(criterion.get("name", "")).strip()
        if not cid or not name:
            fail(422, "Every rubric criterion requires id and name")
        if cid in ids:
            fail(422, "Rubric criterion IDs must be unique")
        ids.add(cid)
        try:
            weight = float(criterion["weight"])
            max_score = float(criterion["maxScore"])
        except (KeyError, TypeError, ValueError) as exc:
            raise HTTPException(422, "Each rubric criterion requires numeric weight and maximum score") from exc
        if weight <= 0 or max_score <= 0:
            fail(422, "Rubric weights and maximum scores must be positive")
        total += weight
    if abs(total - 100.0) > 1e-6:
        fail(422, "Rubric weights must total exactly 100%")


def validate_event_dates(data: EventIn | EventUpdate) -> None:
    values = {
        "registrationStart": getattr(data, "registrationStart", None),
        "registrationDeadline": getattr(data, "registrationDeadline", None),
        "submissionDeadline": getattr(data, "submissionDeadline", None),
        "judgingDeadline": getattr(data, "judgingDeadline", None),
    }
    ordered = [v for v in values.values() if v is not None]
    if any(a > b for a, b in zip(ordered, ordered[1:])):
        fail(422, "Event dates must be chronological")


def user_data(user: User) -> dict:
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "organization": user.organization,
        "orgType": user.org_type,
        "affiliation": user.affiliation,
        "title": user.title,
        "specialization": user.specialization,
        "college": user.college,
        "degree": user.degree,
        "graduationYear": user.graduation_year,
        "githubUrl": user.github_url,
    }


def event_data(event: Event, db: Session) -> dict:
    count = db.scalar(
        select(func.count()).select_from(Membership).where(
            Membership.event_id == event.id,
            Membership.status.in_(["approved", "pending"]),
        )
    ) or 0
    return {
        "id": event.id,
        "title": event.title,
        "tagline": event.tagline,
        "description": event.description,
        "eventCode": event.event_code,
        "accessCode": event.access_code,
        "status": event.status,
        "isPublic": event.is_public,
        "registrationMode": event.registration_mode,
        "editingPolicy": event.editing_policy,
        "versioningEnabled": event.versioning_enabled,
        "minTeamSize": event.min_team_size,
        "maxTeamSize": event.max_team_size,
        "participantCapacity": event.participant_capacity,
        "judgesPerProject": event.judges_per_project,
        "registrationStart": event.registration_start,
        "registrationDeadline": event.registration_deadline,
        "submissionDeadline": event.submission_deadline,
        "judgingDeadline": event.judging_deadline,
        "tracks": event.tracks or [],
        "prizes": event.prizes,
        "rubric": event.rubric or [],
        "normalizationMethod": event.normalization_method,
        "tieBreakOrder": event.tie_break_order or ["normalized_score", "raw_score", "code_name"],
        "identityRevealed": False,
        "participantsCount": count,
    }


def member_data(db: Session, team: Team) -> list[dict]:
    output = []
    for membership in team_members(db, team.id):
        user = db.get(User, membership.user_id)
        if user:
            output.append(
                {
                    "id": user.id,
                    "name": user.name,
                    "email": user.email,
                    "college": user.college or "",
                    "role": membership.role,
                    "isLeader": membership.is_leader,
                }
            )
    return output


def review_data(db: Session, review: Review, viewer: User | None = None) -> dict:
    scores = db.scalars(select(ReviewCriterionScore).where(ReviewCriterionScore.review_id == review.id)).all()
    show_judge = viewer is not None and viewer.role == Role.ORGANIZER
    return {
        "id": review.id,
        "judgeId": review.judge_id if show_judge or (viewer and viewer.id == review.judge_id) else None,
        "judgeName": (db.get(User, review.judge_id).name if show_judge else ("You" if viewer and viewer.id == review.judge_id else "Judge")),
        "criteriaScores": {s.criterion_id: s.score for s in scores},
        "justifications": {s.criterion_id: s.justification for s in scores},
        "totalRaw": review.total_raw,
        "submittedAt": review.updated_at,
        "status": review.status,
    }


def project_data(db: Session, project: Project, viewer: User | None = None, blind: bool = False) -> dict:
    event = db.get(Event, project.event_id)
    if event is None:
        fail(404, "Event not found")
    team = db.get(Team, project.team_id)
    members = member_data(db, team) if team else []
    assigned = db.scalars(select(JudgeAssignment).where(JudgeAssignment.project_id == project.id)).all()

    if viewer and viewer.role == Role.JUDGE:
        reviews = db.scalars(select(Review).where(Review.project_id == project.id, Review.judge_id == viewer.id)).all()
    elif viewer and viewer.role == Role.PARTICIPANT:
        reviews = []
    else:
        reviews = db.scalars(select(Review).where(Review.project_id == project.id)).all()

    scores = [review_data(db, review, viewer) for review in reviews]
    versions = db.scalars(
        select(ProjectVersion).where(ProjectVersion.project_id == project.id).order_by(ProjectVersion.version)
    ).all()

    latest_result = db.scalar(
        select(Result).where(Result.project_id == project.id, Result.published.is_(True)).order_by(Result.created_at.desc())
    )
    result = {
        "id": project.id,
        "eventId": project.event_id,
        "codeName": project.code_name,
        "title": project.title,
        "tagline": project.tagline,
        "track": project.track,
        "problem": project.problem,
        "solution": project.solution,
        "techStack": project.tech_stack or [],
        "githubUrl": project.github_url,
        "demoUrl": project.demo_url,
        "presentationFileName": project.presentation_file_name,
        "submittedAt": project.submitted_at,
        "status": project.status,
        "assignedJudges": [] if blind or (viewer and viewer.role == Role.PARTICIPANT) else [a.judge_id for a in assigned],
        "scores": scores,
        "rawAverage": latest_result.raw_score if latest_result else 0,
        "normalizedScore": latest_result.normalized_score if latest_result else 0,
        "zScoreRaw": latest_result.normalized_score if latest_result and event.normalization_method == "z_score" else 0,
        "rank": latest_result.rank if latest_result else 0,
        "versions": [
            {"version": v.version, "timestamp": v.timestamp, "summary": v.summary, "editedBy": v.edited_by}
            for v in versions
        ],
    }
    if not blind:
        result.update({
            "teamName": team.name if team else "",
            "members": members,
            "college": members[0]["college"] if members else "",
        })
    else:
        # Blind responses intentionally omit team/member identity and assignment metadata.
        result.update({"teamName": "", "members": [], "college": ""})
    return result


def audit_action_rows(db: Session, event_id: str) -> list[dict]:
    rows = db.scalars(select(AuditLog).where(AuditLog.event_id == event_id).order_by(AuditLog.created_at.desc())).all()
    output = []
    for row in rows:
        actor = db.get(User, row.actor_id) if row.actor_id else None
        output.append({
            "id": row.id,
            "eventId": row.event_id,
            "timestamp": row.created_at,
            "actor": actor.name if actor else "system",
            "actorRole": actor.role if actor else "system",
            "action": row.action,
            "entity": row.entity_type,
            "details": ", ".join(f"{k}: {v}" for k, v in (row.details or {}).items()),
        })
    return output


def event_open_for_registration(event: Event) -> None:
    current = now()
    if event.status != EventStatus.REGISTRATION:
        fail(409, "Registration is closed for this event phase")
    if event.registration_start and current < event.registration_start:
        fail(409, "Registration has not opened")
    if event.registration_deadline and current > event.registration_deadline:
        fail(409, "Registration is closed")

def event_in_phase(event: Event, phase: str, label: str) -> None:
    if event.status != phase:
        fail(409, f"{label} is only available during the {phase} phase")

def validate_status_transition(current: str, target: str) -> None:
    if target == current:
        return
    allowed = {
        EventStatus.DRAFT: {EventStatus.REGISTRATION, EventStatus.CLOSED},
        EventStatus.REGISTRATION: {EventStatus.SUBMISSION, EventStatus.CLOSED},
        EventStatus.SUBMISSION: {EventStatus.JUDGING, EventStatus.CLOSED},
        EventStatus.JUDGING: {EventStatus.CLOSED},
        EventStatus.RESULTS: {EventStatus.ARCHIVED},
    }
    if target not in allowed.get(current, set()):
        fail(409, f"Invalid event status transition: {current} -> {target}")


def submission_is_editable(event: Event, project: Project, db: Session) -> bool:
    if event.editing_policy == "locked":
        return False
    if event.submission_deadline and now() > event.submission_deadline:
        return False
    if event.editing_policy == "lock-on-first-review":
        return not bool(db.scalar(select(Review.id).where(Review.project_id == project.id)))
    return True


def require_project_access(db: Session, project: Project, user: User, allow_organizer: bool = True) -> Event:
    event = get_event_or_404(db, project.event_id)
    if user.role == Role.ORGANIZER:
        if not allow_organizer or event.organizer_id != user.id:
            fail(403, "Permission denied")
    elif user.role == Role.JUDGE:
        if not db.scalar(select(JudgeAssignment).where(JudgeAssignment.project_id == project.id, JudgeAssignment.judge_id == user.id)):
            fail(403, "Project not assigned")
    elif user.role == Role.PARTICIPANT:
        if not db.scalar(select(TeamMember).where(TeamMember.team_id == project.team_id, TeamMember.user_id == user.id)):
            fail(403, "You are not a member of this project team")
    return event


def blocking_conflict(db: Session, project: Project, judge: User) -> str | None:
    if db.scalar(select(TeamMember).where(TeamMember.team_id == project.team_id, TeamMember.user_id == judge.id)):
        return "Judge is a project team member"
    if db.scalar(
        select(Project.id)
        .join(Team, Team.id == Project.team_id)
        .join(TeamMember, TeamMember.team_id == Team.id)
        .where(Project.event_id == project.event_id, TeamMember.user_id == judge.id)
    ):
        return "Judge participated in the event"
    if db.scalar(
        select(JudgeConflict).where(
            JudgeConflict.project_id == project.id,
            JudgeConflict.judge_id == judge.id,
            JudgeConflict.blocking.is_(True),
        )
    ):
        conflict = db.scalar(
            select(JudgeConflict).where(
                JudgeConflict.project_id == project.id,
                JudgeConflict.judge_id == judge.id,
                JudgeConflict.blocking.is_(True),
            )
        )
        return conflict.reason if conflict else "Blocking conflict exists"
    return None


def validate_review_scores(event: Event, scores: dict[str, float], require_all: bool) -> float:
    rubric = {str(c["id"]): c for c in event.rubric}
    unknown = set(scores) - set(rubric)
    if unknown:
        fail(422, f"Unknown rubric criteria: {', '.join(sorted(unknown))}")
    if require_all and set(scores) != set(rubric):
        missing = sorted(set(rubric) - set(scores))
        fail(422, f"Missing required rubric criteria: {', '.join(missing)}")
    total = 0.0
    for criterion_id, value in scores.items():
        try:
            score = float(value)
        except (TypeError, ValueError) as exc:
            raise HTTPException(422, f"Score for {criterion_id} must be numeric") from exc
        max_score = float(rubric[criterion_id]["maxScore"])
        if score < 0 or score > max_score:
            fail(422, f"Score for {criterion_id} must be between 0 and {max_score}")
        total += (score / max_score) * float(rubric[criterion_id]["weight"])
    return round(total, 4)


def calculate_normalized(event: Event, completed: dict[str, list[Review]], db: Session) -> tuple[dict[str, dict], dict]:
    all_reviews = [review for reviews in completed.values() for review in reviews]
    judge_scores: dict[str, list[float]] = {}
    for review in all_reviews:
        judge_scores.setdefault(review.judge_id, []).append(review.total_raw)

    statistics: dict[str, dict] = {}
    for judge_id, values in judge_scores.items():
        mu = mean(values)
        sd = pstdev(values) if len(values) > 1 else 0.0
        statistics[judge_id] = {"mean": round(mu, 6), "std": round(sd, 6), "count": len(values)}

    method = event.normalization_method
    if method == "z_score":
        normalized_by_project: dict[str, float] = {}
        for project_id, reviews in completed.items():
            z_values = []
            for review in reviews:
                stats = statistics[review.judge_id]
                z_values.append((review.total_raw - stats["mean"]) / stats["std"] if stats["std"] > 0 else 0.0)
            normalized_by_project[project_id] = mean(z_values) if z_values else 0.0
        metadata = {"method": method, "fallback": "zero_z_for_singleton_or_zero_variance_judge", "judgeStatistics": statistics}
    elif method == "trimmed_mean":
        normalized_by_project = {}
        for project_id, reviews in completed.items():
            values = sorted(r.total_raw for r in reviews)
            trim = 1 if len(values) >= 3 else 0
            kept = values[trim:len(values) - trim] if len(values) > 2 * trim else values
            normalized_by_project[project_id] = mean(kept) if kept else 0.0
        metadata = {"method": method, "trim": "one value from each tail when at least three judges exist", "judgeStatistics": statistics}
    elif method == "borda":
        normalized_by_project = {project_id: 0.0 for project_id in completed}
        by_judge: dict[str, list[tuple[str, float]]] = {}
        for project_id, reviews in completed.items():
            for review in reviews:
                by_judge.setdefault(review.judge_id, []).append((project_id, review.total_raw))
        for judge_id, entries in by_judge.items():
            ordered = sorted(entries, key=lambda x: x[1], reverse=True)
            n = len(ordered)
            for position, (project_id, _) in enumerate(ordered):
                normalized_by_project[project_id] += (n - position) / n * 100
        for project_id in normalized_by_project:
            normalized_by_project[project_id] /= max(len(completed[project_id]), 1)
        metadata = {"method": method, "judgeStatistics": statistics}
    else:
        fail(422, f"Unsupported normalization method: {method}")
    return {
        project_id: {"normalized": round(normalized_by_project[project_id], 6), "raw": round(mean(r.total_raw for r in reviews), 6)}
        for project_id, reviews in completed.items()
    }, metadata


# ---------------------------- health/auth ----------------------------

@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


def auth_response(user: User, response: Response) -> dict:
    response.set_cookie("agamotto_refresh", create_refresh_token(user), httponly=True, secure=False, samesite="lax", max_age=7 * 24 * 60 * 60, path="/api/auth")
    return {"accessToken": create_token(user), "tokenType": "bearer", "user": user_data(user)}

@app.post("/auth/register")
def register(data: RegisterIn, response: Response, db: Session = Depends(get_db)):
    role = data.role.lower()
    if role not in {Role.ORGANIZER, Role.JUDGE, Role.PARTICIPANT}:
        fail(422, "Invalid role")
    email = data.email.strip().lower()
    if db.scalar(select(User).where(User.email == email)):
        fail(409, "Email already registered")
    user = User(
        email=email,
        name=data.name.strip(),
        password_hash=hash_password(data.password),
        role=role,
        organization=data.organization,
        org_type=data.orgType,
        affiliation=data.affiliation,
        title=data.title,
        specialization=data.specialization,
        college=data.college,
        degree=data.degree,
        graduation_year=data.graduationYear,
        github_url=data.githubUrl,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Email already registered") from exc
    db.refresh(user)
    return auth_response(user, response)


@app.post("/auth/login")
def login(data: LoginIn, response: Response, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == data.email.strip().lower()))
    if not user or not verify_password(data.password, user.password_hash):
        fail(401, "Invalid email or password")
    return auth_response(user, response)


@app.post("/auth/refresh")
def refresh(response: Response, agamotto_refresh: str | None = Cookie(default=None), db: Session = Depends(get_db)):
    if not agamotto_refresh:
        fail(401, "Refresh token required")
    payload = decode_refresh_token(agamotto_refresh)
    user = db.get(User, payload.get("sub"))
    if not user:
        fail(401, "User not found")
    return auth_response(user, response)

@app.post("/auth/logout")
def logout(response: Response):
    response.delete_cookie("agamotto_refresh", path="/api/auth")
    return {"loggedOut": True}

@app.get("/auth/me")
def me(user: User = Depends(current_user)):
    return user_data(user)


# ---------------------------- events ----------------------------

@app.get("/events")
def list_events(db: Session = Depends(get_db), user: User = Depends(current_user)):
    events = db.scalars(select(Event).order_by(Event.created_at.desc())).all()
    if user.role == Role.ORGANIZER:
        events = [e for e in events if e.organizer_id == user.id]
    else:
        events = [e for e in events if e.is_public or membership_for(db, e.id, user.id)]
    return [event_data(e, db) for e in events]


@app.post("/events", status_code=201)
def create_event(data: EventIn, db: Session = Depends(get_db), user: User = Depends(require_role(Role.ORGANIZER))):
    if data.minTeamSize > data.maxTeamSize:
        fail(422, "Minimum team size cannot exceed maximum")
    validate_event_dates(data)
    rubric = [c.model_dump() for c in data.rubric]
    rubric_valid(rubric)
    if data.normalizationMethod not in {"z_score", "trimmed_mean", "borda"}:
        fail(422, "Unsupported normalization method")
    if data.status not in {EventStatus.DRAFT, EventStatus.REGISTRATION}:
        fail(422, "New events must start in draft or registration")
    allowed_ties = {"normalized_score", "raw_score", "code_name"}
    if not data.tieBreakOrder or len(data.tieBreakOrder) != len(set(data.tieBreakOrder)) or any(item not in allowed_ties for item in data.tieBreakOrder):
        fail(422, "Tie-break order must contain unique values from normalized_score, raw_score, code_name")
    event = Event(
        organizer_id=user.id,
        title=data.title,
        tagline=data.tagline,
        description=data.description,
        event_code=data.eventCode.strip().upper(),
        access_code=data.accessCode,
        status=data.status,
        is_public=data.isPublic,
        registration_mode=data.registrationMode,
        editing_policy=data.editingPolicy,
        versioning_enabled=data.versioningEnabled,
        min_team_size=data.minTeamSize,
        max_team_size=data.maxTeamSize,
        participant_capacity=data.participantCapacity,
        judges_per_project=data.judgesPerProject,
        registration_start=data.registrationStart,
        registration_deadline=data.registrationDeadline,
        submission_deadline=data.submissionDeadline,
        judging_deadline=data.judgingDeadline,
        tracks=data.tracks,
        rubric=rubric,
        normalization_method=data.normalizationMethod,
        tie_break_order=data.tieBreakOrder,
        prizes=data.prizes,
    )
    db.add(event)
    try:
        db.flush()
        audit(db, user, event.id, "EVENT_CREATED", "event", event.id, {"title": event.title})
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Event code is already in use") from exc
    db.refresh(event)
    return event_data(event, db)


@app.get("/events/{event_id}")
def get_event(event_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    event = get_event_or_404(db, event_id)
    if not event.is_public and user.role != Role.ORGANIZER and not membership_for(db, event.id, user.id):
        fail(403, "Private event")
    return event_data(event, db)


@app.patch("/events/{event_id}")
def update_event(event_id: str, data: EventUpdate, db: Session = Depends(get_db), user: User = Depends(require_role(Role.ORGANIZER))):
    event = require_event_owner(db, event_id, user)
    values = data.model_dump(exclude_unset=True)
    if "minTeamSize" in values and "maxTeamSize" in values:
        if values["minTeamSize"] > values["maxTeamSize"]:
            fail(422, "Minimum team size cannot exceed maximum")
    if "rubric" in values:
        values["rubric"] = [c.model_dump() if hasattr(c, "model_dump") else c for c in values["rubric"]]
        rubric_valid(values["rubric"])
    if "normalizationMethod" in values and values["normalizationMethod"] not in {"z_score", "trimmed_mean", "borda"}:
        fail(422, "Unsupported normalization method")
    if "tieBreakOrder" in values:
        allowed_ties = {"normalized_score", "raw_score", "code_name"}
        if not values["tieBreakOrder"] or len(values["tieBreakOrder"]) != len(set(values["tieBreakOrder"])) or any(item not in allowed_ties for item in values["tieBreakOrder"]):
            fail(422, "Tie-break order must contain unique values from normalized_score, raw_score, code_name")
    if "registrationStart" in values or "registrationDeadline" in values or "submissionDeadline" in values or "judgingDeadline" in values:
        merged = {
            "registrationStart": values.get("registrationStart", event.registration_start),
            "registrationDeadline": values.get("registrationDeadline", event.registration_deadline),
            "submissionDeadline": values.get("submissionDeadline", event.submission_deadline),
            "judgingDeadline": values.get("judgingDeadline", event.judging_deadline),
        }
        ordered = [v for v in merged.values() if v is not None]
        if any(a > b for a, b in zip(ordered, ordered[1:])):
            fail(422, "Event dates must be chronological")
    if "status" in values:
        validate_status_transition(event.status, values["status"])
    mapping = {
        "title": "title", "tagline": "tagline", "description": "description", "eventCode": "event_code",
        "accessCode": "access_code", "status": "status", "isPublic": "is_public", "registrationMode": "registration_mode",
        "editingPolicy": "editing_policy", "versioningEnabled": "versioning_enabled", "minTeamSize": "min_team_size",
        "maxTeamSize": "max_team_size", "participantCapacity": "participant_capacity", "judgesPerProject": "judges_per_project",
        "registrationStart": "registration_start", "registrationDeadline": "registration_deadline", "submissionDeadline": "submission_deadline",
        "judgingDeadline": "judging_deadline", "tracks": "tracks", "rubric": "rubric", "normalizationMethod": "normalization_method", "tieBreakOrder": "tie_break_order",
        "prizes": "prizes",
    }
    for key, value in values.items():
        if key in mapping:
            setattr(event, mapping[key], value.upper() if key == "eventCode" and isinstance(value, str) else value)
    if event.min_team_size > event.max_team_size:
        fail(422, "Minimum team size cannot exceed maximum")
    try:
        db.flush()
        audit(db, user, event.id, "EVENT_UPDATED", "event", event.id, {"fields": list(values)})
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Event code is already in use") from exc
    db.refresh(event)
    return event_data(event, db)


# ---------------------------- registration ----------------------------

@app.post("/events/join-by-code")
def join_by_code(data: JoinByCodeIn, db: Session = Depends(get_db), user: User = Depends(require_role(Role.PARTICIPANT))):
    event = db.scalar(select(Event).where(Event.event_code == data.eventCode.strip().upper()))
    if not event:
        fail(404, "Event not found for event code")
    if not event.is_public and data.accessCode != event.access_code:
        fail(403, "Invalid event access code")
    return register_event(event.id, RegistrationIn(accessCode=data.accessCode), db, user)


@app.post("/events/{event_id}/register")
def register_event(event_id: str, data: RegistrationIn, db: Session = Depends(get_db), user: User = Depends(require_role(Role.PARTICIPANT))):
    event = get_event_or_404(db, event_id)
    event_open_for_registration(event)
    if not event.is_public and data.accessCode != event.access_code:
        fail(403, "Invalid event access code")
    if membership_for(db, event.id, user.id):
        fail(409, "Participant is already registered")
    count = db.scalar(select(func.count()).select_from(Membership).where(Membership.event_id == event.id)) or 0
    if event.participant_capacity and count >= event.participant_capacity:
        fail(409, "Participant capacity reached")
    status_value = "approved" if event.registration_mode == "open" else "pending"
    membership = Membership(event_id=event.id, user_id=user.id, status=status_value)
    db.add(membership)
    try:
        db.flush()
        audit(db, user, event.id, "PARTICIPANT_REGISTERED" if status_value == "approved" else "PARTICIPANT_REGISTERED_BY_CODE", "membership", membership.id, {"status": status_value})
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Participant is already registered") from exc
    return {"registered": True, "status": status_value}


@app.get("/events/{event_id}/participants")
def participants(event_id: str, db: Session = Depends(get_db), user: User = Depends(require_role(Role.ORGANIZER))):
    require_event_owner(db, event_id, user)
    output = []
    memberships = db.scalars(select(Membership).where(Membership.event_id == event_id).order_by(Membership.created_at)).all()
    for membership in memberships:
        participant = db.get(User, membership.user_id)
        team = participant_team(db, event_id, membership.user_id)
        output.append({
            "id": participant.id,
            "name": participant.name,
            "email": participant.email,
            "college": participant.college or "",
            "degree": participant.degree or "",
            "graduationYear": participant.graduation_year or "",
            "teamId": team.id if team else None,
            "teamName": team.name if team else None,
            "status": membership.status,
            "registeredAt": membership.created_at,
            "github": participant.github_url or "",
        })
    return output


@app.patch("/events/{event_id}/participants/{participant_id}")
def decide_membership(event_id: str, participant_id: str, data: MembershipDecision, db: Session = Depends(get_db), user: User = Depends(require_role(Role.ORGANIZER))):
    event = require_event_owner(db, event_id, user)
    if data.status not in {"approved", "rejected"}:
        fail(422, "Membership status must be approved or rejected")
    membership = membership_for(db, event_id, participant_id)
    if not membership:
        fail(404, "Membership not found")
    membership.status = data.status
    audit(db, user, event.id, "MEMBERSHIP_APPROVED" if data.status == "approved" else "MEMBERSHIP_REJECTED", "membership", membership.id, {"status": data.status})
    db.commit()
    return {"id": membership.id, "status": membership.status}


# ---------------------------- teams ----------------------------

@app.post("/events/{event_id}/teams", status_code=201)
def create_team(event_id: str, data: TeamIn, db: Session = Depends(get_db), user: User = Depends(require_role(Role.PARTICIPANT))):
    if data.eventId != event_id:
        fail(422, "Event ID does not match path")
    event = get_event_or_404(db, event_id)
    membership = membership_for(db, event_id, user.id)
    if not membership or membership.status != "approved":
        fail(403, "You are not an approved participant")
    if participant_team(db, event_id, user.id):
        fail(409, "You already belong to a team in this event")
    if event.status not in {EventStatus.REGISTRATION, EventStatus.SUBMISSION}:
        fail(409, "Team changes are closed")
    team = Team(event_id=event_id, name=data.name.strip(), track=data.track, invite_code=f"{data.name[:4].upper()}-{str(uuid4())[:6].upper()}")
    db.add(team)
    db.flush()
    db.add(TeamMember(team_id=team.id, user_id=user.id, is_leader=True, role="Team Lead"))
    audit(db, user, event_id, "TEAM_CREATED", "team", team.id, {})
    db.commit()
    db.refresh(team)
    return team_data(db, team)


@app.get("/events/{event_id}/teams")
def teams(event_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    event = get_event_or_404(db, event_id)
    if user.role != Role.ORGANIZER and not membership_for(db, event_id, user.id):
        fail(403, "Not a member of this event")
    if user.role == Role.PARTICIPANT:
        own = participant_team(db, event_id, user.id)
        return [team_data(db, own)] if own else []
    return [team_data(db, team) for team in db.scalars(select(Team).where(Team.event_id == event_id)).all()]


def team_data(db: Session, team: Team) -> dict:
    return {
        "id": team.id,
        "eventId": team.event_id,
        "name": team.name,
        "inviteCode": team.invite_code,
        "track": team.track,
        "members": member_data(db, team),
    }


@app.post("/teams/{team_id}/members")
def add_member(team_id: str, data: MemberIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    team = db.get(Team, team_id)
    if not team:
        fail(404, "Team not found")
    event = get_event_or_404(db, team.event_id)
    target = db.get(User, data.userId)
    if not target or target.role != Role.PARTICIPANT:
        fail(404, "Participant not found")
    leader = db.scalar(select(TeamMember).where(TeamMember.team_id == team.id, TeamMember.user_id == user.id, TeamMember.is_leader.is_(True)))
    if user.role != Role.ORGANIZER and not leader:
        fail(403, "Only the team leader can manage membership")
    if event.status not in {EventStatus.REGISTRATION, EventStatus.SUBMISSION}:
        fail(409, "Team changes are closed")
    target_membership = membership_for(db, event.id, target.id)
    if not target_membership or target_membership.status != "approved":
        fail(403, "Participant is not approved for this event")
    if participant_team(db, event.id, target.id):
        fail(409, "Participant already has a team in this event")
    if team_member_count(db, team.id) >= event.max_team_size:
        fail(409, "Maximum team size reached")
    db.add(TeamMember(team_id=team.id, user_id=target.id, is_leader=data.isLeader, role=data.role))
    audit(db, user, event.id, "TEAM_UPDATED", "team", team.id, {"addedUserId": target.id})
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Participant is already on this team") from exc
    db.refresh(team)
    return team_data(db, team)


# ---------------------------- projects ----------------------------

@app.post("/events/{event_id}/projects", status_code=201)
def create_project(event_id: str, data: ProjectIn, db: Session = Depends(get_db), user: User = Depends(require_role(Role.PARTICIPANT))):
    if data.eventId != event_id:
        fail(422, "Event ID does not match path")
    event = get_event_or_404(db, event_id)
    event_in_phase(event, EventStatus.SUBMISSION, "Submission")
    if event.submission_deadline and now() > event.submission_deadline:
        fail(409, "Submission deadline has passed")
    team = db.get(Team, data.teamId)
    if not team or team.event_id != event_id:
        fail(404, "Team not found")
    if not db.scalar(select(TeamMember).where(TeamMember.team_id == team.id, TeamMember.user_id == user.id)):
        fail(403, "Not a team member")
    if team_member_count(db, team.id) < event.min_team_size:
        fail(409, f"Team must contain at least {event.min_team_size} approved member(s) before submission")
    if db.scalar(select(Project).where(Project.team_id == team.id)):
        fail(409, "Team already has a project")
    project = Project(
        event_id=event_id,
        team_id=team.id,
        code_name=f"PROJECT-{str(uuid4())[:8].upper()}",
        title=data.title,
        tagline=data.tagline,
        problem=data.problem,
        solution=data.solution,
        tech_stack=data.techStack,
        github_url=data.githubUrl,
        demo_url=data.demoUrl,
        presentation_file_name=data.presentationFileName,
        track=data.track,
    )
    db.add(project)
    db.flush()
    if event.versioning_enabled:
        db.add(ProjectVersion(project_id=project.id, version=1, edited_by=user.id, summary="Initial submission", snapshot={"title": project.title, "problem": project.problem, "solution": project.solution, "techStack": project.tech_stack, "githubUrl": project.github_url, "demoUrl": project.demo_url}))
    audit(db, user, event_id, "PROJECT_CREATED", "project", project.id, {"teamId": team.id})
    db.commit()
    db.refresh(project)
    return project_data(db, project, user, False)


@app.patch("/projects/{project_id}")
def update_project(project_id: str, data: ProjectUpdate, db: Session = Depends(get_db), user: User = Depends(current_user)):
    project = db.get(Project, project_id)
    if not project:
        fail(404, "Project not found")
    event = require_project_access(db, project, user, allow_organizer=True)
    if user.role == Role.JUDGE:
        fail(403, "Judges cannot edit submissions")
    if user.role == Role.PARTICIPANT and event.status != EventStatus.SUBMISSION:
        fail(409, "Submission editing is closed outside the submission phase")
    if user.role == Role.PARTICIPANT and not submission_is_editable(event, project, db):
        fail(409, "Submission editing is closed by event policy")
    values = data.model_dump(exclude_unset=True, exclude={"summary"})
    if "status" in values and values["status"] not in {"draft", "submitted", "locked"}:
        fail(422, "Invalid project status")
    if user.role == Role.PARTICIPANT and values.get("status") == "locked" and not submission_is_editable(event, project, db):
        fail(409, "Submission is already locked by event policy")
    mapping = {"title": "title", "tagline": "tagline", "problem": "problem", "solution": "solution", "techStack": "tech_stack", "githubUrl": "github_url", "demoUrl": "demo_url", "presentationFileName": "presentation_file_name", "track": "track", "status": "status"}
    changed = False
    for key, value in values.items():
        if key in mapping and value is not None:
            if getattr(project, mapping[key]) != value:
                setattr(project, mapping[key], value)
                changed = True
    if changed:
        project.version += 1
        project.submitted_at = now()
        if event.versioning_enabled:
            db.add(ProjectVersion(project_id=project.id, version=project.version, edited_by=user.id, summary=data.summary, snapshot={"title": project.title, "problem": project.problem, "solution": project.solution, "techStack": project.tech_stack, "githubUrl": project.github_url, "demoUrl": project.demo_url, "track": project.track}))
        audit(db, user, event.id, "PROJECT_UPDATED", "project", project.id, {"version": project.version, "summary": data.summary})
        db.commit()
    return project_data(db, project, user, False)


@app.get("/events/{event_id}/projects")
def list_projects(event_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    event = get_event_or_404(db, event_id)
    projects = db.scalars(select(Project).where(Project.event_id == event_id)).all()
    if user.role == Role.ORGANIZER:
        if event.organizer_id != user.id:
            fail(403, "Permission denied")
        return [project_data(db, project, user, False) for project in projects]
    if user.role == Role.JUDGE:
        assigned = {a.project_id for a in db.scalars(select(JudgeAssignment).where(JudgeAssignment.judge_id == user.id)).all()}
        return [project_data(db, project, user, True) for project in projects if project.id in assigned]
    team = participant_team(db, event_id, user.id)
    if not team:
        return []
    return [project_data(db, project, user, False) for project in projects if project.team_id == team.id]


@app.get("/projects/{project_id}")
def get_project(project_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    project = db.get(Project, project_id)
    if not project:
        fail(404, "Project not found")
    blind = user.role == Role.JUDGE
    require_project_access(db, project, user)
    return project_data(db, project, user, blind)


# ---------------------------- judge assignment/conflicts ----------------------------

@app.post("/assignments")
def assign(data: AssignmentIn, db: Session = Depends(get_db), user: User = Depends(require_role(Role.ORGANIZER))):
    project = db.get(Project, data.projectId)
    judge = db.get(User, data.judgeId)
    if not project or not judge:
        fail(404, "Project or judge not found")
    if judge.role != Role.JUDGE:
        fail(422, "Assigned user must have judge role")
    event = require_event_owner(db, project.event_id, user)
    event_in_phase(event, EventStatus.JUDGING, "Judge assignment")
    if db.scalar(select(JudgeAssignment).where(JudgeAssignment.project_id == project.id, JudgeAssignment.judge_id == judge.id)):
        fail(409, "Judge already assigned")
    reason = blocking_conflict(db, project, judge)
    if reason:
        audit(db, user, event.id, "JUDGE_ASSIGNMENT_BLOCKED", "assignment", project.id, {"judgeId": judge.id, "reason": reason})
        db.commit()
        fail(409, reason)
    assignment = JudgeAssignment(project_id=project.id, judge_id=judge.id)
    db.add(assignment)
    audit(db, user, event.id, "JUDGE_ASSIGNED", "assignment", assignment.id, {"judgeId": judge.id, "projectId": project.id})
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Judge already assigned") from exc
    return {"assigned": True, "id": assignment.id}


@app.delete("/assignments/{project_id}/{judge_id}")
def unassign(project_id: str, judge_id: str, db: Session = Depends(get_db), user: User = Depends(require_role(Role.ORGANIZER))):
    assignment = db.scalar(select(JudgeAssignment).where(JudgeAssignment.project_id == project_id, JudgeAssignment.judge_id == judge_id))
    if not assignment:
        fail(404, "Assignment not found")
    project = db.get(Project, project_id)
    event = require_event_owner(db, project.event_id, user)
    db.delete(assignment)
    audit(db, user, event.id, "JUDGE_ASSIGNMENT_REMOVED", "assignment", assignment.id, {})
    db.commit()
    return {"removed": True}


@app.post("/conflicts")
def declare_conflict(data: ConflictIn, db: Session = Depends(get_db), user: User = Depends(require_role(Role.JUDGE))):
    event_id = None
    if data.projectId:
        project = db.get(Project, data.projectId)
        if not project:
            fail(404, "Project not found")
        event_id = project.event_id
    else:
        fail(422, "Project ID is required for a judging conflict")
    conflict = JudgeConflict(event_id=event_id, judge_id=user.id, project_id=data.projectId, reason=data.reason, blocking=True)
    db.add(conflict)
    audit(db, user, event_id, "CONFLICT_DECLARED", "judge_conflict", conflict.id, {"projectId": data.projectId, "reason": data.reason})
    db.commit()
    return {"id": conflict.id, "blocking": True}


@app.post("/events/{event_id}/conflicts")
def organizer_conflict(event_id: str, data: ConflictIn, db: Session = Depends(get_db), user: User = Depends(require_role(Role.ORGANIZER))):
    event = require_event_owner(db, event_id, user)
    if not data.projectId:
        fail(422, "Project ID is required")
    project = db.get(Project, data.projectId)
    if not project or project.event_id != event.id:
        fail(404, "Project not found")
    conflict = JudgeConflict(event_id=event.id, judge_id=user.id, project_id=project.id, reason=data.reason, blocking=True)
    db.add(conflict)
    audit(db, user, event.id, "CONFLICT_DECLARED", "judge_conflict", conflict.id, {"projectId": project.id, "reason": data.reason, "source": "organizer"})
    db.commit()
    return {"id": conflict.id, "blocking": True}


@app.post("/events/{event_id}/auto-assign")
def auto_assign(event_id: str, db: Session = Depends(get_db), user: User = Depends(require_role(Role.ORGANIZER))):
    event = require_event_owner(db, event_id, user)
    event_in_phase(event, EventStatus.JUDGING, "Judge assignment")
    judges = db.scalars(select(User).where(User.role == Role.JUDGE)).all()
    projects = db.scalars(select(Project).where(Project.event_id == event_id)).all()
    created = 0
    blocked = 0
    for project in projects:
        existing = {a.judge_id for a in db.scalars(select(JudgeAssignment).where(JudgeAssignment.project_id == project.id)).all()}
        while len(existing) < event.judges_per_project:
            candidates = []
            for judge in judges:
                if judge.id in existing:
                    continue
                reason = blocking_conflict(db, project, judge)
                if reason:
                    continue
                load = db.scalar(select(func.count()).select_from(JudgeAssignment).where(JudgeAssignment.judge_id == judge.id)) or 0
                candidates.append((load, judge.id, judge))
            if not candidates:
                blocked += 1
                break
            _, _, judge = min(candidates, key=lambda item: (item[0], item[1]))
            assignment = JudgeAssignment(project_id=project.id, judge_id=judge.id)
            db.add(assignment)
            db.flush()
            existing.add(judge.id)
            created += 1
            audit(db, user, event.id, "JUDGE_ASSIGNED", "assignment", assignment.id, {"judgeId": judge.id, "projectId": project.id, "mode": "automatic"})
    audit(db, user, event.id, "AUTO_ASSIGN_EXECUTED", "event", event.id, {"pairings": created, "unfilledProjects": blocked})
    db.commit()
    return {"created": created, "unfilledProjects": blocked}


@app.get("/events/{event_id}/judges")
def judges(event_id: str, db: Session = Depends(get_db), user: User = Depends(require_role(Role.ORGANIZER))):
    require_event_owner(db, event_id, user)
    output = []
    for judge in db.scalars(select(User).where(User.role == Role.JUDGE)).all():
        assignments = db.scalars(select(JudgeAssignment).join(Project).where(JudgeAssignment.judge_id == judge.id, Project.event_id == event_id)).all()
        completed = sum(1 for assignment in assignments if db.scalar(select(Review.id).where(Review.project_id == assignment.project_id, Review.judge_id == judge.id, Review.status.in_([ReviewStatus.FINALIZED, ReviewStatus.LOCKED]))))
        conflicts = db.scalars(select(JudgeConflict).where(JudgeConflict.event_id == event_id, JudgeConflict.judge_id == judge.id)).all()
        output.append({
            "id": judge.id,
            "name": judge.name,
            "email": judge.email,
            "affiliation": judge.affiliation or "",
            "title": judge.title or "",
            "track": judge.specialization or "",
            "assignedCount": len(assignments),
            "completedCount": completed,
            "conflicts": [{"projectId": c.project_id, "reason": c.reason} for c in conflicts if c.project_id],
            "scoringBias": 0,
        })
    return output


# ---------------------------- reviews ----------------------------

@app.post("/reviews")
def save_review(data: ReviewIn, db: Session = Depends(get_db), user: User = Depends(require_role(Role.JUDGE))):
    project = db.get(Project, data.projectId)
    if not project:
        fail(404, "Project not found")
    event = require_project_access(db, project, user, allow_organizer=False)
    event_in_phase(event, EventStatus.JUDGING, "Review")
    if blocking_conflict(db, project, user):
        fail(409, "Judge has a blocking conflict for this project")
    if data.status not in {ReviewStatus.DRAFT, ReviewStatus.FINALIZED, ReviewStatus.LOCKED}:
        fail(422, "Invalid review status")
    if event.judging_deadline and now() > event.judging_deadline:
        fail(409, "Judging deadline has passed")
    review = db.scalar(select(Review).where(Review.project_id == project.id, Review.judge_id == user.id))
    current = review.status if review else ReviewStatus.DRAFT
    if current == ReviewStatus.LOCKED:
        fail(409, "Locked reviews cannot be modified")
    if current == ReviewStatus.FINALIZED and data.status != ReviewStatus.LOCKED:
        fail(409, "Finalized reviews can only transition to locked")
    if current == ReviewStatus.DRAFT and data.status == ReviewStatus.LOCKED:
        fail(409, "A draft review must be finalized before it can be locked")
    finalized = data.status in {ReviewStatus.FINALIZED, ReviewStatus.LOCKED}
    total = validate_review_scores(event, data.scores, require_all=finalized)
    if finalized:
        rubric_ids = {str(c["id"]) for c in event.rubric}
        missing_justifications = [cid for cid in rubric_ids if not str(data.justifications.get(cid, "")).strip()]
        if missing_justifications:
            fail(422, f"Every finalized criterion requires justification: {', '.join(sorted(missing_justifications))}")
    if review is None:
        review = Review(project_id=project.id, judge_id=user.id)
        db.add(review)
        db.flush()
        action = "REVIEW_CREATED"
    else:
        action = "REVIEW_FINALIZED" if data.status == ReviewStatus.FINALIZED else "REVIEW_LOCKED" if data.status == ReviewStatus.LOCKED else "REVIEW_UPDATED"
    review.status = data.status
    review.total_raw = total
    review.justification = data.justification
    review.updated_at = now()
    existing_scores = {s.criterion_id: s for s in db.scalars(select(ReviewCriterionScore).where(ReviewCriterionScore.review_id == review.id)).all()}
    for criterion_id, score in data.scores.items():
        row = existing_scores.get(criterion_id)
        justification = data.justifications.get(criterion_id, "")
        if row:
            row.score = float(score)
            row.justification = justification
        else:
            db.add(ReviewCriterionScore(review_id=review.id, criterion_id=criterion_id, score=float(score), justification=justification))
    audit(db, user, event.id, action, "review", review.id, {"projectId": project.id, "status": data.status})
    db.commit()
    return {"id": review.id, "status": review.status, "totalRaw": review.total_raw}


@app.post("/reviews/reopen")
def reopen_review(data: ReopenIn, db: Session = Depends(get_db), user: User = Depends(require_role(Role.ORGANIZER))):
    project = db.get(Project, data.projectId)
    if not project:
        fail(404, "Project not found")
    event = require_event_owner(db, project.event_id, user)
    review = db.scalar(select(Review).where(Review.project_id == project.id, Review.judge_id == data.judgeId))
    if not review:
        fail(404, "Review not found")
    if review.status == ReviewStatus.DRAFT:
        fail(409, "Review is already a draft")
    review.status = ReviewStatus.DRAFT
    review.updated_at = now()
    audit(db, user, event.id, "REVIEW_REOPENED_BY_ORGANIZER", "review", review.id, {"reason": data.reason})
    db.commit()
    return {"status": ReviewStatus.DRAFT}


@app.get("/me/reviews")
def my_reviews(db: Session = Depends(get_db), user: User = Depends(require_role(Role.JUDGE))):
    reviews = db.scalars(select(Review).where(Review.judge_id == user.id).order_by(Review.updated_at.desc())).all()
    return [{"id": r.id, "projectId": r.project_id, "status": r.status, "totalRaw": r.total_raw} for r in reviews]


# ---------------------------- results ----------------------------

@app.post("/events/{event_id}/results/calculate")
def calculate_results(event_id: str, data: ResultCalculateIn | None = None, db: Session = Depends(get_db), user: User = Depends(require_role(Role.ORGANIZER))):
    event = require_event_owner(db, event_id, user)
    if event.status not in {EventStatus.JUDGING, EventStatus.RESULTS}:
        fail(409, "Results can only be calculated during or after judging")
    request = data or ResultCalculateIn()
    projects = db.scalars(select(Project).where(Project.event_id == event_id)).all()
    if not projects:
        fail(409, "No projects available for result calculation")

    completed: dict[str, list[Review]] = {}
    incomplete: list[dict] = []
    for project in projects:
        assignments = db.scalars(select(JudgeAssignment).where(JudgeAssignment.project_id == project.id)).all()
        reviews = db.scalars(select(Review).where(Review.project_id == project.id, Review.status.in_([ReviewStatus.FINALIZED, ReviewStatus.LOCKED]))).all()
        assigned_ids = {a.judge_id for a in assignments}
        reviewed_ids = {r.judge_id for r in reviews}
        missing_assignments = max(event.judges_per_project - len(assignments), 0)
        missing_reviews = len(assigned_ids - reviewed_ids)
        if missing_assignments or missing_reviews or len(reviews) < event.judges_per_project:
            incomplete.append({"projectId": project.id, "missingAssignments": missing_assignments, "missingReviews": missing_reviews, "completedReviews": len(reviews)})
        if reviews:
            completed[project.id] = reviews

    if incomplete and not request.override:
        fail(409, f"Judging incomplete: {incomplete}")
    if incomplete and request.override and not request.reason:
        fail(422, "An organizer override requires an explicit reason")
    if not completed:
        fail(409, "No completed reviews available")

    normalized, statistics = calculate_normalized(event, completed, db)
    tie_order = event.tie_break_order or ["normalized_score", "raw_score", "code_name"]
    project_codes = {p.id: p.code_name for p in projects}
    def tie_key(item):
        project_id, values = item
        keys = []
        for field in tie_order:
            if field == "normalized_score": keys.append(-values["normalized"])
            elif field == "raw_score": keys.append(-values["raw"])
            elif field == "code_name": keys.append(project_codes[project_id])
        return tuple(keys)
    ordered = sorted(normalized.items(), key=tie_key)

    snapshot = NormalizationSnapshot(event_id=event.id, method=event.normalization_method, statistics=statistics, results=[])
    db.add(snapshot)
    db.flush()

    result_rows = []
    for rank, (project_id, values) in enumerate(ordered, 1):
        row = {
            "projectId": project_id,
            "rawScore": values["raw"],
            "normalizedScore": values["normalized"],
            "finalScore": values["normalized"],
            "rank": rank,
        }
        result_rows.append(row)
        db.add(Result(event_id=event.id, project_id=project_id, raw_score=values["raw"], normalized_score=values["normalized"], final_score=values["normalized"], rank=rank, snapshot_id=snapshot.id, published=False))
    snapshot.results = result_rows
    audit(db, user, event.id, "RESULTS_CALCULATED", "normalization_snapshot", snapshot.id, {"override": request.override, "reason": request.reason, "method": event.normalization_method, "tieBreakOrder": tie_order})
    db.commit()
    return {"snapshotId": snapshot.id, "results": result_rows, "incomplete": incomplete, "statistics": statistics}


@app.post("/events/{event_id}/results/publish")
def publish_results(event_id: str, db: Session = Depends(get_db), user: User = Depends(require_role(Role.ORGANIZER))):
    event = require_event_owner(db, event_id, user)
    if event.status not in {EventStatus.JUDGING, EventStatus.RESULTS}:
        fail(409, "Results cannot be published in the current event phase")
    latest_snapshot = db.scalar(select(NormalizationSnapshot).where(NormalizationSnapshot.event_id == event.id).order_by(NormalizationSnapshot.created_at.desc()))
    if not latest_snapshot:
        fail(409, "Calculate results before publishing")
    rows = db.scalars(select(Result).where(Result.snapshot_id == latest_snapshot.id)).all()
    if not rows:
        fail(409, "No result rows available")
    db.query(Result).filter(Result.event_id == event.id).update({Result.published: False}, synchronize_session=False)
    for row in rows:
        row.published = True
    event.status = EventStatus.RESULTS
    audit(db, user, event.id, "RESULTS_PUBLISHED", "normalization_snapshot", latest_snapshot.id, {"snapshotId": latest_snapshot.id})
    db.commit()
    return {"published": True, "snapshotId": latest_snapshot.id}


@app.get("/events/{event_id}/results")
def get_results(event_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    event = get_event_or_404(db, event_id)
    if user.role == Role.ORGANIZER and event.organizer_id != user.id:
        fail(403, "Permission denied")
    if user.role == Role.PARTICIPANT:
        team = participant_team(db, event.id, user.id)
        if not team:
            return []
    rows = db.scalars(select(Result).where(Result.event_id == event.id, Result.published.is_(True)).order_by(Result.rank)).all()
    output = []
    for row in rows:
        if user.role == Role.PARTICIPANT and db.get(Project, row.project_id).team_id != participant_team(db, event.id, user.id).id:
            continue
        output.append({"projectId": row.project_id, "rawScore": row.raw_score, "normalizedScore": row.normalized_score, "finalScore": row.final_score, "rank": row.rank, "snapshotId": row.snapshot_id})
    return output


# ---------------------------- organizer/admin data ----------------------------

@app.get("/events/{event_id}/audit")
def audit_list(event_id: str, db: Session = Depends(get_db), user: User = Depends(require_role(Role.ORGANIZER))):
    require_event_owner(db, event_id, user)
    return audit_action_rows(db, event_id)


@app.get("/events/{event_id}/integrity")
def integrity_pulse(event_id: str, db: Session = Depends(get_db), user: User = Depends(require_role(Role.ORGANIZER))):
    event = require_event_owner(db, event_id, user)
    projects = db.scalars(select(Project).where(Project.event_id == event.id)).all()
    blocked = db.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.event_id == event.id, AuditLog.action == "JUDGE_ASSIGNMENT_BLOCKED")) or 0
    conflicts = db.scalar(select(func.count()).select_from(JudgeConflict).where(JudgeConflict.event_id == event.id, JudgeConflict.blocking.is_(True))) or 0
    incomplete = []
    for project in projects:
        count = db.scalar(select(func.count()).select_from(Review).where(Review.project_id == project.id, Review.status.in_([ReviewStatus.FINALIZED, ReviewStatus.LOCKED]))) or 0
        assignments = db.scalar(select(func.count()).select_from(JudgeAssignment).where(JudgeAssignment.project_id == project.id)) or 0
        if assignments < event.judges_per_project or count < event.judges_per_project:
            incomplete.append(project.id)
    return {"incompleteProjects": incomplete, "blockedAssignments": blocked, "blockingConflicts": conflicts}


@app.get("/events/{event_id}/judgelens")
def judge_lens(event_id: str, db: Session = Depends(get_db), user: User = Depends(require_role(Role.ORGANIZER))):
    event = require_event_owner(db, event_id, user)
    reviews = db.scalars(select(Review).join(Project).where(Project.event_id == event.id)).all()
    by_judge: dict[str, list[float]] = {}
    for review in reviews:
        by_judge.setdefault(review.judge_id, []).append(review.total_raw)
    return {
        "reviewCount": len(reviews),
        "completedCount": sum(r.status in {ReviewStatus.FINALIZED, ReviewStatus.LOCKED} for r in reviews),
        "judgeVariation": {judge_id: {"mean": mean(values), "std": pstdev(values) if len(values) > 1 else 0, "count": len(values)} for judge_id, values in by_judge.items()},
        "criterionScores": [],
        "reviewTiming": [{"reviewId": r.id, "updatedAt": r.updated_at} for r in reviews],
    }


# ---------------------------- proof, exports, certificates, analytics ----------------------------

@app.get("/events/{event_id}/normalization-proof/{snapshot_id}")
def normalization_proof(event_id: str, snapshot_id: str, db: Session = Depends(get_db), user: User = Depends(require_role(Role.ORGANIZER))):
    event = require_event_owner(db, event_id, user)
    snapshot = db.get(NormalizationSnapshot, snapshot_id)
    if not snapshot or snapshot.event_id != event.id:
        fail(404, "Normalization snapshot not found")
    return {"snapshotId": snapshot.id, "eventId": event.id, "method": snapshot.method, "createdAt": snapshot.created_at, "statistics": snapshot.statistics, "results": snapshot.results, "formula": "z=(judge_score-judge_mean)/judge_std; zero contribution when judge std is zero" if snapshot.method == "z_score" else "See method-specific snapshot metadata"}

@app.get("/events/{event_id}/export")
def export_event(event_id: str, format: str = "json", db: Session = Depends(get_db), user: User = Depends(require_role(Role.ORGANIZER))):
    import csv, io
    event = require_event_owner(db, event_id, user)
    projects = db.scalars(select(Project).where(Project.event_id == event.id)).all()
    rows = []
    for project in projects:
        latest = db.scalar(select(Result).where(Result.project_id == project.id, Result.published.is_(True)).order_by(Result.created_at.desc()))
        rows.append({"projectId": project.id, "codeName": project.code_name, "title": project.title, "rawScore": latest.raw_score if latest else None, "normalizedScore": latest.normalized_score if latest else None, "rank": latest.rank if latest else None})
    if format.lower() == "csv":
        out=io.StringIO(); writer=csv.DictWriter(out, fieldnames=list(rows[0].keys()) if rows else ["projectId","codeName","title","rawScore","normalizedScore","rank"]); writer.writeheader(); writer.writerows(rows)
        return Response(out.getvalue(), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename={event.event_code}-results.csv"})
    if format.lower() != "json": fail(422, "Export format must be json or csv")
    return {"event": event_data(event, db), "results": rows, "audit": audit_action_rows(db, event.id)}

@app.get("/events/{event_id}/analytics")
def analytics(event_id: str, db: Session = Depends(get_db), user: User = Depends(require_role(Role.ORGANIZER))):
    event = require_event_owner(db, event_id, user)
    projects = db.scalars(select(Project).where(Project.event_id == event.id)).all()
    assignments = db.scalars(select(JudgeAssignment).join(Project).where(Project.event_id == event.id)).all()
    reviews = db.scalars(select(Review).join(Project).where(Project.event_id == event.id)).all()
    completed = sum(r.status in {ReviewStatus.FINALIZED, ReviewStatus.LOCKED} for r in reviews)
    return {"participants": event_data(event, db)["participantsCount"], "projects": len(projects), "assignments": len(assignments), "reviews": len(reviews), "completedReviews": completed, "completionRate": round(completed / max(len(assignments), 1) * 100, 2), "published": bool(db.scalar(select(Result.id).where(Result.event_id == event.id, Result.published.is_(True))))}

@app.post("/events/{event_id}/reminders")
def create_reminder(event_id: str, message: str, db: Session = Depends(get_db), user: User = Depends(require_role(Role.ORGANIZER))):
    event = require_event_owner(db, event_id, user)
    memberships = db.scalars(select(Membership).where(Membership.event_id == event.id, Membership.status == "approved")).all()
    judges = db.scalars(select(JudgeAssignment.judge_id).join(Project).where(Project.event_id == event.id).distinct()).all()
    user_ids = {m.user_id for m in memberships} | set(judges)
    for uid in user_ids: db.add(Notification(user_id=uid, event_id=event.id, message=message.strip()))
    audit(db, user, event.id, "REMINDER_SENT", "event", event.id, {"recipientCount": len(user_ids)})
    db.commit()
    return {"sent": len(user_ids)}

@app.get("/me/notifications")
def my_notifications(db: Session = Depends(get_db), user: User = Depends(current_user)):
    rows = db.scalars(select(Notification).where(Notification.user_id == user.id).order_by(Notification.created_at.desc())).all()
    return [{"id": n.id, "eventId": n.event_id, "message": n.message, "read": n.read, "createdAt": n.created_at} for n in rows]

@app.get("/events/{event_id}/certificates")
def certificates(event_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    event = get_event_or_404(db, event_id)
    if event.status != EventStatus.ARCHIVED:
        fail(409, "Certificates are available after archive")
    if user.role == Role.ORGANIZER and event.organizer_id != user.id:
        fail(403, "Permission denied")
    rows = db.scalars(select(Result).where(Result.event_id == event.id, Result.published.is_(True)).order_by(Result.rank)).all()
    output=[]
    for row in rows:
        project=db.get(Project,row.project_id); team=db.get(Team,project.team_id) if project else None
        if user.role == Role.PARTICIPANT and (not team or not db.scalar(select(TeamMember).where(TeamMember.team_id == team.id, TeamMember.user_id == user.id))):
            continue
        for member in team_members(db, team.id) if team else []:
            person=db.get(User,member.user_id)
            output.append({"certificateId": f"{event.event_code}-{row.rank}-{person.id[:8].upper()}", "recipient": person.name if person else "", "project": project.title if project else "", "rank": row.rank, "event": event.title})
    return output

# ---------------------------- participant convenience ----------------------------

@app.get("/me/teams")
def my_teams(db: Session = Depends(get_db), user: User = Depends(current_user)):
    teams = db.scalars(select(Team).join(TeamMember).where(TeamMember.user_id == user.id)).all()
    return [team_data(db, team) for team in teams]


@app.get("/me/projects")
def my_projects(db: Session = Depends(get_db), user: User = Depends(current_user)):
    projects = db.scalars(select(Project).join(Team, Team.id == Project.team_id).join(TeamMember, TeamMember.team_id == Team.id).where(TeamMember.user_id == user.id)).all()
    return [project_data(db, project, user, False) for project in projects]


# ---------------------------- lifecycle / archive ----------------------------

@app.post("/events/{event_id}/archive")
def archive_event(event_id: str, db: Session = Depends(get_db), user: User = Depends(require_role(Role.ORGANIZER))):
    event = require_event_owner(db, event_id, user)
    if event.status != EventStatus.RESULTS:
        fail(409, "Only events with published results can be archived")
    event.status = EventStatus.ARCHIVED
    audit(db, user, event.id, "EVENT_ARCHIVED", "event", event.id, {})
    db.commit()
    return {"archived": True, "status": event.status}


# Canonical API namespace aliases. Legacy paths remain available for compatibility.
_existing_api_routes = list(app.routes)
for _route in _existing_api_routes:
    if not isinstance(_route, APIRoute) or _route.path.startswith("/api/") or _route.path in {"/docs", "/redoc", "/openapi.json"}:
        continue
    _route.include_in_schema = False
    app.add_api_route(
        "/api" + _route.path, _route.endpoint, methods=list(_route.methods or []),
        response_model=_route.response_model, status_code=_route.status_code,
        dependencies=_route.dependencies, response_class=_route.response_class,
        response_model_include=_route.response_model_include, response_model_exclude=_route.response_model_exclude,
        response_model_by_alias=_route.response_model_by_alias, response_model_exclude_unset=_route.response_model_exclude_unset,
        response_model_exclude_defaults=_route.response_model_exclude_defaults, response_model_exclude_none=_route.response_model_exclude_none,
        include_in_schema=True, name=_route.name + "_api"
    )
