import importlib.util
import re
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KIT = ROOT / "install-kit"

spec = importlib.util.spec_from_file_location("build_install_kit", ROOT / "tools" / "build-install-kit.py")
build_install_kit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build_install_kit)


class InstallKitTests(unittest.TestCase):
    def test_archive_matches_working_tree(self):
        self.assertTrue(build_install_kit.OUTPUT.is_file(), "run tools/build-install-kit.py")
        self.assertEqual(build_install_kit.OUTPUT.read_bytes(), build_install_kit.build(),
                         "site/ai-os-install-kit.zip is stale; run tools/build-install-kit.py")

    def test_archive_layout(self):
        version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
        with zipfile.ZipFile(build_install_kit.OUTPUT) as archive:
            names = archive.namelist()
        prefix = f"ai-os-public-{version}/"
        self.assertTrue(all(n.startswith(prefix) for n in names))
        for required in ("install-kit/START-HERE.md", "install.py", "skills/project-setup.md", "LICENSE"):
            self.assertIn(prefix + required, names)
        self.assertFalse([n for n in names if n[len(prefix):].startswith(("site/", ".github/"))])

    def test_archive_text_uses_lf(self):
        with zipfile.ZipFile(build_install_kit.OUTPUT) as archive:
            crlf = [info.filename for info in archive.infolist()
                    if b"\0" not in (data := archive.read(info)) and b"\r\n" in data]
        self.assertEqual(crlf, [])

    def test_library_paths_in_kit_exist(self):
        pattern = re.compile(r"`((?:skills|personas|agents|docs|runtime)/[^`\s]+?\.(?:md|py|ps1)|install\.py)`")
        kit_files = sorted(KIT.rglob("*.md"))
        self.assertTrue(kit_files)
        for kit_file in kit_files:
            text = kit_file.read_text(encoding="utf-8")
            for match in pattern.finditer(text):
                with self.subTest(file=kit_file.name, path=match.group(1)):
                    self.assertTrue((ROOT / match.group(1)).is_file())

    def test_kit_internal_references_exist(self):
        for name in ("PRINCIPLES.md", "install-state.md", "adapters/claude-code.md", "adapters/codex.md",
                     "adapters/other-agent.md"):
            self.assertTrue((KIT / name).is_file(), name)
        self.assertEqual(len(list((KIT / "levels").glob("L[0-4]-*.md"))), 5)


if __name__ == "__main__":
    unittest.main()
