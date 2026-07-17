# Integration policy

Classify every integration **before** implementing it. The design plan carries a table:

| Integration | Local strategy | Writes possible? | Secret source and safety rule | Fidelity caveat | Evidence surface |

Pick one of the patterns below per integration. The classification is the design decision; the code
follows from it.

## Run real locally

For services that are part of the app stack and safe to own locally: web app, admin app, API,
worker, local DB, Redis, queue worker, search index, object-store emulator.

Evidence: process health, logs, DB rows, queue state, browser output.

## Use a read-only real service

When realism matters and writes are impossible or safely scoped: public CMS token, read-only
catalog, maps/browser public key, read-only feature metadata.

Never copy a write-capable token into the sandbox.

Evidence: rendered content, request logs, an explicit caveat that writes are not covered.

## Use vendor test mode

When the vendor has a real sandbox environment: payment processors in test mode, email provider
sandbox domains, SMS test numbers, webhook test endpoints.

Reject live keys by prefix or vendor metadata where possible.

Evidence: webhook logs, signed fixture events, DB state changes, analytics events, provider test ids.

## Mock with request recording

When writes would affect partners, cost money, create bookings, mutate CRM records, send messages,
or trigger fulfillment: booking providers, shipping, CRM, enrichment APIs, supplier APIs,
irreversible fulfillment, most AI providers by default, tax engines, address verification, fraud
scoring.

- Route traffic through a local mock proxy.
- Record every request as JSONL with sensitive headers and body fields redacted.
- Validate that requests match seeded scenario ids where possible.
- Log unregistered requests loudly — a silent unmatched request is how fake coverage starts.

Evidence: request counts, latest payloads, matched fixture names, unregistered request list.

## Shim in the browser

When a third-party browser script is not the thing under inspection: payment elements, analytics
scripts, CAPTCHA, ads, tag managers, heatmaps, support widgets.

Make the shim explicit in readiness/status output, and see `operating-lessons.md` — a shim proves
the route, never the integration.

Evidence: page loads, console stays clean, app receives expected callbacks.

## Route to a local sink

For observability and side effects agents need to inspect.

- **Email** — never send real email by default. Local outbox with HTML, text, headers,
  attachments, metadata. Commands: `emails`, `email latest --html`, `email latest --grep <text>`.
  SMTP redirects to a local capture service; platform email bindings write `.eml`/`.html`/`.txt`
  plus metadata JSON.
- **Analytics** — local JSONL sink. Point the SDK host config at the sandbox mock proxy; accept
  capture/batch/identify/group/decide/flags routes and the static script; return harmless
  flag/bootstrap responses; write every event to `analytics-events.jsonl`. Preserve event names,
  timestamps, hashed distinct ids, safe properties, request context. Redact emails, names, tokens,
  cookies, authorization headers, and long free-text by default. Provide
  `analytics --require "Checkout Started"` and `analytics --latest`.
- **Error tracking** — fake DSN pointing at the local container; route browser and server envelopes
  to a Sentry-compatible sink such as [Urgentry](https://github.com/urgentry/urgentry) when the app
  already emits Sentry-compatible events and a real local issue UI beats a raw envelope log.
  Preserve issue title, stack frames, tags, release/environment, request URL, breadcrumbs.
- **Webhooks** — local receiver, or a deterministic signed fixture sender that uses the same
  verification path as production. Capture secret material only into sandbox artifacts.
- **Queues and cron** — local queue state and manual triggers: `queue list`, `queue drain`,
  `queue retry <id>`, `cron run nightly-settlement`. Local dead-letter artifact. Record job attempts
  and failures with redaction. The scenario summary says whether expected jobs enqueued *and*
  processed.
- **Object storage and media** — uploads to a local emulator or filesystem bucket; public CDN reads
  may use real read-only URLs when visual fidelity matters. Record media requests. Assert important
  images actually decode when the scenario cares.

An empty sink is evidence too: a 500 in the browser with no recorded issue is an observability gap
the sandbox should surface, not hide.

## Disable explicitly

When local fidelity would be fake, dangerous, or too expensive for the first phase: anti-bot and
CAPTCHA, fraud/risk engines, production-only bindings, irreversible fulfillment, high-cost AI
agents, live compliance systems.

Disable **only** in local sandbox mode; fail closed everywhere else. Surface the disabled feature in
status and summary as a fidelity caveat. Do not pretend the scenario covers it.

## Add an app-code seam

When production code is too rigid to support safe local fidelity.

Good seams: env-configured service base URLs, local-safe email transport, analytics/error DSNs
configurable by env, provider clients routed by base URL, seeded local auth/session support, feature
flags from local config, explicit local disable switches, graceful degradation when optional
read-only content is absent.

Bad sandbox bleed:

- Product branches that exist only to fake success in the sandbox.
- Business-logic bypasses that make a flow green.
- Teaching production code about a specific harness command.
- Silent disabling outside local sandbox mode.
- Hiding missing fidelity instead of reporting it as a caveat.

## Escalate to a human

When a choice changes business behavior, security posture, payment state, booking state,
fulfillment, production data access, or compliance guarantees.

## Worked example: payments

Payments show every pattern at once, which is why they are the best test of the policy:

- **Real enough** — the server talks to vendor test mode, webhook signatures verify through the
  production code path, local DB mutations are real.
- **Shimmed** — the embedded browser payment UI can be replaced with a deterministic shim when the
  card iframe is not what is being evaluated.
- **Recorded** — every webhook attempt and outgoing provider call lands in artifacts.
- **Guarded** — a live key fails startup before the sandbox reaches the browser.

Support a long-running local webhook listener when useful, and a deterministic signed fixture sender
for proof runs.

Evidence: webhook log, local DB row, analytics event, payment id, signed fixture result.

## Feature flags

Pin local flag state in generated config, or mock the flag service endpoint. Scenario metadata says
which flags are on and off. Status lists non-default flags so an agent does not misread behavior as
a bug.

## Remote-only infrastructure

If a feature depends on remote bindings or platform-only services, pick one honestly: build a local
emulator, use explicit remote test mode with guardrails, or disable it and label it not covered. Do
not fake coverage.
