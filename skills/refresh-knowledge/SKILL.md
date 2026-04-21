---
name: refresh-knowledge
description: |
  Pull the latest merged PRs and default-branch commits from 0xPolygon/bor and
  0xPolygon/heimdall-v2 into the local knowledge base. Use when the user asks
  phrases like "refresh the GitHub data", "pull latest bor PRs", "update the
  upgrade knowledge base", "ingest recent heimdall commits", "sync github",
  or whenever `summarize-upgrades` reports stale/missing data and the user
  wants to refresh before re-asking.
type: skill
---

# refresh-knowledge

Incrementally fetch merged PRs and commits from the two upgrade-bearing repos
and persist them as NDJSON under `data/github/`. Cursor is tracked in
`data/github/.cursor.json` so repeated runs only fetch new rows.

## When to trigger

- **"Refresh the GitHub data"** / **"Pull latest Bor PRs"** / **"Sync heimdall commits"**
- **"Update the upgrade knowledge base"**
- Implicitly before `summarize-upgrades` if `data/github/bor/prs.jsonl` does not exist
  or its most recent entry is older than the user-requested date window.

Do **not** trigger for questions answered from static docs — those go to `answer-faq`.

## Inputs

- `--repos` (default: `bor,heimdall-v2`) — comma-separated short names.
- `--since` (default: `30d`) — lookback window; accepts `30d`, `12h`, `2w`, or
  a date like `2026-04-01`.

## Workflow

1. Check `GITHUB_TOKEN` is exported (unauthenticated access is capped at 60 req/hr).
   If absent, warn the user but proceed.
2. Invoke `scripts/ingest.py` with any user-supplied `--repos` / `--since`. The
   script shells into `polygon_frp.github_ingest`.
3. Parse the JSON summary printed on stdout:

   ```json
   {"prs_written": {"bor": 3}, "commits_written": {"bor": 12, "heimdall-v2": 0}, "total": 15}
   ```

4. Report counts per repo + the effective lookback to the user.
5. On non-zero exit, read the logged exit code and explain: `1` rate-limit,
   `2` network, `3` auth. Suggest `GITHUB_TOKEN` for rate-limit/auth.

## Output contract

Always print the structured summary and the total new-row count. Never mutate
`data/docs/`. Never commit `data/github/` (it is `.gitignore`d).

## Related skills

- `summarize-upgrades` — consumes the NDJSON this skill writes.
- `answer-faq` — consumes `data/docs/*.md` only; independent of this skill.
