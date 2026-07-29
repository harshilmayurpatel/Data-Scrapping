# 🏀 Basketball Stats Scraper & Analyzer

A Python project that scrapes team per-game statistics from [Basketball-Reference.com](https://www.basketball-reference.com/) for four NBA seasons and one WNBA season, runs basic statistical analysis, and generates charts — all packaged into a live, interactive demo.

---

## 🚀 Live Demo

**Try it live on Streamlit Community Cloud:** https://data-scrapping-aonbno2rm9z9adkfkvaxwy.streamlit.app/

> No installation needed — pick a league/season in the app and click **Scrape & Analyze** to see it fetch live data, compute stats, and draw the chart in real time.

---

## 📋 Project Requirements Checklist

| Requirement | Status | Explanation |
|---|---|---|
| Pulls data from the internet | ✅ | Using `requests` + `BeautifulSoup` |
| Pulls data from 5 different webpages (using pandas) | ✅ | 5 different Basketball-Reference pages scraped |
| Basic calculations on numerical data from 3+ pages | ✅ | Performed in `summarize_column()` |
| Use of your own methods where appropriate | ✅ | `fetch_table()`, `summarize_column()`, `check_if_file_changed()` |
| Produce at least 3 charts from 3 pages | ✅ | One chart generated per dataset (5 total) |
| Save the data to a file | ✅ | Each dataset saved as CSV via `to_csv()` |
| 1 webpage changes daily | ✅ | CSV comparison flags updates automatically |
| 5 webpages from 5 different sources | ✅ | 5 different pages on Basketball-Reference |
| Basic calculations on all 5 webpages | ✅ | Summary stats printed wherever `PTS` exists |
| Use BeautifulSoup on 1+ webpage to parse HTML | ✅ | Used for all 5 webpages |
| Produce 5 charts from all 5 webpages | ✅ | One chart per dataset — 5 total |
| Save the charts as images | ✅ | Each chart saved as `.png` |
| Read previous file and check if data changed | ✅ | Handled by `check_if_file_changed()` |

### Additional enhancements

- Full BeautifulSoup parsing instead of `pandas.read_html`
- Custom `User-Agent` headers to avoid request blocking
- Seaborn styling for cleaner plots
- Per-file change detection printed for every run
- Explicit `plt.close()` after every chart to avoid memory buildup
- **Interactive Streamlit interface** so the whole pipeline can be demoed live in the browser instead of only via terminal output

---

## 🛠 Tech Stack

`requests` · `BeautifulSoup4` · `pandas` · `matplotlib` · `seaborn` · `numpy` · `streamlit`

---

## 📦 Run Locally

```bash
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>
pip install -r requirements.txt
streamlit run app.py
```

Then open the local URL Streamlit prints (usually `http://localhost:8501`).

---

## ☁️ Deployment Notes

**Why Streamlit Cloud instead of Hugging Face Spaces:** Hugging Face changed its policy so that creating a new Gradio or Docker Space now requires a paid plan — only Static Spaces are free. Since this project needs a live Python backend (to scrape on demand), Streamlit Community Cloud was used instead, which hosts interactive Python apps for free.

**To deploy on Streamlit Community Cloud:**
1. Push `app.py` and `requirements.txt` to a public GitHub repo (this one).
2. Go to [share.streamlit.io](https://share.streamlit.io), sign in with GitHub, and click **New app**.
3. Select this repo, branch `main`, and main file path `app.py`.
4. Click **Deploy** — Streamlit builds the environment from `requirements.txt` and gives you a public `*.streamlit.app` URL.
5. Paste that URL into the **Live Demo** section at the top of this README.

---

## 📁 Suggested Repo Structure

```
.
├── app.py                    # Streamlit app (also the deployment entry point)
├── requirements.txt          # Dependencies
├── README.md                 # This file
└── projectrequirements.txt   # Original detailed requirements checklist
```

---

## 📄 Code

<details>
<summary>Click to expand <code>app.py</code></summary>

```python
"""
Basketball Stats Scraper & Analyzer
Author: Madhur Gattani, Harshil Patel and Bevyn Mauru
Purpose: ITC Final Project - Interactive Streamlit Cloud demo
"""

import os
import numpy as np
import pandas as pd
import requests
import streamlit as st
import matplotlib
matplotlib.use("Agg")  # headless backend, safe for cloud hosting
import matplotlib.pyplot as plt
import seaborn as sns
from bs4 import BeautifulSoup, Comment

sns.set(style="whitegrid")

# ------------------------------------------------------------------
# Config
# ------------------------------------------------------------------
URLS = {
    "nba_2021": "https://www.basketball-reference.com/leagues/NBA_2021.html",
    "nba_2022": "https://www.basketball-reference.com/leagues/NBA_2022.html",
    "nba_2023": "https://www.basketball-reference.com/leagues/NBA_2023.html",
    "nba_2024": "https://www.basketball-reference.com/leagues/NBA_2024.html",
    "wnba_2023": "https://www.basketball-reference.com/wnba/years/2023.html",
}

TABLE_IDS = {key: "per_game-team" for key in URLS}
GRAPH_TYPES = ["bar", "pie", "line", "scatter", "hist"]
HEADERS = {"User-Agent": "Mozilla/5.0"}
DATA_DIR = "data"
CHART_DIR = "charts"
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(CHART_DIR, exist_ok=True)


# ------------------------------------------------------------------
# Core functions (same logic as the original script, adapted to
# return values instead of printing, so the UI can display them)
# ------------------------------------------------------------------
def fetch_table(url, table_id):
    response = requests.get(url, headers=HEADERS, timeout=20)
    if response.status_code != 200:
        return None, f"Failed to fetch {url} (status {response.status_code})"

    soup = BeautifulSoup(response.content, "html.parser")
    table = soup.find("table", id=table_id)

    if not table:
        comments = soup.find_all(string=lambda text: isinstance(text, Comment))
        for comment in comments:
            if table_id in comment:
                comment_soup = BeautifulSoup(comment, "html.parser")
                table = comment_soup.find("table", id=table_id)
                if table:
                    break

    if not table:
        return None, f"Table '{table_id}' not found in {url}"

    headers_list = [th.text.strip() for th in table.thead.find_all("th") if th.text.strip() != "Rk"]
    rows = []
    for row in table.tbody.find_all("tr"):
        if row.get("class") and "thead" in row["class"]:
            continue
        cols = row.find_all("td")
        stats = [td.text.strip() for td in cols]
        if len(stats) == len(headers_list):
            rows.append(stats)

    df = pd.DataFrame(rows, columns=headers_list)
    return df, f"Scraped {len(df)} rows from {url}"


def summarize_column(df, col_name, label):
    df[col_name] = pd.to_numeric(df[col_name], errors="coerce")
    mode_val = df[col_name].mode().iloc[0] if not df[col_name].mode().empty else "N/A"
    return (
        f"**Summary for {label} - {col_name}**\n\n"
        f"- Mean: {df[col_name].mean():.2f}\n"
        f"- Median: {df[col_name].median():.2f}\n"
        f"- Mode: {mode_val}\n"
        f"- Min: {df[col_name].min()}\n"
        f"- Max: {df[col_name].max()}\n"
    )


def check_if_file_changed(filename, new_df):
    if not os.path.exists(filename):
        return f"{os.path.basename(filename)} created (new)."
    old_df = pd.read_csv(filename)
    if old_df.equals(new_df):
        return f"{os.path.basename(filename)} has not changed."
    return f"{os.path.basename(filename)} has changed!"


def make_chart(df, key, graph_type, chart_path):
    df = df.copy()
    df["PTS"] = pd.to_numeric(df["PTS"], errors="coerce")
    df = df.dropna(subset=["PTS"])
    top10 = df.sort_values("PTS", ascending=False).head(10)

    plt.figure(figsize=(10, 6))
    if graph_type == "bar":
        sns.barplot(data=top10, x="PTS", y="Team", hue="Team", palette="coolwarm", legend=False)
        plt.title(f"Bar Plot - Top 10 Teams by PTS ({key.upper()})")
    elif graph_type == "pie":
        plt.pie(top10["PTS"], labels=top10["Team"], autopct="%1.1f%%", startangle=140)
        plt.title(f"Pie Chart - Top 10 Teams by PTS ({key.upper()})")
        plt.axis("equal")
    elif graph_type == "line":
        plt.plot(top10["Team"], top10["PTS"], marker="o")
        plt.title(f"Line Graph - Top 10 Teams by PTS ({key.upper()})")
        plt.xlabel("Team")
        plt.ylabel("Points Per Game")
        plt.xticks(rotation=45)
    elif graph_type == "scatter":
        plt.scatter(top10["PTS"], np.arange(len(top10)), c=top10["PTS"], cmap="viridis", s=100)
        plt.yticks(np.arange(len(top10)), top10["Team"])
        plt.title(f"Scatter Plot - Top 10 Teams by PTS ({key.upper()})")
        plt.xlabel("Points Per Game")
        plt.ylabel("Team")
    elif graph_type == "hist":
        sns.histplot(top10["PTS"], kde=True, color="green")
        plt.title(f"Histogram - Distribution of PTS ({key.upper()})")
        plt.xlabel("Points Per Game")

    plt.tight_layout()
    plt.savefig(chart_path)
    plt.close()
    return top10


# ------------------------------------------------------------------
# Pipeline
# ------------------------------------------------------------------
def process_one(key, idx):
    url = URLS[key]
    df, fetch_msg = fetch_table(url, TABLE_IDS[key])
    log = [f"Scraping {key.upper()} from {url}", fetch_msg]

    if df is None:
        return log, None, "", None

    csv_path = os.path.join(DATA_DIR, f"{key}.csv")
    log.append(check_if_file_changed(csv_path, df))
    df.to_csv(csv_path, index=False)

    summary_text = ""
    if "PTS" in df.columns:
        summary_text = summarize_column(df, "PTS", key.upper())

    graph_type = GRAPH_TYPES[idx % len(GRAPH_TYPES)]
    chart_path = os.path.join(CHART_DIR, f"{key}_chart.png")
    top10 = make_chart(df, key, graph_type, chart_path)
    log.append(f"Saved chart as {chart_path} ({graph_type} chart)")

    return log, top10, summary_text, chart_path


def run_analysis(selection):
    if not selection:
        return "Please select at least one league/season.", None, "", []

    keys = list(URLS.keys()) if "All Leagues" in selection else selection

    all_log = []
    all_summaries = []
    charts = []
    last_table = None

    for idx, key in enumerate(keys):
        try:
            log, top10, summary_text, chart_path = process_one(key, idx)
        except Exception as exc:
            log, top10, summary_text, chart_path = ([f"Error processing {key}: {exc}"], None, "", None)
        all_log.extend(log)
        if summary_text:
            all_summaries.append(summary_text)
        if chart_path:
            charts.append(chart_path)
        if top10 is not None:
            last_table = top10

    all_log.append("\nAll tasks completed!")
    status = "\n".join(all_log)
    summary = "\n\n---\n\n".join(all_summaries) if all_summaries else "No summary available."
    return status, last_table, summary, charts


# ------------------------------------------------------------------
# Streamlit UI
# ------------------------------------------------------------------
st.set_page_config(page_title="Basketball Stats Scraper & Analyzer", page_icon="🏀", layout="wide")

st.title("🏀 Basketball Stats Scraper & Analyzer")
st.markdown(
    "Live scraping + analysis of team per-game stats from "
    "[Basketball-Reference.com](https://www.basketball-reference.com/). "
    "Pick one or more leagues/seasons below, or choose **All Leagues** to "
    "reproduce the full original pipeline.\n\n"
    "_Built by Madhur Gattani, Harshil Patel and Bevyn Mauru — ITC Final Project._"
)

LEAGUE_CHOICES = list(URLS.keys()) + ["All Leagues"]
selection = st.multiselect(
    "Select league(s)/season(s)",
    LEAGUE_CHOICES,
    default=["nba_2024"],
)

if st.button("🚀 Scrape & Analyze", type="primary"):
    with st.spinner("Scraping live data and generating charts..."):
        status, last_table, summary, charts = run_analysis(selection)

    st.subheader("Status Log")
    st.text(status)

    if summary:
        st.subheader("Statistical Summary")
        st.markdown(summary)

    if last_table is not None:
        st.subheader("Top 10 Teams by PTS (most recent selection)")
        st.dataframe(last_table)

    if charts:
        st.subheader("Generated Charts")
        cols = st.columns(2)
        for i, chart_path in enumerate(charts):
            with cols[i % 2]:
                st.image(chart_path)
```

</details>
