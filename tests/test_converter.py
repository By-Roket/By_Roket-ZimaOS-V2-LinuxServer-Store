"""Regression checks for WisdomSky-to-ZimaOS conversion."""

from pathlib import Path
import sys
from tempfile import TemporaryDirectory
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


class ComposeNameTests(unittest.TestCase):
    def test_dots_are_removed_from_compose_project_names(self):
        self.assertEqual(
            convert_wisdomsky.normalize_compose_name(
                "linuxserver-changedetection.io"
            ),
            "linuxserver-changedetection-io",
        )

    def test_existing_valid_compose_project_name_is_preserved(self):
        self.assertEqual(
            convert_wisdomsky.normalize_compose_name("linuxserver-jellyfin"),
            "linuxserver-jellyfin",
        )

    def test_missing_compose_project_name_is_rejected(self):
        with self.assertRaises(ValueError):
            convert_wisdomsky.normalize_compose_name(None)


class MainServiceTests(unittest.TestCase):
    def test_generic_main_service_uses_application_name(self):
        service = {"image": "linuxserver/freetube:latest"}
        compose = {"services": {"app": service}}
        metadata = {"main": "app"}

        convert_wisdomsky.normalize_main_service(compose, metadata, "freetube")

        self.assertEqual(compose["services"], {"freetube": service})
        self.assertEqual(metadata["main"], "freetube")

    def test_existing_application_service_name_is_preserved(self):
        service = {"image": "linuxserver/freetube:latest"}
        compose = {"services": {"freetube": service}}
        metadata = {"main": "freetube"}

        convert_wisdomsky.normalize_main_service(compose, metadata, "freetube")

        self.assertEqual(compose["services"], {"freetube": service})
        self.assertEqual(metadata["main"], "freetube")

    def test_other_services_are_preserved_in_their_original_order(self):
        compose = {"services": {"app": {}, "database": {}}}
        metadata = {"main": "app"}

        convert_wisdomsky.normalize_main_service(compose, metadata, "freetube")

        self.assertEqual(list(compose["services"]), ["freetube", "database"])
        self.assertEqual(metadata["main"], "freetube")

    def test_existing_service_name_collision_is_rejected(self):
        compose = {"services": {"app": {}, "freetube": {}}}
        metadata = {"main": "app"}

        with self.assertRaisesRegex(ValueError, "already exists"):
            convert_wisdomsky.normalize_main_service(
                compose, metadata, "freetube"
            )

    def test_missing_main_service_is_rejected(self):
        compose = {"services": {"app": {}}}
        metadata = {"main": "missing"}

        with self.assertRaisesRegex(ValueError, "not found"):
            convert_wisdomsky.normalize_main_service(
                compose, metadata, "freetube"
            )

    def test_full_conversion_renames_service_and_updates_web_entry(self):
        with TemporaryDirectory() as directory:
            app_directory = Path(directory) / "Freetube"
            app_directory.mkdir()
            compose_path = app_directory / "docker-compose.yml"
            compose_path.write_text(
                "name: linuxserver-freetube\n"
                "services:\n"
                "  app:\n"
                "    image: linuxserver/freetube:latest\n"
                "    environment:\n"
                "      PUID: $PUID\n"
                "      PGID: $PGID\n"
                "      TZ: $TZ\n"
                "    ports:\n"
                "      - target: 3000\n"
                "        published: 3000\n"
                "    volumes:\n"
                "      - type: bind\n"
                "        source: /DATA/AppData/freetube/config\n"
                "        target: /config\n"
                "x-casaos:\n"
                "  main: app\n",
                encoding="utf-8",
            )

            convert_wisdomsky.convert_app(compose_path)

            with compose_path.open("r", encoding="utf-8") as file:
                converted = convert_wisdomsky.yaml.safe_load(file)

        self.assertEqual(list(converted["services"]), ["freetube"])
        self.assertEqual(converted["x-casaos"]["main"], "freetube")
        self.assertEqual(converted["x-casaos"]["port_map"], "3000")
        self.assertEqual(
            converted["services"]["freetube"]["container_name"],
            "freetube-by-roket",
        )
        self.assertEqual(
            converted["services"]["freetube"]["volumes"][0]["source"],
            "/DATA/AppData/$AppID/config",
        )
        self.assertEqual(
            converted["services"]["freetube"]["environment"],
            {"PUID": "$PUID", "PGID": "$PGID", "TZ": "$TZ"},
        )


