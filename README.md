# Istation Historical Data Pull

Internal support tool for downloading historical Istation reports on behalf of districts. Built for the Amira Learning support team.

## What it does

- Pulls historical CSV exports from `secure.istation.com` for any district
- Supports Executive Summary, Usage, Usage Trend, Level Movement, and Completion reports
- Covers school years 2018-19 through 2024-25
- Runs fully automated after a one-time Google SSO login

## Quick Start

```bash
git clone https://github.com/derekarmesto-support/istation-historical-data-pull.git
cd istation-historical-data-pull
pip install streamlit selenium requests
streamlit run istation_dashboard.py --server.port 8503
```

Then open http://localhost:8503 in Chrome.

## Full Setup & Usage Guide

See the [Employee Handoff Guide](https://claude.ai/code/artifact/handoff) for step-by-step installation instructions (Mac and Windows) and a walkthrough of the Reports tab.

## Files

| File | Purpose |
|------|---------|
| `istation_dashboard.py` | Streamlit dashboard — start here |
| `istation_extractor.py` | Batch extractor for the Historical Run tab |
| `istation_live_actions.py` | On-demand downloader for the Reports tab |
| `filter_exports.py` | Utility for filtering exports by student ID |
| `Historical Data Request - Sheet1.csv` | Request queue for batch runs |
| `District name and organization oid.csv` | District name / OID lookup table |
| `requirements.txt` | Python dependencies |

## Requirements

- Python 3.9+
- Google Chrome (latest)
- ChromeDriver (Mac: via Homebrew; Windows: auto-managed by Selenium)
- Google account with Istation admin access

## Tabs

**Request Sheet** — View and manage the batch request queue. Add districts, school years, and products.

**Historical Run** — Launch the batch extractor against all pending rows in the request sheet.

**Reports** — On-demand single-district downloader. Fill in the form and hit Start Download.
