---
name: agent-vocabulary-coach
description: Coach developers to incrementally expand their vocabulary into the next useful wave of precise, pragmatic engineering language, using their agent chat logs as evidence. Use when someone wants to communicate more accurately with coding agents, improve planning language, identify their personal engineering lexicon, adopt useful industry concepts, or find crisp terms for recurring ideas they currently describe indirectly.
---

# Agent Vocabulary Coach

Use real agent conversations to help a developer become more accurate and pragmatic. Diagnose their present vocabulary, then introduce a small next wave of language that materially improves how they frame work, constrain scope, explain risk, demand proof, and steer agents.

The audit is a means, not the outcome. The outcome is vocabulary the developer naturally uses in later work.

## Extract the dialogue

Prefer local source logs over memory or conversation summaries. For Codex CLI history, run:

```bash
coach_corpus=$(mktemp)
python3 scripts/extract_codex_dialogue.py \
  --codex-home ~/.codex \
  --dedupe text \
  --stats > "$coach_corpus"
```

Resolve `scripts/extract_codex_dialogue.py` relative to this skill directory. It retains plausible root-session user and assistant messages while filtering system wrappers, tool output, subagent sessions and notifications, injected goals, oversized pasted material, and exact replayed text.

Treat the result as a candidate corpus. Manually inspect every quoted message in its original log context. Replayed prompts, pasted reviews, generated plans, and shell output can survive heuristics. Use timestamps rather than file order when establishing chronology.

If the history uses another format, reproduce the same fields: timestamp, role, source/session, workspace, and unmodified message text.

## Establish the current edge

Sample the oldest human messages before judging agent influence. Separate:

- **Personal language:** recurring metaphors, directive verbs, sentence patterns, and evaluative language used across domains.
- **Owned industry language:** precise engineering terms already used naturally.
- **Emerging language:** terms that appear recently or only with prompting.
- **Unlabeled concepts:** recurring explanations that still lack a stable compact name.

Do not confuse frequency with distinctiveness. Common terms such as `invariant`, `idempotent`, `source of truth`, `first-class`, and `semantic` may be useful without being part of the developer's personal communication fingerprint.

For an agent-influence claim, require an assistant use before a verified human-authored use and preferably later reuse in another context. Label it a strong adoption trail, plausible pickup, or already theirs. Chronology does not prove where a word was learned.

## Choose the next useful wave

Introduce 3–5 terms per coaching pass. Favor terms that are adjacent to the developer's existing mental models and immediately usable in real prompts.

A candidate earns a place only when it:

1. names a recurring concept visible in the corpus;
2. reduces a paragraph to a precise shared label;
3. changes what an agent would do, constrain, inspect, or prove;
4. improves reasoning about scope, boundaries, failure, lifecycle, ownership, migration, or evidence;
5. is not already part of the developer's active vocabulary;
6. is established engineering language, or is clearly labeled as a tailored working term.

Apply the **steering test**: rewrite one of the developer's actual prompts with the candidate term. If the term does not make the requested action or constraint more exact, omit it.

Avoid vocabulary theater. Reject terms that are merely academic, fashionable, synonymous with language the developer already prefers, or likely to make prompts less legible. The goal is pragmatic compression, not sounding technical.

## Verify that a term is actually missing

Before proposing a term:

1. search exact spelling, inflections, hyphenation, and close variants;
2. inspect whether the developer already uses an equivalent phrase;
3. verify the proposed technical sense, not only the spelling;
4. check multiple dates and projects;
5. reject the suggestion if their existing phrase works better.

For example, do not propose `escalation ladder` when the developer already uses it. `Abstraction leakage` may be useful when they repeatedly describe proof machinery or internal representations “bleeding into app land,” if the formal term itself is absent or not yet active.

## Teach through the developer's own work

For every term in the active wave, provide:

- **Term:** the exact phrase to adopt.
- **Meaning here:** a plain definition tailored to their systems.
- **Use it when:** the recognizable situation that should trigger it.
- **Do not use it for:** a nearby concept it should not blur into.
- **Before → after:** one real prompt excerpt rewritten in their voice.
- **Steering delta:** what the agent can now infer or do more accurately.

Prefer one strong example over a taxonomy. Do not assign flashcards or artificial exercises unless requested. Encourage adoption by reusing the term naturally when the corresponding situation next appears.

## Make improvement incremental

On later passes, search for natural human reuse of previously introduced terms:

- **Active:** introduced but not yet used independently.
- **Adopting:** used naturally once in a relevant prompt.
- **Graduated:** reused accurately across dates or contexts.
- **Rejected:** did not fit, duplicated existing language, or made communication worse.

When the user wants ongoing tracking, maintain `~/.local/state/agent-vocabulary-coach/lexicon.md`. Seed it from `assets/lexicon-template.md`; never store personal log excerpts inside the shareable skill directory. Update the ledger only from verified human messages.

Replace graduated terms with the next adjacent wave. Do not keep expanding faster than the developer is adopting.

## Use an independent pass

When subagents are available, give one a blind audit. Pass only the raw log location, filtering requirements, and these questions:

1. What language does this developer favor beyond normal industry usage?
2. What recurring concepts lack a crisp name that would improve agent steering?
3. Which 3–5 candidates form the most useful next wave?

Do not pass candidate words, earlier conclusions, or expected answers. Ask for dated evidence, cross-project checks, and a distinction between strong evidence and interpretation. Synthesize after the blind result returns.

## Report the coaching pass

Lead with the developer's communication fingerprint, but spend most of the response on forward movement.

Include:

1. a concise description of current strengths;
2. terms already owned or recently graduated;
3. the 3–5-term active wave with before/after rewrites and steering deltas;
4. terms considered but rejected, when that prevents obvious repetition;
5. a methodology caveat covering filtering, duplication, and causality.

If asked for a character-limited summary, draft the full coaching pass first, then compress and verify the exact character count.
