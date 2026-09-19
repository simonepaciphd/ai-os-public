"""Regenerate distributed runtime digests after reviewing a runtime change."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1] / "runtime"
upstream_path = root / "UPSTREAM.json"
product_version = (root.parent / "VERSION").read_text(encoding="utf-8").strip()
upstream = json.loads(upstream_path.read_text(encoding="utf-8-sig"))
upstream["product_version"] = product_version
for item in upstream["files"]:
    item["distributed_sha256"] = hashlib.sha256((root / item["path"]).read_bytes()).hexdigest()
upstream_path.write_text(json.dumps(upstream, sort_keys=True, indent=2) + "\n", encoding="utf-8", newline="\n")
files = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
         for p in sorted(root.rglob("*")) if p.is_file() and p.name != "MANIFEST.json"
         and "__pycache__" not in p.parts and p.suffix != ".pyc"}
(root / "MANIFEST.json").write_text(json.dumps({"version": "public-native-1", "product_version": product_version, "files": files},
                                               sort_keys=True, indent=2) + "\n", encoding="utf-8", newline="\n")
