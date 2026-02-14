#!/usr/bin/env python3
"""
Research Radar - Automated research signal aggregator
Fetches from: arXiv, Semantic Scholar, HackerNews, Reddit
Outputs: JSON data files for dashboard consumption
"""

import json
import os
import time
import re
from datetime import datetime, timedelta
from pathlib import Path
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET

DATA_DIR = Path(__file__).parent.parent / "docs" / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ─── Configuration ───────────────────────────────────────────────────────────
# Edit these to customize your research radar

ARXIV_CATEGORIES = ["cs.HC", "cs.AI", "cs.CL", "cs.SE"]
ARXIV_KEYWORDS = [
    "human-AI collaboration",
    "LLM agent",
    "AI agent",
    "qualitative analysis",
    "human-centered AI",
    "responsible AI",
    "trustworthy AI",
    "human-LLM interaction",
    "AI-assisted analysis",
    "collaborative AI",
    "agentic AI",
    "computer-supported cooperative work",
]

SEMANTIC_SCHOLAR_KEYWORDS = [
    "human-AI collaboration LLM",
    "AI agent workflow",
    "LLM qualitative analysis",
    "human-centered AI systems",
]

# Authors to track on Semantic Scholar (name -> Semantic Scholar author ID)
# Find IDs at: https://www.semanticscholar.org/
TRACKED_AUTHORS = {
    "Shneiderman, Ben": "1740403",
    "Amershi, Saleema": "2668412",
    "Horvitz, Eric": "144901256",
    "Bansal, Gagan": "46610912",
    "Wu, Tongshuang": "47830705",
    "Liang, Percy": "2630822",
}

HN_KEYWORDS = [
    "AI agent",
    "LLM agent",
    "human-AI",
    "AI collaboration",
    "AI assistant",
    "agentic",
]

REDDIT_SUBREDDITS = ["MachineLearning", "artificial", "LocalLLaMA"]
REDDIT_KEYWORDS = ["agent", "human-AI", "agentic", "collaboration", "qualitative"]

DAYS_LOOKBACK = 7  # How many days back to search


# ─── Helpers ─────────────────────────────────────────────────────────────────

def safe_request(url, headers=None, max_retries=3, delay=2):
    """Make HTTP request with retries and rate limiting."""
    if headers is None:
        headers = {"User-Agent": "ResearchRadar/1.0 (academic research tool)"}
    req = urllib.request.Request(url, headers=headers)
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read().decode("utf-8")
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(delay * (attempt + 1))
            else:
                print(f"  ✗ Failed after {max_retries} attempts: {url[:80]}... — {e}")
                return None


def keyword_match(text, keywords):
    """Check if any keyword appears in text (case-insensitive)."""
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in keywords)


# ─── arXiv ───────────────────────────────────────────────────────────────────

def fetch_arxiv():
    """Fetch recent papers from arXiv matching our categories and keywords."""
    print("📄 Fetching arXiv papers...")
    results = []
    seen_ids = set()

    for keyword in ARXIV_KEYWORDS:
        # Search across our categories with this keyword
        cat_query = "+OR+".join(f"cat:{c}" for c in ARXIV_CATEGORIES)
        query = f'({cat_query})+AND+all:"{urllib.parse.quote(keyword)}"'
        url = (
            f"http://export.arxiv.org/api/query?search_query={query}"
            f"&start=0&max_results=20&sortBy=submittedDate&sortOrder=descending"
        )

        xml_data = safe_request(url)
        if not xml_data:
            continue

        root = ET.fromstring(xml_data)
        ns = {"atom": "http://www.w3.org/2005/Atom"}

        for entry in root.findall("atom:entry", ns):
            arxiv_id = entry.find("atom:id", ns).text.split("/abs/")[-1]
            if arxiv_id in seen_ids:
                continue
            seen_ids.add(arxiv_id)

            title = entry.find("atom:title", ns).text.strip().replace("\n", " ")
            summary = entry.find("atom:summary", ns).text.strip().replace("\n", " ")
            published = entry.find("atom:published", ns).text[:10]
            authors = [a.find("atom:name", ns).text for a in entry.findall("atom:author", ns)]
            categories = [c.get("term") for c in entry.findall("atom:category", ns)]
            link = f"https://arxiv.org/abs/{arxiv_id}"

            # Check if within lookback window
            pub_date = datetime.strptime(published, "%Y-%m-%d")
            if pub_date < datetime.now() - timedelta(days=DAYS_LOOKBACK + 2):
                continue

            results.append({
                "id": arxiv_id,
                "title": title,
                "authors": authors[:5],  # Limit to first 5
                "summary": summary[:500],
                "published": published,
                "categories": categories[:5],
                "link": link,
                "matched_keyword": keyword,
                "source": "arxiv",
            })

        time.sleep(3)  # Be nice to arXiv API

    # Deduplicate and sort by date
    results.sort(key=lambda x: x["published"], reverse=True)
    print(f"  ✓ Found {len(results)} arXiv papers")
    return results


