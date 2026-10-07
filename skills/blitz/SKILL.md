---
name: blitz
description: "Clears a backlog in one push: inventories the user's open PRs and issues, grills the user for the product decisions only they can make, decides the engineering ones, then runs worker subagents and lands the work as a few large roll-up PRs, closing or absorbing what is stale. Use only when the user asks to blitz a backlog, or to sweep their open PRs and issues into roll-up PRs with workers."
compatibility: Requires a harness that runs subagents in parallel with a model choice per agent, git worktrees, and a forge CLI such as gh.
license: MIT
metadata:
  author: jokull
  version: "1.0"
---

# Blitz

Turn a backlog of open PRs and issues into a few large roll-up PRs, landed. You are the
orchestrator. The user supplies product decisions, you supply every engineering decision, workers
supply the edits.

The repository's own instructions (its `AGENTS.md`, its publish and merge skills, its test policy)
own every command and gate. This skill owns the shape of the push.

## 1. Inventory

List every open PR the user authored and every open issue in the user's area of the codebase. Area
means code ownership, not issue author: include a teammate's issue about the user's code, exclude
the user's own issue about a teammate's code. Reuse an inventory already in the conversation.

Give each item exactly one **disposition**, from evidence you read (checks, commits behind main,
linked PRs, comment trail), not from its labels:

| Disposition | Meaning |
| --- | --- |
| `land` | A PR that is close. Update it, fix it, merge it as it is. |
| `absorb` | A stale PR or a ready issue. Redo the work in a wave, then close the original with a link. |
| `close` | Obsolete, duplicate, fixed elsewhere, or outside the user's area. |
| `hold` | Blocked on something outside this push. Name the blocker. |
| `decide` | Waits on a product decision from the user. |

Done when every item has one disposition, and every `close` and `hold` carries its evidence.

## 2. Harvest

Load the `grilling` skill (`/grill-me`) and run it over the `decide` items; where it is absent,
interview in rounds, each round the questions whose prerequisites are settled. Put only **product decisions** to
the user: what the product should do, what is still wanted, who owns a boundary item. Each question
carries your recommended answer.

Coding and architecture decisions are yours. Make them, and report them beside the grill round as a
**decision log**: one line each, the choice and its reason, so the user overrules a line instead of
answering a question. An engineering decision enters the grill only as a one-way door: data loss, a
public contract, or money and security at the design level.

Show the full disposition table with the first round. The user's confirmation of that table is the
consent for every close and absorb that follows.

Done when no item is `decide` and the user has confirmed the table.

## 3. Plan the waves

Group the `absorb` items into **waves**. One wave is one roll-up PR, sized large: a wave holds every
item of one area that one reviewer can hold in mind, each item as its own commit. Items that touch
the same files share a wave. An item gets a PR of its own only for a reason you can state: a
migration, a one-way door, or a change that must revert alone.

Cut each wave into **slices** with exclusive file ownership, one worker per slice.

Consult the **advisor**, the strongest model available (Fable, as an advisor tool or a read-only
subagent), for sequencing across waves, for a
design with more than one plausible shape, and for the root cause of a hard bug. The advisor plans
and diagnoses; a worker implements what it hands back.

Order: `land` PRs first, then waves by risk, lowest first. Keep few roll-ups open at once; a wave
opens when an earlier one has landed.

Done when every `absorb` item sits in exactly one slice and no file has two owners.

## 4. Dispatch workers

Launch all workers of a wave in one message, each on the worker model (Sonnet), each in its own
worktree on a branch cut from the wave branch. A brief holds:

- **What** — the items with their acceptance, one commit per item.
- **Where** — the files and directories the worker owns.
- **How** — the patterns to copy and the repo skills that apply.
- **Decisions** — the product answers and decision-log lines for its items, as settled facts.
- **Checks** — surgical only, below.
- **Return** — commits, each check with its output, and anything left undone. Commit on the branch;
  the orchestrator pushes and opens the PR.

**Surgical** checks are the linter and type check on the changed files alone (for example
`oxlint --type-aware --type-check <files>`), plus at most two test files that assert the change.
Builds, package-wide type checks, and whole test lanes belong to hosted CI on the roll-up. Heavy
commands run one at a time across the machine through one shared lock (`lockf` on macOS, `flock` on
Linux); tell workers that a wait at the lock is normal.

Done when every worker has returned and you have read each diff.

## 5. Roll up

Merge the worker branches into the wave branch. Read the combined diff and run one independent
review on it; send each finding back to the worker that owns the file. Open one PR whose body lists
every item with its closing reference and every absorbed PR. Hosted CI on this PR is the full check.

When your confidence in a roll-up is the blocker, raise it with another review pass and a fix; the
user is asked only for what you cannot produce.

Done when the roll-up is open and every wave item is in its diff, or back in the inventory with a
reason.

## 6. Land and close

Follow each roll-up through review and CI to merge with the repo's merge workflow, then to
production. After the merge, close each absorbed PR with a link to the roll-up, and close each
`close` item with its evidence.

Finish with a report: landed, closed, held with blockers, and the decision log.
