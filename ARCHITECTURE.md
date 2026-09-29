# AGAMOTTO Architecture

## 1. Purpose

AGAMOTTO is a self-hostable hackathon platform whose differentiating subsystem is its judging engine.

The architecture is deliberately centered on server-side workflow enforcement:

```text
registration
   ↓
teams
   ↓
submission
   ↓
judge assignment
   ↓
conflict check
   ↓
blind judging
   ↓
structured review
   ↓
normalization
   ↓
result snapshot
   ↓
publication
   ↓
archive
```

The supplied implementation is a three-service Docker Compose application:

```text
┌──────────────────────────┐
│ web                      │
│ Next.js / React /        │
│ Tailwind                 │
│ :3000                    │
└────────────┬─────────────┘
             │ HTTP/JSON
             ▼
┌──────────────────────────┐
│ api                      │
│ FastAPI                  │
│ SQLAlchemy 2.x           │
│ JWT authentication       │
│ :8000                    │
└────────────┬─────────────┘
             │ SQL
             ▼
┌──────────────────────────┐
│ postgres                 │
│ PostgreSQL 17            │
│ :5432                    │
└──────────────────────────┘
```

## 2. Deployment model

The supplied `docker-compose.yml` defines:

- `postgres`: PostgreSQL 17 Alpine with a persistent Docker volume
- `api`: FastAPI application
- `frontend`: Next.js production application

The API waits for PostgreSQL health, then runs:

```bash
alembic upgrade head
python -m app.seed_demo_accounts
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

This makes a local seeded environment possible without a cloud database or external authentication service.

The frontend receives the API base URL through `NEXT_PUBLIC_API_URL`, defaulting to:

```text
http://localhost:8000/api
```

## 3. Backend layering

The implementation keeps business rules in the FastAPI layer and persistence in SQLAlchemy/PostgreSQL.

Conceptually:

```text
HTTP Router
   │
   ├── authentication / role checks
   ├── request validation
   ├── event ownership / membership checks
   │
   ▼
Domain workflow functions
   │
   ├── assignment
   ├── conflict
   ├── review
   ├── scoring
   ├── normalization
   ├── results
   ├── audit
   └── lifecycle
   │
   ▼
SQLAlchemy models / transactions
   │
   ▼
PostgreSQL
```

Routes are intentionally thin around the main workflow decisions. The implementation uses helper functions for access control, phase checks, conflict detection, score validation, normalization, serialization, and auditing.

## 4. Frontend

The frontend uses:

- Next.js
- React
- TypeScript
- Tailwind CSS
- Lucide icons

The frontend communicates with the API through a small API client. It sends a bearer access token when available and includes credentials for the refresh-cookie flow.

The UI is role-oriented:

```text
Organizer
 ├── events
 ├── participants
 ├── teams
 ├── projects
 ├── judges
 ├── rubric/settings
 ├── judging progress
 ├── results
 ├── JudgeLens
 ├── Integrity Pulse
 └── audit trail

Judge
 ├── assigned projects
 ├── blind project view
 ├── rubric
 └── review lifecycle

Participant
 ├── events
 ├── teams
 ├── project submission
 └── published results
```

The backend remains authoritative; frontend visibility is not treated as a security boundary.

## 5. Authentication flow

The authentication sequence is:

```text
Login
  │
  ├── verify password
  │
  ├── issue short-lived access token
  │
  └── issue refresh token as HTTP-only cookie
        │
        ▼
     Refresh
        │
        ├── validate refresh token
        └── issue new access + refresh tokens
```

The frontend keeps the access token in memory. The refresh token is stored by the browser as an HTTP-only cookie.

Logout deletes the refresh cookie.

Password storage uses a salted PBKDF2-HMAC-SHA256 derivation in the supplied backend.

## 6. Authorization

Every sensitive operation is checked server-side.

The main checks are:

1. Is the request authenticated?
2. Does the user have the required role?
3. Does the user own or belong to the relevant event?
4. Does the workflow permit the requested operation?
5. Does the user have access to the specific project/review/resource?

Examples:

- Organizer-only event configuration checks event ownership.
- Judges can access only projects assigned to them.
- Participants can access their own team's project.
- Judges cannot edit submissions.
- Locked reviews reject modifications.
- Result calculation requires organizer ownership.

## 7. Blind judging enforcement

Blindness is implemented at the API/data serialization layer.

For a judge viewing an assigned project, the serializer intentionally omits:

- team name
- team members
- participant names
- participant college
- assignment metadata

The blind response retains judging-relevant project content such as:

- project code
- title
- tagline
- problem
- solution
- technology stack
- repository/demo information
- track
- rubric context

A judge also receives only their own review when project review data is serialized.

This is stronger than simply hiding fields in React because the API itself constructs a blind representation.

## 8. Assignment architecture

Manual assignment:

```text
Organizer
   ↓
