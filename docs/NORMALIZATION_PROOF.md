# Normalization Proof

AGAMOTTO stores each result calculation as an immutable normalization snapshot. A snapshot records:

- normalization method
- creation timestamp
- per-judge mean, standard deviation and review count
- fallback metadata where applicable
- the exact result rows used for ranking
- configured tie-break order

For z-score normalization, each judge's review is standardized as:

`z = (judge_score - judge_mean) / judge_standard_deviation`

A judge with a single review or zero variance contributes a deterministic zero z-score rather than producing an undefined value. The API exposes the stored calculation through:

`GET /api/events/{event_id}/normalization-proof/{snapshot_id}`

Published results reference their snapshot ID, allowing the published ranking to be traced back to the stored normalization inputs.
