# Research Radar 📡

Automated research signal aggregator that monitors arXiv, Semantic Scholar, HackerNews, and Reddit for topics relevant to your research. Outputs a clean dashboard hosted on GitHub Pages.

## How It Works

```
GitHub Actions (Mon & Thu, 8:00 UTC)
    → Python script fetches from all sources
    → Writes JSON to docs/data/
    → Commits & pushes
    → GitHub Pages serves the dashboard
```

## Quick Setup (10 minutes)

### 1. Create GitHub Repository

```bash
cd research-radar
git init
git add .
git commit -m "Initial setup"
gh repo create research-radar --private --push
# or: create repo on GitHub and push manually
```

### 2. Enable GitHub Pages

1. Go to repo → **Settings** → **Pages**
2. Set source to **GitHub Actions**

### 3. (Optional) Add Semantic Scholar API Key

For higher rate limits on Semantic Scholar:
1. Get a free key at https://www.semanticscholar.org/product/api
2. Go to repo → **Settings** → **Secrets and variables** → **Actions**
3. Add secret: `S2_API_KEY` = your key

### 4. Run It

- **Manual trigger**: Go to **Actions** tab → "Research Radar - Weekly Fetch" → "Run workflow"
- **Automatic**: Runs every Monday and Thursday at 8:00 UTC

### 5. View Dashboard

After first run, your dashboard will be at:
```
https://<your-username>.github.io/research-radar/
```

## Customization

Edit `scripts/fetch_all.py` to change:

- **`ARXIV_KEYWORDS`** — What to search on arXiv
- **`ARXIV_CATEGORIES`** — Which arXiv categories to monitor (cs.HC, cs.AI, cs.CL, cs.SE)
- **`TRACKED_AUTHORS`** — Semantic Scholar author IDs to follow
- **`HN_KEYWORDS`** / **`REDDIT_KEYWORDS`** — Community discussion filters
- **`REDDIT_SUBREDDITS`** — Which subreddits to monitor
- **`DAYS_LOOKBACK`** — Time window for results (default: 7 days)

### Finding Semantic Scholar Author IDs

1. Go to https://www.semanticscholar.org/
2. Search for an author
3. The ID is in the URL: `semanticscholar.org/author/Name/AUTHOR_ID`

### Changing Schedule

Edit `.github/workflows/fetch.yml`, the `cron` line:
```yaml
- cron: '0 8 * * 1,4'  # Mon & Thu at 8:00 UTC
- cron: '0 8 * * 1'    # Weekly on Monday
- cron: '0 8 * * *'    # Daily
```

## Local Development

```bash
# Run fetch locally
python scripts/fetch_all.py

# Preview dashboard
cd docs && python -m http.server 8000
# Open http://localhost:8000
```

## Dashboard Features

- **Source filtering** — Toggle between arXiv, Semantic Scholar, HN, Reddit
- **Keyword filtering** — Click keyword pills to drill down
- **Search** — Full text search across titles, authors, abstracts (press `/` to focus)
- **Responsive** — Works on mobile

## Adding X/Twitter Monitoring

Twitter/X requires API access ($100/month for Basic tier). If you have access, create `scripts/fetch_twitter.py` and add accounts/keywords to track. An alternative free approach:

1. Use [Nitter](https://nitter.net) RSS feeds (when available)
2. Or use a service like [Feedbin](https://feedbin.com) which can convert Twitter to RSS

For now, the dashboard covers the most important academic signals without Twitter API costs.

## Adding Google Scholar Alerts

Google Scholar Alerts don't have an API, but you can:

1. Set up alerts at https://scholar.google.com/scholar_alerts
2. Have them delivered to your email
3. The Semantic Scholar integration in this tool covers similar ground with better API access
