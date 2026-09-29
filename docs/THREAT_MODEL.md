# AGAMOTTO Threat Model

## Assets

- Judge identity and authentication credentials
- Participant/team identity
- Submission content and private event access codes
- Judge assignments and declared conflicts
- Raw scores, criterion justifications and review state
- Published result snapshots and audit records

## Trust boundaries

1. Browser ↔ API: all sensitive authorization is rechecked server-side.
2. API ↔ PostgreSQL: database is trusted storage; clients never write directly to it.
3. Organizer ↔ judging engine: organizer controls configuration, but immutable review and published-result rules remain enforced by the API.

## Main threats and mitigations

| Threat | Mitigation |
|---|---|
| Judge sees participant identity | Blind serializer removes team/member/college identity for judge responses. |
| Participant sees judge identity | Participant serializers omit assignment/review identity. |
| Judge scores conflicted project | Conflict checks run before every review save and before assignment. |
| Judge scores unassigned project | Sensitive project access requires an active judge assignment. |
| Locked review is altered | Review state machine rejects all edits after LOCKED. |
| Results published early | Incomplete assignments/reviews block calculation unless organizer supplies an explicit audited override. |
| Token persists in browser storage | Access token is memory-only; refresh token is HTTP-only cookie. |
| Arbitrary event phase jump | Server-side event transition validation rejects invalid lifecycle transitions. |
| Result ranking changes nondeterministically | Configured tie-break order is persisted and applied deterministically. |
| Audit claims are unverifiable | Audit records are append-only application records; no cryptographic integrity claim is made. |

## Deliberate non-goals

- No AI cheating accusation or confidence score.
- No AI interpretation of judging evidence.
- No cryptographic hash-chain claim unless such a mechanism is actually implemented.
- No judge-to-participant messaging channel.
