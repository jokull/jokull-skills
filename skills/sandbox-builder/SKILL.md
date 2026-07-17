---
name: sandbox-builder
description: "Designs and builds an agent sandbox for an existing monorepo: a disposable, per-worktree runtime where coding agents can open the app in a real browser, seed scenarios, inspect logs and side effects, and produce evidence without fighting other agents over ports or a shared dev database. Use when asked to build an agent sandbox, give agents a runtime or browser access, set up per-worktree dev environments, isolate parallel agents, or replace 'I ran it locally' with reproducible proof."
compatibility: Targets a monorepo on a real workstation with Docker (OrbStack preferred on macOS), persistent caches, and enough RAM/CPU for parallel worktrees. Not aimed at small stateless CI containers.
license: MIT
metadata:
  author: jokull
  version: "1.0"
---

# Sandbox Builder

Build an agent sandbox: a disposable, inspectable, worktree-local runtime where an agent can behave
like a careful human doing manual QA — open real flows in a browser, read logs, check emails and
analytics, inspect side effects, and leave evidence behind.

This is not another E2E suite and not a prettier `docker compose up`. Framing it as committed
browser tests produces a brittle suite nobody trusts. Frame it as a playground with green lights,
x-ray visibility, honest integration fidelity, and repeatable teardown.

The shape you are aiming for — one universe per worktree, instead of every agent colliding on
`localhost:3000`:

```text
agent-a worktree
  https://web.agent-a.acme.local
  https://admin.agent-a.acme.local
  /tmp/acme-sandbox/workspaces/agent-a/
  /tmp/acme-sandbox/runs/run_abc123/

agent-b worktree
  https://web.agent-b.acme.local
  https://admin.agent-b.acme.local
  /tmp/acme-sandbox/workspaces/agent-b/
  /tmp/acme-sandbox/runs/run_def456/
```

Agent A fixes checkout while agent B investigates admin reporting. Both drive real browsers, both
have clean scoped logs, their own seeded data, and their own proof folder. The pretty domain is not
the point — the point is that anyone can look at a worktree and know it has its own app, its own
services, and its own evidence trail.

## The rule: discovery before code

**Inspect the repo, produce a design plan, and wait for approval before implementing.** Never guess
the topology. A sandbox wired to an imagined service graph is worse than no sandbox, because the
first failure teaches the agent to distrust the whole harness.

Discover: package manager and workspace layout; browser surfaces (web, admin, docs, storybook);
backend services (API, workers, queues, cron, webhooks); data stores; existing dev commands and
build graph; existing Docker or devcontainer setup; existing browser tooling; env and secret
loading; the production/staging/local integration boundary; existing observability (logs,
analytics, errors, email); and any worktree or workspace conventions already in play.

Then ask only what the code cannot tell you. Good questions: which surfaces must be
browser-addressable first; which scenarios matter most for QA; which integrations have safe
test-mode credentials; which systems must **never** receive writes; which remote-only features
should be disabled and labeled; what the host environment actually is.

The design plan states the command surface, services, ports, artifact paths, integration policy,
and the first green light. Then stop and get approval.

## Baseline stack

Use this unless the repo or host gives a concrete reason not to:

- One disposable Docker container per run or workspace, with the repo mounted in.
- [Procpane](https://github.com/jokull/procpane) as the in-container supervisor — healthcheck-gated
  services, addressable process names, queryable status, tail/grep, signaling.
- The monorepo's native package manager and task runner. Turbo pairs naturally with Procpane when
  services map onto Turbo tasks.
- [OrbStack](https://orbstack.dev/) on macOS for fast Docker and local container domains.
- Stable pretty per-worktree URLs where possible; plain localhost ports as the fallback for Linux,
  VPS, Docker Desktop, or CI.
- [Superset](https://docs.superset.sh/workspaces) or equivalent worktree orchestration as the
  parallel-agent flow.

## Phases

Keep the whole architecture in mind; get a real green light early.

1. **Discovery and design** — inspect, classify, propose, ask, wait for approval.
2. **Minimal container runtime** — one container, core services under Procpane, safe generated env,
   host secrets masked, run registry and artifact directory, `up` / `status` / `down`.
3. **Green light** — from a *fresh* worktree: services start, URLs and ports resolve, processes
   report healthy, logs are tail/grep-able, artifact metadata is written, failures are actionable.
   This is the first thing worth demonstrating.
4. **Browser vision** — browser helper capturing screenshots, console errors, page errors, failed
   requests, result JSON; seeded auth state; a basic smoke command.
5. **Scenario seeds** — small named bundles, seed radii, composable context, seed summary.
6. **Local observability** — email outbox, analytics ledger, error sink, request recorder, webhook
   fixtures.
7. **Workspace mode** — stable per-worktree ids and port reservations, pretty URLs, workspace
   metadata, no-argument commands preferring the current workspace.
8. **Documentation** — integration policy, caveats, common commands, how to produce PR evidence,
   how to add scenarios.

Do not stop at a design. After approval, build the first vertical slice and prove the green light
with real command output.

## References

Read these when you reach the phase that needs them — not upfront.

- **`references/architecture.md`** — run and workspace registries, container boundary, process
  supervision, browser access, artifacts, scenario seeds, the command surface, and the launch-panel
  output. Read during design (phase 1) and while building phases 2–7.
- **`references/integration-policy.md`** — how to classify every integration before implementing it:
  run real, read-only real, vendor test mode, mock-and-record, browser shim, local sink, disable
  explicitly, or add an app-code seam. Read during design, before touching any provider.
- **`references/operating-lessons.md`** — what goes wrong once the thing is running: false proof,
  cache and staleness traps, cost control. Read when writing the docs in phase 8, and when a
  sandbox is behaving strangely.
- **`references/worked-example.md`** — one real build, concrete: the Procpane service graph with its
  health checks and dependency ordering, the integration policy as actually decided, seed radii,
  a good app-code seam, workspace mode, and what a full-stack sandbox does to bundler memory. Read
  it during design when the abstractions above need grounding — but run your own discovery rather
  than copying the topology.

## Quality bar

The sandbox works when an agent can start a worktree-local environment without babysitting; see
which services are healthy; open the app at stable URLs; exercise a seeded scenario; inspect logs
and side effects without shelling into the container; see external calls and local observability
output; produce a screenshot plus at least one durable invariant; tear down cleanly; and do all of
that in parallel with another agent in another worktree.

If a feature cannot be represented honestly, mark it disabled or partially covered in `status` and
`summary`. Never fake coverage — a sandbox that lies is worth less than one that admits a gap.
