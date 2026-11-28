#!/usr/bin/env python3
"""
GitHub Contribution Progress Chart Generator
Queries GitHub GraphQL API and generates a futuristic SVG line chart.
Runs via GitHub Actions, committed to assets/progress-chart.svg
"""

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from math import ceil

# ── Config ────────────────────────────────────────────────────────────────────
USERNAME = os.environ.get("GITHUB_USERNAME", "MAFAZ9416")
TOKEN    = os.environ.get("GITHUB_TOKEN", "")
OUT_PATH = os.environ.get("OUTPUT_PATH", "assets/progress-chart.svg")

# Design tokens (must match the README design system)
BG_OUTER    = "#0D0D0F"
BG_CARD     = "#161622"
BORDER      = "#1E1E2E"
PURPLE      = "#9D4EDD"
CYAN        = "#00F5FF"
LIME        = "#B5FF4D"
TEXT_DIM    = "#555570"
TEXT_MID    = "#8888AA"
TEXT_LIGHT  = "#E8E8F0"

W, H        = 900, 220
PAD_L       = 60   # left padding (y-axis labels)
PAD_R       = 24   # right padding
PAD_T       = 48   # top padding (header)
PAD_B       = 38   # bottom padding (month labels)
CHART_W     = W - PAD_L - PAD_R   # 816
CHART_H     = H - PAD_T - PAD_B   # 134


