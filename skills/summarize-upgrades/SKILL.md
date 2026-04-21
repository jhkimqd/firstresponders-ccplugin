---
name: summarize-upgrades
description: |
  Summarize recent changes to 0xPolygon/bor and 0xPolygon/heimdall-v2 from
  the locally-ingested NDJSON knowledge base. Use when the user asks things
  like "what changed in Bor recently?", "any new checkpoint logic since
  <date>?", "heimdall-v2 upgrades this month", "bor PRs touching consensus
  in the last 2 weeks", or "summarize recent heimdall merges".
type: skill
---

# summarize-upgrades

Reads `data/github/{bor,heimdall-v2}/prs.jsonl` and produces a grouped-by-week
digest of merged PRs with citation URLs. Optional keyword and date filters let
the responder zoom in on a topic (checkpoint, consensus, gas, migration, etc.).

## When to trigger

- **"What changed in Bor recently?"**, **"Bor upgrades this week"**
- **"Any new checkpoint logic since <date>?"**, **"Heimdall changes since Tuesday?"**
- **"PRs touching <keyword>"** where `<keyword>` is a subsystem name (e.g. gas,
  staking, bridge, consensus, checkpoint, milestone).

If the data is stale or missing, advise the user to run `refresh-knowledge`
first (or invoke that skill and retry).

## Inputs

- `--repo` — `bor`, `heimdall-v2`, or `both` (default).
- `--since` — ISO date (`2026-04-01`) or relative (`30d`, `2w`, `12h`). Default: `14d`.
- `--until` — optional upper bound, same format as `--since`.
- `--keywords` — comma-separated substrings matched case-insensitively against
  PR title + body + filenames.
- `--limit` — cap number of PRs listed (default: 50).
- `--format` — `markdown` (default) or `json`.

## Workflow

1. Invoke `scripts/summarize.py` with the parsed inputs. The script reads the
   NDJSON files directly — it does not hit GitHub.
2. The script emits Markdown grouped by ISO-week (`YYYY-Www`) with bullet items
   of the form:

   ```
   - **#1234** — Add milestone batching (alice) — [link](https://github.com/0xPolygon/bor/pull/1234)
   ```

3. Present the digest verbatim. Cite the PR URL for every claim; do not
   paraphrase PR bodies without linking.
4. If zero matches, say so and suggest widening `--since` or dropping
   `--keywords`.

## Output contract

- Every bullet MUST include the PR URL (SPEC §5.1 "cite PR URLs").
- Never invent PRs or bodies — only what is in the JSONL files.
- Never call the GitHub API from this skill (that's `refresh-knowledge`'s job).

## Related skills

- `refresh-knowledge` — populates the NDJSON this skill reads.
- `answer-faq` — for static doc Q&A (unrelated to GitHub).