# ─── Semantic Scholar ────────────────────────────────────────────────────────

def fetch_semantic_scholar():
    """Fetch papers from Semantic Scholar by keywords and tracked authors."""
    print("🔬 Fetching Semantic Scholar papers...")
    results = []
    seen_ids = set()
    api_key = os.environ.get("S2_API_KEY", "")
    headers = {"User-Agent": "ResearchRadar/1.0"}
    if api_key:
        headers["x-api-key"] = api_key

    # Keyword search
    for keyword in SEMANTIC_SCHOLAR_KEYWORDS:
        url = (
            f"https://api.semanticscholar.org/graph/v1/paper/search"
            f"?query={urllib.parse.quote(keyword)}"
            f"&limit=10&fields=title,authors,abstract,year,url,publicationDate,citationCount"
            f"&year={datetime.now().year}-{datetime.now().year}"
        )

        data = safe_request(url, headers=headers)
        if not data:
            continue

        try:
            parsed = json.loads(data)
            for paper in parsed.get("data", []):
                pid = paper.get("paperId", "")
                if pid in seen_ids or not pid:
                    continue
                seen_ids.add(pid)

                pub_date = paper.get("publicationDate", "")
                if pub_date:
                    try:
                        pd = datetime.strptime(pub_date, "%Y-%m-%d")
                        if pd < datetime.now() - timedelta(days=DAYS_LOOKBACK * 4):
                            continue
                    except ValueError:
                        pass

                results.append({
                    "id": pid,
                    "title": paper.get("title", ""),
                    "authors": [a["name"] for a in paper.get("authors", [])[:5]],
                    "summary": (paper.get("abstract") or "")[:500],
                    "published": pub_date or str(datetime.now().year),
                    "citations": paper.get("citationCount", 0),
                    "link": paper.get("url", ""),
                    "matched_keyword": keyword,
                    "source": "semantic_scholar",
                })
        except json.JSONDecodeError:
            pass

        time.sleep(1)

    # Tracked authors - recent papers
    for author_name, author_id in TRACKED_AUTHORS.items():
        url = (
            f"https://api.semanticscholar.org/graph/v1/author/{author_id}/papers"
            f"?limit=5&fields=title,authors,abstract,year,url,publicationDate,citationCount"
        )
        data = safe_request(url, headers=headers)
        if not data:
            continue

        try:
            parsed = json.loads(data)
            for paper in parsed.get("data", []):
                pid = paper.get("paperId", "")
                if pid in seen_ids or not pid:
                    continue
                seen_ids.add(pid)

                pub_date = paper.get("publicationDate", "")
                if pub_date:
                    try:
                        pd = datetime.strptime(pub_date, "%Y-%m-%d")
                        if pd < datetime.now() - timedelta(days=60):
                            continue
                    except ValueError:
                        pass

                results.append({
                    "id": pid,
                    "title": paper.get("title", ""),
                    "authors": [a["name"] for a in paper.get("authors", [])[:5]],
                    "summary": (paper.get("abstract") or "")[:500],
                    "published": pub_date or str(datetime.now().year),
                    "citations": paper.get("citationCount", 0),
                    "link": paper.get("url", ""),
                    "matched_keyword": f"author:{author_name}",
                    "source": "semantic_scholar",
                })
        except json.JSONDecodeError:
            pass

        time.sleep(1)

    results.sort(key=lambda x: x.get("published", ""), reverse=True)
    print(f"  ✓ Found {len(results)} Semantic Scholar papers")
    return results


# ─── HackerNews ──────────────────────────────────────────────────────────────

