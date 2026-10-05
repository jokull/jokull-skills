---
name: memory-retro
description: Audit an agent's saved memories for stale facts, duplicates and contradictions, then reconcile them with the user one decision at a time. Use when asked to clean up, fix, audit or reconcile memory, when two memories conflict, when a recalled memory turned out wrong, or after a retro changed instruction files that memories also describe.
license: MIT
---

# Memory retro

A retro for what the agent *remembers*, where a session retro covers how it *worked*. You are reconciling a memory store against the **ground truth**: the files, commands and instruction files that exist right now. A memory is a claim; the environment is the evidence; the user breaks ties the evidence cannot.

## Steps

1. **Locate the store.** Default to the current project's auto-memory directory (Claude Code: `~/.claude/projects/<project>/memory/`, indexed by `MEMORY.md`). If the user names another project or "all projects", take those directories instead. Other harnesses keep memory elsewhere; ask where if you cannot find it.
   *Done when* you have the list of memory files in scope and have read every one in full, plus the index.

2. **Check each memory against ground truth.** For every factual claim a memory makes (a path, a command, a hostname, a tool, a setting, a file's contents), look at the thing itself. Give each memory one verdict:
   - **current**: every checkable claim holds.
   - **stale**: a claim no longer holds. Record what is true now.
   - **unverifiable**: it records a preference or decision with nothing in the environment to check it against.
   - **redundant**: an instruction file (`AGENTS.md`, `CLAUDE.md`, a rule, a skill) now states the same thing, so the memory is a second copy.
   *Done when* every memory in scope has a verdict and, for stale ones, the evidence.

3. **Find the conflicts.** Compare memories with each other and with the instruction files that load in the same sessions. A **conflict** is two sources that would steer the agent in different directions on the same question. A **duplicate** is two memories carrying one meaning.
   *Done when* every pair is either cleared or listed with both texts side by side.

4. **Resolve what evidence settles.** Fix these without asking, and list them afterwards:
   - a stale claim whose replacement you verified (rewrite the memory to the current fact);
   - a duplicate (merge into the better-named file, delete the other);
   - a broken `[[link]]` or an index line whose file is gone.
   Timestamps and a memory's own wording about itself are hints, never proof of which side is current.

5. **Ask the user about the rest, one decision at a time.** For each conflict or doubtful memory that evidence does not settle, show both sides and what you checked, give your recommendation, and wait for the answer before the next question. Order by how much wrong behaviour the conflict could cause. The usual outcomes: keep one side, merge into a new wording, promote the memory into an instruction file, or delete it.
   *Done when* no listed conflict is unanswered. A user who stops early leaves the remainder listed, untouched.

6. **Apply and rebuild the index.** Make the agreed edits. Each memory holds one fact and keeps its frontmatter; relative dates become absolute. Rewrite the index so it has exactly one line per remaining file and nothing else.
   *Done when* every file in the directory has an index line, every index line has a file, and no memory contradicts another or a loaded instruction file.

7. **Report.** What was fixed on evidence, what the user decided, what was deleted, and what stays unverifiable.

## Reference

- **Promote, don't hoard.** A memory that every session needs belongs in an instruction file, where it is reviewed and versioned. A memory earns its place by being true, specific, and absent from everywhere else.
- **Redundant is a deletion candidate, not an automatic one.** An instruction file that only loads in some directories does not cover a memory that loads in others. Check where each actually loads before calling it a copy.
- **Deleting is reversible only if you say what you deleted.** Quote each deleted memory in the report.
- **Scope creep.** Fixing an instruction file because a memory exposed a mistake in it is a separate change: name it in the report and ask before editing.
