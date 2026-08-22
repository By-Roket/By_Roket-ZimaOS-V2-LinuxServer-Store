"""Regression checks for the generated ZimaOS V2 store layout."""

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import verify_dist  # noqa: E402


class DistVerificationTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.root = Path(self.temporary_directory.name)
        self.source = self.root / "source"
        self.dist = self.root / "dist"
        self.app_id = "by-roket.linuxserver.example"

        (self.source / "Apps" / "Example").mkdir(parents=True)
        (self.source / "Apps" / "Example" / "docker-compose.yml").write_text(
            "name: example\n", encoding="utf-8"
        )
        (self.source / "store-config.json").write_text(
            json.dumps(
                {
                    "version": 2,
                    "store_id": "by-roket.zimaos.linuxserver",
                    "name": {"en_US": "Store", "fr_FR": "Boutique"},
                }
            ),
            encoding="utf-8",
        )

        app_directory = self.dist / "apps" / self.app_id
        (app_directory / "assets").mkdir(parents=True)
        (app_directory / "docker-compose.yml").write_text(
            "name: example\n", encoding="utf-8"
        )
        (app_directory / "meta.json").write_text("{}", encoding="utf-8")
        (self.dist / "store.json").write_text(
            json.dumps(
                {"version": 2, "store_id": "by-roket.zimaos.linuxserver"}
            ),
            encoding="utf-8",
        )
        (self.dist / "store.fr_FR.json").write_text("{}", encoding="utf-8")
        (self.dist / "index.json").write_text(
            json.dumps(
                {
                    "version": 2,
                    "app_count": 1,
                    "base_url": "https://example.test/store",
                    "apps": [{"id": self.app_id}],
                }
            ),
            encoding="utf-8",
        )
        (self.dist / "metadata.tar.gz").write_bytes(b"metadata")
        (self.dist / "metadata.sha256").write_text("checksum", encoding="utf-8")

    def run_verifier(self):
        arguments = [
            "verify_dist.py",
            "--source",
            str(self.source),
            "--dist",
            str(self.dist),
            "--base-url",
            "https://example.test/store",
        ]

        with patch.object(sys, "argv", arguments):
            with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                return verify_dist.main()

    def test_complete_distribution_is_accepted(self):
        self.assertEqual(self.run_verifier(), 0)

    def test_missing_french_store_overlay_is_rejected(self):
        (self.dist / "store.fr_FR.json").unlink()

        self.assertEqual(self.run_verifier(), 1)

    def test_missing_application_metadata_is_rejected(self):
        (self.dist / "apps" / self.app_id / "meta.json").unlink()

        self.assertEqual(self.run_verifier(), 1)


if __name__ == "__main__":
    unittest.main()
