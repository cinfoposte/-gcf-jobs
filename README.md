# Green Climate Fund Job Scraper

Automated RSS feed generator for job listings from the Green Climate Fund (GCF).

## RSS Feed URL
**Live Feed:** `https://cinfoposte.github.io/gcf-jobs/gcf_jobs.xml`

## About
This scraper automatically fetches job listings from [jobs.greenclimate.fund](https://jobs.greenclimate.fund/en/sites/CX_1001/jobs) and generates an RSS 2.0 compliant feed that updates twice weekly.

## Features
- ✅ Scrapes JavaScript-rendered job listings using Selenium
- ✅ Generates W3C-valid RSS 2.0 feed
- ✅ Automated updates via GitHub Actions (Sundays & Wednesdays at 9:00 UTC)
- ✅ Publicly accessible via GitHub Pages
- ✅ No server required - runs entirely on GitHub infrastructure

## Update Schedule
The feed automatically updates:
- **Sundays** at 9:00 UTC
- **Wednesdays** at 9:00 UTC

## Job Information Included
Each job listing includes:
- Job title
- Direct link to application page
- Location
- Department (when available)
- Posting date (when available)

## Technical Details
- **Language:** Python 3.11
- **Scraping:** Selenium WebDriver with Chrome headless
- **Parsing:** BeautifulSoup4
- **Format:** RSS 2.0

## Local Usage

### Prerequisites
- Python 3.8+
- Chrome/Chromium browser

### Installation
```bash
pip install -r requirements.txt
```

### Run Scraper
```bash
python gcf_scraper.py
```

This generates `gcf_jobs.xml` in the current directory.

## Validation
Validate the RSS feed at: https://validator.w3.org/feed/

## About Green Climate Fund
The Green Climate Fund (GCF) is the world's largest dedicated climate fund, helping developing countries raise and realize their climate ambitions.

---

**Created by:** cinfoposte
**GitHub:** https://github.com/cinfoposte/gcf-jobs
**License:** MIT
