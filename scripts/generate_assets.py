#!/usr/bin/env python3
"""
Generate profile README assets:
  - assets/word-cloud.png   (technology word cloud)
  - assets/trend-chart.png  (yearly stars / repos / commits trend)
"""

import os
import re
import sys
import time
from datetime import datetime, timezone

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from wordcloud import WordCloud

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
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")

BG_COLOR = "#0d1117"
PANEL_COLOR = "#161b22"
BORDER_COLOR = "#30363d"
TEXT_COLOR = "#c9d1d9"

# ---------------------------------------------------------------------------
# Technology topic → display-name mapping
# Focuses on apps / services, not programming languages.
# ---------------------------------------------------------------------------
TOPIC_MAP = {
    # Home Automation
    "home-assistant": "Home Assistant",
    "homeassistant": "Home Assistant",
    "homeassistant-custom-component": "Home Assistant",
    "homeassistant-integration": "Home Assistant",
    "home-assistant-integration": "Home Assistant",
    "hacs": "HACS",
    "lovelace": "Lovelace",
    "lovelace-custom-card": "Lovelace",
    "custom-card": "Home Assistant",
    "custom-component": "Home Assistant",
    "dashboard": "Home Assistant",
    "esphome": "ESPHome",
    "mqtt": "MQTT",
    "music-assistant": "Music Assistant",
    # Microsoft Cloud
    "azure": "Azure",
    "azure-ai": "Azure AI",
    "azureai": "Azure AI",
    "azure-automation": "Azure Automation",
    "microsoft": "Microsoft 365",
    "microsoft-365": "Microsoft 365",
    "microsoft-azure": "Azure",
    "microsoft365": "Microsoft 365",
    "office-365": "Microsoft 365",
    "office365": "Microsoft 365",
    "microsoft-graph": "Microsoft Graph",
    "outlook": "Outlook",
    "outlook-365": "Outlook",
    "copilot": "Copilot",
    "dynamics-365": "Dynamics 365",
    "entra-id": "Entra ID",
    "entraid": "Entra ID",
    "fabric": "Microsoft Fabric",
    "viva": "Microsoft Viva",
    "power-apps": "Power Apps",
    "power-automate": "Power Automate",
    "power-bi": "Power BI",
    "power-platform": "Power Platform",
    "powerplatform": "Power Platform",
    # AI / LLM
    "openai": "OpenAI",
    "localai": "LocalAI",
    "elevenlabs": "ElevenLabs",
    "elevenlabs-tts": "ElevenLabs",
    "llm": "LLM",
    "ai": "AI",
    "rag": "RAG",
    "tts": "Text-to-Speech",
    "speech-api": "Azure Speech",
    "speech-synthesis": "Azure Speech",
    "text-to-speech": "Text-to-Speech",
    "image-generation": "Image Generation",
    "sora-2": "Azure OpenAI",
    "sora2": "Azure OpenAI",
    # Infrastructure / DevOps
    "docker": "Docker",
    "container": "Docker",
    "portainer": "Portainer",
    "unifi": "UniFi",
    "unifi-controller": "UniFi",
    "unifi-dream-machine": "UniFi",
    "ubiquiti": "UniFi",
    "udm": "UniFi",
    "ssh": "SSH",
    "backup": "Backup",
    "rsync": "rsync",
    "porkbun": "Porkbun",
    "ssl": "SSL/TLS",
    # Entertainment / Pop Culture themes
    "alien": "Alien",
    "aliens": "Alien",
    "weyland-yutani": "Weyland-Yutani",
    "transformers": "Transformers",
    "rick-and-morty": "Rick & Morty",
    "rickandmorty": "Rick & Morty",
    # Media / Smart Home devices
    "youtube": "YouTube",
    "lg": "LG webOS",
    "webos": "LG webOS",
    "webos-tv": "LG webOS",
    "nvidia": "NVIDIA GPU",
    "gpu": "NVIDIA GPU",
    "bluetooth": "Bluetooth",
    # Knowledge / Docs
    "wiki": "Wiki",
    "documentation": "Documentation",
    "markdown": "Markdown",
    "open-webui": "Open WebUI",
}

# ---------------------------------------------------------------------------
# GitHub helpers
# ---------------------------------------------------------------------------

def get_repos():
    repos = []
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


def get_commit_count_for_year(owner, repo_name, year):
    """Count commits by *owner* in a repo for a given calendar year.

    Uses per_page=1 + the Link rel="last" header trick so that only one
    HTTP request is needed per (repo, year) pair.
    """
    since = f"{year}-01-01T00:00:00Z"
    until = f"{year + 1}-01-01T00:00:00Z"
    url = (
        f"https://api.github.com/repos/{owner}/{repo_name}/commits"
        f"?author={owner}&since={since}&until={until}&per_page=1"
    )
    resp = requests.get(url, headers=HEADERS, timeout=30)
    if resp.status_code != 200:
        return 0
    data = resp.json()
    if not isinstance(data, list):
        return 0

    link = resp.headers.get("Link", "")
    if 'rel="last"' in link:
        m = re.search(r"[?&]page=(\d+)>;\s*rel=\"last\"", link)
        if m:
            return int(m.group(1))

    return len(data)


# ---------------------------------------------------------------------------
# Word-cloud generator
# ---------------------------------------------------------------------------

