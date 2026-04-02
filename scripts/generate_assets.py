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
from xml.sax.saxutils import escape as xml_escape

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
# Language colour map (GitHub linguist colours)
# ---------------------------------------------------------------------------
LANGUAGE_COLORS = {
    "Python": "#3572A5",
    "JavaScript": "#f1e05a",
    "TypeScript": "#3178c6",
    "HTML": "#e34c26",
    "CSS": "#563d7c",
    "Shell": "#89e051",
    "PowerShell": "#012456",
    "Jinja": "#a52a22",
    "Go": "#00ADD8",
    "Ruby": "#701516",
    "Java": "#b07219",
    "C#": "#178600",
    "C++": "#f34b7d",
    "C": "#555555",
    "Rust": "#dea584",
    "Vue": "#41B883",
}

# ---------------------------------------------------------------------------
# Octicon SVG path data (16×16 viewBox)
# ---------------------------------------------------------------------------
_ICON_STAR = (
    "M8 .25a.75.75 0 0 1 .673.418l1.882 3.815 4.21.612a.75.75 0 0 1 "
    ".416 1.279l-3.046 2.97.719 4.192a.75.75 0 0 1-1.088.791L8 12.347"
    "l-3.766 1.98a.75.75 0 0 1-1.088-.79l.72-4.194L.818 6.374a.75.75 "
    "0 0 1 .416-1.28l4.21-.611L7.327.668A.75.75 0 0 1 8 .25z"
)
_ICON_FORK = (
    "M5 3.25a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0zm0 2.122a2.25 "
    "2.25 0 1 0-1.5 0v.878A2.25 2.25 0 0 0 5.75 8.5h1.5v2.128a2.251 "
    "2.251 0 1 0 1.5 0V8.5h1.5a2.25 2.25 0 0 0 2.25-2.25v-.878a2.25 "
    "2.25 0 1 0-1.5 0v.878a.75.75 0 0 1-.75.75h-4.5A.75.75 0 0 1 5 "
    "6.25v-.878zm3.75 7.378a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 "
    "0zm3-8.75a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5z"
)
_ICON_REPO = (
    "M2 2.5A2.5 2.5 0 0 1 4.5 0h8.75a.75.75 0 0 1 .75.75v12.5a.75"
    ".75 0 0 1-.75.75h-2.5a.75.75 0 0 1 0-1.5h1.75v-2h-8a1 1 0 0 "
    "0-.714 1.7.75.75 0 1 1-1.072 1.05A2.495 2.495 0 0 1 2 11.5zm"
    "10.5-1h-8a1 1 0 0 0-1 1v6.708A2.486 2.486 0 0 1 4.5 9h8zM5 "
    "12.25a.25.25 0 0 1 .25-.25h3.5a.25.25 0 0 1 .25.25v3.25a.25"
    ".25 0 0 1-.4.2l-1.45-1.087a.25.25 0 0 0-.3 0L5.4 15.7a.25"
    ".25 0 0 1-.4-.2z"
)
_ICON_COMMIT = (
    "M11.93 8.5a4.002 4.002 0 0 1-7.86 0H.75a.75.75 0 0 1 0-1.5h3.32"
    "a4.002 4.002 0 0 1 7.86 0h3.32a.75.75 0 0 1 0 1.5Zm-1.43-.5a2.5 "
    "2.5 0 1 0-5 0 2.5 2.5 0 0 0 5 0Z"
)

_SVG_FONT = (
    "-apple-system, BlinkMacSystemFont, Segoe UI, Helvetica, Arial, "
    "sans-serif"
)

# Approximate width of a single character in the 12 px SVG font, used for
# horizontal spacing calculations in the repo-card footer.
_APPROX_CHAR_WIDTH = 7.2

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
        ("Cumulative Stars", stars_vals, COLOR_STARS, "o-"),
        ("Repositories Created", repos_vals, COLOR_REPOS, "s--"),
        ("Commits", commits_vals, COLOR_COMMITS, "^:"),
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
# SVG card generators  (replace unreliable github-readme-stats service)
# ---------------------------------------------------------------------------

def _svg_octicon(path_d, x, y, fill, size=16):
    """Return an embedded SVG element for an Octicon at *(x, y)*."""
    return (
        f'<svg x="{x}" y="{y}" width="{size}" height="{size}" '
        f'viewBox="0 0 16 16">'
        f'<path fill-rule="evenodd" d="{path_d}" fill="{fill}"/></svg>'
    )


def _wrap_text(text, max_chars=54):
    """Word-wrap *text* into at most two lines of *max_chars* each."""
    if not text:
        return [""]
    text = text.strip()
    if len(text) <= max_chars:
        return [text]
    words = text.split()
    lines: list[str] = []
    line = ""
    for word in words:
        candidate = f"{line} {word}".strip()
        if len(candidate) > max_chars and line:
            lines.append(line)
            line = word
            if len(lines) == 2:
                break
        else:
            line = candidate
    if line and len(lines) < 2:
        lines.append(line)
    # Truncate last line if the full description didn't fit
    total_used = sum(len(l) for l in lines) + len(lines) - 1
    if total_used < len(text) and len(lines) == 2:
        lines[1] = lines[1][:max_chars - 3].rstrip() + "..."
    return lines[:2]


