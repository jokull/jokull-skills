# Worked example

One real implementation, to make the abstractions concrete. The repo: a travel-commerce monorepo —
a Next.js storefront, a Vite admin SPA, a Hono API on Cloudflare Workers, Postgres, Stripe, a
headless CMS, several booking/inventory providers, PostHog, Sentry.

Vendor-specific names are genericized; the decisions are as built. Do not copy the topology —
copy the reasoning, then run your own discovery.

## The service graph

Eight processes in one container, under Procpane. The whole graph is declarative, and the shape of
it *is* the readiness model:

```toml
[tasks."@acme/sandbox#container:postgres"]
healthcheck.tcp = 5432
healthcheck.start_period = "2s"

[tasks."@acme/sandbox#container:seed"]
healthcheck.exit = 0                    # a task that finishes, not a service
healthcheck.start_period = "1s"
depends_on."@acme/sandbox#container:postgres" = "healthy"

[tasks."@acme/sandbox#container:mock-proxy"]
healthcheck.log = "listening on"
healthcheck.start_period = "1s"

[tasks."@acme/sandbox#container:stripe-webhook"]
healthcheck.log = "stripe webhook listener ready"

[tasks."@acme/sandbox#container:errors"]          # local Sentry-compatible sink
healthcheck.log = "urgentry sandbox DSN ready"

[tasks."@acme/sandbox#container:api"]
healthcheck.log = "VITE .* ready in|ready in"
healthcheck.start_period = "5s"
depends_on."@acme/sandbox#container:seed" = "completed"
depends_on."@acme/sandbox#container:mock-proxy" = "healthy"
depends_on."@acme/sandbox#container:stripe-webhook" = "healthy"
depends_on."@acme/sandbox#container:errors" = "healthy"

[tasks."@acme/sandbox#container:web"]
healthcheck.log = "Ready in|started server on|Compiled"
depends_on."@acme/sandbox#container:api" = "healthy"

[tasks."@acme/sandbox#container:admin"]
healthcheck.log = "VITE .* ready in|Local:.*localhost"
depends_on."@acme/sandbox#container:api" = "healthy"

[tasks."@acme/sandbox#container:domain-proxy"]    # Host-header router for pretty URLs
healthcheck.log = "sandbox domain proxy listening on"
depends_on."@acme/sandbox#container:api" = "healthy"
depends_on."@acme/sandbox#container:web" = "healthy"
depends_on."@acme/sandbox#container:admin" = "healthy"
```

Three health-check kinds do all the work: `tcp` for the database, `exit = 0` for the seed (a task
that completes rather than runs), and `log` regexes for anything that announces itself. The API
waits on the seed *completing* and every sink being *healthy* — so by the time the app is up, there
is nowhere for an event to leak to except a local sink. That ordering is a safety property, not a
convenience.

This is also where `wait` gets its meaning: readiness is the leaf of the dependency graph, not "the
container started."

## The integration policy, as decided

| Integration | Strategy | Writes | Secret rule | Caveat |
|---|---|---|---|---|
| Postgres, API, web, admin | Run real locally | yes, local | none | — |
| Maps | Read-only real | no | public browser token | — |
| CMS | Read-only real | no | public read token only; server token populated *from* the read token | no write coverage |
| Stripe | Vendor test mode | test only | `pk_test_` / `sk_test_` prefix required; live keys reject before Docker starts | browser Stripe.js is shimmed |
| Booking providers (×3) | Mock + record | never | no live credentials, ever | fixture fidelity only |
| Sentry | Local sink | local | fake DSN → local container | — |
| PostHog | Local sink | local | mock proxy | — |
| AI planner feature | Disabled | — | `*_DISABLED=1` | not covered |
| CAPTCHA | Disabled | — | blank site key | app treats missing key as no capability; API fails closed when deployed |
| Worker remote bindings | Disabled | — | — | not covered |

Things worth stealing from this table:

**The live-key check runs before Docker starts.** Not at request time, not as a warning — startup
refuses. A guard that fires after the browser opens has already lost.

