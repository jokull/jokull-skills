# Architecture

The concepts to design the sandbox around. Adapt names to the repo; preserve the capabilities.

## Run registry

- Every run has a run id.
- Every run writes `run.json`: services, ports, URLs, artifact paths, process names, seed summary,
  fidelity caveats.
- Artifacts live under a stable host directory, e.g. `/tmp/<project>-sandbox/runs/<run-id>/`.
- Write an `env.sh` (or equivalent) so an agent can source useful URLs and paths.
- Provide `status`, `summary`, and `down`.

## Workspace registry

- Every worktree has a stable workspace id, derived from worktree path, branch, git common dir,
  and/or workspace name.
- Port reservations survive teardown unless explicitly released.
- Workspace state lives under `/tmp/<project>-sandbox/workspaces/<workspace-id>/`.
- Emit metadata for the workspace tool, e.g. `.superset/ports.json`.
- No-argument commands prefer the current workspace's run.
- Aim for readable workspace-scoped URLs:

  ```text
  https://web.<workspace>.<project>.local
  https://admin.<workspace>.<project>.local
  https://api.<workspace>.<project>.local
  ```

  Extend the pattern for more surfaces: `docs`, `storybook`, `worker`, `mail`, `errors`, `queue`,
  `analytics`.

- Without pretty local domains, keep the same model with direct ports plus metadata:

  ```json
  {
    "workspace": "agent-a",
    "services": {
      "web": { "url": "http://127.0.0.1:43100" },
      "admin": { "url": "http://127.0.0.1:43101" },
      "api": { "url": "http://127.0.0.1:43102" }
    },
    "artifacts": "/tmp/acme-sandbox/runs/run_abc123"
  }
  ```

## Container boundary

- One container per run/workspace, repo mounted in.
- Mask host `.env`, `.env.*`, `.dev.vars`, and similar secret files inside the container by default.
- Generate sandbox env files from a curated allowlist. Copy only read-only, public, fake, or
  vendor-test-mode values.
- Reject live/production credentials where a prefix or metadata check is possible — fail startup
  before the sandbox ever reaches a browser.
- Keep the build context small. Cache installs and build outputs where safe. Make image rebuilds
  explicit when refreshing base tools.

## Process supervision

- Run every app service through the supervisor ([Procpane](https://github.com/jokull/procpane)).
- Addressable process name per service, health check per service.
- Expose status, tail, grep, restart/signal, and log collection.
- On startup failure, print the failing process and its relevant logs.
- An agent should never have to shell into the container for a routine failure.

## Browser access

- A helper that opens a target surface and path.
- Capture screenshots, console errors, page errors, failed requests, and route state.
- Support seeded auth state for common roles.
- Support both direct ports and pretty per-workspace URLs; prefer local domains on macOS.
- Do not maintain a hand-written route registry — infer routes from app source and scenario
  metadata.

## Artifacts

Write everything important into the run artifact directory: screenshots, browser result JSON,
process logs, external request logs, analytics events, email outbox, error events, media request
logs, webhook logs, seed summary, final summary.

Make artifacts easy to quote in a PR. The final summary combines browser evidence with durable
invariants: DB rows, URL state, session state, request logs, email artifacts, analytics events,
error issues, queue entries, process health.

## Scenario seeds

Treat seeding as a first-class agent surface, not hidden fixture setup.

Radii expand to *ordered named bundles*, not separate hardcoded seed paths:

```text
z  -> baseline reference data only
s  -> baseline + admin user + customer user
m  -> s + ordinary domain spine (account/order/project/booking)
l  -> m + checkout/provider/content/workflow bundles
xl -> l + expensive or broad scenario data, only if truly useful
```

Generic bundle names: `reference-data`, `admin-user`, `customer-user`, `basic-account`, `order`,
`booking`, `checkout-ready`, `content-page`, `provider-fixture`, `workflow-with-webhook`,
`queue-backlog`, `analytics-demo`, `error-demo`. Keep exact names project-specific.

- Seeds create real local data in the local DB or stores. Prefer product-real behavior over
  sandbox-only branches.
- Bundles are composable and idempotent, sharing a seed context so later bundles reuse earlier ids
  — a `booking` bundle reuses the customer/order from `order`; a `webhook` bundle reuses the payment
  id from `checkout-ready`.
- Keep bundle order deterministic; deduplicate expanded bundles.
- Let agents request exact bundles when that is clearer than a radius.
- Write `seed-summary.json` for tools and `seed-summary.md` for humans.

Good seed metadata: user ids and roles, auth state hints, primary app paths, entity ids, provider
fixture ids, expected webhook ids, expected analytics events, visible selectors, critical media
selectors, known caveats.

Bad seed design: one giant kitchen-sink fixture every scenario depends on, or important generated
ids buried in logs the agent cannot parse.

## Command surface

Adapt the names, preserve the capabilities:

- `sandbox up --seed <scenario|radius|bundle,bundle>` — start a disposable proof run
- `sandbox seeds` — list known radii and bundles
- `sandbox workspace up --seed <scenario> --reuse` — start or reuse the current worktree's sandbox
- `sandbox status [run-id]` — readiness, URLs, processes, artifacts, caveats
- `sandbox browse [run-id] <app> <path> [--auth <role>]` — open browser, capture evidence
- `sandbox smoke [run-id] <scenario>` — scenario-defined browser check, writes artifacts
- `sandbox logs <service>` / `sandbox pane <service>` — tail/grep/status/restart
- `sandbox emails`, `sandbox email latest --html` — inspect outbox
- `sandbox analytics --require <event>` — inspect analytics ledger
- `sandbox errors` — inspect error sink
- `sandbox requests` — inspect external request recorder
- `sandbox webhook <fixture>` — send a deterministic signed webhook fixture
- `sandbox summary [run-id]` — write final evidence summary
- `sandbox down [run-id]` — stop and clean up

Workspace scripts: setup (generate env, copy safe local state, allocate ports, write metadata), run
(start/reuse), teardown (stop, optionally release ports).

## The launch panel

Startup output is part of the product. It should read like a launch panel, not a wall of logs — it
teaches agents and humans how to use the sandbox without reading the README:

```text
Sandbox workspace ready: agent-a

Apps
  web      https://web.agent-a.acme.local      http://127.0.0.1:43100
  admin    https://admin.agent-a.acme.local    http://127.0.0.1:43101
  api      https://api.agent-a.acme.local      http://127.0.0.1:43102

Seed
  radius     m
  bundles    reference-data, admin-user, customer-user, order, booking
  summary    /tmp/acme-sandbox/runs/run_abc123/seed-summary.md
  ids        customer=cus_123 order=ord_456 booking=bkg_789

X-ray
  logs       sandbox logs api
  browser    sandbox browse web /
  email      sandbox emails
  analytics  sandbox analytics
  errors     sandbox errors
  summary    sandbox summary

Artifacts
  /tmp/acme-sandbox/runs/run_abc123
```

Workspace setup/run output should include: workspace name and id, browser URLs per surface, direct
ports, selected seed radius or bundles, seed summary path and important ids, artifact directory,
supervisor status, readiness summary, and clear failure output with log pointers.
