#!/usr/bin/env python3
"""Extract plausible dialogue for incremental vocabulary coaching."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any


INJECTED_PREFIXES = (
    "# AGENTS.md instructions",
    "# SKILLS.md instructions",
    "<environment_context",
    "<recommended_plugins",
    "<user_instructions",
    "<subagent_notification",
    "<goal",
    "<turn_aborted",
    "<user_action",
    "<context>",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract user/assistant dialogue from Codex CLI session logs."
    )
    parser.add_argument(
        "--codex-home",
        type=Path,
        default=Path.home() / ".codex",
        help="Codex data directory (default: ~/.codex)",
    )
    parser.add_argument(
        "--role",
        choices=("user", "assistant", "both"),
        default="both",
        help="Roles to emit (default: both)",
    )
    parser.add_argument("--since", help="Earliest date, YYYY-MM-DD")
    parser.add_argument("--until", help="Latest date, YYYY-MM-DD")
    parser.add_argument(
        "--max-user-chars",
        type=int,
        default=6000,
        help="Filter longer user messages as likely pasted material (default: 6000)",
    )
    parser.add_argument(
        "--max-assistant-chars",
        type=int,
        default=16000,
        help="Filter longer assistant messages (default: 16000)",
    )
    parser.add_argument(
        "--dedupe",
        choices=("timestamp", "text", "none"),
        default="timestamp",
        help="Deduplication mode (default: timestamp)",
    )
    parser.add_argument(
        "--include-filtered",
        action="store_true",
        help="Emit filtered records with excluded_reason for auditing",
    )
    parser.add_argument(
        "--stats", action="store_true", help="Print extraction counts to stderr"
    )
    return parser.parse_args()


def content_text(content: Any) -> str:
    if not isinstance(content, list):
        return ""
    parts = []
    for item in content:
        if not isinstance(item, dict):
            continue
        if item.get("type") in {"input_text", "output_text", "text"}:
            text = item.get("text")
            if isinstance(text, str):
                parts.append(text)
    return "\n".join(parts)


def is_subagent_meta(payload: dict[str, Any]) -> bool:
    if payload.get("thread_source") == "subagent":
        return True
    source = payload.get("source")
    return isinstance(source, dict) and "subagent" in source


def iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    subagent = False
    session: dict[str, Any] = {"source": str(path)}

    with path.open(encoding="utf-8", errors="replace") as handle:
        for line_number, line in enumerate(handle, start=1):
            is_meta = '"type":"session_meta"' in line
            is_message = (
                '"type":"response_item"' in line and '"type":"message"' in line
            )
            if not is_meta and not is_message:
                continue

            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue

            if item.get("type") == "session_meta":
                payload = item.get("payload") or {}
                if not isinstance(payload, dict):
                    continue
                subagent = is_subagent_meta(payload)
                session.update(
                    {
                        "session_id": payload.get("id") or payload.get("session_id"),
                        "cwd": payload.get("cwd"),
                        "session_timestamp": payload.get("timestamp"),
                    }
                )
                continue

            if subagent or item.get("type") != "response_item":
                continue
            payload = item.get("payload") or {}
            if not isinstance(payload, dict) or payload.get("type") != "message":
                continue
            role = payload.get("role")
            if role not in {"user", "assistant"}:
                continue
            text = content_text(payload.get("content"))
            if not text:
                continue
            yield {
                **session,
                "line": line_number,
                "timestamp": item.get("timestamp"),
                "role": role,
                "text": text,
            }


def iter_legacy_json(path: Path) -> Iterator[dict[str, Any]]:
    try:
        document = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (json.JSONDecodeError, OSError):
        return

    session = document.get("session") or {}
    if not isinstance(session, dict):
        session = {}
    for index, item in enumerate(document.get("items") or []):
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        if role not in {"user", "assistant"}:
            continue
        text = content_text(item.get("content"))
        if not text:
            continue
        yield {
            "source": str(path),
            "line": index + 1,
            "session_id": session.get("id"),
            "cwd": session.get("cwd"),
            "session_timestamp": session.get("timestamp"),
            "timestamp": item.get("timestamp") or session.get("timestamp"),
            "role": role,
            "text": text,
        }


def source_files(codex_home: Path) -> list[Path]:
    sessions = codex_home / "sessions"
    archived = codex_home / "archived_sessions"
    paths = list(sessions.glob("*.json"))
    paths.extend(sessions.glob("**/*.jsonl"))
    paths.extend(archived.glob("*.jsonl"))
    return sorted(set(paths))


def exclusion_reason(record: dict[str, Any], args: argparse.Namespace) -> str | None:
    text = record["text"]
    stripped = text.lstrip()
    if record["role"] == "user" and stripped.startswith(INJECTED_PREFIXES):
        return "injected-wrapper"
    limit = (
        args.max_user_chars
        if record["role"] == "user"
        else args.max_assistant_chars
    )
    if len(text) > limit:
        return "oversized"
    timestamp = record.get("timestamp") or record.get("session_timestamp") or ""
    date = timestamp[:10]
    if args.since and date and date < args.since:
        return "before-since"
    if args.until and date and date > args.until:
        return "after-until"
    if args.role != "both" and record["role"] != args.role:
        return "role"
    return None


def normalized_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


def dedupe_key(record: dict[str, Any], mode: str) -> tuple[str, ...] | None:
    if mode == "none":
        return None
    normalized = normalized_text(record["text"])
    if mode == "text":
        return (record["role"], normalized)
    timestamp = record.get("timestamp") or record.get("session_timestamp") or ""
    return (record["role"], timestamp, normalized)


def main() -> int:
    args = parse_args()
    counts = {"sources": 0, "seen": 0, "emitted": 0, "filtered": 0, "duplicates": 0}
    seen: set[tuple[str, ...]] = set()

    for path in source_files(args.codex_home.expanduser()):
        counts["sources"] += 1
        records = iter_jsonl(path) if path.suffix == ".jsonl" else iter_legacy_json(path)
        for record in records:
            counts["seen"] += 1
            reason = exclusion_reason(record, args)
            key = dedupe_key(record, args.dedupe)
            if not reason and key is not None and key in seen:
                reason = "duplicate"
                counts["duplicates"] += 1
            if key is not None:
                seen.add(key)

            if reason:
                counts["filtered"] += 1
                if not args.include_filtered:
                    continue
                record["excluded_reason"] = reason

            print(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
            counts["emitted"] += 1

    if args.stats:
        print(" ".join(f"{key}={value}" for key, value in counts.items()), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