project + judge
   ↓
role check
   ↓
event ownership
   ↓
judging phase
   ↓
duplicate assignment check
   ↓
blocking conflict check
   ↓
create assignment
   ↓
audit
```

Automatic assignment:

```text
projects
   ↓
for each project
   ↓
find judges without existing assignment
   ↓
remove conflicting judges
   ↓
measure current workload
   ↓
choose lowest workload
   ↓
repeat until judges_per_project reached
```

The automatic algorithm uses deterministic tie-breaking between equal workloads by judge ID.

## 9. Conflict model

The server blocks assignment when any of these conditions applies:

- judge is a member of the project team
- judge participated in the event
- judge has a blocking declared conflict
- organizer has recorded a blocking conflict

A blocked manual assignment returns HTTP 409 and creates a `JUDGE_ASSIGNMENT_BLOCKED` audit event.

Judge-declared and organizer-recorded conflicts are stored in `judge_conflicts`.

## 10. Review architecture

Reviews are stored separately from criterion scores:

```text
reviews
   │
   ├── judge
   ├── project
   ├── status
   ├── total_raw
   └── timestamps
          │
          └── review_criterion_scores
                ├── criterion_id
                ├── score
                └── justification
```

The server enforces:

```text
DRAFT → FINALIZED → LOCKED
```

Rules:

- DRAFT can be edited.
- FINALIZED requires all rubric criteria and criterion justifications.
- FINALIZED can transition to LOCKED.
- DRAFT cannot jump directly to LOCKED.
- LOCKED cannot be modified through the normal review endpoint.
- Organizer reopening changes the review back to DRAFT and records the reason in the audit log.

## 11. Scoring

For each criterion:

```text
criterion contribution =
    (score / maxScore) × weight
```

The weighted criterion contributions are summed into the review's `total_raw`.

The backend rejects:

- unknown criterion IDs
- non-numeric scores
- scores below zero
- scores above `maxScore`
- missing criteria when finalizing
- missing criterion justifications when finalizing

## 12. Normalization

The event stores its configured normalization method.

Implemented methods:

- `z_score`
- `trimmed_mean`
- `borda`

### Z-score

For every judge:

```text
mean_j = mean(all completed raw scores by judge j)

std_j = population standard deviation of those scores

z(i,j) = (score(i,j) - mean_j) / std_j
```

If `std_j == 0`, the implementation contributes `0.0` for that judge/project rather than producing an undefined value.

The project normalized score is the mean of the available judge z-scores.

### Trimmed mean

When at least three judge scores exist for a project, one value is removed from each tail before averaging. Otherwise the available values are averaged without trimming.

### Borda

Each judge ranks their available project scores. The implementation awards a decreasing point fraction by position and averages the contribution across completed reviews for the project.

### Snapshot

Every calculation creates a `normalization_snapshots` row containing:

- method
- per-judge statistics
- result rows
- calculation metadata

The result rows reference the snapshot ID.

## 13. Result calculation

The result path is:

```text
completed reviews
       ↓
raw weighted score
       ↓
configured normalization
       ↓
configured tie-break order
       ↓
normalization snapshot
       ↓
result rows
       ↓
