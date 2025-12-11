"""Build event timelines and write Markdown DFIR reports.

This module provides utilities to:
- Normalize and sort events in chronological order
- Render simple Markdown tables
- Generate a complete case report including file hashes, metadata findings,
  and a human-readable event timeline
"""

from pathlib import Path  # File path handling
from typing import Any, Dict, List, Tuple  # Structured event types and sort key
from datetime import datetime  # Timestamp parsing for timeline ordering


def _event_sort_key(event: Dict[str, Any]) -> Tuple[int, str]:
    """Produce a stable, sortable key for an event.

    - Prefer ISO8601 timestamps (e.g., '2025-01-01T12:00:00') and convert
      them to a Unix timestamp integer for accurate sorting.
    - If parsing fails, return a default (0) so such events group at the start.
    - Include the original timestamp string to keep sort stable among equals.
    """
    ts = event.get("timestamp")
    if isinstance(ts, str):
        try:
            dt = datetime.fromisoformat(ts)
            return (int(dt.timestamp()), ts)
        except Exception:
            pass
    # Fallback: treat missing/unparseable timestamps as earliest
    return (0, str(ts))


def build_timeline(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalize and sort events chronologically.

    - Creates a shallow copy of events to avoid mutating caller data.
    - Sorts using the sort key that prefers ISO timestamps.
    Returns a new list sorted by timestamp, best-effort normalization.
    """
    # Copy events to avoid mutating caller data
    normalized = [dict(e) for e in events]
    normalized.sort(key=_event_sort_key)
    return normalized


def _md_table(headers: List[str], rows: List[List[str]]) -> str:
    """Build a simple Markdown table string from headers and rows.

    The format uses a header row and a separator row of '---' to be compatible
    with common Markdown renderers.
    """
    # Header row
    out = ["| " + " | ".join(headers) + " |"]
    # Separator row (use --- for each column)
    out.append("| " + " | ".join(["---"] * len(headers)) + " |")
    # Data rows
    for r in rows:
        out.append("| " + " | ".join(r) + " |")
    return "\n".join(out)


def write_report(
    case_id: str,
    case_path: Path,
    hashes: List[Dict[str, Any]],
    metadata: List[Dict[str, Any]],
    timeline: List[Dict[str, Any]],
    reports_dir: Path,
) -> Path:
    """Generate a Markdown report and return its file path.

    The report includes:
    - Title and case info
    - File hash table (MD5/SHA1/SHA256)
    - Metadata findings grouped by file
    - Timeline table (Timestamp, Type, Details)
    """
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / f"case_{case_id}_report.md"

    # Build file hash table rows
    hash_rows: List[List[str]] = []
    for h in hashes:
        rel = str(Path(h["path"]).relative_to(case_path)) if h.get("path") else ""
        hash_rows.append([rel, h.get("md5", ""), h.get("sha1", ""), h.get("sha256", "")])

    # Build metadata sections per file
    meta_sections: List[str] = []
    for m in metadata:
        path_str = m.get("path", "")
        rel = str(Path(path_str).relative_to(case_path)) if path_str else ""
        items = m.get("metadata", {})
        meta_sections.append(f"### {rel}\n" + "\n".join([f"- {k}: {v}" for k, v in items.items()]))

    # Build timeline rows with human-readable details
    tl_rows: List[List[str]] = []
    for e in timeline:
        ts = str(e.get("timestamp", ""))
        etype = str(e.get("type", ""))
        details = ""
        source = e.get("source", "")
        if etype == "ssh_failed_login":
            details = f"Failed SSH login for user `{e.get('user', '')}` from {e.get('ip', '')} (source: {source})"
        elif etype == "http_request":
            details = f"HTTP {e.get('method', '')} {e.get('path', '')} from {e.get('ip', '')} with status {e.get('status', '')} (source: {source})"
        elif etype == "browser_visit":
            title = e.get("title") or ""
            details = f"Visited {e.get('url', '')} ({title}) (source: {source})"
        else:
            # Generic detail fallback
            details = f"Event details: {e}"
        tl_rows.append([ts, etype, details])

    lines: List[str] = []
    lines.append(f"# DFIR Case Report: {case_id}")
    lines.append("")
    lines.append(f"Case directory: {case_path}")
    lines.append("")

    # Hash section
    lines.append("## File Hashes")
    lines.append("")
    lines.append(_md_table(["File", "MD5", "SHA1", "SHA256"], hash_rows) if hash_rows else "(No files hashed)")
    lines.append("")

    # Metadata section
    lines.append("## Metadata Findings")
    lines.append("")
    if meta_sections:
        lines.append("\n\n".join(meta_sections))
    else:
        lines.append("(No metadata found)")
    lines.append("")

    # Timeline section
    lines.append("## Event Timeline")
    lines.append("")
    lines.append(_md_table(["Timestamp", "Type", "Details"], tl_rows) if tl_rows else "(No events found)")
    lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path