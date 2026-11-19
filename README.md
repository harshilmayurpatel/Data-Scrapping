# NBA Stats Scraper & Analyzer

Scrapes team per-game statistics for four NBA seasons and one WNBA season from [Basketball-Reference](https://www.basketball-reference.com/), runs summary statistics, and draws charts, all from a live Streamlit app.

**▶ [Try the live app](https://data-scrapping-aonbno2rm9z9adkfkvaxwy.streamlit.app/)**: pick a league and season, click **Scrape & Analyze**, and watch it fetch, analyze and chart the data in real time. If the app has been asleep, Streamlit takes a few seconds to wake it.

```
Basketball-Reference pages ──► Requests + BeautifulSoup ──► Pandas DataFrame
                                                                  │
         Charts (PNG) ◄── Matplotlib / Seaborn ◄── Summary stats ◄┤
                                                                  │
                                    CSV snapshot + change check ◄─┘
```

## What it does
- **Scrapes 5 pages:** NBA 2021, 2022, 2023, 2024 and WNBA 2023 team per-game tables.
- **Parses the HTML itself** with BeautifulSoup, including tables the site hides inside HTML comments.
- **Summarizes** points per game for each season: mean, median, mode, min and max.
- **Charts the top 10 teams** by points per game, with a different chart type per season (bar, pie, line, scatter, histogram).
- **Detects changes:** each run saves a CSV and compares it with the previous snapshot, so updated stats are flagged.

## Built to be reliable
- **Polite scraping:** stays under the site's rate limit (one request about every 4 seconds) and retries on rate limits or server errors.
- **Robust parsing:** falls back to other table IDs the site has used, so a small markup change doesn't break a run.
- **Real browser headers,** because a bare user agent is often refused.
- **Cloud-safe plotting:** a headless Matplotlib backend, and every figure is closed after saving.

## Stack
Python · Requests · BeautifulSoup · Pandas · NumPy · Matplotlib · Seaborn · Streamlit

## Run locally
```bash
git clone https://github.com/harshilmayurpatel/nba-stats-scraper.git
cd nba-stats-scraper
pip install -r requirements.txt
streamlit run app.py
```
Then open the URL Streamlit prints (usually http://localhost:8501).

## Project structure
```
app.py            Scraper, analysis, charts and the Streamlit UI
requirements.txt  Dependencies
```

## Team
A team project by Madhur Gattani, Harshil Patel and Bevyn Mauru. The work was presented at ICERI as "Web Scraping and Data Analysis using BeautifulSoup".

---
More of my work: **[harshilmayurpatel.github.io](https://harshilmayurpatel.github.io/)**
