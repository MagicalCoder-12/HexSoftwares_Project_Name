"""
YouTube Data Dashboard with Streamlit
--------------------------------------
Interactive dashboard for visualizing YouTube channel analytics:
views, subscriber growth, top videos, and engagement metrics.

Usage:
    conda activate ml
    streamlit run youtube_dashboard.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import random
import time

st.set_page_config(page_title="YouTube Data Dashboard", layout="wide")
st.title("📺 YouTube Data Dashboard")
st.markdown("Analyze video views, subscriber growth, and engagement metrics.")

# ---------------------------------------------------------------------------
# SAMPLE DATA GENERATOR (fallback when no API key is provided)
# ---------------------------------------------------------------------------
def generate_sample_data():
    """Generate realistic sample YouTube channel data for demonstration."""
    random.seed(42)
    np.random.seed(42)

    # Channel overview
    channel_stats = {
        "Subscribers": 1_250_000,
        "Total Views": 187_000_000,
        "Total Videos": 423,
        "Avg Views/Video": 442_000,
    }

    # Monthly subscriber growth (24 months)
    months = pd.date_range("2024-01-01", periods=24, freq="ME")
    base_subs = 800_000
    sub_growth = []
    for i in range(24):
        base_subs += np.random.randint(8_000, 45_000)
        sub_growth.append(base_subs + int(np.random.normal(0, 5000)))

    subscriber_history = pd.DataFrame({
        "Month": months,
        "Subscribers": sub_growth,
        "New Subscribers": [np.random.randint(8_000, 50_000) for _ in range(24)],
    })

    # Top 20 videos
    video_titles = [
        f"How to {" ".join(np.random.choice(
            ["Build", "Learn", "Master", "Create", "Understand", "Deploy",
             "Optimize", "Debug", "Design", "Automate", "Scale", "Test",
             "Refactor", "Integrate", "Analyze"], size=3))} in Python"
        for _ in range(20)
    ]

    top_videos = pd.DataFrame({
        "Video": [t[:40] + "..." for t in video_titles],
        "Views": np.random.randint(200_000, 5_000_000, 20),
        "Likes": np.random.randint(5_000, 250_000, 20),
        "Comments": np.random.randint(200, 15_000, 20),
        "Watch Time (hours)": np.random.randint(50_000, 2_000_000, 20),
        "Publish Date": [
            datetime(2024, 1, 1) + timedelta(days=random.randint(0, 700))
            for _ in range(20)
        ],
    })
    top_videos["Engagement Rate"] = (
        (top_videos["Likes"] + top_videos["Comments"]) / top_videos["Views"] * 100
    ).round(2)
    top_videos = top_videos.sort_values("Views", ascending=False).reset_index(drop=True)

    return channel_stats, subscriber_history, top_videos


# ---------------------------------------------------------------------------
# YOUTUBE DATA API INTEGRATION
# ---------------------------------------------------------------------------
def fetch_youtube_data(api_key, channel_id):
    """Fetch real data from YouTube Data API v3."""
    try:
        from googleapiclient.discovery import build

        youtube = build("youtube", "v3", developerKey=api_key)

        # Channel statistics
        channel_resp = youtube.channels().list(
            part="statistics,snippet", id=channel_id
        ).execute()

        if not channel_resp["items"]:
            st.error("Channel not found. Check the Channel ID.")
            return None, None, None

        ch = channel_resp["items"][0]
        stats = ch["statistics"]
        channel_stats = {
            "Subscribers": int(stats.get("subscriberCount", 0)),
            "Total Views": int(stats.get("viewCount", 0)),
            "Total Videos": int(stats.get("videoCount", 0)),
            "Avg Views/Video": (
                int(stats.get("viewCount", 0)) // max(int(stats.get("videoCount", 1)), 1)
            ),
        }

        # Recent videos
        videos_resp = youtube.search().list(
            part="snippet", channelId=channel_id,
            order="date", maxResults=50, type="video"
        ).execute()

        video_ids = [item["id"]["videoId"] for item in videos_resp["items"]]

        video_data = []
        for vid in video_ids:
            v_resp = youtube.videos().list(
                part="statistics,snippet", id=vid
            ).execute()
            if v_resp["items"]:
                v = v_resp["items"][0]
                sts = v["statistics"]
                video_data.append({
                    "Video": v["snippet"]["title"][:50],
                    "Views": int(sts.get("viewCount", 0)),
                    "Likes": int(sts.get("likeCount", 0)),
                    "Comments": int(sts.get("commentCount", 0)),
                    "Publish Date": v["snippet"]["publishedAt"][:10],
                })

        if not video_data:
            st.warning("No videos found for this channel.")
            return channel_stats, None, None

        top_videos = pd.DataFrame(video_data)
        top_videos["Watch Time (hours)"] = top_videos["Views"] * np.random.uniform(
            0.05, 0.15, len(top_videos)
        ).astype(int)
        top_videos["Engagement Rate"] = (
            (top_videos["Likes"] + top_videos["Comments"]) / top_videos["Views"] * 100
        ).round(2)
        top_videos = top_videos.sort_values("Views", ascending=False).reset_index(drop=True)

        return channel_stats, None, top_videos

    except Exception as e:
        st.error(f"API Error: {e}")
        return None, None, None


# ---------------------------------------------------------------------------
# SIDEBAR CONFIGURATION
# ---------------------------------------------------------------------------
st.sidebar.header("⚙️ Configuration")

use_api = st.sidebar.checkbox("Use YouTube Data API", value=False)

channel_stats = None
subscriber_history = None
top_videos = None

if use_api:
    api_key = st.sidebar.text_input("YouTube API Key", type="password")
    channel_id = st.sidebar.text_input(
        "Channel ID",
        help="Found in the channel's URL: youtube.com/channel/UC...",
    )
    if st.sidebar.button("Fetch Data") and api_key and channel_id:
        with st.spinner("Fetching data from YouTube API..."):
            channel_stats, subscriber_history, top_videos = fetch_youtube_data(
                api_key, channel_id
            )
    elif not api_key or not channel_id:
        st.sidebar.info("Enter API Key and Channel ID, then click 'Fetch Data'.")
        channel_stats, subscriber_history, top_videos = generate_sample_data()
        st.sidebar.info("ℹ️ Showing sample data. Provide API credentials for live data.")
    else:
        channel_stats, subscriber_history, top_videos = generate_sample_data()
else:
    channel_stats, subscriber_history, top_videos = generate_sample_data()
    st.sidebar.info("ℹ️ Showing sample data. Check 'Use YouTube Data API' for live data.")


# ---------------------------------------------------------------------------
# MAIN DASHBOARD
# ---------------------------------------------------------------------------
if channel_stats is None:
    channel_stats, subscriber_history, top_videos = generate_sample_data()

# --- KPI Cards ---
st.subheader("📊 Channel Overview")
kpi_cols = st.columns(len(channel_stats))
for i, (label, value) in enumerate(channel_stats.items()):
    with kpi_cols[i]:
        if value >= 1_000_000:
            display = f"{value / 1_000_000:.2f}M"
        elif value >= 1_000:
            display = f"{value / 1_000:.1f}K"
        else:
            display = str(value)
        st.metric(label=label, value=display)

# --- Top Performing Videos ---
st.subheader("🏆 Top Performing Videos")

sort_by = st.selectbox("Sort videos by:", ["Views", "Likes", "Comments", "Engagement Rate"])
top_n = st.slider("Number of videos to display:", 5, 20, 10)

sorted_videos = top_videos.sort_values(sort_by, ascending=False).head(top_n)

fig_bar = px.bar(
    sorted_videos,
    x=sort_by,
    y="Video",
    orientation="h",
    color=sort_by,
    color_continuous_scale="viridis",
    title=f"Top {top_n} Videos by {sort_by}",
)
fig_bar.update_layout(yaxis={"categoryorder": "total ascending"}, height=500)
st.plotly_chart(fig_bar, use_container_width=True)

# --- Video Details Table ---
with st.expander("📋 View Video Details Table"):
    st.dataframe(
        top_videos.head(20).style.format({
            "Views": "{:,.0f}",
            "Likes": "{:,.0f}",
            "Comments": "{:,.0f}",
            "Watch Time (hours)": "{:,.0f}",
            "Engagement Rate": "{:.2f}%",
        }),
        use_container_width=True,
        hide_index=True,
    )

# --- Engagement Analysis ---
st.subheader("📈 Engagement Analysis")

col1, col2 = st.columns(2)

with col1:
    # Views vs Likes scatter
    fig_scatter = px.scatter(
        top_videos.head(20),
        x="Views",
        y="Likes",
        size="Comments",
        color="Engagement Rate",
        hover_name="Video",
        title="Views vs Likes (bubble size = Comments)",
        color_continuous_scale="plasma",
        trendline="ols",
    )
    st.plotly_chart(fig_scatter, use_container_width=True)

with col2:
    # Engagement rate distribution
    fig_hist = px.histogram(
        top_videos,
        x="Engagement Rate",
        nbins=20,
        title="Distribution of Engagement Rates",
        color_discrete_sequence=["#FF6B6B"],
        marginal="box",
    )
    st.plotly_chart(fig_hist, use_container_width=True)

# --- Subscriber Growth Trends ---
if subscriber_history is not None:
    st.subheader("📈 Subscriber Growth Trends")

    growth_metric = st.radio(
        "Select metric:", ["Subscribers", "New Subscribers"], horizontal=True
    )

    fig_line = go.Figure()
    fig_line.add_trace(go.Scatter(
        x=subscriber_history["Month"],
        y=subscriber_history[growth_metric],
        mode="lines+markers",
        name=growth_metric,
        line=dict(color="#FF0000", width=3),
        marker=dict(size=6),
    ))

    fig_line.update_layout(
        title=f"{growth_metric} Over Time",
        xaxis_title="Month",
        yaxis_title=growth_metric,
        height=450,
        hovermode="x unified",
    )
    st.plotly_chart(fig_line, use_container_width=True)

    # Growth rate
    subscriber_history["Growth Rate (%)"] = subscriber_history["New Subscribers"].pct_change(
    ) * 100
    avg_growth = subscriber_history["New Subscribers"].mean()

    st.metric(
        label="Avg Monthly Subscriber Growth",
        value=f"{avg_growth:,.0f}",
        delta=f"{subscriber_history['Growth Rate (%)'].mean():.1f}% monthly",
    )

# --- Publish Date Analysis ---
st.subheader("📅 Publishing Patterns & Performance")
if "Publish Date" in top_videos.columns:
    top_videos["Publish Date"] = pd.to_datetime(top_videos["Publish Date"])
    top_videos["Publish Month"] = top_videos["Publish Date"].dt.to_period("M").astype(str)

    monthly_perf = top_videos.groupby("Publish Month").agg(
        {"Views": "sum", "Likes": "sum", "Comments": "sum", "Video": "count"}
    ).rename(columns={"Video": "Video Count"}).reset_index()

    fig_multi = go.Figure()
    fig_multi.add_trace(go.Bar(
        x=monthly_perf["Publish Month"],
        y=monthly_perf["Views"] / 1e6,
        name="Views (M)",
        marker_color="#FF6B6B",
    ))
    fig_multi.add_trace(go.Scatter(
        x=monthly_perf["Publish Month"],
        y=monthly_perf["Video Count"],
        name="Videos Published",
        yaxis="y2",
        line=dict(color="#4ECDC4", width=3),
        mode="lines+markers",
    ))

    fig_multi.update_layout(
        title="Monthly Views vs Videos Published",
        xaxis_title="Month",
        yaxis_title="Total Views (Millions)",
        yaxis2=dict(
            title="Videos Published",
            overlaying="y",
            side="right",
            showgrid=False,
        ),
        height=400,
        hovermode="x unified",
        legend=dict(x=0.01, y=0.99),
    )
    st.plotly_chart(fig_multi, use_container_width=True)

# --- Correlation Heatmap ---
st.subheader("🔗 Metric Correlations")
numeric_cols = top_videos.select_dtypes(include=[np.number]).columns
corr_data = top_videos[numeric_cols].dropna()

if len(corr_data) > 1:
    corr_matrix = corr_data.corr()

    fig_heatmap = px.imshow(
        corr_matrix,
        text_auto=".2f",
        color_continuous_scale="RdBu_r",
        aspect="auto",
        title="Correlation Between Video Metrics",
        zmin=-1,
        zmax=1,
    )
    fig_heatmap.update_layout(height=500)
    st.plotly_chart(fig_heatmap, use_container_width=True)

# --- Footer ---
st.markdown("---")
st.caption(
    "Built with Streamlit, Plotly & YouTube Data API v3 | "
    "Data refreshes on each fetch."
)
