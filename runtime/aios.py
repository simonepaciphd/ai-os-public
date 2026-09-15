"""Portable native bookkeeping entrypoint. Python 3.11+, standard library only."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

RUNTIME = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(RUNTIME / "src"))


def verify_runtime():
    manifest = RUNTIME / "MANIFEST.json"
    expected = json.loads(manifest.read_text(encoding="utf-8-sig"))
    for relative, sha in expected["files"].items():
        path = (RUNTIME / relative).resolve()
        if not path.is_relative_to(RUNTIME) or hashlib.sha256(path.read_bytes()).hexdigest() != sha:
            raise ValueError("runtime-integrity-failed")


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        verify_runtime()
        if "--config" in argv:
            config = Path(argv[argv.index("--config") + 1]).resolve()
        else:
            config = RUNTIME.parent / "config" / "ownership.json"
            if not any(x in argv for x in ("--describe", "--validate")):
                argv.extend(["--config", str(config)])
        if "--doctor" in argv or "--status" in argv:
            from aios_native.bookkeeping import Bookkeeper
            from aios_core.coord import snapshot
            bk = Bookkeeper(config)
            bk.ownership()
            controls = bk.control()
            if "--doctor" in argv:
                for path in [bk.root, bk.coord / "sessions"]:
                    if not path.is_dir():
                        raise ValueError("installation-directory-missing")
                print(json.dumps({"status": "ok" if controls == "clear" else "cleanup-only",
                                  "controls": controls, "runtime_integrity": "verified",
                                  "storage_format": bk.config["storage_format"],
                                  "projects": sorted(bk.config["projects"]),
                                  "host_delivery": "requires-real-session-check"}))
                return 0 if controls == "clear" else 2
            view = snapshot(bk.coord, bk.clock())
            print(json.dumps({"controls": controls,
                              "sessions": [{"id": x.id, "live": x.live, "claims": x.claims}
                                           for x in view.verdicts],
                              "publication": {p: bk.publication_status(p)
                                              for p in bk.config["projects"]}}, default=list))
            return 0
        from aios_native.ingress import main as native_main
        return native_main(argv)
    except (OSError, ValueError, KeyError, IndexError) as exc:
        # Paths, input bodies and exception messages stay out of hook diagnostics.
        print(json.dumps({"continue": False, "stopReason": "AI OS installation check failed",
                          "error_class": type(exc).__name__}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