publication
```

Before calculation, the API checks every project for:

- missing assignments
- missing completed reviews
- insufficient completed review count

If anything is incomplete, calculation is blocked.

An organizer can explicitly override this gate by providing a reason. The override is included in the `RESULTS_CALCULATED` audit event.

## 14. Deterministic ranking

The event stores a configurable tie-break order.

Allowed fields:

```text
normalized_score
raw_score
code_name
```

The default is:

```text
normalized_score → raw_score → code_name
```

The ranking code applies these fields in order. Descending numeric values are preferred; `code_name` provides the final deterministic string ordering.

## 15. Publication and snapshotting

A calculation creates a new normalization snapshot and associated result rows.

Publication selects the latest snapshot, marks its rows as published, sets the event to `RESULTS`, and records `RESULTS_PUBLISHED`.

Published result rows retain the snapshot ID, so the published ranking can be traced to the calculation snapshot that produced it.

## 16. Audit architecture

Audit records contain:

```text
actor_id
event_id
action
entity_type
entity_id
details (JSON)
created_at
```

Examples:

```text
EVENT_CREATED
TEAM_CREATED
PROJECT_CREATED
PROJECT_UPDATED
JUDGE_ASSIGNED
JUDGE_ASSIGNMENT_BLOCKED
CONFLICT_DECLARED
REVIEW_CREATED
REVIEW_FINALIZED
REVIEW_LOCKED
REVIEW_REOPENED_BY_ORGANIZER
RESULTS_CALCULATED
RESULTS_PUBLISHED
EVENT_ARCHIVED
```

These are application audit records. The architecture deliberately does not claim blockchain or cryptographic hash-chain verification.

## 17. Integrity Pulse

Integrity Pulse is an operational status view, not an accusation engine.

The current implementation reports:

- incomplete projects
- blocked assignment count
- blocking conflict count

It does not label participants or judges as dishonest or cheating based on numerical patterns.

## 18. JudgeLens

The current JudgeLens endpoint provides:

- review count
- completed review count
- per-judge mean
- per-judge standard deviation
- per-judge review count
- review update timing

The current API response leaves criterion-level aggregation empty.

**Planned:** criterion-level aggregation if required by the final product specification.

## 19. REST resources

Canonical API paths include:

```text
/api/auth
/api/events
/api/teams
/api/projects
/api/judges
/api/assignments
/api/conflicts
/api/reviews
/api/results
/api/integrity
```

The application also exposes supporting paths for:

- audit
- JudgeLens
- normalization proof
- export
- analytics
- notifications
- certificates
- archive

OpenAPI is available at:

```text
http://localhost:8000/docs
```

Legacy non-prefixed routes remain available for compatibility but are hidden from the OpenAPI schema.

## 20. Error policy

The implementation uses controlled HTTP errors for expected workflow conditions:

| Status | Meaning |
|---|---|
| 400 / 422 | Invalid request or validation failure |
| 401 | Authentication failure |
| 403 | Permission denied |
| 404 | Resource not found |
| 409 | Conflict or invalid workflow state |
| 500 | Unexpected server error |

Examples of intentional 409 cases include duplicate event code, duplicate assignment, blocking judge conflict, closed submission phase, locked review mutation, incomplete result calculation, and invalid lifecycle transitions.

Database uniqueness violations are converted to controlled 409 responses where appropriate.

## 21. Transactions and concurrency

The database uses uniqueness constraints for critical relationships, including:

- one membership per user/event
- one team membership per team/user
- one project per team
- one judge/project assignment
- one review per judge/project
- one criterion score per review/criterion
- one result row per snapshot/project

The API catches relevant `IntegrityError` exceptions and maps them to HTTP 409 responses rather than exposing an accidental server error.

## 22. Offline/self-host design

The supplied deployment does not require:

- external auth
- cloud database
- external judging API
- external AI service
- blockchain service

PostgreSQL is local to the Compose stack, and the API seeds demo accounts/data at startup.

This makes the application suitable for a self-hosted/offline-oriented hackathon environment, subject to the host having the required container images/dependencies available.

## 23. Testing strategy

The backend test suite uses:

- pytest
- FastAPI `TestClient`
- SQLAlchemy
- an in-memory SQLite database for tests

The tests reset the database for each test and cover the critical judging workflow.

Current run:

```text
14 passed
```

The supplied tests include:

- auth and role enforcement
- duplicate event code
- rubric validation
- registration
- team capacity
- project creation
- blind identity isolation
- conflict blocking
- review state machine
- score range validation
- result snapshot/publication
- registration approval
- project versioning
- refresh-cookie lifecycle
- incomplete judging
- organizer override
- audited reopen
- assignment balancing

## 24. Threat model summary

| Threat | Current mitigation |
|---|---|
| Judge sees participant identity | Blind API serializer |
| Participant sees judge identity | Participant serializer omits assignment/review identity |
| Judge judges conflicted project | Conflict check before assignment and review |
| Judge accesses unassigned project | Assignment required by project-access helper |
| Locked review altered | State-machine check |
| Results published with incomplete judging | Completeness gate with explicit audited override |
| Access token persists in local storage | Access token is held in frontend memory |
| Refresh token exposed to JavaScript | HTTP-only cookie |
| Event phase bypass | Server-side transition checks |
| Nondeterministic ties | Persisted tie-break order |
| False integrity claim | No cryptographic/blockchain claim |

## 25. Planned architecture work

The following should be treated as Planned rather than implemented:

- criterion-level JudgeLens aggregation
- generated certificate documents/PDFs
- cryptographic result verification, if desired
- AI judging
- AI cheating detection
- any external messaging system

The implementation should continue to follow:

> Correctness > Security > Workflow integrity > Auditability > Usability > Visual polish
