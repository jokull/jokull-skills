---
name: gh-pr-image
description: Embeds local screenshots, GIFs, visual diffs, or proof images into a GitHub PR body or comment without committing image artifacts to the repo, by hosting them as release assets on a per-PR prerelease. Use when a PR needs visual proof from local files, when `gh pr edit` or `gh issue comment` won't upload an image, or when a temporary image host would expire.
compatibility: Requires the `gh` CLI, authenticated, with write access to the target repository.
license: MIT
metadata:
  author: jokull
  version: "1.0"
---

# GitHub PR Images

Use GitHub release assets as a durable image host for PR markdown. `gh pr edit`,
`gh issue comment`, and `gh gist create` do not upload local PNG/GIF files into
PR markdown. Temporary file hosts expire or disappear.

This is the preferred CLI-only path for private repos: the image renders for
people who can read the repo, while unauthenticated direct requests may return
`404`.

## Upload

Create or reuse one prerelease per PR:

```bash
PR_NUMBER=123          # the PR you are attaching proof to
TAG="pr-${PR_NUMBER}-proof-assets"
IMAGE="/absolute/or/relative/path/to/screenshot.png"
ASSET_NAME="$(basename "$IMAGE")"
UPLOAD_IMAGE="/tmp/$ASSET_NAME"
REPO="$(gh repo view --json nameWithOwner --jq .nameWithOwner)"
TARGET="$(git rev-parse HEAD)"

gh release view "$TAG" >/dev/null 2>&1 || gh release create "$TAG" \
  --target "$TARGET" \
  --title "PR #${PR_NUMBER} proof assets" \
  --notes "Image assets for PR #${PR_NUMBER}." \
  --prerelease \
  --latest=false

cp "$IMAGE" "$UPLOAD_IMAGE"
gh release upload "$TAG" "$UPLOAD_IMAGE" --clobber

IMAGE_URL="$(gh api "repos/$REPO/releases/tags/$TAG" \
  --jq ".assets[] | select(.name==\"$ASSET_NAME\") | .browser_download_url")"
printf '![proof](%s)\n' "$IMAGE_URL"
```

Use unique `ASSET_NAME` values when uploading multiple images to the same tag,
for example `<run-id>-before.png` and `<run-id>-after.png`. Do not rely on
`path#label` to rename the release asset; GitHub treats that as a display label,
while the asset URL still uses the uploaded file's basename.

## PR Comment

```bash
cat > /tmp/pr-proof.md <<EOF
## Proof

![proof screenshot]($IMAGE_URL)

- Run: \`<run-id>\`
- Local artifact: \`<path-to-local-image>\`
- Invariants: \`<short proof facts>\`
EOF

gh issue comment "$PR_NUMBER" --body-file /tmp/pr-proof.md
```

To update the last comment from the same GitHub user:

```bash
gh issue comment "$PR_NUMBER" --edit-last --body-file /tmp/pr-proof.md
```

## PR Body

Prefer comments for iterative proof. If the final PR body should include the
image, read the existing body first and write a full replacement:

```bash
gh pr view "$PR_NUMBER" --json body --jq .body > /tmp/pr-body.md
# edit /tmp/pr-body.md
gh pr edit "$PR_NUMBER" --body-file /tmp/pr-body.md
```

## Cleanup

Release assets can stay until the PR is merged. To remove the image host later:

```bash
gh release delete "$TAG" --yes --cleanup-tag
```
