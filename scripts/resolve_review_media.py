"""Resolve removed, SHA-identical reviewed MP3 copies to their preserved production masters."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
_doc=json.loads((ROOT/"audio/review-media-dedup.json").read_text(encoding="utf-8"))
_PAIRS={item["review_path"]: item["production_path"] for item in _doc["pairs"]}

def resolve_review_media(path):
    p=Path(path)
    key=p.relative_to(ROOT).as_posix() if p.is_absolute() else p.as_posix()
    return ROOT/_PAIRS.get(key,key)
