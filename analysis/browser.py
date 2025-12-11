from pathlib import Path  # File system paths
from typing import Any, Dict, List  # Event typing for browser visits
import sqlite3  # Built-in SQLite client for history databases
from datetime import datetime, timedelta  # Timestamp conversions


def _chrome_time_to_datetime(value: int | float) -> datetime | None:
    """Convert Chrome/Edge 'last_visit_time' to a datetime.

    Chrome stores timestamps as microseconds since January 1, 1601 UTC.
    """
    try:
        epoch = datetime(1601, 1, 1)
        return epoch + timedelta(microseconds=int(value))
    except Exception:
        return None


def _firefox_time_to_datetime(value: int | float) -> datetime | None:
    """Convert Firefox 'last_visit_date' (microseconds since Unix epoch) to datetime."""
    try:
        epoch = datetime(1970, 1, 1)
        return epoch + timedelta(microseconds=int(value))
    except Exception:
        return None


def _parse_chrome_history(path: Path, limit: int = 200) -> List[Dict[str, Any]]:
    """Parse Chrome/Edge History SQLite DB to produce browser visit events.

    The 'urls' table stores URL, title, and last_visit_time used here.
    """
    events: List[Dict[str, Any]] = []
    try:
        conn = sqlite3.connect(str(path))
        cur = conn.cursor()
        # Basic query from 'urls' table; avoiding joins for simplicity
        cur.execute(
            "SELECT url, title, last_visit_time FROM urls ORDER BY last_visit_time DESC LIMIT ?",
            (limit,),
        )
        rows = cur.fetchall()
        for url, title, last_visit_time in rows:
            dt = _chrome_time_to_datetime(last_visit_time)
            events.append(
                {
                    "timestamp": dt.isoformat() if dt else str(last_visit_time),
                    "timestamp_raw": last_visit_time,
                    "type": "browser_visit",
                    "url": url,
                    "title": title or "",
                    "source": str(path),
                }
            )
    except Exception:
        return events
    finally:
        try:
            conn.close()
        except Exception:
            pass
    return events


def _parse_firefox_places(path: Path, limit: int = 200) -> List[Dict[str, Any]]:
    """Parse Firefox places.sqlite to produce browser visit events.

    The 'moz_places' table stores URL, title, and last_visit_date used here.
    """
    events: List[Dict[str, Any]] = []
    try:
        conn = sqlite3.connect(str(path))
        cur = conn.cursor()
        cur.execute(
            "SELECT url, title, last_visit_date FROM moz_places ORDER BY last_visit_date DESC LIMIT ?",
            (limit,),
        )
        rows = cur.fetchall()
        for url, title, last_visit_date in rows:
            dt = _firefox_time_to_datetime(last_visit_date)
            events.append(
                {
                    "timestamp": dt.isoformat() if dt else str(last_visit_date),
                    "timestamp_raw": last_visit_date,
                    "type": "browser_visit",
                    "url": url,
                    "title": title or "",
                    "source": str(path),
                }
            )
    except Exception:
        return events
    finally:
        try:
            conn.close()
        except Exception:
            pass
    return events


def parse_browser_history(case_path: Path) -> List[Dict[str, Any]]:
    """Locate Chrome/Edge ('History') and Firefox ('places.sqlite') databases and parse them.

    Browsing activity can contextualize events (e.g., user visited phishing site).
    """
    events: List[Dict[str, Any]] = []
    for path in case_path.rglob("*"):
        if not path.is_file():
            continue
        name = path.name
        if name == "History":
            events.extend(_parse_chrome_history(path))
        elif name == "places.sqlite":
            events.extend(_parse_firefox_places(path))
    return events