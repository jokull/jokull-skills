# jokull-skills

Agent skills, source of truth. `~/.agents/skills/` and `~/.claude/skills/` hold symlinks into
`skills/` here — edits are live, and every change is a real diff. Never edit a skill through the
symlink path as if it were a separate copy; it is this repo.

## Format

Skills follow the [Agent Skills standard](https://agentskills.io/specification). These live in
`~/.agents/`, so they must work in Codex and other harnesses too.

**Use only the six standard frontmatter fields:** `name`, `description` (both required), `license`,
`compatibility`, `metadata`, `allowed-tools`.

**Do not use Claude Code's extensions** — `disable-model-invocation`, `user-invocable`,
`context: fork`, `agent`, `model`, `effort`, `argument-hint`, `arguments`, `disallowed-tools`,
`paths`, `hooks`, `when_to_use`. They are silently ignored elsewhere, so a skill that depends on one
behaves differently depending on which agent loaded it. If a skill genuinely needs one, that is a
decision to make on purpose, not by reflex.

Constraints: `name` is 1–64 chars, lowercase alphanumeric and single hyphens, must match the
directory name. `description` is ≤1024 chars. `compatibility` is ≤500 chars and only belongs on
skills with real environment requirements.

## Conventions

- **Description is a routing rule, not a summary.** It is the only thing an agent sees when
  deciding whether to load the skill. Lead with the use case, then the trigger phrases.
- **One job per skill.** The body loads whole; a bloated skill taxes every invocation.
- **Under 500 lines.** Push detail into `references/`, one level deep, and say explicitly when to
  read it.
- **Deterministic work goes in `scripts/`,** not prose describing the steps.
- **No human-facing files inside a skill directory** — no README, no CHANGELOG. Skills are for
  agents; every file is potential context. Human docs belong at the repo root.
- **No machine state in the repo.** Anything naming real paths, databases, or hosts is local state:
  keep it under `~/.local/state/<skill>/` and ship a template in `assets/`. See `skills/mole`.
- **Worked examples beat abstract rules.**

## Adding a skill

1. `skills/<name>/SKILL.md` with standard frontmatter.
2. Add a row to the README table.
3. `scripts/link-skills.sh` — idempotent, safe to re-run.

The script refuses to overwrite a real directory at either link target, so an un-committed skill
can never be clobbered. Move it into `skills/` first.
