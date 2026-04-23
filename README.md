# 2026 KDF Marathon — Race Plan

Interactive race plan for the 2026 Kentucky Derby Festival Marathon (Louisville, KY — April 25, 2026).

**[Open the interactive plan → keanegleeson.github.io/kdf-marathon-2026](https://keanegleeson.github.io/kdf-marathon-2026/)**

## What's in here

| File | Purpose |
| --- | --- |
| `race_plan.html` | The interactive plan — map, elevation profile, splits, fueling, mile-by-mile cues. Self-contained (only external deps are Leaflet + Chart.js via CDN). |
| `index.html` | Redirect to `race_plan.html` so the GitHub Pages root URL works. |
| `KDF_Marathon.gpx` | A previous runner's GPX of the course (the source of truth for the route + elevation profile). |
| `2026-Humana-miniMarathon-Marathon-Course.pdf` | Official KDF course map (water/Powerade/medical icons). |
| `Activities.csv` | Garmin Connect activity export (training log used for fitness calibration). |
| `route_data.json` | Sampled GPX + per-mile/per-km elevation summary (embedded into the HTML at build time). |
| `analyze_gpx.py` | Per-mile elevation breakdown of the GPX (CLI). |
| `export_route.py` | Sample the GPX and emit `route_data.json`. |
| `render_pdf.py` | Render the official PDF to `course_page_1.png` (was used to read off aid station positions). |
| `build_html.py` | Build `race_plan.html` end-to-end from the GPX. |

## Rebuilding the HTML

```bash
py export_route.py    # GPX → route_data.json
py build_html.py      # → race_plan.html
```

Python 3.11+; only stdlib + (for `render_pdf.py`) `pymupdf`.

## Goals (current)

| Goal | Pace | Finish (chip) |
| --- | --- | --- |
| Stretch | 4:00 / km | ~2:48:50 |
| Watch prediction | 4:03 / km | ~2:50:55 |
| Sim pace | 4:08 / km | ~2:54:25 |

Course: 26.22 mi / 42.20 km certified (GPX measured ~26.44 / ~42.55 due to GPS drift on city loops).

## Course profile

Three phases:
- **Km 1–18 (mi 1–11)** — net mildly downhill through downtown + Old Louisville. Easy to overcook.
- **Km 19–26 (mi 12–16)** — Iroquois Park climb (~30 m / ~94 ft sustained over ~1.5 km, then rolling), then big descent back out.
- **Km 27–42 (mi 17–26)** — flat grind back via Eastern Pkwy to the Waterfront finish.
