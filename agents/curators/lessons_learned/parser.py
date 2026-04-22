"""
agents/curators/lessons_learned/parser.py

Markdown parser for Protean Pursuits LESSONS_LEARNED files.

Format (authoritative, per docs/LESSONS_LEARNED.md):

    ## LL-040 — <title>

    **Date:** 2026-04-21
    **Discovered via:** <optional>
    **Severity:** HIGH — optional trailing detail
    **Affected:** <free-form list of teams/agents>

    ### Symptom
    ...
    ### Fix
    ...

Returns a list of dicts with keys:
    ll_id     — "LL-NNN" (must be numeric after the dash)
    title     — everything after "— " on the heading line
    date      — ISO date string or "" if missing
    severity  — full severity line body, e.g. "HIGH — initial fix..."
    affected  — full affected line body, or ""
    body      — the entire markdown body between the heading and the
                next LL-NNN heading (exclusive), including ### subsections

The parser is deliberately permissive: unknown ** labels are ignored,
and missing metadata fields become empty strings rather than raising.
Malformed entries (non-numeric IDs) are skipped silently.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional


# ## LL-040 — <title>   (em dash OR plain hyphen; numeric id required)
_HEADING_RE = re.compile(r"^##\s+LL-(\d+)\s+[—\-]\s+(.+?)\s*$")

# Accept any of — or - or : after a **Field:** marker, with optional space.
_FIELD_RE = re.compile(r"^\*\*(?P<label>[^:*]+):\*\*\s*(?P<value>.+?)\s*$")


def _parse_entry(ll_id: str, title: str, block: str) -> dict:
    date = ""
    severity = ""
    affected = ""

    for line in block.splitlines():
        m = _FIELD_RE.match(line)
        if not m:
            continue
        label = m.group("label").strip().lower()
        value = m.group("value").strip()
        if label == "date":
            date = value
        elif label == "severity":
            severity = value
        elif label == "affected":
            affected = value

    return {
        "ll_id":    f"LL-{ll_id}",
        "title":    title,
        "date":     date,
        "severity": severity,
        "affected": affected,
        "body":     block,
    }


def parse_ll_file(path: Path | str) -> list[dict]:
    """
    Parse a LESSONS_LEARNED.md file and return the list of entries.
    Missing file → [] (non-fatal, caller logs).
    """
    p = Path(path)
    if not p.exists():
        return []

    lines = p.read_text().splitlines()
    entries: list[dict] = []

    # Walk once, accumulating the body for each heading until the next one.
    current_id: Optional[str] = None
    current_title: Optional[str] = None
    current_body: list[str] = []

    def _flush():
        if current_id is not None and current_title is not None:
            entries.append(_parse_entry(
                current_id, current_title, "\n".join(current_body)
            ))

    for line in lines:
        m = _HEADING_RE.match(line)
        if m:
            _flush()
            current_id = m.group(1)
            current_title = m.group(2).strip()
            current_body = []
        else:
            if current_id is not None:
                current_body.append(line)

    _flush()
    return entries
