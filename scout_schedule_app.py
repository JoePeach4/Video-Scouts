import streamlit as st
import pandas as pd
import requests
from io import StringIO

SHEET_ID = "1tO3A9D8O2Wbir1jmKMkOh85EIPsrB5NjNZAJJ5K1aHo"
GID = "1299150361"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

st.set_page_config(page_title="Video Week 183 – Scout Schedule", page_icon="🎬", layout="wide")

st.markdown("""
<style>
.game-card{background:#f8f9fa;border-left:4px solid #e63946;border-radius:8px;padding:1rem 1.2rem;margin-bottom:0.8rem}
.game-card h4{margin:0 0 0.4rem 0;color:#1a1a2e;font-size:1.05rem}
.tag{display:inline-block;background:#e63946;color:white;border-radius:12px;padding:2px 10px;font-size:0.78rem;margin-right:6px;margin-top:4px}
.tag-player{background:#457b9d}
.metric-box{background:#1a1a2e;color:white;border-radius:10px;padding:0.8rem 1rem;text-align:center;margin-bottom:0.5rem}
.metric-box .num{font-size:2rem;font-weight:700}
.metric-box .label{font-size:0.8rem;opacity:0.75}
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=300)
def load_data():
    try:
        response = requests.get(CSV_URL, timeout=15)
        response.raise_for_status()
    except Exception as e:
        return None, str(e)
    df_raw = pd.read_csv(StringIO(response.text), header=None)
    header_row = 0
    for i, row in df_raw.iterrows():
        row_vals = [str(v).strip() for v in row]
        if "Fixture Date" in row_vals or "Home Team" in row_vals:
            header_row = i
            break
    df = pd.read_csv(StringIO(response.text), header=header_row)
    df.columns = df.columns.str.strip()
    return df, None

df, error = load_data()

if error:
    st.error(f"❌ Could not load Google Sheet: {error}")
    st.info("Make sure the sheet is shared: Share → 'Anyone with the link' → Viewer")
    st.stop()

if df is None or df.empty:
    st.warning("Sheet loaded but appears empty.")
    st.stop()

required_cols = ["Fixture Date", "Home Team", "Away Team", "Scout", "Player 1", "Player 2"]
missing = [c for c in required_cols if c not in df.columns]
if missing:
    st.error(f"Missing columns: {missing}")
    st.write("Columns found:", df.columns.tolist())
    st.dataframe(df.head(10))
    st.stop()

df = df[required_cols].copy()
df.dropna(subset=["Home Team", "Away Team"], inplace=True)
df = df[df["Home Team"].str.strip() != ""]
df["Fixture Date"] = pd.to_datetime(df["Fixture Date"], errors="coerce", dayfirst=True)
df.sort_values("Fixture Date", inplace=True)

valid_scouts = sorted(df["Scout"].dropna().str.strip().unique().tolist())
valid_scouts = [s for s in valid_scouts if s]

if "logged_in_scout" not in st.session_state:
    st.session_state.logged_in_scout = None

if st.session_state.logged_in_scout is None:
    st.markdown("# 🎬 Video Week 183")
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("### 👤 Scout Login")
        st.markdown("Enter your full name to view your assigned games.")
        name_input = st.text_input("Full Name", placeholder="e.g. John Smith")
        login_btn = st.button("View My Schedule", type="primary", use_container_width=True)
        if login_btn:
            name_clean = name_input.strip()
            matched = next((s for s in valid_scouts if s.lower() == name_clean.lower()), None)
            if matched:
                st.session_state.logged_in_scout = matched
                st.rerun()
            elif name_clean == "":
                st.warning("Please enter your full name.")
            else:
                st.error(f"❌ '{name_clean}' was not found. Check your name matches exactly as assigned in the schedule.")
    st.stop()

scout = st.session_state.logged_in_scout
filtered = df[df["Scout"].str.strip().str.lower() == scout.lower()].copy()

col_title, col_logout = st.columns([5, 1])
with col_title:
    st.markdown(f"# 🎬 Video Week 183 – {scout}'s Schedule")
    st.markdown(f"Showing all games assigned to **{scout}**")
with col_logout:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🚪 Log Out", use_container_width=True):
        st.session_state.logged_in_scout = None
        st.rerun()

st.markdown("---")
st.sidebar.header("🔍 Filter My Games")

valid_dates = filtered["Fixture Date"].dropna()
if not valid_dates.empty:
    min_d, max_d = valid_dates.min().date(), valid_dates.max().date()
    date_range = st.sidebar.date_input("Date range", value=(min_d, max_d), min_value=min_d, max_value=max_d) if min_d < max_d else (min_d, max_d)
else:
    date_range = None

team_search = st.sidebar.text_input("Search team", placeholder="e.g. Arsenal")
player_search = st.sidebar.text_input("Search player", placeholder="e.g. Smith")

if date_range and len(date_range) == 2:
    filtered = filtered[(filtered["Fixture Date"] >= pd.Timestamp(date_range[0])) & (filtered["Fixture Date"] <= pd.Timestamp(date_range[1]))]
if team_search:
    filtered = filtered[filtered["Home Team"].str.contains(team_search, case=False, na=False) | filtered["Away Team"].str.contains(team_search, case=False, na=False)]
if player_search:
    filtered = filtered[filtered["Player 1"].str.contains(player_search, case=False, na=False) | filtered["Player 2"].str.contains(player_search, case=False, na=False)]

c1, c2, c3, c4 = st.columns(4)
all_players = pd.concat([filtered["Player 1"], filtered["Player 2"]]).dropna().unique()
for col, num, label in [(c1, len(filtered), "Games"), (c2, filtered["Fixture Date"].nunique(), "Matchdays"), (c3, len(all_players), "Players to Scout"), (c4, pd.concat([filtered["Home Team"], filtered["Away Team"]]).nunique(), "Teams")]:
    col.markdown(f'<div class="metric-box"><div class="num">{num}</div><div class="label">{label}</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
view_mode = st.radio("View as", ["📋 Cards", "📊 Table"], horizontal=True)

if filtered.empty:
    st.info("No games match the current filters.")
elif view_mode == "📋 Cards":
    for date, group in filtered.groupby(filtered["Fixture Date"].dt.date, sort=True):
        st.markdown(f"### 📅 {pd.Timestamp(date).strftime('%A, %d %B %Y')}")
        for _, row in group.iterrows():
            p_tags = "".join([f'<span class="tag tag-player">👤 {row[p]}</span>' for p in ["Player 1","Player 2"] if pd.notna(row[p]) and str(row[p]).strip()])
            if not p_tags:
                p_tags = '<span style="color:#aaa;font-size:0.85rem">No players assigned</span>'
            st.markdown(f'<div class="game-card"><h4>⚽ {row["Home Team"]} vs {row["Away Team"]}</h4>{p_tags}</div>', unsafe_allow_html=True)
        st.markdown("---")
else:
    display = filtered.copy()
    display["Fixture Date"] = display["Fixture Date"].dt.strftime("%d %b %Y")
    st.dataframe(display.drop(columns=["Scout"]).reset_index(drop=True), use_container_width=True, height=500)

st.sidebar.markdown("---")
export = filtered.copy()
export["Fixture Date"] = export["Fixture Date"].dt.strftime("%d %b %Y")
st.sidebar.download_button("⬇️ Download My Schedule (CSV)", export.drop(columns=["Scout"]).to_csv(index=False).encode(), f"VideoWeek183_{scout.replace(' ','_')}.csv", "text/csv")
st.sidebar.caption("Data refreshes every 5 minutes from Google Sheets.")
