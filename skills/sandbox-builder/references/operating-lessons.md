# Operating lessons

What goes wrong after the sandbox works. These are the failure modes that show up once agents use
it daily — worth designing against early, and worth writing into the sandbox's own usage docs
(phase 8).

## False proof

The sandbox's whole value is that its evidence is trustworthy. Every lesson here is really the same
lesson.

**A screenshot alone is not evidence.** Pair browser output with at least one durable invariant: URL
state, a DB row, a mock request log, the email outbox, a recorded error, absence of console/network
errors, or decoded media. A screenshot proves a page rendered; it does not prove the system did
anything.

**A shim proves the route, not the integration.** If the browser payment element is shimmed, a
successful-looking checkout page proves the route renders — it proves nothing about payment
confirmation. Prove the integration through the server path, a signed webhook fixture, or a driver
that leaves the third party real. Make every active shim visible in `status` so nobody mistakes
shimmed for covered.

**A redirect is not the destination.** Flows that can bounce to an interstitial (pricing changed,
session expired, consent) will eventually produce a screenshot of the wrong page labeled as the
right one. Require proof that the *final* URL is the intended step, plus a state assertion from the
page itself.

**Name what a scenario does not cover.** If the run disabled fraud checks or mocked a supplier, the
summary says so. An agent that reports "checkout works" after mocking the payment provider has
produced a confident lie, and a reviewer cannot tell from the artifact alone.

## Staleness

**Trust a live probe, not a written file.** Any metadata file — ports, run ids, workspace state —
can describe a previous run. `status` should resolve the current run *and* probe the container,
reporting `ok: false` with a reason and a non-zero exit when the container has exited or been
removed. A green status must mean the thing is actually running.

**Readiness is a gate, not a guess.** Provide a `wait` command that returns only when the browser,
API, and required services are genuinely safe to exercise, and have workspace startup call it.
"Container started" and "app ready" are different events, and the gap between them is where flaky
proof comes from.

**A slow first page load is usually compilation, not a hang.** Check supervisor status before
rerunning browser work or declaring a timeout.

## Cost

The expensive part is the first boot. Everything after should be warm — work with the caching model
instead of around it.

- **Reuse one sandbox across related attempts.** Do not `down`/`up` between checks; restarting
  throws away nothing but time.
- **Warm restarts keep compiler caches** and skip installs when dependencies are unchanged. Fresh
  worktrees still benefit from a machine-shared package store and build cache.
- **Give stale caches an escape hatch that is not a rebuild.** A cache-clear env flag on the normal
  `up` path beats reaching for a full image rebuild; reserve rebuilds for changes to the container's
  base tooling.
- **Automate janitor duties.** Teardown should prune volumes of deleted worktrees, stopped
  containers, and stale image generations. Unbounded per-worktree volumes accumulate fast and
  silently — hundreds of volumes and tens of gigabytes within weeks. Manual cleanup by hand is
  error-prone; a `prune --dry-run` is for diagnosing, not for routine use.

## Scope

**Do not start a sandbox just because the worktree supports one.** Code review, docs, dependency
bumps, and any non-runtime validation should stay outside it. Booting a container to read a diff is
pure latency, and habitual over-use trains agents to reach for it reflexively.

**Do not let it drift into an E2E suite.** The pressure to commit "just one" browser test is
constant, and it ends with a brittle suite nobody trusts and a sandbox nobody uses. Scenario smoke
commands live with the harness; product assertions live in the product's own tests.

**Infer routes from source, not a registry.** A hand-maintained list of app paths goes stale on the
first refactor and then lies to every agent that reads it.