def fetch_contributions():
    """Fetch last 12 months of monthly contribution counts via GraphQL."""
    if not TOKEN:
        print("[WARN] No GITHUB_TOKEN set — using placeholder data.", file=sys.stderr)
        return None

    query = """
    query($login: String!) {
      user(login: $login) {
        contributionsCollection {
          contributionCalendar {
            weeks {
              contributionDays {
                date
                contributionCount
              }
            }
          }
        }
      }
    }
    """
    payload = json.dumps({"query": query, "variables": {"login": USERNAME}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type":  "application/json",
            "User-Agent":    "MAFAZ-Profile-Chart/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read())
    except Exception as e:
        print(f"[ERROR] GraphQL request failed: {e}", file=sys.stderr)
        return None

    if "errors" in data:
        print(f"[ERROR] GraphQL errors: {data['errors']}", file=sys.stderr)
        return None

    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]

    # Aggregate by month (last 12 calendar months)
    now   = datetime.now(timezone.utc)
    months = {}
    for week in weeks:
        for day in week["contributionDays"]:
            d = datetime.fromisoformat(day["date"]).replace(tzinfo=timezone.utc)
            # Only last 12 months
            delta_months = (now.year - d.year) * 12 + (now.month - d.month)
            if 0 <= delta_months < 12:
                key = d.strftime("%Y-%m")
                months[key] = months.get(key, 0) + day["contributionCount"]

    # Sort ascending
    sorted_months = sorted(months.items())
    if not sorted_months:
        return None
    return sorted_months   # [(YYYY-MM, count), ...]


def month_abbr(ym: str) -> str:
    """Convert '2024-11' to 'Nov'."""
    dt = datetime.strptime(ym, "%Y-%m")
    return dt.strftime("%b")


def bezier_path(points) -> str:
    """Generate a smooth cubic Bézier SVG path through a list of (x,y) points."""
    if len(points) < 2:
        return ""
    d = f"M{points[0][0]:.1f},{points[0][1]:.1f}"
    for i in range(1, len(points)):
        x0, y0 = points[i - 1]
        x1, y1 = points[i]
        cx = (x0 + x1) / 2
        d += f" C{cx:.1f},{y0:.1f} {cx:.1f},{y1:.1f} {x1:.1f},{y1:.1f}"
    return d


def map_y(value, max_val) -> float:
    """Map a contribution count to a Y coordinate (inverted)."""
    if max_val == 0:
        return PAD_T + CHART_H
    ratio = value / max_val
    # Leave 10% padding at top of chart area
    return PAD_T + CHART_H - (ratio * CHART_H * 0.90)


def generate_svg(monthly_data, is_placeholder: bool = False) -> str:
    """Build the full SVG string."""
    n = len(monthly_data)
    max_val = max(c for _, c in monthly_data) if monthly_data else 1
    max_val = max(max_val, 1)

    # X positions (evenly spaced across chart width)
    xs = [PAD_L + i * (CHART_W / (n - 1)) if n > 1 else PAD_L + CHART_W / 2
          for i in range(n)]
    ys = [map_y(c, max_val) for _, c in monthly_data]
    pts = list(zip(xs, ys))

    # Area fill path (closed)
    area = bezier_path(pts)
    area_closed = f"{area} L{xs[-1]:.1f},{PAD_T + CHART_H} L{xs[0]:.1f},{PAD_T + CHART_H} Z"

    # Grid Y values
    grid_ys = [PAD_T + CHART_H * i / 4 for i in range(5)]
    grid_labels = [str(ceil(max_val * (4 - i) / 4)) for i in range(5)]

    # Build SVG
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    ph_note = " · PLACEHOLDER DATA" if is_placeholder else f" · Updated {now_str}"

    lines = [
        f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">',
        "  <defs>",
        f'    <linearGradient id="cBg" x1="0%" y1="0%" x2="100%" y2="100%">',
        f'      <stop offset="0%" style="stop-color:{BG_CARD}"/>',
        f'      <stop offset="100%" style="stop-color:#111117"/>',
        "    </linearGradient>",
        f'    <linearGradient id="lineG" x1="0%" y1="0%" x2="100%" y2="0%">',
        f'      <stop offset="0%" style="stop-color:{PURPLE}"/>',
        f'      <stop offset="50%" style="stop-color:{CYAN}"/>',
        f'      <stop offset="100%" style="stop-color:{LIME}"/>',
        "    </linearGradient>",
        f'    <linearGradient id="areaG" x1="0%" y1="0%" x2="0%" y2="100%">',
        f'      <stop offset="0%" style="stop-color:{CYAN};stop-opacity:0.18"/>',
        f'      <stop offset="100%" style="stop-color:{CYAN};stop-opacity:0"/>',
        "    </linearGradient>",
        f'    <linearGradient id="topDiv" x1="0%" y1="0%" x2="100%" y2="0%">',
        f'      <stop offset="0%" style="stop-color:{PURPLE};stop-opacity:0"/>',
        f'      <stop offset="30%" style="stop-color:{PURPLE}"/>',
        f'      <stop offset="70%" style="stop-color:{CYAN}"/>',
        f'      <stop offset="100%" style="stop-color:{CYAN};stop-opacity:0"/>',
        "    </linearGradient>",
        '    <filter id="glow"><feGaussianBlur stdDeviation="2.5" result="b"/>',
        '      <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>',
        '    <filter id="dGlow"><feGaussianBlur stdDeviation="3" result="b"/>',
        '      <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>',
        "    <style>",
        "      @keyframes lp{0%,100%{opacity:0.75}50%{opacity:1}}",
        "      @keyframes dp{0%,100%{r:4;opacity:1}50%{r:6;opacity:0.8}}",
        "      .cline{animation:lp 3s ease-in-out infinite}",
        "      .ldot{animation:dp 2s ease-in-out infinite}",
        "    </style>",
        "  </defs>",

        # Background
        f'  <rect width="{W}" height="{H}" rx="14" fill="url(#cBg)" stroke="{BORDER}" stroke-width="1"/>',
        f'  <rect x="0" y="0" width="4" height="{H}" rx="2" fill="{CYAN}"/>',

        # Header
        f'  <text x="22" y="28" font-family="\'Courier New\',monospace" font-size="10" fill="{CYAN}" letter-spacing="2">GITHUB CONTRIBUTION PROGRESS · 12 MONTHS</text>',
        f'  <text x="{W-16}" y="28" font-family="\'Courier New\',monospace" font-size="8" fill="{TEXT_DIM}" text-anchor="end">{ph_note}</text>',

        # Grid lines
        "  <g>",
    ]
    for gy, gl in zip(grid_ys, grid_labels):
        lines += [
            f'    <line x1="{PAD_L}" y1="{gy:.1f}" x2="{W-PAD_R}" y2="{gy:.1f}" stroke="{BORDER}" stroke-width="1"/>',
            f'    <text x="{PAD_L-6}" y="{gy+4:.1f}" font-family="\'Courier New\',monospace" font-size="8" fill="{TEXT_DIM}" text-anchor="end">{gl}</text>',
        ]
    lines.append("  </g>")

    # Vertical dashed guides
    lines.append(f'  <g stroke="{BORDER}" stroke-width="0.5" stroke-dasharray="3,3">')
    for x in xs:
        lines.append(f'    <line x1="{x:.1f}" y1="{PAD_T}" x2="{x:.1f}" y2="{PAD_T + CHART_H}"/>')
    lines.append("  </g>")

    # Area fill
    lines.append(f'  <path d="{area_closed}" fill="url(#areaG)"/>')

    # Main line (glow duplicate)
    main_path = bezier_path(pts)
    lines.append(f'  <path d="{main_path}" fill="none" stroke="{CYAN}" stroke-width="4" stroke-linecap="round" opacity="0.25" filter="url(#glow)"/>')
    lines.append(f'  <path d="{main_path}" fill="none" stroke="url(#lineG)" stroke-width="2.5" stroke-linecap="round" filter="url(#glow)" class="cline"/>')

    # Data points
    for i, (x, y) in enumerate(pts):
        is_last = (i == len(pts) - 1)
        col = LIME if is_last else CYAN
        cls = ' class="ldot"' if is_last else ''
        gf  = ' filter="url(#dGlow)"'
        r   = "5" if is_last else "3"
        lines.append(f'  <circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{col}"{gf}{cls}/>')
        if is_last:
            lines.append(f'  <circle cx="{x:.1f}" cy="{y:.1f}" r="10" fill="{col}" fill-opacity="0.2" class="ldot"/>')

    # Month labels
    lines.append("  <g>")
    for i, ((ym, _), x) in enumerate(zip(monthly_data, xs)):
        col = LIME if i == n - 1 else TEXT_DIM
        label = "NOW" if i == n - 1 else month_abbr(ym)
        lines.append(f'    <text x="{x:.1f}" y="{H - 8}" font-family="\'Courier New\',monospace" font-size="7.5" fill="{col}" text-anchor="middle">{label}</text>')
    lines.append("  </g>")

    # Bottom note
    note_text = "Chart updated daily via GitHub Actions · Real GitHub contribution data"
    if is_placeholder:
        note_text = "⚠ Placeholder data shown · Run GitHub Actions to generate real chart"
    lines.append(f'  <text x="{W//2}" y="{H-2}" font-family="\'Courier New\',monospace" font-size="8" fill="{TEXT_DIM}" text-anchor="middle">{note_text}</text>')

    lines.append("</svg>")
    return "\n".join(lines)


def placeholder_data():
    """12-month rising trend placeholder (illustrative only)."""
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    result = []
    counts = [4, 7, 12, 8, 15, 20, 18, 25, 22, 30, 28, 35]
    for i in range(12):
        m = (now.month - 11 + i)
        y = now.year + (m - 1) // 12
        m = ((m - 1) % 12) + 1
        key = f"{y:04d}-{m:02d}"
        result.append((key, counts[i]))
    return result


def main():
    print(f"[INFO] Generating progress chart for @{USERNAME}")
    monthly = fetch_contributions()
    is_ph   = monthly is None
    if is_ph:
        print("[INFO] Using placeholder data.")
        monthly = placeholder_data()

    svg = generate_svg(monthly, is_placeholder=is_ph)

    os.makedirs(os.path.dirname(OUT_PATH) if os.path.dirname(OUT_PATH) else ".", exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"[OK] Chart written to {OUT_PATH} ({len(monthly)} months)")


if __name__ == "__main__":
    main()
