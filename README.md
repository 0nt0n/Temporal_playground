# Temporal agent playground (Python)

A minimal, runnable sandbox that shows why Temporal is interesting for our
core agent. Your agent loop becomes a **Workflow**; LLM / tool / `opencode`
calls become **Activities**. Runs with **zero secrets** (the LLM is mocked,
`opencode` has a fallback), so you can clone and go.

> Not for the repo — this is the scratch playground Терентьев asked for.

## What it demonstrates

1. **Durable execution** — kill the worker mid-run, restart it, the agent
   resumes from the last finished step. No re-running completed LLM calls.
2. **No Postgres state table** — loop position + every intermediate result
   live in Temporal's Event History, not in a `states` table you maintain.
3. **Human-in-the-loop** — a "risky" step pauses until an `approve` signal.
4. **CLI integration** — a step is routed to the `opencode` CLI from inside
   an Activity (the pattern for wiring any CLI/agent into Temporal).

## Files

| file | role |
|------|------|
| `workflow.py`   | the agent loop — deterministic orchestration only |
| `activities.py` | LLM call + `opencode` call — the side effects |
| `worker.py`     | hosts & runs the code (kill this to simulate a crash) |
| `starter.py`    | kicks off one run |
| `approve.py`    | sends the human approval signal |
| `shared.py`     | dataclasses passed across boundaries |

## Run it

**1. Start a local Temporal server** (recommended path — the Temporal CLI):

```bash
# install the CLI once
curl -sSf https://temporal.download/cli.sh | sh   # or: brew install temporal
# then:
temporal server start-dev
```

This gives you the server on `localhost:7233` and the Web UI on
`http://localhost:8233`. (Alternative self-hosted / Docker stack for a more
"bank-like" setup: github.com/temporalio/docker-compose.)

**2. Install deps & start the worker:**

```bash
pip install -r requirements.txt
python worker.py
```

**3. In a second terminal, start a run:**

```bash
python starter.py
```

It will process a few steps, then **pause** at the `[approval]` step.

**4. Approve it (third terminal, or reuse):**

```bash
python approve.py          # or: python approve.py false   (to reject)
```

## The crash demo (the money shot for the talk)

1. `python starter.py`
2. Watch the worker log `🔵 [ACTIVITY call_llm] EXECUTING` for the first steps.
3. **Ctrl+C the worker** after a step or two.
4. Restart it: `python worker.py`
5. Notice the already-completed steps do **not** print `EXECUTING` again —
   their results are replayed from history; the agent continues where it
   stopped. Open the Web UI to see the full Event History for `agent-demo-1`.

## How this maps to our orchestrator

| Today (rough) | With Temporal |
|---------------|---------------|
| `states` table in PG, hand-written | Event History (durable, automatic) |
| custom retry / backoff code | `RetryPolicy` per Activity |
| cron / poller to resume stuck jobs | automatic replay on worker restart |
| ad-hoc "waiting for approval" flags | Signals + `wait_condition` |
| bespoke status endpoint reading PG | Queries |

## Next steps (Phase 4)

- Swap the mock in `activities.py` for a real model (one block, marked in code).
- Try the official **Temporal ↔ LangGraph** plugin (preview) — it lets you drop
  external checkpointers (PG/Redis) entirely, since Temporal owns durability.
  `pip install "temporalio[langgraph]"`, samples in `temporalio/samples-python`.
- For `opencode`, compare shelling out (`opencode run`) vs. driving
  `opencode serve` over its HTTP API from the Activity.

## Known gotchas to mention in the talk

- Workflow code must be **deterministic** (no I/O, no random, no wall-clock);
  everything non-deterministic goes in Activities.
- Changing workflow code for **in-flight** runs needs Worker Versioning /
  patching — plan for it before production.
- Porting a very dynamic agent's routing straight into Temporal can feel
  verbose; the common answer is LangGraph (reasoning) *on top of* Temporal
  (durability), not one replacing the other.
