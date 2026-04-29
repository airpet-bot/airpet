"""Regression coverage for .gitignore hygiene (ACR-008)."""
import os
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GITIGNORE_PATH = os.path.join(REPO_ROOT, ".gitignore")


class TestGitignoreHygiene(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(GITIGNORE_PATH, "r") as f:
            cls.lines = f.read().splitlines()
        cls.patterns = {line.strip() for line in cls.lines if line.strip() and not line.strip().startswith("#")}

    def test_playwright_mcp_logs_ignored(self):
        self.assertIn(".playwright-mcp/", self.patterns)

    def test_playwright_yml_artifacts_ignored(self):
        self.assertIn("/test_*.yml", self.patterns)

    def test_playwright_snapshot_markdown_ignored(self):
        self.assertIn("/snapshot-*.md", self.patterns)

    def test_scratch_gdml_ignored(self):
        self.assertIn("geant4/example_geometry.gdml", self.patterns)

    def test_geant4_scratch_notes_ignored(self):
        self.assertIn("geant4/notes.txt", self.patterns)

    def test_verification_output_ignored(self):
        self.assertIn("verification_run/", self.patterns)

    def test_machine_local_ref_ignored(self):
        self.assertIn("ref/", self.patterns)

    def test_macos_ds_store_ignored(self):
        self.assertIn(".DS_Store", self.patterns)


if __name__ == "__main__":
    unittest.main()
