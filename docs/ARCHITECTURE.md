# AGAMOTTO Architecture

AGAMOTTO is a self-hosted three-tier application:

- **Web:** Next.js App Router, React and Tailwind.
- **API:** FastAPI with PostgreSQL persistence and Alembic migrations.
- **Database:** PostgreSQL 17 in the supplied Docker Compose stack.

The API exposes canonical `/api/...` routes in OpenAPI. Legacy non-prefixed routes remain as compatibility aliases.

Critical judging behaviour is server-side: assignment eligibility, conflicts, blind serialization, review state transitions, criterion validation, completeness gates, normalization snapshots and deterministic ranking.
