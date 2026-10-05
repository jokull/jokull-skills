---
name: migrate-to-cf
description: Migrate a Cloudflare Workers project from Wrangler config to the cf CLI and cloudflare.config.ts, preserving deploy parity and never deploying. Use when asked to migrate a repo from wrangler to cf, adopt cloudflare.config.ts, or replace wrangler scripts with cf.
license: MIT
compatibility: Requires Node, the repo's own package manager, and network access to npm. Uses the open-beta `cf` CLI.
---

# Migrate a Wrangler project to `cf`

You are moving one repository from `wrangler.{jsonc,json,toml}` to `cloudflare.config.ts` and the `cf` CLI. The migration is **parity-preserving**: after it, the same Worker deploys with the same name, bindings, routes and triggers. Nothing reaches Cloudflare during this work.

## Guardrails

These hold for the whole run.

- **Dry runs only.** A deploy script you rewrite is a deploy command: run its parts by hand with `--dry-run` and never execute the script itself. Every `cf deploy`, `cf previews deploy`, `cf workers versions create` and `wrangler deploy` carries `--dry-run`. Resource commands are read-only (`list`, `get`).
- **Local branch only.** Commit on the migration branch; leave pushing and PRs to the human.
- **Work in a fresh worktree** off the default branch's HEAD, so the human's working tree and uncommitted changes stay as they are.
- **Values stay where they are.** Account IDs, resource IDs and vars move from the Wrangler config into `cloudflare.config.ts` unchanged. Secrets stay as `bindings.secret()` declarations; their values are never read, printed or copied. Reference repos are for *shape*; take no values from them.
- **`cf` runs from the project**, pinned in `devDependencies` and invoked through the package manager (`pnpm exec cf`, `npx cf`, `bunx cf`). A globally installed `cf` may be absent from your shell.

## Steps

1. **Survey.** List every Wrangler config in the repo (`fd -H -g 'wrangler*.{toml,jsonc,json}' -E node_modules`, which also catches variants such as `wrangler.redirect.jsonc`) and, for each, every place that invokes Wrangler: `package.json` scripts, `.github/workflows`, shell scripts, docs, `AGENTS.md`/`README.md`. Read the repo's `AGENTS.md` or `CLAUDE.md` first and follow it.
   *Done when* you have a list of deploy targets and, per target, a list of every Wrangler invocation with its file and line.

2. **Baseline.** Install dependencies with the repo's package manager and run the existing build and typecheck for each target, before changing anything.
   *Done when* you know which checks pass on the untouched tree. A check that is already red is recorded as pre-existing and is not yours to fix.

3. **Run the codemod.** In each target directory run `cf migrate --dry-run` (through `npx -y cf@latest` the first time), read what it would change, then run it for real. It writes `cloudflare.config.ts` and `wrangler.config.ts`, and pins `cf`. It picks the Vite bundler when `@cloudflare/vite-plugin` is declared and the Wrangler bundler otherwise; override with `--bundler` only with a reason.
   *Done when* every target has a `cloudflare.config.ts` and the install is clean.

4. **Prove parity.** Compare the original Wrangler config with the generated `cloudflare.config.ts` field by field, and fix the new config by hand where the codemod dropped or changed something. Environments (`env.*` blocks) become modes: `defineConfig(({ mode }) => …)`, selected with `--mode`.
   *Done when* every binding, var, route or custom domain, cron or queue trigger, Durable Object and its migrations, compatibility date and flag, asset setting, and observability setting in the original has a row in a parity table saying where it now lives.

5. **Move the invocations.** Replace each Wrangler invocation from step 1 with its `cf` equivalent. Find the command with `cf cli search "<task>"` and confirm flags with that one command's `--help`. Usual mappings: `wrangler dev` → `cf dev`, `wrangler deploy` → `cf deploy`, `wrangler types` → `cf workers types`, `wrangler d1 …` → `cf d1 …`. Framework dev servers (`vite dev`, `astro dev`) stay as they are. Edit CI workflow steps; never trigger them.
   *Done when* every invocation from step 1 is either migrated or listed under "stays on Wrangler" with the reason.

