"""
Basketball Stats Scraper & Analyzer
Author: Madhur Gattani, Harshil Patel and Bevyn Mauru
Purpose: ITC Final Project - Interactive Streamlit Cloud demo
"""

import os
import time
from io import StringIO
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
# Fallback ids the site has used for the team per-game table
TABLE_ID_FALLBACKS = ["per_game-team", "per_game_team", "team-stats-per_game", "team_stats"]
GRAPH_TYPES = ["bar", "pie", "line", "scatter", "hist"]
# A bare "Mozilla/5.0" is often rejected (403); send normal browser headers
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/140.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
# Sports-Reference allows ~20 requests/minute; stay well under it
REQUEST_GAP_SECONDS = 4
MAX_RETRIES = 3
DATA_DIR = "data"
CHART_DIR = "charts"
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(CHART_DIR, exist_ok=True)


# ------------------------------------------------------------------
# Core functions (same logic as the original script, adapted to
# return values instead of printing, so the UI can display them)
# ------------------------------------------------------------------
_SESSION = requests.Session()
_SESSION.headers.update(HEADERS)
_last_request_time = 0.0


def _polite_get(url):
    """GET with spacing between requests and retry on rate limits / server errors."""
    global _last_request_time
    response = None
    for attempt in range(1, MAX_RETRIES + 1):
        wait = REQUEST_GAP_SECONDS - (time.time() - _last_request_time)
        if wait > 0:
            time.sleep(wait)
        try:
            response = _SESSION.get(url, timeout=30)
        except requests.RequestException as exc:
            _last_request_time = time.time()
            if attempt == MAX_RETRIES:
                return None, f"Network error fetching {url}: {exc}"
            time.sleep(5 * attempt)
            continue
        _last_request_time = time.time()

        if response.status_code == 200:
            return response, None
        if response.status_code in (429, 500, 502, 503, 504) and attempt < MAX_RETRIES:
            retry_after = response.headers.get("Retry-After", "")
            delay = int(retry_after) if retry_after.isdigit() else 10 * attempt
            time.sleep(min(delay, 60))
            continue
        break

    code = response.status_code if response is not None else "no response"
    hint = ""
    if code == 429:
        hint = " - rate limited by the site; wait a few minutes and try again"
    elif code == 403:
        hint = " - the site blocked the request"
    return None, f"Failed to fetch {url} (status {code}){hint}"


def _find_table(html, table_id):
    """Find the table, including ones the site hides inside HTML comments."""
    soup = BeautifulSoup(html, "lxml")
    candidates = [table_id] + [t for t in TABLE_ID_FALLBACKS if t != table_id]

    for tid in candidates:
        table = soup.find("table", id=tid)
        if table:
            return table
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        if "<table" not in comment:
            continue
        comment_soup = BeautifulSoup(comment, "lxml")
        for tid in candidates:
            table = comment_soup.find("table", id=tid)
            if table:
                return table
    # Last resort: any table whose id looks like a team per-game table
    for scope in [soup] + [BeautifulSoup(c, "lxml") for c in soup.find_all(string=lambda t: isinstance(t, Comment)) if "<table" in c]:
        for table in scope.find_all("table", id=True):
            tid = table["id"].lower()
            if "per_game" in tid and "team" in tid and "opp" not in tid:
                return table
    return None


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_table(url, table_id):
    response, error = _polite_get(url)
    if error:
        return None, error

    table = _find_table(response.text, table_id)
    if table is None:
        return None, f"Table '{table_id}' not found in {url}"

    df = pd.read_html(StringIO(str(table)))[0]

    # Flatten multi-row headers if present
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[-1] for col in df.columns]
    df.columns = [str(c).strip() for c in df.columns]

    df = df.drop(columns=[c for c in df.columns if c == "Rk"], errors="ignore")
    if "Team" in df.columns:
        df = df[df["Team"].notna()]
        df = df[df["Team"] != "Team"]  # repeated header rows
        df = df[~df["Team"].astype(str).str.contains("League Average", case=False)]
        df["Team"] = df["Team"].astype(str).str.replace("*", "", regex=False).str.strip()
    df = df.reset_index(drop=True)

    if df.empty:
        return None, f"Table found in {url} but it had no team rows"
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
