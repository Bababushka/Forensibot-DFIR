"""Analysis package for DFIR Case Automation Bot.

This package contains modular analysis components used by the bot:
- hashing: Compute MD5/SHA1/SHA256 for files
- metadata: Extract metadata from images, PDFs, and DOCX files
- logs: Parse common log formats to produce event records
- browser: Parse browser history databases (Chrome/Edge and Firefox)
- timeline: Build a chronological timeline and generate a Markdown report

Each module exposes a main function that accepts a pathlib.Path pointing to
the case evidence directory and returns structured results for downstream
processing.

Importing functions here provides a clean, single import surface for bot.py
(e.g., `from analysis import compute_hashes_for_case`).
"""

from .hashing import compute_hashes_for_case  # file hashing across the case directory
from .metadata import extract_metadata_for_case  # image/PDF/DOCX metadata extraction
from .logs import parse_logs_for_case  # auth.log and access.log events
from .browser import parse_browser_history  # Chrome/Edge and Firefox history events
from .timeline import build_timeline, write_report  # sort events and write Markdown report

__all__ = [
    "compute_hashes_for_case",
    "extract_metadata_for_case",
    "parse_logs_for_case",
    "parse_browser_history",
    "build_timeline",
    "write_report",
]