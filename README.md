# AGAMOTTO

### Hackathon Management & Verifiable Judging Platform

AGAMOTTO is a self-hostable hackathon management platform focused on fair, blind, conflict-aware, auditable judging.

Roles:
- Organizer
- Judge
- Participant

Lifecycle:

**Registration → Teams → Eligibility → Submission → Judge Assignment → Judging → Scoring → Normalization → Results → Certificates → Archiving**

---

## 1. Core Product

The central system is the **judging engine**.

It must ensure:

- eligible judge assignment
- conflict detection before assignment
- blind judging
- judges cannot see other judges' active scores
- controlled review lifecycle
- incomplete judging can block result publication
- score normalization
- stable published result snapshots
- audit logging of important mutations

The application must use real backend data and real workflow enforcement.

---

## 2. Roles

### Organizer

Can:

- create/configure events
- configure registration and team rules
- manage participants and teams
- manage submissions
- configure judging
- assign judges
- manage conflicts
- monitor judging
- calculate and publish results
- manage certificates
- archive events
- inspect audit activity

### Judge

Can:

- view assigned projects
- view blind project information
- view rubric
- enter criterion scores
- provide justification
- save drafts
- finalize reviews
- lock finalized reviews where permitted
- view own judging progress

Must not:

- see participant identity during blind judging
- see other judges' active scores
- judge a conflicted project
- communicate with participants through the judging system

### Participant

Can:

- register for events
- create/join teams
- manage team membership according to event rules
- submit projects
- edit submissions according to event policy
- view submission status
- view published results

---

## 3. Event Management

Events support:

- title
- tagline
- description
- unique event code
- access code
- public/private visibility
- registration mode
- registration start/deadline
- submission deadline
- judging deadline
- participant capacity
- minimum/maximum team size
- judges per project
- tracks
- prizes
- rubric
- normalization method
- editing policy
- submission versioning

Duplicate event codes must return **HTTP 409 Conflict**, not an accidental HTTP 500.

---

## 4. Registration

Support:

- public/private events
- event/access codes
- open registration
- approval-required registration
- registration start/deadline
- participant capacity

Backend must enforce registration lifecycle and reject closed or not-yet-open registration.

---

## 5. Teams

Teams belong to an event.

The system must enforce configured minimum and maximum team sizes and any one-team-per-event rule.

Participants can create/join teams and manage membership according to event rules.

---

## 6. Project Submission

Each team submits one project.

Supported project information may include:

- project name
- problem statement
- solution
- technology stack
- GitHub repository
- demo URL
- presentation
- team information

Submission editing follows event policy.

If versioning is enabled, meaningful updates preserve version information.

Never display a successful submission state when the backend operation failed.

---

## 7. Judge Assignment

Judges can be assigned manually or automatically.

Automatic assignment should consider:

- judges required per project
- workload balancing
- conflicts
- eligibility

Invalid assignments must be blocked by the backend.

---

## 8. Conflict Management

A judge must not be assigned to a project when a blocking conflict exists.

Blocking conditions include:

- judge is a project team member
- judge submitted the project
- declared judge conflict
- organizer-recorded conflict

Conflict enforcement must happen on the backend, not only in the UI.

Invalid assignment attempts should return a controlled conflict response.

---

## 9. Blind Judging

Blind judging is a core feature.

When enabled, the backend must prevent participant-identifying information from reaching judges.

A blind project response may expose:

- project code
- project title
- problem
- solution
- technology stack
- demo
- repository
- rubric

It must not expose:

- participant names
- team member identities
- private organizer information
- other judges' scores

Blindness must be enforced at the API/data layer, not merely by hiding UI fields.

---

## 10. Review Lifecycle

Reviews follow:

**DRAFT → FINALIZED → LOCKED**

### DRAFT
Judge can edit.

### FINALIZED
Judge has submitted the evaluation.

### LOCKED
Normal judging operations cannot modify the review.

The backend must enforce these transitions.

---

## 11. Judging

A review contains:

- criterion scores
- justification
- review status
- timestamps
- judge/project relationship

Judges must not see other judges' active scores.

Unauthorized score modification must be blocked.

---

## 12. Rubric

Every event requires at least one rubric criterion.

Each criterion requires:

- `id`
- `weight`
- `maxScore`