**The CMS server token is populated from the public read token.** Not a separate secret to manage,
and structurally incapable of writing. The rule "never add a CMS write key to make test content" is
written into the docs precisely because it's the tempting shortcut.

**The error sink uses a deterministic numeric project id** so real Sentry SDK DSNs are accepted
unmodified while every event stays in the container. The app doesn't know it's in a sandbox.

**The analytics sink records event names, a safe property allowlist (`orderId`, `amount`), and
hashed identifiers.** Enough to assert an event contract; not enough to leak a customer.

## Seed radii

Radii expand to ordered bundle lists — one array per tier, each spreading the previous:

```ts
const ZERO   = ["exchange-rates"]                        // reference data only
const SMALL  = [...ZERO,   "admin-user", "super-admin-user", "admin-target-user",
                           "editor-user", "customer"]
const MEDIUM = [...SMALL,  "order", "booking"]           // the domain spine
const LARGE  = [...MEDIUM, "homepage-builder", "checkout-ready",
                           "traveler-details-checkout", "tour-commerce-basic",
                           "itinerary-templates"]
```

Note `super-admin-user` and `admin-target-user` as *separate* fixtures from `admin-user`. That
falls out of a real need: proving a privileged cross-admin action requires an actor and a distinct
target, and if the seed only has one admin, the agent will silently prove nothing. Seed design is
scenario design.

`l` requires Stripe test keys; the tiers are honest about what they cost.

## A good app-code seam

The best illustration of seam-versus-bleed in the whole build.

Tour scenarios need product-real tour pages, but the CMS is read-only in the sandbox — so seeded
tours have no CMS record. The app renders a published tour with no CMS id through the *normal* page
hierarchy: local DB rows supply title, type, location, rating, and the bookable checkout summary,
while CMS-rich sections (gallery, editorial copy, FAQ, video) are simply absent.

That is product behavior, not a sandbox branch. Content-less tours degrade gracefully in
production too, and CMS-backed tours still fail closed when their query misses. The sandbox got its
fixture by making the app *genuinely more configurable* — no `if (sandbox) return fakeTour()`
anywhere.

Contrast the shape you're avoiding: a product branch that fakes success, which proves the branch
works and nothing else.

## Workspace mode

Stable workspace id derived from the workspace name, worktree path, current branch, and git common
dir. State at `/tmp/acme-sandbox/workspaces/<id>/workspace.json`; run artifacts keep the same
`/tmp/acme-sandbox/runs/<run-id>/run.json` shape as disposable proof runs — one artifact contract,
two modes.

Each workspace holds a lock-protected stable port block for every service. Pretty URLs come from an
OrbStack wildcard `dev.orbstack.domains` label plus that small in-container Host-header proxy
routing `web` / `admin` / `api`:

```text
https://web.<workspace>.acme.local
https://admin.<workspace>.acme.local
https://api.<workspace>.acme.local
```

Raw port URLs stay published as direct backend targets, so the model degrades to plain localhost
where OrbStack isn't available.

A subtlety worth knowing: **raw `127.0.0.1` admin URLs can behave differently from the pretty URL**,
because a request with no workspace label in the Host header can hit an app's local auth fallback.
When both exist, say in the docs which one is authoritative for browser proof.

## The Turbopack datapoint

Measured in-sandbox, seed `l`, six routes, 2026-07-07. Webpack dev on Next 16.2.x held ~6.0–6.5GB
RSS for the server and ~10.6GB container-wide; Turbopack on 16.3.0-preview.5 held ~1.9GB with no
panics. The sandbox had pinned `--webpack` because Turbopack memory-panicked under full-stack load
on 16.2.x; 16.3's cache-eviction work fixed it, and the pin came off.

Two lessons. **A full-stack sandbox is a memory-pressure test** your normal dev server isn't —
eight processes plus a browser in one container surfaces bundler regressions early. And **leave the
escape hatch documented**: `--webpack` on the web task, named in the docs, so the next regression
costs a flag rather than an investigation.
