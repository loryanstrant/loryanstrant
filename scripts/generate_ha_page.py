#!/usr/bin/env python3
"""
Generate home-assistant.md — a dynamically built page listing all of
loryanstrant's non-forked Home Assistant repos, sorted alphabetically
by display name.

Data collected per repo
-----------------------
- Display name   (from hacs.json → fallback: humanised repo name)
- Component type (Theme / Dashboard / Integration, derived from topics)
- Description    (GitHub repo description)
- Latest release (tag + date, from GitHub Releases API)
- Star count     (from repo metadata)
- Preview image  (first matching image found in repo)
"""

import os
import re
import sys
import time
from datetime import datetime, timezone

try:
    import requests
except ImportError:
    sys.exit("requests is required: pip install requests")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
USERNAME = "loryanstrant"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
HEADERS = {"Authorization": f"Bearer {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "..", "home-assistant.md")

# ---------------------------------------------------------------------------
# Topic sets used for repo detection and type classification
# ---------------------------------------------------------------------------
# Any repo whose topics include at least one of these is considered HA-related
HA_TOPICS = frozenset(
    {
        "home-assistant",
        "homeassistant",
        "homeassistant-custom-component",
        "homeassistant-integration",
        "home-assistant-integration",
        "hacs",
        "hacs-theme",
        "hacs-integration",
        "lovelace",
        "lovelace-custom-card",
        "custom-card",
        "custom-component",
        "dashboard",
    }
)

THEME_TOPICS = frozenset({"theme", "hacs-theme"})
INTEGRATION_TOPICS = frozenset(
    {
        "homeassistant-integration",
        "homeassistant-custom-component",
        "integration",
        "custom-component",
        "hacs-integration",
    }
)
DASHBOARD_TOPICS = frozenset(
    {
        "dashboard",
        "lovelace",
        "lovelace-custom-card",
        "custom-card",
        "card",
        "cards",
    }
)

# Name prefixes that identify HA repos even when topics are absent
HA_NAME_PREFIXES = ("ha-", "ha_", "homeassistant", "home-assistant")

# Repos explicitly excluded from the page (e.g. listings, resource collections)
EXCLUDED_REPOS = frozenset(
    {
        "HomeAssistantPlusMicrosoft",
    }
)

# Image file extensions we'll accept as preview images
IMAGE_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg", ".gif", ".webp"})

# Keywords we look for in image file names (in priority order)
IMAGE_KEYWORDS = ["preview", "screenshot", "banner", "logo", "card", "theme"]

# Directories to search for preview images (empty string = repo root)
IMAGE_SEARCH_DIRS = ["", "screenshots", "docs", "images", "assets", "docs/images"]


# ---------------------------------------------------------------------------
# Repo fetching
# ---------------------------------------------------------------------------

def get_all_repos() -> list[dict]:
    """Return all public repos for USERNAME, paginating as needed."""
    repos: list[dict] = []
    page = 1
    while True:
        url = (
            f"https://api.github.com/users/{USERNAME}/repos"
            f"?per_page=100&page={page}"
        )
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return repos


# ---------------------------------------------------------------------------
# HA detection
# ---------------------------------------------------------------------------

def is_ha_repo(repo: dict) -> bool:
    """Return True for non-forked repos that are Home Assistant related."""
    if repo.get("fork"):
        return False
    if repo["name"] in EXCLUDED_REPOS:
        return False
    topics = set(repo.get("topics", []))
    if topics & HA_TOPICS:
        return True
    # Catch repos without topics but with a clearly HA-related name
    lower = repo["name"].lower()
    return any(lower.startswith(p) for p in HA_NAME_PREFIXES)


# ---------------------------------------------------------------------------
# Component-type classification
# ---------------------------------------------------------------------------

def get_component_types(topics: list[str]) -> list[str]:
    """Return a list of human-readable component types inferred from topics."""
    topic_set = set(topics)
    types: list[str] = []
    if topic_set & THEME_TOPICS:
        types.append("Theme")
    if topic_set & INTEGRATION_TOPICS:
        types.append("Integration")
    if topic_set & DASHBOARD_TOPICS:
        types.append("Dashboard")
    return types or ["Other"]


# ---------------------------------------------------------------------------
# Display-name resolution
# ---------------------------------------------------------------------------

def _humanise_repo_name(repo_name: str) -> str:
    """
    Convert a raw repo name into a readable display name.

    Examples
    --------
    ha-weylandyutani            → Weylandyutani   (hacs.json preferred)
    HA-Azure-AI-tasks           → Azure AI Tasks  (hacs.json preferred)
    ha-MU-TH-UR-6000-cards      → MU TH UR 6000 Cards
    HA-CustomComponentMonitor   → Custom Component Monitor
    HomeAssistantPlusMicrosoft  → Plus Microsoft
    blackout                    → Blackout
    """
    name = repo_name
    lower = name.lower()
    for prefix in HA_NAME_PREFIXES:
        if lower.startswith(prefix):
            name = name[len(prefix):]
            break

    # Insert spaces at CamelCase transitions before splitting on separators
    # e.g. "CustomComponentMonitor" → "Custom Component Monitor"
    name = re.sub(r"([a-z])([A-Z])", r"\1 \2", name)
    name = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", name)

    # Replace hyphens and underscores with spaces, then split
    parts = re.split(r"[-_ ]+", name)

    result = []
    for part in parts:
        if not part:
            continue
        if part.isupper() and len(part) > 1:
            result.append(part)   # keep acronyms as-is (e.g. AI, LG, MU)
        else:
            result.append(part.capitalize())
    return " ".join(result)


def _get_hacs_name(repo_name: str, default_branch: str = "main") -> str | None:
    """Try to read the display name from hacs.json in the repo root."""
    for branch in dict.fromkeys([default_branch, "main", "master"]):
        url = (
            f"https://raw.githubusercontent.com/{USERNAME}/"
            f"{repo_name}/{branch}/hacs.json"
        )
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                name = data.get("name")
                if name and isinstance(name, str):
                    return name.strip()
        except Exception:
            pass
    return None


def get_display_name(repo: dict) -> str:
    """Resolve the best human-readable name for a repo."""
    hacs_name = _get_hacs_name(
        repo["name"], repo.get("default_branch", "main")
    )
    return hacs_name if hacs_name else _humanise_repo_name(repo["name"])


# ---------------------------------------------------------------------------
# Release metadata
# ---------------------------------------------------------------------------

def get_latest_release(repo_name: str) -> tuple[str | None, str | None]:
    """
    Return ``(tag, date_str)`` for the repo's latest GitHub Release.
    Both values are ``None`` if the repo has no releases.
    """
    url = (
        f"https://api.github.com/repos/{USERNAME}/{repo_name}/releases/latest"
    )
    resp = requests.get(url, headers=HEADERS, timeout=15)
    if resp.status_code == 200:
        data = resp.json()
        tag = data.get("tag_name") or None
        published = data.get("published_at", "")
        date_str = published[:10] if published else None   # YYYY-MM-DD
        return tag, date_str
    return None, None


# ---------------------------------------------------------------------------
# Preview image discovery
# ---------------------------------------------------------------------------

def find_preview_image(repo_name: str, default_branch: str = "main") -> str | None:
    """
    Return a raw.githubusercontent.com URL for the most relevant preview
    image found in the repo, or *None* if none is found.

    Search strategy
    ---------------
    1. Check each directory in ``IMAGE_SEARCH_DIRS`` via the GitHub Contents API.
    2. Within each directory prefer files whose names contain a keyword from
       ``IMAGE_KEYWORDS`` (checked in order).
    3. Return the first match found; stop searching once a match is found.
    """
    for directory in IMAGE_SEARCH_DIRS:
        api_url = (
            f"https://api.github.com/repos/{USERNAME}/{repo_name}/contents"
            + (f"/{directory}" if directory else "")
        )
        try:
            resp = requests.get(api_url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                continue
            items = resp.json()
            if not isinstance(items, list):
                continue
        except Exception:
            continue

        # Build a quick lookup: keyword → raw URL (first matching file)
        file_map: dict[str, str] = {}
        for item in items:
            if item.get("type") != "file":
                continue
            name_lower = item["name"].lower()
            ext = os.path.splitext(name_lower)[1]
            if ext not in IMAGE_EXTENSIONS:
                continue
            for kw in IMAGE_KEYWORDS:
                if kw in name_lower and kw not in file_map:
                    raw_url = (
                        f"https://raw.githubusercontent.com/{USERNAME}/"
                        f"{repo_name}/{default_branch}/{item['path']}"
                    )
                    file_map[kw] = raw_url

        # Return the highest-priority keyword hit for this directory
        for kw in IMAGE_KEYWORDS:
            if kw in file_map:
                return file_map[kw]

    return None


# ---------------------------------------------------------------------------
# Markdown page generation
# ---------------------------------------------------------------------------

_TYPE_EMOJI: dict[str, str] = {
    "Theme": "🎨",
    "Integration": "🔌",
    "Dashboard": "📊",
    "Other": "📦",
}


def _type_label(types: list[str]) -> str:
    return " · ".join(f"{_TYPE_EMOJI.get(t, '📦')} {t}" for t in types)


def generate_page(projects: list[dict]) -> str:
    today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")

    lines = [
        "# 🏠 Home Assistant Projects",
        "",
        "> My open-source Home Assistant custom integrations, themes, and dashboard cards —",
        f"> auto-updated weekly. **Last updated: {today}**",
        "",
        "---",
        "",
        "| Preview | Name | Type | Description | Latest Release | Stars |",
        "|:-------:|------|------|-------------|:--------------:|:-----:|",
    ]

    for p in projects:
        # Preview image cell
        if p["image_url"]:
            img = (
                f'<img src="{p["image_url"]}" '
                f'width="120" alt="preview" />'
            )
        else:
            img = ""

        name_cell = f'[{p["display_name"]}]({p["html_url"]})'
        type_cell = _type_label(p["types"])

        # Escape pipe characters that would break the table
        desc = (p["description"] or "").replace("|", "\\|").replace("\n", " ")

        if p["release_tag"]:
            release = f'`{p["release_tag"]}`'
            if p["release_date"]:
                release += f"<br/><sub>{p['release_date']}</sub>"
        else:
            release = "—"

        stars = f"⭐ {p['stars']:,}" if p["stars"] else "—"

        lines.append(
            f"| {img} | {name_cell} | {type_cell} | {desc} | {release} | {stars} |"
        )

    lines += [
        "",
        "---",
        "",
        f"*Auto-generated by [GitHub Actions](.github/workflows/update-ha-page.yml). "
        f"Last run: {today}.*",
        "",
    ]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("Fetching all repos …")
    all_repos = get_all_repos()
    print(f"  Total repos: {len(all_repos)}")

    ha_repos = [r for r in all_repos if is_ha_repo(r)]
    print(f"  Home Assistant repos: {len(ha_repos)}")

    projects: list[dict] = []
    for idx, repo in enumerate(ha_repos, 1):
        name = repo["name"]
        print(f"  [{idx}/{len(ha_repos)}] {name} …")

        default_branch = repo.get("default_branch", "main")

        display_name = get_display_name(repo)
        topics = repo.get("topics", [])
        types = get_component_types(topics)
        release_tag, release_date = get_latest_release(name)
        image_url = find_preview_image(name, default_branch)

        projects.append(
            {
                "display_name": display_name,
                "repo_name": name,
                "html_url": repo["html_url"],
                "types": types,
                "description": repo.get("description") or "",
                "release_tag": release_tag,
                "release_date": release_date,
                "stars": repo.get("stargazers_count", 0),
                "image_url": image_url,
            }
        )

        time.sleep(0.3)  # stay well within secondary rate limits

    # Sort alphabetically by display name (case-insensitive)
    projects.sort(key=lambda p: p["display_name"].lower())

    print("Generating home-assistant.md …")
    content = generate_page(projects)

    out_path = os.path.abspath(OUTPUT_FILE)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(content)
    print(f"  Saved → {out_path}")
    print("Done!")


if __name__ == "__main__":
    main()
