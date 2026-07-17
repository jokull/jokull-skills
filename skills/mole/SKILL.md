---
name: mole
description: "Wraps the `mo` (mole) Mac cleanup CLI with judgment, memory, and follow-through: runs dry-run previews, curates them against remembered safe/risky verdicts for this machine, recalls past sessions and past user decisions, and brainstorms prune targets mole itself doesn't scan. Use when the user asks to free up disk space, clean the Mac, run mole or mo, or prune old project build artifacts."
compatibility: Requires macOS and the `mo` CLI (github.com/tw93/mole). Install with `brew install tw93/tap/mole`.
license: MIT
metadata:
  author: jokull
  version: "1.0"
---

# Mole

`mo` finds and deletes things. This skill is the judgment layer on top: which of those things are
worth deleting *on this machine*, and a memory of what happened so each run starts smarter than the
last.

Never run a real (non-dry-run) command without the user approving that specific bucket first.
Dry-runs are free.

## Memory

Machine-specific verdicts live at **`~/.local/state/mole-skill/memory.md`** — deliberately outside
this skill directory, because the skill is shareable and the verdicts are not: they name this
machine's databases, repos, and directories.

Read it at the start of every session. If it does not exist, seed it from
`assets/memory-template.md` and tell the user you started a fresh log.

Mole's own history and logs are ground truth for *what happened*. `memory.md` is ground truth for
*why* — the judgment calls that never appear in mole's output.

## Command reference (avoid re-running `mo --help`)

```
mo status [-json]               Health snapshot: disk free, memory, running procs
mo analyze [-json] [path]       Disk usage breakdown (defaults to whole disk)
mo clean --dry-run              Caches/logs/temp/app-leftovers preview
mo purge --dry-run              Old project build artifacts (node_modules, target/, .venv, ...)
mo installer --dry-run          Stray .dmg/.pkg/.iso/.xip/.zip installers
mo uninstall --list             Apps mole knows how to fully remove
mo uninstall --dry-run APP      Preview one app removal (leftovers + binary)
mo history --json [--limit N]   Mole's run log — ground truth for what actually happened
```

Real runs drop `--dry-run`. `mo clean` needs `sudo -v` first for the system-cache portion — ask,
never sudo silently.

State mole already keeps (read it, don't guess):

- `~/.config/mole/whitelist` — paths mole will never touch
- `~/.config/mole/purge_paths` — directories `mo purge` scans
- `~/.config/mole/clean-list.txt` — last `mo clean` preview, path by path
- `~/.config/mole/operations.log`, `mole.log` — raw logs

## Workflow

1. **Orient.** Run `mo status` and `mo history --json --limit 10`. Note free space and whether a
   session ran recently — don't re-suggest what was just cleaned.

2. **Read memory** at `~/.local/state/mole-skill/memory.md`: prior verdicts, space-freed history,
   standing brainstorm list.

3. **Dry-run sweep.** `mo clean --dry-run`, `mo purge --dry-run`, and `mo installer --dry-run`
   unless memory says otherwise. Add `mo analyze -json` or `mo uninstall --list` only if the user
   wants a deeper look.

4. **Curate — never dump raw output.** Cross-reference every line against memory and judgment:
   - Package-manager caches (npm/pnpm/bun/pip/uv/go/corepack) → safe, regenerate on next install.
   - Browser caches → safe, costs one slow reload.
   - `mo purge` hits inside active repos → verify first (`git status --porcelain`, recent mtime) or
     ask. A `node_modules` lost mid-feature-branch is a real cost.
   - Anything whitelisted or previously marked "keep" → don't re-suggest; note it was skipped.
   - Big single items (model caches, JetBrains caches, Docker data, browser profiles) → report the
     size, recommend against unless the user pushes. These are usually whitelisted for a reason.

   Present one prioritized list: item, size, verdict (safe / verify / skip), one-line reason.

5. **Ask before acting.** Explicit go-ahead per bucket — clean, purge, installer, or a named
   uninstall. Never pass `--permanent`, and never touch `mo uninstall`/`mo remove` unless the user
   named the exact app.

6. **Brainstorm past mole's scope.** Mole scans only what it was coded to scan. Suggest 2–3
   concrete manual checks it misses — Docker images and volumes, Xcode DerivedData and simulator
   runtimes, large `~/Downloads` files, Photos originals, Time Machine local snapshots, old VM and
   disk images, stale git worktrees, bloated `.git` objects in dormant repos. Check memory first so
   you don't re-suggest something already declined.

7. **Update memory** after any real run or brainstorm: date, what ran, GB freed (take the number
   from `mo history --json`, don't estimate), new keep/skip verdicts, and the brainstorm list with
   items marked actioned / declined / still-open.

Prune verdicts that have gone stale. A remembered "safe to delete" pointing at a path that now
holds something real is worse than no memory at all.