def fetch_hackernews():
    """Fetch relevant HN stories using Algolia search API."""
    print("🟠 Fetching HackerNews stories...")
    results = []
    seen_ids = set()
    cutoff = int((datetime.now() - timedelta(days=DAYS_LOOKBACK)).timestamp())

    for keyword in HN_KEYWORDS:
        url = (
            f"https://hn.algolia.com/api/v1/search?"
            f"query={urllib.parse.quote(keyword)}"
            f"&tags=story&numericFilters=created_at_i>{cutoff}"
            f"&hitsPerPage=10"
        )

        data = safe_request(url)
        if not data:
            continue

        try:
            parsed = json.loads(data)
            for hit in parsed.get("hits", []):
                hid = hit.get("objectID", "")
                if hid in seen_ids:
                    continue
                seen_ids.add(hid)

                results.append({
                    "id": hid,
                    "title": hit.get("title", ""),
                    "link": hit.get("url") or f"https://news.ycombinator.com/item?id={hid}",
                    "hn_link": f"https://news.ycombinator.com/item?id={hid}",
                    "points": hit.get("points", 0),
                    "comments": hit.get("num_comments", 0),
                    "published": hit.get("created_at", "")[:10],
                    "matched_keyword": keyword,
                    "source": "hackernews",
                })
        except json.JSONDecodeError:
            pass

        time.sleep(0.5)

    results.sort(key=lambda x: x.get("points", 0), reverse=True)
    print(f"  ✓ Found {len(results)} HN stories")
    return results


# ─── Reddit ──────────────────────────────────────────────────────────────────

def fetch_reddit():
    """Fetch relevant Reddit posts."""
    print("🔴 Fetching Reddit posts...")
    results = []
    seen_ids = set()

    for subreddit in REDDIT_SUBREDDITS:
        url = f"https://www.reddit.com/r/{subreddit}/new.json?limit=50"
        headers = {"User-Agent": "ResearchRadar/1.0 (academic research aggregator)"}

        data = safe_request(url, headers=headers)
        if not data:
            continue

        try:
            parsed = json.loads(data)
            for child in parsed.get("data", {}).get("children", []):
                post = child.get("data", {})
                rid = post.get("id", "")
                if rid in seen_ids:
                    continue

                title = post.get("title", "")
                selftext = post.get("selftext", "")
                combined = f"{title} {selftext}"

                if not keyword_match(combined, REDDIT_KEYWORDS):
                    continue

                seen_ids.add(rid)

                created = datetime.fromtimestamp(post.get("created_utc", 0))
                if created < datetime.now() - timedelta(days=DAYS_LOOKBACK):
                    continue

                results.append({
                    "id": rid,
                    "title": title,
                    "subreddit": subreddit,
                    "link": f"https://reddit.com{post.get('permalink', '')}",
                    "score": post.get("score", 0),
                    "comments": post.get("num_comments", 0),
                    "published": created.strftime("%Y-%m-%d"),
                    "matched_keyword": next(
                        (kw for kw in REDDIT_KEYWORDS if kw.lower() in combined.lower()),
                        ""
                    ),
                    "source": "reddit",
                })
        except json.JSONDecodeError:
            pass

        time.sleep(2)

    results.sort(key=lambda x: x.get("score", 0), reverse=True)
    print(f"  ✓ Found {len(results)} Reddit posts")
    return results


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    print(f"\n{'='*60}")
    print(f"  Research Radar — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}\n")

    all_data = {
        "meta": {
            "fetched_at": datetime.now().isoformat(),
            "lookback_days": DAYS_LOOKBACK,
            "keywords": ARXIV_KEYWORDS,
        },
        "arxiv": fetch_arxiv(),
        "semantic_scholar": fetch_semantic_scholar(),
        "hackernews": fetch_hackernews(),
        "reddit": fetch_reddit(),
    }

    # Write combined data
    output_path = DATA_DIR / "latest.json"
    with open(output_path, "w") as f:
        json.dump(all_data, f, indent=2, ensure_ascii=False)

    # Also write a dated archive
    date_str = datetime.now().strftime("%Y-%m-%d")
    archive_path = DATA_DIR / f"archive-{date_str}.json"
    with open(archive_path, "w") as f:
        json.dump(all_data, f, indent=2, ensure_ascii=False)

    total = sum(len(all_data[k]) for k in ["arxiv", "semantic_scholar", "hackernews", "reddit"])
    print(f"\n✅ Done! Total items: {total}")
    print(f"   Output: {output_path}")


if __name__ == "__main__":
    main()
