#!/usr/bin/env python3

from pathlib import Path
import re
import sys
import yaml


APPS_DIR = Path("Apps")

ALLOWED_CATEGORIES = {
    "Media",
    "Productivity",
    "Home",
    "Networking",
    "AI",
    "Finance",
    "Social",
    "Developer",
    "Others",
}


# Port interne de l'interface Web pour les applications ambiguës.
# None signifie que l'application n'expose volontairement aucune interface Web.
WEB_UI_TARGET_PORTS = {
    "citron": "3000",
    "deluge": "8112",
    "emby": "8096",
    "feed2toot": None,
    "freetube": "3000",
    "jellyfin": "8096",
    "ldap-auth": "8888",
    "minetest": None,
    "minisatip": "8875",
    "nano": "8075",
    "plex-meta-manager": None,
    "quassel-core": None,
    "resilio-sync": "8888",
    "series-troxide": "3000",
    "steamos": "3000",
    "syncthing": "8384",
    "syslog-ng": None,
    "transmission": "9091",
    "tvheadend": "9981",
    "ubooquity": "2202",
}


# Priorité aux applications que nous connaissons précisément.
EXACT_CATEGORIES = {
    # Media
    "jellyfin": "Media",
    "plex": "Media",
    "emby": "Media",
    "sonarr": "Media",
    "radarr": "Media",
    "lidarr": "Media",
    "readarr": "Media",
    "bazarr": "Media",
    "prowlarr": "Media",
    "tautulli": "Media",
    "overseerr": "Media",
    "ombi": "Media",
    "calibre-web": "Media",
    "airsonic-advanced": "Media",
    "navidrome": "Media",

    # Productivity
    "nextcloud": "Productivity",
    "freshrss": "Productivity",
    "bookstack": "Productivity",
    "wikijs": "Productivity",

    # Home
    "homeassistant": "Home",
    "home-assistant": "Home",
    "esphome": "Home",

    # Networking
    "adguardhome-sync": "Networking",
    "ddclient": "Networking",
    "duckdns": "Networking",
    "wireguard": "Networking",
    "swag": "Networking",
    "openssh-server": "Networking",
    "netbootxyz": "Networking",
    "librespeed": "Networking",
    "socket-proxy": "Networking",

    # Developer
    "code-server": "Developer",
    "docker-mods": "Developer",
    "mariadb": "Developer",
}


# Deuxième niveau : détection par mots-clés.
KEYWORD_CATEGORIES = [
    (
        "Media",
        (
            "media", "video", "audio", "music", "photo",
            "movie", "tv", "torrent", "subtitle",
            "jelly", "plex", "emby",
            "sonarr", "radarr", "lidarr", "readarr",
        ),
    ),
    (
        "Networking",
        (
            "network", "dns", "proxy", "vpn", "wireguard",
            "ssh", "ddns", "duckdns", "nginx",
            "swag", "speedtest",
        ),
    ),
    (
        "Developer",
        (
            "code", "git", "database", "mariadb",
            "mysql", "postgres", "redis",
            "docker", "development",
        ),
    ),
    (
        "Home",
        (
            "homeassistant", "home-assistant",
            "esphome", "automation", "iot",
        ),
    ),
    (
        "Productivity",
        (
            "cloud", "document", "wiki", "book",
            "rss", "office", "calendar",
            "notes", "productivity",
        ),
    ),
    (
    "AI",
    (
        "llm",
        "ollama",
        "machine-learning",
        "machine learning",
        "whisper",
        "stable-diffusion",
        "stable diffusion",
    ),
),
    (
        "Finance",
        (
            "finance", "budget", "money",
        ),
    ),
    (
        "Social",
        (
            "social", "chat", "matrix",
            "mastodon",
        ),
    ),
]


def normalize_locale_keys(value):
    """Convert legacy locale keys recursively."""
    if isinstance(value, dict):
        result = {}

        for key, item in value.items():
            if key == "en_us":
                key = "en_US"
            elif key == "fr_fr":
                key = "fr_FR"
            elif key == "zh_cn":
                key = "zh_CN"

            result[key] = normalize_locale_keys(item)

        return result

    if isinstance(value, list):
        return [normalize_locale_keys(item) for item in value]

    return value


def slugify(value):
    """Create a stable ZimaOS-compatible identifier component."""
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9_-]+", "-", value)
    value = re.sub(r"-+", "-", value)
    return value.strip("-_")


def extract_version(compose):
    """Get the Docker image tag without inventing a fake version."""
    services = compose.get("services", {})

    for service in services.values():
        if not isinstance(service, dict):
            continue

        image = service.get("image")
        if not isinstance(image, str):
            continue

        # Examples:
        # linuxserver/nextcloud:34.0.3
        # lscr.io/linuxserver/jellyfin:10.10.7
        last_part = image.rsplit("/", 1)[-1]

        if ":" in last_part:
            tag = last_part.rsplit(":", 1)[1].strip()

            if tag:
                return tag

    # ZimaOS requires x-casaos.version.
    # "latest" is preferable to inventing a false numeric version.
    return "latest"

def keyword_matches(text, keyword):
    """Match complete words or phrases instead of arbitrary substrings."""
    normalized_text = re.sub(
        r"[^a-z0-9]+",
        " ",
        text.lower()
    ).strip()

    normalized_keyword = re.sub(
        r"[^a-z0-9]+",
        " ",
        keyword.lower()
    ).strip()

    if not normalized_keyword:
        return False

    return (
        f" {normalized_keyword} "
        in f" {normalized_text} "
    )


