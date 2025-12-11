from pathlib import Path  # File system paths
from typing import Any, Dict, List  # Structured event typing
import re  # Regular expressions for log line parsing
from datetime import datetime  # Timestamp normalization


def _parse_auth_log(path: Path) -> List[Dict[str, Any]]:
    """Parse SSH auth.log for failed login attempts.

    The typical line format resembles:
    'Jan 10 12:34:56 hostname sshd[123]: Failed password for user from 1.2.3.4 port 22 ssh2'
    This parser extracts the timestamp, user, and IP when possible.
    """
    events: List[Dict[str, Any]] = []

    # Pattern supports both 'Failed password for user' and 'Failed password for invalid user user'
    pattern = re.compile(
        r"^(?P<ts>\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}).*Failed password for(?: invalid user)?\s+(?P<user>\S+)\s+from\s+(?P<ip>\d{1,3}(?:\.\d{1,3}){3})",
        re.IGNORECASE,
    )

    try:
        for line in path.read_text(errors="ignore").splitlines():
            m = pattern.search(line)
            if not m:
                continue
            ts_raw = m.group("ts")
            user = m.group("user")
            ip = m.group("ip")

            # auth.log lacks a year; we approximate with the current year
            try:
                dt = datetime.strptime(ts_raw, "%b %d %H:%M:%S")
                dt = dt.replace(year=datetime.utcnow().year)
                ts_norm = dt.isoformat()
            except Exception:
                ts_norm = ts_raw

            events.append(
                {
                    "timestamp": ts_norm,
                    "type": "ssh_failed_login",
                    "user": user,
                    "ip": ip,
                    "source": str(path),
                }
            )
    except Exception:
        return events

    return events


def _parse_access_log(path: Path) -> List[Dict[str, Any]]:
    """Parse Apache-style access logs for HTTP requests.

    Example line:
    '1.2.3.4 - - [10/Oct/2000:13:55:36 -0700] "GET /index.html HTTP/1.0" 200 2326'
    """
    events: List[Dict[str, Any]] = []
    pattern = re.compile(
        r"^(?P<ip>\d{1,3}(?:\.\d{1,3}){3}).*\[(?P<ts>[^\]]+)\]\s+\"(?P<method>\S+)\s+(?P<path>\S+)\s+[^\"]+\"\s+(?P<status>\d{3})",
        re.IGNORECASE,
    )

    try:
        for line in path.read_text(errors="ignore").splitlines():
            m = pattern.search(line)
            if not m:
                continue
            ip = m.group("ip")
            ts_raw = m.group("ts")
            method = m.group("method")
            req_path = m.group("path")
            status = m.group("status")

            # Attempt to normalize timestamps like '10/Oct/2000:13:55:36 -0700'
            try:
                dt = datetime.strptime(ts_raw.split()[0], "%d/%b/%Y:%H:%M:%S")
                ts_norm = dt.isoformat()
            except Exception:
                ts_norm = ts_raw

            events.append(
                {
                    "timestamp": ts_norm,
                    "type": "http_request",
                    "ip": ip,
                    "method": method,
                    "path": req_path,
                    "status": status,
                    "source": str(path),
                }
            )
    except Exception:
        return events

    return events


def parse_logs_for_case(case_path: Path) -> List[Dict[str, Any]]:
    """Locate and parse typical SSH and HTTP logs to produce event records.

    - auth.log: Extract failed SSH login attempts
    - *access.log*: Extract HTTP request events from Apache-style logs
    """
    events: List[Dict[str, Any]] = []
    for path in case_path.rglob("*"):
        if not path.is_file():
            continue
        name = path.name.lower()
        if name == "auth.log":
            events.extend(_parse_auth_log(path))
        elif "access.log" in name:
            events.extend(_parse_access_log(path))
    return events