class MainContainerTests(unittest.TestCase):
    def test_container_name_uses_application_name_before_store_suffix(self):
        compose = {"services": {"freetube": {}}}
        metadata = {"main": "freetube"}

        convert_wisdomsky.normalize_main_container(
            compose, metadata, "freetube"
        )

        self.assertEqual(
            compose["services"]["freetube"]["container_name"],
            "freetube-by-roket",
        )

    def test_other_container_names_are_not_changed(self):
        compose = {
            "services": {
                "freetube": {},
                "database": {"container_name": "existing-database"},
            }
        }

        convert_wisdomsky.normalize_main_container(
            compose, {"main": "freetube"}, "freetube"
        )

        self.assertEqual(
            compose["services"]["database"]["container_name"],
            "existing-database",
        )


class AppDataVolumeTests(unittest.TestCase):
    def test_application_data_uses_dynamic_application_identifier(self):
        compose = {
            "services": {
                "freetube": {
                    "volumes": [{
                        "type": "bind",
                        "source": "/DATA/AppData/freetube/config",
                        "target": "/config",
                    }]
                }
            }
        }

        convert_wisdomsky.normalize_appdata_volumes(
            compose, "Freetube", "freetube"
        )

        self.assertEqual(
            compose["services"]["freetube"]["volumes"][0]["source"],
            "/DATA/AppData/$AppID/config",
        )

    def test_original_directory_with_dots_is_supported(self):
        compose = {
            "services": {
                "changedetection-io": {
                    "volumes": [{
                        "source": "/DATA/AppData/changedetection.io/config"
                    }]
                }
            }
        }

        convert_wisdomsky.normalize_appdata_volumes(
            compose, "Changedetection.io", "changedetection-io"
        )

        self.assertEqual(
            compose["services"]["changedetection-io"]["volumes"][0][
                "source"
            ],
            "/DATA/AppData/$AppID/config",
        )

    def test_unrelated_and_already_dynamic_paths_are_preserved(self):
        volumes = [
            {"source": "/DATA/Media"},
            {"source": "/DATA/AppData/shared/config"},
            {"source": "/DATA/AppData/$AppID/config"},
        ]
        compose = {"services": {"freetube": {"volumes": volumes}}}

        convert_wisdomsky.normalize_appdata_volumes(
            compose, "Freetube", "freetube"
        )

        self.assertEqual(
            [volume["source"] for volume in volumes],
            [
                "/DATA/Media",
                "/DATA/AppData/shared/config",
                "/DATA/AppData/$AppID/config",
            ],
        )

    def test_short_volume_syntax_is_supported(self):
        compose = {
            "services": {
                "freetube": {
                    "volumes": [
                        "/DATA/AppData/freetube/config:/config:ro"
                    ]
                }
            }
        }

        convert_wisdomsky.normalize_appdata_volumes(
            compose, "Freetube", "freetube"
        )

        self.assertEqual(
            compose["services"]["freetube"]["volumes"],
            ["/DATA/AppData/$AppID/config:/config:ro"],
        )


class IconTests(unittest.TestCase):
    def test_known_broken_icon_uses_application_specific_linuxserver_logo(self):
        metadata = {"icon": "https://broken.example/icon.png"}

        convert_wisdomsky.normalize_app_icons(metadata, "projectsend")

        expected = (
            f"{convert_wisdomsky.LINUXSERVER_ICON_BASE}projectsend-logo.png"
        )
        self.assertEqual(metadata["icon"], expected)
        self.assertEqual(metadata["thumbnail"], expected)

    def test_generic_linuxserver_logo_is_used_when_no_app_logo_is_available(self):
        metadata = {"icon": "https://broken.example/icon.png"}

        convert_wisdomsky.normalize_app_icons(metadata, "nano")

        self.assertEqual(
            metadata["icon"],
            f"{convert_wisdomsky.LINUXSERVER_ICON_BASE}linuxserver-ls-icon.png",
        )

    def test_existing_working_icons_are_preserved(self):
        metadata = {
            "icon": "https://valid.example/icon.png",
            "thumbnail": "https://valid.example/thumbnail.png",
        }

        convert_wisdomsky.normalize_app_icons(metadata, "jellyfin")

        self.assertEqual(metadata["icon"], "https://valid.example/icon.png")
        self.assertEqual(
            metadata["thumbnail"], "https://valid.example/thumbnail.png"
        )


if __name__ == "__main__":
    unittest.main()
