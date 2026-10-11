# SCALING — Algeria AI Sales Bot

## Bottlenecks (current)
1. **In-memory stores** — `LEADS` dict + `AUDIT` list in
   `backend/app/api/router.py` live in process memory: no persistence, no
   sharing across workers, unbounded growth except rate-bucket pruning.
2. **Unbounded list response** — fixed: `GET /api/v1/leads` now takes
   `limit` (default 50, max 500) + `offset` (default 0).
3. **Rate limiter is in-memory per process** (`_RATE_BUCKETS`, 120 req / 60 s
   per client+path, max 5000 buckets with oldest-evicted) — restarts reset it.
4. **Draft generation** calls the LLM gateway server-side with no local
   timeout/pool tuning in this version; gateway latency dominates `/drafts`.

## Tuning variables / constants
| Setting | Location | Default |
|---|---|---|
| `_RATE_LIMIT_MAX` | `backend/app/api/router.py` | 120 req / window |
| `_RATE_LIMIT_WINDOW_S` | `backend/app/api/router.py` | 60 s |
| `limit` / `offset` | `GET /api/v1/leads` query | 50 / 0 (max 500) |
| `LLM_BASE_URL` / `LLM_MODEL` | env (`.env.example`) | gateway URL / `gpt-5-mini` |
| `ENABLE_EXTERNAL_DELIVERY` | env | `false` (delivery off) |

No DB pool exists (no database in this version) — nothing to tune there.

## Remaining capacity limits (honest)
- Single-process memory store: capacity ≈ RAM for leads/audit; restart =
  data loss. A persistent store (Postgres + migrations) is the real fix for
  scale-out; until then run **one replica** only.
- Rate limit does not coordinate across replicas; N replicas ≈ N× limit.
- `GET /api/v1/analytics` scans all leads per call (O(n)) — fine for
  hundreds of leads, degrades linearly into the tens of thousands.