def build_word_frequencies(repos):
    freq = {}
    for repo in repos:
        for topic in repo.get("topics", []):
            display = TOPIC_MAP.get(topic)
            if display:
                freq[display] = freq.get(display, 0) + 1
    return freq


def generate_word_cloud(repos, out_path):
    freq = build_word_frequencies(repos)
    if not freq:
        print("  No topics found – skipping word cloud.")
        return

    wc = WordCloud(
        width=900,
        height=420,
        background_color=BG_COLOR,
        colormap="Blues",
        max_words=60,
        relative_scaling=0.6,
        min_font_size=14,
        prefer_horizontal=0.8,
        collocations=False,
        margin=8,
    )
    wc.generate_from_frequencies(freq)

    fig, ax = plt.subplots(figsize=(9, 4.2))
    fig.patch.set_facecolor(BG_COLOR)
    ax.set_facecolor(BG_COLOR)
    ax.imshow(wc, interpolation="bilinear")
    ax.axis("off")
    plt.tight_layout(pad=0)
    plt.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=BG_COLOR)
    plt.close()
    print(f"  Word cloud saved → {out_path}")


# ---------------------------------------------------------------------------
# Trend-chart generator
# ---------------------------------------------------------------------------

def aggregate_yearly(repos):
    by_year = {}
    for r in repos:
        year = int(r["created_at"][:4])
        entry = by_year.setdefault(year, {"repos": 0, "stars": 0})
        entry["repos"] += 1
        entry["stars"] += r.get("stargazers_count", 0)
    return by_year


def collect_commits(repos):
    """Get commit counts per year across all repos.

    For each repo, iterates over every calendar year from its creation year
    to the current year and uses the Link-header trick to get an accurate
    count with a single API call per (repo, year) pair.
    """
    commits_by_year = {}
    current_year = datetime.now(tz=timezone.utc).year
    print(f"  Collecting commit history for {len(repos)} repos …")
    for idx, repo in enumerate(repos, 1):
        created_year = int(repo["created_at"][:4])
        name = repo["name"]
        for year in range(created_year, current_year + 1):
            count = get_commit_count_for_year(USERNAME, name, year)
            commits_by_year[year] = commits_by_year.get(year, 0) + count
            time.sleep(0.1)  # stay within secondary rate limits
        if idx % 10 == 0:
            print(f"    {idx}/{len(repos)} repos processed")
    return commits_by_year


def generate_trend_chart(repos, commits_by_year, out_path):
    by_year = aggregate_yearly(repos)

    current_year = datetime.now(tz=timezone.utc).year
    years = sorted(
        y for y in set(list(by_year) + list(commits_by_year))
        if 2019 <= y <= current_year
    )

    # Compute cumulative stars (accumulating over time)
    stars_per_year = [by_year.get(y, {}).get("stars", 0) for y in years]
    stars_vals = []
    running_total = 0
    for s in stars_per_year:
        running_total += s
        stars_vals.append(running_total)

    repos_vals = [by_year.get(y, {}).get("repos", 0) for y in years]
    commits_vals = [commits_by_year.get(y, 0) for y in years]

    x = np.arange(len(years))
    x_labels = [str(y) for y in years]

    COLOR_STARS = "#f1c40f"
    COLOR_REPOS = "#58a6ff"
    COLOR_COMMITS = "#3fb950"

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    fig.patch.set_facecolor(BG_COLOR)

    datasets = [
        ("Cumulative Stars ⭐", stars_vals, COLOR_STARS, "o-"),
        ("Repos Created 📦", repos_vals, COLOR_REPOS, "s--"),
        ("Commits 🔨", commits_vals, COLOR_COMMITS, "^:"),
    ]

    for ax, (title, vals, color, style) in zip(axes, datasets):
        ax.set_facecolor(PANEL_COLOR)
        ax.plot(x, vals, style, color=color, linewidth=2.5, markersize=7)
        ax.set_title(title, color=TEXT_COLOR, fontsize=12, pad=10)
        ax.set_xticks(x)
        ax.set_xticklabels(x_labels, color=TEXT_COLOR, fontsize=10)
        ax.tick_params(axis="x", colors=TEXT_COLOR)
        ax.tick_params(axis="y", labelcolor=TEXT_COLOR)
        ax.set_ylim(bottom=0)
        ax.grid(True, alpha=0.15, color=BORDER_COLOR, linestyle="--")
        for spine in ax.spines.values():
            spine.set_color(BORDER_COLOR)

    fig.suptitle(
        "My GitHub Journey",
        color=TEXT_COLOR, fontsize=14, y=1.02,
    )

    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=BG_COLOR)
    plt.close()
    print(f"  Trend chart saved → {out_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    os.makedirs(ASSETS_DIR, exist_ok=True)

    print("Fetching repos …")
    repos = get_repos()
    print(f"  Found {len(repos)} repos")

    print("Generating word cloud …")
    generate_word_cloud(repos, os.path.join(ASSETS_DIR, "word-cloud.png"))

    print("Collecting commit activity (may take a minute) …")
    commits_by_year = collect_commits(repos)

    print("Generating trend chart …")
    generate_trend_chart(
        repos, commits_by_year, os.path.join(ASSETS_DIR, "trend-chart.png")
    )

    print("Done!")


if __name__ == "__main__":
    main()