Example:

```json
[
  {
    "id": "innovation",
    "name": "Innovation",
    "weight": 30,
    "maxScore": 10
  },
  {
    "id": "technical",
    "name": "Technical Implementation",
    "weight": 30,
    "maxScore": 10
  },
  {
    "id": "impact",
    "name": "Impact",
    "weight": 25,
    "maxScore": 10
  },
  {
    "id": "presentation",
    "name": "Presentation",
    "weight": 15,
    "maxScore": 10
  }
]
```

Rules:

- criterion IDs must be unique
- weights must be positive
- maximum scores must be positive
- weights must total exactly 100%

---

## 13. Judging Completion

Results should normally be blocked when required judging is incomplete.

Detect:

- missing reviews
- incomplete reviews
- unfinalized reviews
- missing assignments

Any organizer override must require an explicit reason and be auditable.

---

## 14. Normalization

AGAMOTTO supports score normalization.

Primary method:

**Judge-level Z-score normalization**

Preserve:

- raw scores
- normalized scores
- judge-level statistics
- normalization method
- result calculation information

Normalization must only run when sufficient data exists.

If insufficient data prevents the configured method, use the defined fallback rather than silently producing misleading results.

---

## 15. Results

Pipeline:

**Raw Reviews → Score Calculation → Normalization → Final Ranking → Result Snapshot → Publication**

Results may contain:

- project
- raw score
- normalized score
- final score
- rank

Published results must be stable snapshots and must not silently change because of later mutations.

---

## 16. JudgeLens

JudgeLens is deterministic judging analysis.

It may show:

- score distributions
- criterion-level scores
- judge-level variation
- missing/incomplete reviews
- review timing
- judging progress

It must not invent interpretations or accuse judges of bias, cheating, dishonesty, or suspicious behavior based only on numerical patterns.

---

## 17. Integrity Pulse

Integrity Pulse provides deterministic operational integrity signals such as:

- incomplete judging
- blocked assignments
- conflict records
- unusual workflow states
- missing required actions

It is **not an AI cheating detector**.

Do not accuse participants or judges of misconduct without actual evidence and appropriate human review.

---

## 18. Audit Log

Important mutations should be recorded, including where applicable:

- `EVENT_CREATED`
- `EVENT_UPDATED`
- `PARTICIPANT_REGISTERED`
- `PARTICIPANT_REGISTERED_BY_CODE`
- `MEMBERSHIP_APPROVED`
- `TEAM_CREATED`
- `TEAM_UPDATED`
- `PROJECT_CREATED`
- `PROJECT_UPDATED`
- `JUDGE_ASSIGNED`
- `JUDGE_ASSIGNMENT_BLOCKED`
- `CONFLICT_DECLARED`
- `REVIEW_CREATED`
- `REVIEW_FINALIZED`
- `REVIEW_LOCKED`
- `RESULTS_CALCULATED`
- `RESULTS_PUBLISHED`

Audit records should identify relevant actor, event, entity, action, timestamp, and details.

Do not claim blockchain or cryptographic hash-chain verification unless it is actually implemented.

---

## 19. Authentication & Authorization

Roles:

- `ORGANIZER`
- `JUDGE`
- `PARTICIPANT`

Backend authorization is mandatory.

Every sensitive endpoint must verify:

1. authentication
2. role
3. event ownership/membership
4. required permission

Frontend route protection alone is insufficient.

---

## 20. Frontend

Visual direction:

- monochrome foundation
- muted red accent
- sharp rectangular components
- clean technical interface
- strong typography
- dense information hierarchy
- minimal decorative elements

Avoid:

- excessive gradients
- glassmorphism
- excessive rounded cards
- meaningless animations
- fake verification indicators
- decorative UI that hides functionality

The interface should feel like a serious competition-management system.

---

## 21. Backend

Expected architecture:

```text
FastAPI
   ↓
SQLAlchemy
   ↓
PostgreSQL
```

Responsibilities:

- authentication
- authorization
- event management
- registration
- teams
- projects
- judge assignment
- conflicts
- judging
- normalization
- results
- audit logging
- notifications where implemented
- API serialization

Business rules must primarily live on the backend.

---

## 22. Database

PostgreSQL is the primary database.

Core entities:

- `users`
- `events`
- `memberships`
- `teams`
- `team_members`
- `projects`
- `judge_assignments`
- `judge_conflicts`
- `reviews`
- `review_criterion_scores`
- `results`
- `normalization_snapshots`
- `audit_logs`
- `notifications`

Schema changes must use Alembic migrations.

---

## 23. API Rules

Frontend and backend must use real API data.

Do not create fake frontend success states.

Expected status handling:

- `400 / 422` — invalid request
- `401` — authentication failure
- `403` — permission denied
- `404` — resource not found
- `409` — conflict / invalid workflow state
- `500` — unexpected server error

Known business conflicts must return controlled errors rather than accidental 500 responses.

---

## 24. Demo Accounts

Local development accounts:

```text
Organizer
Email: director@agamotto.systems
Password: LocalDemo123!

Judge
Email: aris.thorne@vertex-systems.io
Password: LocalDemo123!

Participant
Email: kiran@stanford.edu
Password: LocalDemo123!
```

These are development/demo credentials only.

---

## 25. Local Development

### Backend

```bash
cd backend
./.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Frontend

```bash
npm run dev
```

### PostgreSQL

```bash
docker compose up -d postgres
```

### Full stack

```bash
docker compose up -d --build
```

---

## 26. Validation

### Frontend

Verify:

- build passes
- lint passes where configured
- main routes load
- no blank-screen failures
- no fake success states

### Backend

Verify:

- application starts
- authentication works
- API imports successfully
- tests pass
- migrations apply

### End-to-end lifecycle

Verify:

**Organizer login → Create event → Participant registration → Team creation → Project submission → Judge assignment → Conflict rejection → Blind project access → Judge review → Finalize review → Lock review → Calculate results → Normalize scores → Publish results → Participant views result**

---

## 27. Engineering Rules

### DO

- inspect existing architecture before changing it
- reuse working services/models/components
- keep frontend/backend contracts synchronized
- enforce security server-side
- preserve working functionality
- use migrations for schema changes
- validate important workflows
- return controlled errors
- remove dead/broken functionality
- keep the implementation truthful

### DO NOT

- rewrite the application unnecessarily
- create duplicate implementations
- replace real APIs with mock data
- hard-code fake judging results
- fake blockchain
- fake cryptographic verification
- claim SHA-256 integrity when not implemented
- claim AI judging
- claim AI cheating detection
- expose participant identities during blind judging
- expose other judges' active scores
- bypass backend authorization
- silently swallow database errors
- introduce unsupported functionality

---

## 28. Product USP

> **A self-hostable, offline-first hackathon platform with a verifiable judging engine — from conflict-free blind assignment to normalized, auditable results.**

The differentiation is the **judging engine**, not generic event registration.

---

## 29. Definition of Done

AGAMOTTO is complete when:

- all three roles work
- authentication works
- organizers can create/configure events
- participants can register
- teams work
- projects can be submitted
- judges can be assigned
- conflicts prevent invalid assignments
- blind judging is enforced server-side
- judges cannot see each other's active scores
- reviews follow DRAFT → FINALIZED → LOCKED
- incomplete judging is handled correctly
- normalization works
- results can be published
- published results are stable snapshots
- important actions are audited
- frontend/backend use real data
- no fake functionality remains
- complete lifecycle works end-to-end
- frontend builds successfully
- backend starts successfully
- migrations work
- Docker configuration works

---

## 30. Development Principle

**Build what the system can prove.**

If a feature is not actually implemented, the UI must not claim that it is.

Priority:

**Correctness > Security > Workflow integrity > Auditability > Usability > Visual polish**

The goal is a working judging platform, not a simulated demo.


## Final hardening notes

- Canonical API namespace: `/api/...` (legacy paths remain compatible for existing integrations).
- Access tokens are short-lived and held in memory; refresh tokens are HTTP-only cookies.
- Event lifecycle transitions are enforced server-side.
- Judge assignment, conflicts, blind review, review locking/reopening, incomplete-result blocking, deterministic tie-breaks, normalization snapshots and proof are server-side.
- CSV/JSON result export, analytics, notifications/reminders and certificate metadata endpoints are included.

### Local full-stack start

```bash
docker compose up --build
```

The API container runs Alembic migrations and seeds the demo accounts before starting FastAPI.
