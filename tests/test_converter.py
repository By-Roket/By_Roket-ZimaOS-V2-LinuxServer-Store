"""Regression checks for WisdomSky-to-ZimaOS conversion."""

from pathlib import Path
import sys
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import convert_wisdomsky  # noqa: E402


class WebEntryTests(unittest.TestCase):
    def test_known_web_port_uses_actual_published_port(self):
        compose = {
            "services": {
                "app": {
                    "ports": [
                        {"target": 8096, "published": 18096, "protocol": "tcp"},
                        {"target": 8920, "published": 18920, "protocol": "tcp"},
                    ]
                }
            }
        }
        metadata = {"main": "app"}

        convert_wisdomsky.ensure_web_entry(compose, metadata, "jellyfin")

        self.assertEqual(metadata["port_map"], "18096")
        self.assertEqual(metadata["index"], "/")

    def test_headless_service_has_empty_port_map(self):
        compose = {"services": {"app": {}}}
        metadata = {"main": "app"}

        convert_wisdomsky.ensure_web_entry(compose, metadata, "feed2toot")

        self.assertEqual(metadata["port_map"], "")

    def test_unknown_ambiguous_service_is_rejected(self):
        compose = {
            "services": {
                "app": {
                    "ports": [
                        {"target": 80, "published": 8080, "protocol": "tcp"},
                        {"target": 443, "published": 8443, "protocol": "tcp"},
                    ]
                }
            }
        }

        with self.assertRaises(ValueError):
            convert_wisdomsky.ensure_web_entry(
                compose, {"main": "app"}, "unknown-app"
            )

    def test_existing_port_map_is_preserved(self):
        compose = {"services": {"app": {}}}
        metadata = {"main": "app", "port_map": 1234}

        convert_wisdomsky.ensure_web_entry(compose, metadata, "unknown-app")

        self.assertEqual(metadata["port_map"], "1234")


class LocaleTests(unittest.TestCase):
    def test_legacy_locale_keys_are_normalized_recursively(self):
        actual = convert_wisdomsky.normalize_locale_keys(
            {"title": {"en_us": "Example", "fr_fr": "Exemple"}}
        )

        self.assertEqual(
            actual,
            {"title": {"en_US": "Example", "fr_FR": "Exemple"}},
        )


if __name__ == "__main__":
    unittest.main()