6. **Verify.** For each target: the build passes; `cf build` produces output; `cf deploy --dry-run` (once per mode) is accepted; `cf workers types` output typechecks. Every check that passed in step 2 still passes.
   *Done when* each of those is green, or is reported red with its exact error.

7. **Retire or keep the old config.** Delete the Wrangler config only when step 6 is fully green for that target and nothing from step 5 still reads it. Otherwise keep it and say why.

8. **Commit and report.** One commit per target on the migration branch, then report in the shape below.

## When you hit a wall

`cf` is open beta. A missing feature, an auth prompt, or a toolchain requirement you cannot meet (for example a beta `@cloudflare/vite-plugin` that the framework's adapter rejects) is a **finding**, not something to route around. Stop work on that target, leave its Wrangler setup working, and report the exact error. A partial migration that still deploys the old way beats a complete one that might not deploy.

## Known walls

Seen on `cf@1.0.0-beta.12`; check whether each still holds before relying on it.

- **Vite projects need `@cloudflare/vite-plugin` 2.x beta.** The 1.x plugin ignores `cloudflare.config.ts`, and `cf` refuses to run beside it. TanStack Start and vinext build with the beta. The beta writes `.cloudflare/output/v0` and stops writing `dist/` and the redirected `wrangler.json`, so everything that reads those paths (deploy scripts, CI caches and artifacts, `turbo.json` outputs, tests) moves in the same change, and `wrangler deploy` stops working for that target.
- **`@astrojs/cloudflare` rejects the beta plugin.** An Astro site using the adapter stays on Wrangler.
- **Static sites with their own build script are blocked.** `cf build` detects the framework and runs its build itself, skipping the repo's script, and takes no build-command option. Without a Build Output, `cf deploy --prebuilt` has nothing to deploy.
- **`cf d1` works from a database ID and inline SQL**, where `wrangler d1 execute` takes a name and a file. File-based migration scripts stay on Wrangler, which keeps the Wrangler config alive beside the new one.
- **Several accounts on one login** make `cf deploy` stop at account selection. Carry `accountId` into `cloudflare.config.ts` even when the Wrangler config had none, and say you added it.

## Report

- **Targets**: each one, with status *migrated*, *partial*, or *blocked*.
- **Parity table** per target: original field → where it lives now → verified how.
- **Checks**: each command run and its result, baseline versus after.
- **Stays on Wrangler**: each remaining invocation and why.
- **Needs a human**: CI edits to review, dashboard build commands (Workers Builds stores its own build and deploy commands, which no file in the repo changes), anything unverified.
- **Worktree path and branch**, and the commits made.

## Reference

- **Command discovery.** `cf cli search "<describe the task>"` returns five matches. Keep queries anonymous: describe the action and resource type, with no names, domains or IDs. Then read `--help` for the one command you picked. For API detail, swap the leading `cf` for `cf schema`.
- **Config shape.** `import { bindings, defineConfig, triggers } from "cf/config"`. Bindings are typed constructors (`bindings.text`, `bindings.secret`, `bindings.d1`, `bindings.r2`, `bindings.kv`, `bindings.hyperdrive`, …) under `worker.env`; triggers go under `worker.triggers`.
- **`wrangler.config.ts`** holds what remains Wrangler's concern (`defineWranglerConfig` from `wrangler/experimental-config`), such as `types.generate: false` and the assets directory. Keep it while `wrangler` is still a dependency.
- **Build Output.** With the Vite plugin, the build writes `.cloudflare/output/v0`; deploy that exact output with `cf deploy --prebuilt` and the same `--mode` that built it. Gitignore `.cloudflare/` and generated types.
- **Worked example.** If the person points you at a repo that already migrated, read its `cloudflare.config.ts` files for shape only. It may pin an older beta, so trust `--help` over its flags.
