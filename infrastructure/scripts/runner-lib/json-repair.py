#!/usr/bin/env python3
"""JSON Auto-Repair Worker — Shared Infrastructure (runner-lib).

Two-tier repair strategy:
  1. json_repair (pip) — 3M+ downloads/month, covers 15+ error types
  2. Custom fallback — covers the 6 most common LLM errors if pip unavailable

Deterministic — same broken input always produces same repaired output.
Emits metrics to stdout as JSON lines for pipeline integration.

Usage:
    python3 json-repair.py --file path/to/broken.json [--dry-run]
    python3 json-repair.py --dir path/to/output_dir [--dry-run]

References:
    AN_KE_021: Repair Layer Between Generator and Validator
    H9: Bug de Produção → Módulo Shared
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

# ── Tier 1: Try pip json_repair (robust, battle-tested) ──────────────
try:
    from json_repair import repair_json as pip_repair_json  # type: ignore[import-untyped]

    HAS_PIP_REPAIR = True
except ImportError:
    HAS_PIP_REPAIR = False

# ── Metrics accumulator ──────────────────────────────────────────────
_metrics: dict[str, int] = {
    "files_scanned": 0,
    "files_already_valid": 0,
    "files_repaired": 0,
    "files_unrepaired": 0,
    "repairs_pip": 0,
    "repairs_custom": 0,
}


def is_json_valid(content: str) -> bool:
    try:
        json.loads(content)
        return True
    except (json.JSONDecodeError, ValueError):
        return False


# ── Tier 1: pip json_repair ──────────────────────────────────────────
def repair_with_pip(content: str) -> tuple[str, list[str]]:
    """Use pip json_repair library. Returns (repaired, fixes)."""
    if not HAS_PIP_REPAIR:
        return content, []

    # Strip markdown fences first (pip lib doesn't handle these)
    stripped, pre_fixes = _strip_markdown_fences(content)

    repaired = pip_repair_json(stripped, return_objects=False)  # type: ignore[call-overload]
    if isinstance(repaired, str) and is_json_valid(repaired) and repaired != stripped:
        return repaired, pre_fixes + ["pip:json_repair"]
    elif isinstance(repaired, str) and is_json_valid(repaired):
        return repaired, pre_fixes  # fences were the only issue
    return content, []


# ── Tier 2: Custom fallback ──────────────────────────────────────────
def repair_with_custom(content: str) -> tuple[str, list[str]]:
    """Custom regex-based repair for the 6 most common LLM JSON errors."""
    fixes: list[str] = []

    # Fix 0: Strip markdown fences
    content, fence_fixes = _strip_markdown_fences(content)
    fixes.extend(fence_fixes)

    # Fix 0b: Strip leading/trailing non-JSON text
    first_brace = -1
    for i, c in enumerate(content):
        if c in "{[":
            first_brace = i
            break
    last_brace = -1
    for i in range(len(content) - 1, -1, -1):
        if content[i] in "}]":
            last_brace = i
            break
    if first_brace > 0 and last_brace > first_brace:
        prefix = content[:first_brace].strip()
        if prefix and not prefix.startswith(("{", "[")):
            content = content[first_brace : last_brace + 1]
            fixes.append("custom:stripped prefix/suffix")

    # Fix 1: Remove comments
    if "//" in content or "/*" in content:
        cleaned_lines = []
        for line in content.split("\n"):
            result = []
            i = 0
            in_str = False
            escape = False
            while i < len(line):
                ch = line[i]
                if escape:
                    result.append(ch)
                    escape = False
                    i += 1
                    continue
                if ch == "\\" and in_str:
                    result.append(ch)
                    escape = True
                    i += 1
                    continue
                if ch == '"' and not escape:
                    in_str = not in_str
                    result.append(ch)
                    i += 1
                    continue
                if not in_str and ch == "/" and i + 1 < len(line) and line[i + 1] == "/":
                    break
                result.append(ch)
                i += 1
            cleaned_lines.append("".join(result).rstrip())
        new_content = "\n".join(cleaned_lines)
        new_content = re.sub(r"/\*.*?\*/", "", new_content, flags=re.DOTALL)
        if new_content != content:
            content = new_content
            fixes.append("custom:removed comments")

    # Fix 2: Trailing commas
    trailing_comma_re = re.compile(r",\s*([}\]])")
    if trailing_comma_re.search(content):
        content = trailing_comma_re.sub(r"\1", content)
        fixes.append("custom:trailing commas")

    # Fix 3: Missing commas (Haiku #1 failure mode)
    missing_comma_re = re.compile(
        r'("(?:[^"\\]|\\.)*"|true|false|null|\d+(?:\.\d+)?|[}\]])\s*\n(\s*["{[\d])',
    )
    prev = content
    for _ in range(50):
        new = missing_comma_re.sub(r"\1,\n\2", content, count=1)
        if new == content:
            break
        content = new
    if content != prev:
        fixes.append("custom:missing commas")

    # Fix 4: Single quotes → double quotes
    if "'" in content and not is_json_valid(content):
        content = re.sub(r"'([^']*?)'", r'"\1"', content)
        fixes.append("custom:single→double quotes")

    # Fix 5: Unquoted numeric ranges (3-5, 14-28) used as values
    # LLMs write "throughput": 3-5 instead of "throughput": "3-5"
    range_re = re.compile(r":\s*(\d+)-(\d+)\s*([,\n}\]])")
    if range_re.search(content) and not is_json_valid(content):
        content = range_re.sub(r': "\1-\2"\3', content)
        fixes.append("custom:quoted numeric ranges")

    # Fix 6: NaN, Infinity, undefined → null
    for literal in ["NaN", "Infinity", "-Infinity", "undefined"]:
        if literal in content:
            content = re.sub(rf"\b{re.escape(literal)}\b", "null", content)
            fixes.append(f"custom:{literal}→null")

    # Fix 6: Truncated JSON — close unclosed brackets
    if not is_json_valid(content):
        stack = []
        in_str = False
        escape = False
        for ch in content:
            if escape:
                escape = False
                continue
            if ch == "\\" and in_str:
                escape = True
                continue
            if ch == '"' and not escape:
                in_str = not in_str
                continue
            if in_str:
                continue
            if ch in "{[":
                stack.append("}" if ch == "{" else "]")
            elif ch in "}]":
                if stack and stack[-1] == ch:
                    stack.pop()
        if stack:
            closing = "".join(reversed(stack))
            content = content.rstrip().rstrip(",") + "\n" + closing
            fixes.append(f"custom:closed {len(stack)} bracket(s)")

    return content, fixes


def _strip_markdown_fences(content: str) -> tuple[str, list[str]]:
    """Strip markdown fences wrapping JSON."""
    fence_match = re.search(r"```(?:json|yaml|jsonc)?\s*\n(.*?)```", content, re.DOTALL)
    if fence_match:
        return fence_match.group(1).strip(), ["stripped fences"]
    return content, []


# ── Main repair orchestrator ─────────────────────────────────────────
def repair_json_content(content: str) -> tuple[str, list[str], str]:
    """Two-tier repair. Returns (repaired, fixes, tier_used)."""
    if is_json_valid(content):
        return content, [], "none"

    # Tier 1: pip json_repair
    if HAS_PIP_REPAIR:
        repaired, fixes = repair_with_pip(content)
        if fixes and is_json_valid(repaired):
            return repaired, fixes, "pip"

    # Tier 2: custom fallback
    repaired, fixes = repair_with_custom(content)
    if fixes and is_json_valid(repaired):
        return repaired, fixes, "custom"

    # Both tiers failed — return best effort from custom (closer to valid)
    if fixes:
        return repaired, fixes, "custom_partial"
    return content, [], "failed"


def process_file(path: Path, dry_run: bool = False) -> bool:
    """Process a single JSON file. Returns True if fully repaired."""
    _metrics["files_scanned"] += 1
    content = path.read_text(encoding="utf-8")

    if is_json_valid(content):
        _metrics["files_already_valid"] += 1
        return False

    repaired, fixes, tier = repair_json_content(content)

    if not fixes:
        _metrics["files_unrepaired"] += 1
        return False

    if tier == "pip":
        _metrics["repairs_pip"] += 1
    elif tier in ("custom", "custom_partial"):
        _metrics["repairs_custom"] += 1

    if is_json_valid(repaired):
        if not dry_run:
            path.write_text(repaired, encoding="utf-8")
        fix_summary = "; ".join(fixes)
        print(f"  🔧 {path.name}: repaired via {tier} ({fix_summary})")
        _metrics["files_repaired"] += 1
        return True
    else:
        print(f"  ⚠️  {path.name}: partial repair ({'; '.join(fixes)}) — still invalid")
        if not dry_run:
            path.write_text(repaired, encoding="utf-8")
        _metrics["files_unrepaired"] += 1
        return False


def emit_metrics(output_dir: Path | None = None) -> None:
    """Write repair metrics to metrics.jsonl if output_dir provided."""
    if output_dir and any(v > 0 for k, v in _metrics.items() if k != "files_already_valid"):
        metrics_line = json.dumps({
            "event": "json_repair",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "backend": "pip" if HAS_PIP_REPAIR else "custom",
            **_metrics,
        })
        metrics_path = output_dir / "metrics.jsonl"
        with open(metrics_path, "a", encoding="utf-8") as f:
            f.write(metrics_line + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="JSON Auto-Repair (runner-lib shared)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", type=Path, help="Single JSON file to repair")
    group.add_argument("--dir", type=Path, help="Directory to scan for JSON files")
    parser.add_argument("--dry-run", action="store_true", help="Show fixes without writing")
    args = parser.parse_args()

    if not HAS_PIP_REPAIR:
        print("  ℹ️  json_repair pip not available — using custom fallback")

    if args.file:
        if not args.file.exists():
            print(f"File not found: {args.file}", file=sys.stderr)
            sys.exit(1)
        process_file(args.file, args.dry_run)
        emit_metrics(args.file.parent)
    elif args.dir:
        if not args.dir.is_dir():
            print(f"Directory not found: {args.dir}", file=sys.stderr)
            sys.exit(1)
        json_files = sorted(args.dir.glob("*.json"))
        for jf in json_files:
            process_file(jf, args.dry_run)
        if _metrics["files_repaired"] or _metrics["files_unrepaired"]:
            print(
                f"  📊 Repair: {_metrics['files_repaired']} fixed, "
                f"{_metrics['files_unrepaired']} failed "
                f"(backend: {'pip' if HAS_PIP_REPAIR else 'custom'})"
            )
        emit_metrics(args.dir)


if __name__ == "__main__":
    main()
