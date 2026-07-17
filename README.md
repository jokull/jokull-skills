# jokull-skills

Agent skills I actually use, in [Agent Skills](https://agentskills.io) format — portable across
Claude Code, Codex, and other harnesses that read `~/.agents/skills/`.

| Skill | What it's for |
|---|---|
| [`roundtable`](skills/roundtable/SKILL.md) | Adversarial council review of a plan or spec. Independent specialist seats, run in parallel, synthesized into a patched artifact. |
| [`mole`](skills/mole/SKILL.md) | Judgment and memory on top of the [`mo`](https://github.com/tw93/mole) Mac cleanup CLI. Dry-run first, curate, remember the verdicts. |

## Install

```bash
git clone https://github.com/jokull/jokull-skills.git
cd jokull-skills
./scripts/link-skills.sh
```

Skills are symlinked into `~/.agents/skills/` and `~/.claude/skills/`, so this repo stays the
source of truth — a `git pull` updates the installed skills, and edits are live.

## Notes

**`roundtable`** pairs with `/grill-me`: grill your idea into existence, then run it through the
roundtable to bulletproof it. Descended from the `roundtable-review` skill I wrote in a work
monorepo; the change here is that seats run as genuinely independent parallel subagents instead of
sequential passes in one context, so the critiques can't anchor on each other.

**`mole`** keeps its memory at `~/.local/state/mole-skill/memory.md`, outside the skill directory
on purpose — the skill is shareable, but the verdicts name one machine's repos and databases. It
seeds from a template on first run.

## Conventions

See [CLAUDE.md](CLAUDE.md).
