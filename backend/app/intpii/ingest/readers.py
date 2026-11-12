"""Record readers: files (one record per file) and stdin/JSONL (one record per line)."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Iterable, Iterator, TextIO

MAX_FILE_BYTES = 50 * 1024 * 1024


def read_files(paths: Iterable[str]) -> Iterator[tuple[str, str]]:
    for p in paths:
        path = Path(p)
        if path.stat().st_size > MAX_FILE_BYTES:
            raise ValueError(f"{p}: larger than {MAX_FILE_BYTES} bytes; split it or stream it by line")
        yield str(path), path.read_text(encoding="utf-8", errors="replace")


def read_lines(stream: TextIO = sys.stdin, jsonl: bool = False) -> Iterator[tuple[str, str]]:
    """One record per line. With jsonl=True each line is {"id": ..., "text": ...}."""
    for i, line in enumerate(stream):
        line = line.rstrip("\r\n")
        if not line:
            continue
        if jsonl:
            obj = json.loads(line)
            yield str(obj.get("id", i)), obj["text"]
        else:
            yield str(i), line
