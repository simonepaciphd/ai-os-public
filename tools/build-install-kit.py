"""Build site/ai-os-install-kit.zip: the install kit plus the library it installs.

The archive mirrors the repository layout under one top-level folder
(ai-os-public-<VERSION>/), so the kit's paths resolve the same way in a clone
and in the download. It contains every file Git tracks or would track, except
the Pages site and CI configuration. Output is deterministic: sorted entries,
fixed timestamps, fixed permissions, LF line endings in text files. Standard
library and Git only.

    python tools/build-install-kit.py          # write the archive
    python tools/build-install-kit.py --check  # exit 1 if the archive is stale
"""
import argparse
import io
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "site" / "ai-os-install-kit.zip"
EXCLUDED_PREFIXES = ("site/", ".github/")
FIXED_TIME = (1980, 1, 1, 0, 0, 0)


def source_files():
    listed = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT, check=True, capture_output=True,
    ).stdout.decode("utf-8").split("\0")
    files = sorted({p for p in listed if p and not p.startswith(EXCLUDED_PREFIXES)})
    missing = [p for p in files if not (ROOT / p).is_file()]
    if missing:
        raise SystemExit(f"listed but not on disk: {missing}")
    if "install-kit/START-HERE.md" not in files:
        raise SystemExit("install-kit/START-HERE.md is missing")
    return files


def build():
    prefix = f"ai-os-public-{(ROOT / 'VERSION').read_text(encoding='utf-8').strip()}/"
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in source_files():
            info = zipfile.ZipInfo(prefix + path, date_time=FIXED_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, canonical_bytes(ROOT / path))
    return buffer.getvalue()


def canonical_bytes(path):
    # The repository stores text with LF endings; checkouts may convert to CRLF.
    # Normalizing text keeps the archive identical on every platform.
    data = path.read_bytes()
    return data if b"\0" in data else data.replace(b"\r\n", b"\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="compare with the existing archive; write nothing")
    args = parser.parse_args()
    data = build()
    if args.check:
        current = OUTPUT.read_bytes() if OUTPUT.is_file() else b""
        if current != data:
            print(f"stale: {OUTPUT.relative_to(ROOT)} does not match the working tree; rebuild it")
            return 1
        print(f"ok: {OUTPUT.relative_to(ROOT)} is current")
        return 0
    OUTPUT.write_bytes(data)
    print(f"wrote {OUTPUT.relative_to(ROOT)} ({len(data)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
