from datetime import datetime, timedelta, timezone
from sqlalchemy import select

from .database import SessionLocal
from .models import (
    Event, EventStatus, JudgeAssignment, Membership, Project, ProjectVersion,
    Review, ReviewCriterionScore, Role, Team, TeamMember, User,
)
from .security import hash_password

DEMO_ACCOUNTS = (
    ("kiran@stanford.edu", "Kiran Patel", Role.PARTICIPANT),
    ("maya@stanford.edu", "Maya Chen", Role.PARTICIPANT),
    ("noah@stanford.edu", "Noah Williams", Role.PARTICIPANT),
    ("aria@stanford.edu", "Aria Singh", Role.PARTICIPANT),
    ("aris.thorne@vertex-systems.io", "Aris Thorne", Role.JUDGE),
    ("priya.nair@northstar.dev", "Priya Nair", Role.JUDGE),
    ("marcus.lee@forge.ai", "Marcus Lee", Role.JUDGE),
    ("director@agamotto.systems", "Competition Organizer", Role.ORGANIZER),
)
DEMO_PASSWORD = "LocalDemo123!"


def get_or_create_user(db, email, name, role):
    user = db.scalar(select(User).where(User.email == email))
    if user:
        return user
    user = User(
        email=email, name=name, role=role, password_hash=hash_password(DEMO_PASSWORD),
        college="Stanford University" if role == Role.PARTICIPANT else None,
        affiliation="Vertex Systems" if email.startswith("aris") else ("Northstar Dev" if email.startswith("priya") else ("Forge AI" if email.startswith("marcus") else None)),
        title="Principal Architect" if role == Role.JUDGE else None,
    )
    db.add(user); db.flush(); return user


def main() -> None:
    db = SessionLocal()
    try:
        users = {email: get_or_create_user(db, email, name, role) for email, name, role in DEMO_ACCOUNTS}
        db.commit()

        organizer = users["director@agamotto.systems"]
        event = db.scalar(select(Event).where(Event.event_code == "AGAMOTTO-DEMO"))
        if event:
            print("Demo accounts/event already seeded")
            return

        now = datetime.now(timezone.utc)
        event = Event(
            organizer_id=organizer.id,
            title="AGAMOTTO Demo Championship",
            tagline="Blind, conflict-aware, auditable judging",
            description="Full local demo fixture for the AGAMOTTO judging engine.",
            event_code="AGAMOTTO-DEMO",
            status=EventStatus.JUDGING,
            is_public=True,
            registration_mode="open",
            editing_policy="allow-until-deadline",
            versioning_enabled=True,
            min_team_size=1,
            max_team_size=4,
            judges_per_project=2,
            registration_start=now - timedelta(days=2),
            registration_deadline=now - timedelta(days=1),
            submission_deadline=now - timedelta(hours=12),
            judging_deadline=now + timedelta(days=1),
            tracks=["General", "AI"],
            prizes="Demo awards",
            rubric=[
                {"id":"innovation","name":"Innovation","description":"Originality and value","weight":60,"maxScore":10},
                {"id":"technical","name":"Technical","description":"Implementation quality","weight":40,"maxScore":10},
            ],
            normalization_method="z_score",
            tie_break_order=["normalized_score", "raw_score", "code_name"],
        )
        db.add(event); db.flush()

        participants = [users["kiran@stanford.edu"], users["maya@stanford.edu"], users["noah@stanford.edu"], users["aria@stanford.edu"]]
        for person in participants:
            db.add(Membership(event_id=event.id, user_id=person.id, status="approved"))
        db.flush()

        teams=[]
        projects=[]
        for idx, person in enumerate(participants[:2], 1):
            team=Team(event_id=event.id, name=f"Demo Team {idx}", track="AI", invite_code=f"DEMO-{idx}")
            db.add(team); db.flush(); db.add(TeamMember(team_id=team.id,user_id=person.id,is_leader=True,role="Team Lead"))
            project=Project(event_id=event.id,team_id=team.id,code_name=f"DEMO-{idx}",title=f"Demo Project {idx}",tagline="Fixture project",problem="A measurable problem",solution="A working solution",tech_stack=["Python","AI"],github_url="https://example.invalid/repo",demo_url="https://example.invalid/demo",track="AI")
            db.add(project); db.flush(); db.add(ProjectVersion(project_id=project.id,version=1,edited_by=person.id,summary="Initial demo submission",snapshot={"title":project.title}))
            teams.append(team); projects.append(project)

        judges=[users["aris.thorne@vertex-systems.io"],users["priya.nair@northstar.dev"],users["marcus.lee@forge.ai"]]
        for project in projects:
            for judge in judges[:2]:
                assignment=JudgeAssignment(project_id=project.id,judge_id=judge.id)
                db.add(assignment); db.flush()
                scores = {"innovation": 9 if project is projects[0] else 8, "technical": 8 if judge is judges[0] else 7}
                total=(scores["innovation"]/10)*60+(scores["technical"]/10)*40
                review=Review(project_id=project.id,judge_id=judge.id,status="finalized",justification="Fixture review with criterion evidence.",total_raw=total)
                db.add(review); db.flush()
                for cid,score in scores.items():
                    db.add(ReviewCriterionScore(review_id=review.id,criterion_id=cid,score=score,justification=f"Evidence recorded for {cid}."))

        db.commit()
        print("Seeded AGAMOTTO demo fixture")
    finally:
        db.close()

if __name__ == "__main__":
    main()