def generate_stats_card(repos, commits_by_year, out_path):
    """Create an SVG stats card similar to github-readme-stats."""
    total_stars = sum(r.get("stargazers_count", 0) for r in repos)
    total_commits = sum(commits_by_year.values())
    total_repos = len([r for r in repos if not r.get("fork", False)])
    total_forks = sum(r.get("forks_count", 0) for r in repos)

    w, h = 495, 195
    title_fill = TEXT_COLOR
    label_fill = "#8b949e"
    value_fill = TEXT_COLOR

    stats = [
        ("Total Stars Earned", total_stars, _ICON_STAR, "#f1c40f"),
        ("Total Commits", total_commits, _ICON_COMMIT, "#3fb950"),
        ("Public Repos", total_repos, _ICON_REPO, "#58a6ff"),
        ("Total Forks", total_forks, _ICON_FORK, "#8b949e"),
    ]

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" '
        f'height="{h}" viewBox="0 0 {w} {h}">',
        f'<rect width="{w}" height="{h}" rx="4.5" fill="{BG_COLOR}"/>',
        f'<text x="25" y="35" font-family="{_SVG_FONT}" font-size="18" '
        f'font-weight="bold" fill="{title_fill}">'
        f"Loryan&#x27;s GitHub Stats</text>",
    ]

    y_start = 68
    y_step = 32
    for i, (label, value, icon_path, icon_fill) in enumerate(stats):
        y = y_start + i * y_step
        parts.append(_svg_octicon(icon_path, 25, y - 13, icon_fill))
        parts.append(
            f'<text x="50" y="{y}" font-family="{_SVG_FONT}" '
            f'font-size="14" fill="{label_fill}">'
            f"{xml_escape(label)}:</text>"
        )
        parts.append(
            f'<text x="{w - 25}" y="{y}" font-family="{_SVG_FONT}" '
            f'font-size="14" font-weight="bold" fill="{value_fill}" '
            f'text-anchor="end">{value:,}</text>'
        )

    parts.append("</svg>")

    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(parts))
    print(f"  Stats card saved -> {out_path}")


def generate_repo_card(repo, out_path):
    """Create an SVG pin card for a single repository."""
    name = repo["name"]
    desc = repo.get("description") or ""
    lang = repo.get("language") or ""
    stars = repo.get("stargazers_count", 0)
    forks = repo.get("forks_count", 0)
    lang_color = LANGUAGE_COLORS.get(lang, "#8b949e")

    desc_lines = _wrap_text(desc)

    w, h = 400, 120
    name_fill = "#58a6ff"
    desc_fill = "#8b949e"
    footer_fill = "#8b949e"

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" '
        f'height="{h}" viewBox="0 0 {w} {h}">',
        f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" '
        f'rx="4.5" fill="{BG_COLOR}" stroke="{BORDER_COLOR}"/>',
    ]

    # Repo icon + name
    parts.append(_svg_octicon(_ICON_REPO, 20, 14, "#8b949e"))
    parts.append(
        f'<text x="44" y="28" font-family="{_SVG_FONT}" font-size="14" '
        f'font-weight="bold" fill="{name_fill}">'
        f"{xml_escape(name)}</text>"
    )

    # Description (up to two lines)
    desc_y = 50
    for j, line in enumerate(desc_lines):
        parts.append(
            f'<text x="20" y="{desc_y + j * 16}" font-family="{_SVG_FONT}" '
            f'font-size="12" fill="{desc_fill}">'
            f"{xml_escape(line)}</text>"
        )

    # Footer: language · stars · forks
    fy = h - 16
    fx = 20

    if lang:
        parts.append(
            f'<circle cx="{fx + 6}" cy="{fy - 4}" r="6" '
            f'fill="{lang_color}"/>'
        )
        parts.append(
            f'<text x="{fx + 18}" y="{fy}" font-family="{_SVG_FONT}" '
            f'font-size="12" fill="{footer_fill}">'
            f"{xml_escape(lang)}</text>"
        )
        fx += 18 + len(lang) * _APPROX_CHAR_WIDTH + 16

    if stars:
        ix = int(fx)
        parts.append(_svg_octicon(_ICON_STAR, ix, fy - 13, footer_fill))
        parts.append(
            f'<text x="{ix + 20}" y="{fy}" font-family="{_SVG_FONT}" '
            f'font-size="12" fill="{footer_fill}">{stars}</text>'
        )
        fx = ix + 20 + len(str(stars)) * _APPROX_CHAR_WIDTH + 16

    if forks:
        ix = int(fx)
        parts.append(_svg_octicon(_ICON_FORK, ix, fy - 13, footer_fill))
        parts.append(
            f'<text x="{ix + 20}" y="{fy}" font-family="{_SVG_FONT}" '
            f'font-size="12" fill="{footer_fill}">{forks}</text>'
        )

    parts.append("</svg>")

    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(parts))


def generate_repo_cards(repos, assets_dir):
    """Generate SVG pin cards for the top repositories by star count."""
    owned = [r for r in repos if not r.get("fork", False)]
    top = sorted(
        owned, key=lambda r: r.get("stargazers_count", 0), reverse=True
    )[:8]

    for repo in top:
        out = os.path.join(assets_dir, f"pin-{repo['name']}.svg")
        generate_repo_card(repo, out)
        print(f"    {repo['name']} -> {out}")

    return [r["name"] for r in top]


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

    print("Generating GitHub stats card …")
    generate_stats_card(
        repos, commits_by_year,
        os.path.join(ASSETS_DIR, "github-stats.svg"),
    )

    print("Generating repo pin cards …")
    top_names = generate_repo_cards(repos, ASSETS_DIR)
    print(f"  Top repos: {', '.join(top_names)}")

    print("Done!")


if __name__ == "__main__":
    main()
