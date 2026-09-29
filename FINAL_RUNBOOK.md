# AGAMOTTO Final Runbook

## 1. Requirements

- Git
- Docker Desktop / Docker Engine with Compose
- A GitHub account if publishing the repository

No local Node.js or Python installation is required for the Docker path.

## 2. Put this package into a new GitHub repository

Extract this ZIP. From the extracted AGAMOTTO folder:

```bash
git init
git branch -M main
git add .
git commit -m "Initial AGAMOTTO release"
git remote add origin https://github.com/<YOUR_USERNAME>/<NEW_REPO>.git
git push -u origin main
```

Create the empty GitHub repository first. Do not initialize it with a README, .gitignore, or license because this package already contains them.

## 3. Run locally with Docker

From the repository root:

```bash
docker compose up --build
```

Wait for PostgreSQL and the API to start. Open:

- Frontend: http://localhost:3000
- API: http://localhost:8000
- API health: http://localhost:8000/health

The API container automatically runs Alembic migrations and seeds the demo accounts before starting FastAPI.

## 4. Demo accounts

All demo accounts use the same password:

`LocalDemo123!`

Organizer:
`director@agamotto.systems`

Judge:
`aris.thorne@vertex-systems.io`

Participant:
`kiran@stanford.edu`

## 5. Recommended demonstration path

1. Sign in as Organizer.
2. Open the seeded event / organizer dashboard.
3. Inspect teams and projects.
4. Inspect judges and assignments.
5. Open the judging progress view.
6. Sign out.
7. Sign in as Judge.
8. Open assigned submissions.
9. Open a blind review and enter rubric scores + justifications.
10. Finalize / lock the review.
11. Return to Organizer.
12. Calculate results using normalization.
13. Inspect results, JudgeLens, Integrity Pulse, audit trail, and normalization proof.
14. Sign in as Participant and verify participant-facing results when published.

## 6. Environment overrides

Optional root `.env` values:

```env
JWT_SECRET=replace-with-a-long-random-secret
NEXT_PUBLIC_API_URL=http://localhost:8000/api
```

For a different deployment host, change `NEXT_PUBLIC_API_URL` to the public API URL before rebuilding the frontend image.

## 7. Stop / reset

Stop containers:

```bash
docker compose down
```

Stop and remove the local PostgreSQL volume as well:

```bash
docker compose down -v
```

The second command deletes the local demo database and all locally stored event data.

## 8. If Docker is already running and you changed source files

```bash
docker compose up --build
```

For a completely clean image rebuild:

```bash
docker compose build --no-cache

docker compose up
```
