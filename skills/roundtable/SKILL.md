---
name: roundtable
description: "Runs a multi-perspective adversarial critique and synthesis pass over a plan, spec, or architecture proposal. Convenes a council of specialist seats — each an independent subagent that cannot see the others — then synthesizes their critiques into a patched artifact. Use when the user asks for a roundtable, council, swarm, adversarial review, downstream impact check, red team, or specialist feedback before implementation; when a design needs stress-testing after requirements are settled; or when the user wants genuine criticism of a plan or piece of writing instead of agreement."
compatibility: Requires an agent harness that can run read-only subagents in parallel. Without one, independence is lost and the skill degrades to a single-context review.
license: MIT
metadata:
  author: jokull
  version: "1.0"
---

# Roundtable

Use after requirements are settled and before implementation, when a proposal needs sharper
product, architecture, operations, or downstream-impact thinking.

`/grill-me` establishes what *the user* thinks. This skill harvests what *other perspectives*
think. Do not re-run the grill: the user has already decided what they want built.

## The rule that makes this work

**Every seat runs as its own subagent, and all seats launch in a single message so they run
concurrently.** A seat must never see another seat's critique.

This is not a performance optimization — it is the entire premise. Running the seats as sequential
passes in one context means seat five reads seats one through four and anchors on them. That
produces an echo chamber wearing several hats, which is the exact failure this skill exists to
prevent. If the harness cannot spawn parallel subagents, say so plainly in the output rather than
silently degrading.

Seats are critics, not implementers. Every seat prompt must forbid modifying files.

## Workflow

### 1. Establish the proposal

Read the spec, plan, branch diff, and the code or docs the proposal touches. If the user asked for
external inspiration or wants current product behavior checked, browse primary sources and keep the
links.

Write down the **settled assumptions** — decisions already made that seats may not relitigate.
Without this, seats waste their turn arguing the premise. If the proposal is too vague to critique,
stop and say so; a roundtable over a mush of intentions produces mush.

### 2. Choose seats

Pick the 3–6 seats that fit *this* problem. Convening all of them every time is noise, and a seat
with nothing to say will invent something rather than pass.

- **Codebase consistency** — existing patterns, ownership boundaries, naming, generated files, package seams.
- **Simplifier** — tables, states, abstractions, and duplicate concepts that collapse without losing behavior.
- **Product/UX** — labels, trust, empty/loading/error states, editor vs. public surfaces, user expectations.
- **Reliability/operations** — queues, retries, idempotency, leases, observability, cost, support and debug flows.
- **Data/SQL** — schema shape, constraints, indexes, migrations, query plans, deletion semantics.
- **Prompt/AI** — task framing, structured output, validation, repair, protected tokens, privacy and logging.
- **SEO/external research** — current market behavior, search and indexing risk, standards, policy constraints.
- **Downstream integrations** — copied data, caches, APIs, analytics, admin tools, worker bindings.

Add a seat the list doesn't cover when the problem calls for it (security, accessibility, i18n,
migration sequencing, pricing).

### 3. Run the critiques in parallel

Launch every seat in **one message, one subagent each**. In Claude Code that is the Agent tool with
`general-purpose`; use whatever read-only subagent the harness offers elsewhere.

Give each seat the same brief, varying only the lens:

> You are the **{seat}** seat on an adversarial review of the proposal below. Critique it from your
> lens only — other seats cover theirs, and you cannot see their work.
>
> **Proposal:** {inline text, or exact paths to read}
> **Settled — do not relitigate:** {assumptions}
>
> Read whatever code, docs, or sources you need. **Do not modify any file.** Find the failure mode
> a smart reviewer would miss, not the one on the surface. If your lens genuinely has no serious
> concern here, say so and stop — a manufactured objection is worse than silence.
>
> Return exactly:
> - **Strongest concern** — one sentence
> - **Downstream impact** — what concretely breaks, and where
> - **Recommendation** — the specific change
> - **Confidence** — high / medium / low
> - **Evidence** — `file:line` refs, or source links

Include the proposal text inline when it is short enough. Seats that each re-derive the proposal
from scattered files critique slightly different proposals.

### 4. Commune

Synthesize; do not concatenate. Eight critiques pasted end to end is not a roundtable, it is a
mailing list. Sort every point into:

- **Accept now**
- **Accept, narrower scope**
- **Defer** — with the trigger that would revive it
- **Reject** — with the reason

Weight toward changes that remove ambiguity, prevent misleading UX, or make failure modes
observable. Do not let speculative elegance overrule a settled product constraint. When two seats
contradict each other, say so and pick — an unresolved contradiction handed back to the user is
work you were supposed to do.

### 5. Pursue live threads

If a critique is high-leverage but thin on evidence, spend one focused code or web exploration
confirming it before synthesis. If a critique is weak, dismiss it plainly — "the ops seat wanted a
queue; the volume is 40 writes a day" is a complete rebuttal.

### 6. Patch the artifact

Update the spec or plan so accepted decisions land where the implementer will actually see them.
Then scan for contradictions the patch just created and fix them.

## Output

Keep it short. The council was the work; the report is not.

- What the roundtable changed
- What was rejected or scoped down, and why
- Contradiction and validation scans performed
- Links to updated files and any external sources used

Name the seats that found nothing. A silent seat is a real result — it means that lens is clean.