def choose_category(app_name, metadata):
    """Choose the nearest official ZimaOS V2 category."""
    slug = slugify(app_name)

    if slug in EXACT_CATEGORIES:
        return EXACT_CATEGORIES[slug]

    searchable_parts = [app_name]

    if isinstance(metadata, dict):
        for field in ("developer", "author"):
            value = metadata.get(field)
            if isinstance(value, str):
                searchable_parts.append(value)

        for field in ("title", "tagline", "description"):
            value = metadata.get(field)

            if isinstance(value, str):
                searchable_parts.append(value)

            elif isinstance(value, dict):
                searchable_parts.extend(
                    str(text)
                    for text in value.values()
                    if isinstance(text, str)
                )

    searchable = " ".join(searchable_parts).lower()

    for category, keywords in KEYWORD_CATEGORIES:
        if any(
            keyword_matches(searchable, keyword)
            for keyword in keywords
        ):
            return category

    return "Others"

def published_tcp_ports(service):
    """Return (target, published) pairs for published TCP ports."""
    result = []

    for port in service.get("ports", []):
        if isinstance(port, dict):
            protocol = str(port.get("protocol", "tcp")).lower()

            if protocol != "tcp":
                continue

            target = port.get("target")
            published = port.get("published")

            if target is not None and published is not None:
                result.append((str(target), str(published)))

        elif isinstance(port, str):
            value = port.strip()

            if value.endswith("/udp"):
                continue

            value = value.removesuffix("/tcp")
            parts = value.rsplit(":", 2)

            if len(parts) >= 2:
                result.append((parts[-1], parts[-2]))

    return result


def ensure_web_entry(compose, metadata, app_slug):
    """Ensure required ZimaOS V2 web entry fields exist."""
    index = metadata.get("index")

    if not isinstance(index, str) or not index.strip():
        metadata["index"] = "/"

    # Preserve an explicit value, including an empty headless marker.
    if "port_map" in metadata and metadata["port_map"] is not None:
        metadata["port_map"] = str(metadata["port_map"])
        return

    main_service = metadata.get("main")
    services = compose.get("services", {})

    if not isinstance(services, dict):
        raise ValueError("Invalid services section")

    service = services.get(main_service)

    if not isinstance(service, dict):
        raise ValueError(
            f"Main service '{main_service}' not found"
        )

    ports = published_tcp_ports(service)

    if app_slug in WEB_UI_TARGET_PORTS:
        target = WEB_UI_TARGET_PORTS[app_slug]

        if target is None:
            metadata["port_map"] = ""
            return

        candidates = [
            published
            for container_port, published in ports
            if container_port == target
        ]
        candidates = list(dict.fromkeys(candidates))

        if len(candidates) == 1:
            metadata["port_map"] = candidates[0]
            return

        raise ValueError(
            f"Expected one published TCP port for Web UI target "
            f"{target}, found {len(candidates)}"
        )

    candidates = list(dict.fromkeys(
        published
        for _, published in ports
    ))

    if len(candidates) == 1:
        metadata["port_map"] = candidates[0]
        return

    if not candidates:
        metadata["port_map"] = ""
        return

    raise ValueError(
        "Missing x-casaos.port_map and multiple published "
        "TCP ports make Web UI detection ambiguous"
    )

def convert_app(compose_path):
    app_name = compose_path.parent.name

    with compose_path.open("r", encoding="utf-8") as file:
        compose = yaml.safe_load(file)

    if not isinstance(compose, dict):
        raise ValueError("Invalid YAML root")

    compose = normalize_locale_keys(compose)

    metadata = compose.setdefault("x-casaos", {})

    if not isinstance(metadata, dict):
        raise ValueError("Top-level x-casaos must be a mapping")

    app_slug = slugify(app_name)

    # Stable ID: do not derive it from a Docker version.
    metadata["id"] = f"by-roket.linuxserver.{app_slug}"

    # Required by ZimaOS V2.
    metadata["version"] = extract_version(compose)

    # Replace WisdomSky's legacy LinuxServer.io category.
    metadata["category"] = choose_category(app_name, metadata)

    if metadata["category"] not in ALLOWED_CATEGORIES:
        metadata["category"] = "Others"

    ensure_web_entry(compose, metadata, app_slug)

    with compose_path.open("w", encoding="utf-8") as file:
        yaml.safe_dump(
            compose,
            file,
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False,
        )

    return (
        app_name,
        metadata["id"],
        metadata["version"],
        metadata["category"],
    )


def main():
    if not APPS_DIR.exists():
        print("ERROR: Apps/ directory not found.")
        return 1

    compose_files = sorted(APPS_DIR.glob("*/docker-compose.yml"))

    if not compose_files:
        print("ERROR: No Apps/*/docker-compose.yml files found.")
        return 1

    converted = []
    errors = []

    for compose_path in compose_files:
        try:
            converted.append(convert_app(compose_path))
        except Exception as exc:
            errors.append((compose_path, str(exc)))

    print()
    print("=== ZimaOS V2 conversion report ===")
    print(f"Converted applications: {len(converted)}")
    print(f"Errors: {len(errors)}")
    print()

    for app_name, app_id, version, category in converted:
        print(
            f"[OK] {app_name} | "
            f"id={app_id} | "
            f"version={version} | "
            f"category={category}"
        )

    if errors:
        print()
        print("=== ERRORS ===")

        for compose_path, error in errors:
            print(f"[ERROR] {compose_path}: {error}")

        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
