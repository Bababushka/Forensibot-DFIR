from pathlib import Path  # Path objects provide convenient, cross-platform file handling
from typing import Dict, List  # Type hints for clarity
import hashlib  # Standard library hashing algorithms (MD5/SHA1/SHA256)


def _hash_file(path: Path) -> Dict[str, str]:
    """Compute MD5, SHA1, and SHA256 hashes for a single file.

    Streaming in chunks protects memory usage with large evidence files and
    is a common DFIR practice for integrity verification.
    """
    md5 = hashlib.md5()
    sha1 = hashlib.sha1()
    sha256 = hashlib.sha256()

    # Use a 1MB chunk size to balance I/O throughput and memory usage
    chunk_size = 1024 * 1024
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            md5.update(chunk)
            sha1.update(chunk)
            sha256.update(chunk)

    return {
        "path": str(path),
        "md5": md5.hexdigest(),
        "sha1": sha1.hexdigest(),
        "sha256": sha256.hexdigest(),
    }


def compute_hashes_for_case(case_path: Path) -> List[Dict[str, str]]:
    """Walk the case directory recursively and hash all regular files.

    This produces a comprehensive inventory of file fingerprints used for
    comparison, deduplication, and integrity checks.

    Returns a list of dictionaries with keys: path, md5, sha1, sha256.
    """
    results: List[Dict[str, str]] = []
    for path in case_path.rglob("*"):
        # Skip directories and other non-files (like broken symlinks)
        if not path.is_file():
            continue
        try:
            results.append(_hash_file(path))
        except Exception:
            # If a file cannot be read (permissions/corruption), skip gracefully.
            # In DFIR, it's important not to halt on single-file errors.
            continue
    return results