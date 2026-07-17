# Mole Skill Memory

Machine-specific log for the `mole` skill. Lives at `~/.local/state/mole-skill/memory.md`, outside
the skill directory, because the skill is shareable and this is not — it names real paths, repos,
and databases on one machine.

Kept separate from Claude's general auto-memory because it is high-churn and tool-specific. Update
after every real (non-dry-run) session, and whenever a new brainstorm idea comes up.

## Known verdicts (don't re-suggest without new info)

Record judgment calls here, not sizes — mole reports sizes. Each entry: what, the verdict
(**always safe** / **never without confirmation** / **skip**), and the reason that makes the
verdict hold. Re-check any verdict whose path may have changed meaning since it was written.

<!-- Example shape:
- `~/some/cache/path` — **always safe to prune**. Regenerates on next build; never holds real data.
- `foo_postgres_data` — **never touch without per-volume confirmation**. Live local dev database.
- `mo <subcommand>` — **doesn't work headless**, hangs with no TTY. Do X instead.
-->

## Session log

One line per real session: date, what ran, GB freed (from `mo history --json`), free space before
and after.

## Standing brainstorm (manual, outside mole's scope)

Ideas mole can't surface on its own. Mark each **actioned** / **declined** / **still-open**, so a
future session doesn't re-pitch something already settled.
