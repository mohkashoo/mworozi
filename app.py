import os
import time
import json
import math
import sqlite3
import threading
import urllib.request
from datetime import datetime
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

import streamlit as st
import streamlit.components.v1 as components
import networkx as nx
import matplotlib.pyplot as plt
import pandas as pd

from generator import generate_honeytokens, DEPARTMENT_PROMPTS

# ── SQLite Database (production persistence layer) ──────────────────
DB_PATH = os.environ.get("EMBER_DB", "ember.db")
_db_lock = threading.Lock()


def _init_db():
    with _db_lock:
        conn = sqlite3.connect(DB_PATH, timeout=30.0, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
        conn.execute(
            "CREATE TABLE IF NOT EXISTS events ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "timestamp TEXT NOT NULL,"
            "type TEXT NOT NULL,"
            "target TEXT,"
            "ip TEXT DEFAULT '',"
            "ua TEXT DEFAULT ''"
            ")"
        )
        conn.commit()
    return conn


_db_conn = _init_db()


def _db_insert(ts, ev_type, target, ip="", ua=""):
    with _db_lock:
        _db_conn.execute(
            "INSERT INTO events (timestamp, type, target, ip, ua) VALUES (?, ?, ?, ?, ?)",
            (ts, ev_type, target, ip, ua),
        )
        _db_conn.commit()


def _db_query(limit=100):
    with _db_lock:
        rows = _db_conn.execute(
            "SELECT timestamp, type, target, ip, ua FROM events ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [(r[0], r[1], r[2], r[3], r[4]) for r in rows]


def _db_count():
    with _db_lock:
        return _db_conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]


def _db_count_by_type(ev_type):
    with _db_lock:
        return _db_conn.execute("SELECT COUNT(*) FROM events WHERE type=?", (ev_type,)).fetchone()[0]


def _db_clear():
    with _db_lock:
        _db_conn.execute("DELETE FROM events")
        _db_conn.commit()


# ── Async Slack Webhook (background thread, never blocks UI) ─────────
def _send_slack(webhook_url, text):
    if not webhook_url:
        return

    def _fire():
        try:
            payload = json.dumps({"text": text}).encode()
            req = urllib.request.Request(
                webhook_url, data=payload,
                headers={"Content-Type": "application/json"},
            )
            urllib.request.urlopen(req, timeout=5)
        except Exception:
            pass

    threading.Thread(target=_fire, daemon=True).start()


# ── Config ─────────────────────────────────────────────────────────────
ALERTS_LOG = os.environ.get("EMBER_ALERTS_LOG", "alerts.log")
TRACKING_PORT = int(os.environ.get("EMBER_TRACKING_PORT", "8765"))
DEFAULT_OUTPUT = os.environ.get("EMBER_OUTPUT_DIR", "./honeytokens")
CONFIG_PATH = os.environ.get("EMBER_CONFIG", "ember_config.json")


def _load_config():
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH) as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _save_config(key, value):
    try:
        cfg = _load_config()
        cfg[key] = value
        with open(CONFIG_PATH, "w") as f:
            json.dump(cfg, f)
    except Exception:
        pass

# ── Local GeoIP dictionary (fully offline, no network calls) ────────
GEOIP_DB = {
    "127.0.0.1": ("Kigali", "Rwanda", "🇷🇼"),
    "::1": ("Kigali", "Rwanda", "🇷🇼"),
    "localhost": ("Kigali", "Rwanda", "🇷🇼"),
    "192.168.": ("Nairobi", "Kenya", "🇰🇪"),
    "10.": ("Lagos", "Nigeria", "🇳🇬"),
    "172.16.": ("Cape Town", "South Africa", "🇿🇦"),
    "172.17.": ("Cape Town", "South Africa", "🇿🇦"),
    "172.18.": ("Cape Town", "South Africa", "🇿🇦"),
    "172.19.": ("Cape Town", "South Africa", "🇿🇦"),
    "172.20.": ("Cape Town", "South Africa", "🇿🇦"),
    "172.21.": ("Cape Town", "South Africa", "🇿🇦"),
    "172.22.": ("Cape Town", "South Africa", "🇿🇦"),
    "172.23.": ("Cape Town", "South Africa", "🇿🇦"),
    "172.24.": ("Cape Town", "South Africa", "🇿🇦"),
    "172.25.": ("Cape Town", "South Africa", "🇿🇦"),
    "172.26.": ("Cape Town", "South Africa", "🇿🇦"),
    "172.27.": ("Cape Town", "South Africa", "🇿🇦"),
    "172.28.": ("Cape Town", "South Africa", "🇿🇦"),
    "172.29.": ("Cape Town", "South Africa", "🇿🇦"),
    "172.30.": ("Cape Town", "South Africa", "🇿🇦"),
    "172.31.": ("Cape Town", "South Africa", "🇿🇦"),
    "41.": ("Nairobi", "Kenya", "🇰🇪"),
    "102.": ("Johannesburg", "South Africa", "🇿🇦"),
    "105.": ("Casablanca", "Morocco", "🇲🇦"),
    "154.": ("Accra", "Ghana", "🇬🇭"),
    "196.": ("Cairo", "Egypt", "🇪🇬"),
    "197.": ("Tunis", "Tunisia", "🇹🇳"),
}


def geoip(ip: str) -> str:
    if not ip:
        return "📍 Unknown"
    if ip in ("127.0.0.1", "::1", "localhost"):
        return "🇷🇼 Kigali, Rwanda (Local Simulation)"
    for prefix, (city, country, flag) in GEOIP_DB.items():
        if ip.startswith(prefix):
            return f"{flag} {city}, {country}"
    return f"📍 {ip}"
if not os.path.exists(ALERTS_LOG):
    with open(ALERTS_LOG, "w") as f:
        f.write("")

# ── Tracking pixel endpoint (lightweight HTTP server in background) ──
PIXEL_GIF = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00"
    b"\xff\xff\xff\x00\x00\x00"
    b"!\xf9\x04\x00\x00\x00\x00\x00"
    b",\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
)


class TrackingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path.rstrip("/") == "/track":
            params = parse_qs(parsed.query)
            filename = params.get("file", ["unknown"])[0]
            ts = datetime.now().isoformat()
            ip = self.client_address[0]
            ua = self.headers.get("User-Agent", "unknown")
            line = f"{ts}|TRACK|{filename}|{ip}|{ua}\n"
            with open(ALERTS_LOG, "a") as f:
                f.write(line)
            _db_insert(ts, "TRACK", filename, ip, ua)
            self.send_response(200)
            self.send_header("Content-Type", "image/gif")
            self.send_header("Content-Length", str(len(PIXEL_GIF)))
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
            self.end_headers()
            self.wfile.write(PIXEL_GIF)
        else:
            self.send_response(204)
            self.end_headers()

    def log_message(self, fmt, *args):
        pass


_tracking_server = None
_TRACKING_STARTED = False
_tracking_lock = threading.Lock()


def _start_tracking_server_once():
    global _tracking_server, _TRACKING_STARTED
    if _TRACKING_STARTED:
        return
    with _tracking_lock:
        if _TRACKING_STARTED:
            return
        try:
            _tracking_server = HTTPServer(("0.0.0.0", TRACKING_PORT), TrackingHandler)
        except OSError:
            _TRACKING_STARTED = True
            return
        t = threading.Thread(target=_tracking_server.serve_forever, daemon=True)
        t.start()
        _TRACKING_STARTED = True


@st.cache_resource
def _ensure_tracking_server():
    _start_tracking_server_once()
    return TRACKING_PORT


# ── Page config ───────────────────────────────────────────────────────
st.set_page_config(
    page_title="Project Ember — AI HoneyToken Factory",
    page_icon="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/icons/activity.svg",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items=None,
)

# ── Styles (High-Contrast Dark Theme — Optimized for Projectors) ────
st.markdown(
    """
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@500;700;800&family=Inter:wght@500;600;700;800&display=swap');

    * { font-family: 'Inter', sans-serif; }
    .stApp { background: #0a0e17; }
    .main > div { background: #0a0e17; }

    h1, h2, h3 { font-family: 'Inter', sans-serif !important; font-weight: 800 !important; }
    h1 { color: #ffffff !important; letter-spacing: -0.5px; font-size: 2rem !important; }
    h3 { color: #ffffff !important; font-size: 1rem !important; text-transform: uppercase; letter-spacing: 2px; }

    .stButton button {
        background: linear-gradient(135deg, #1565c0, #1976d2) !important;
        color: #ffffff !important;
        border: 2px solid rgba(255,255,255,0.2) !important;
        border-radius: 8px !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
        transition: all 0.3s ease !important;
    }
    .stButton button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 24px rgba(21,101,192,0.5);
    }
    button[kind="primary"] {
        background: linear-gradient(135deg, #d32f2f, #f44336) !important;
        border: 2px solid rgba(255,255,255,0.3) !important;
    }
    button[kind="primary"]:hover {
        box-shadow: 0 4px 24px rgba(211,47,47,0.5) !important;
    }

    div[data-testid="stMetricValue"] {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 2.5rem !important;
        font-weight: 800 !important;
        color: #ffffff !important;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 0.8rem !important;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        color: #aaa !important;
        font-weight: 600 !important;
    }
    div[data-testid="metric-container"] {
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.12);
        border-radius: 12px;
        padding: 16px;
    }

    .stAlert { border-left: 5px solid #f44336 !important; background: rgba(244,67,54,0.12) !important; }
    .stAlert p { color: #ffffff !important; font-weight: 600 !important; }
    .stInfo { border-left: 5px solid #42a5f5 !important; background: rgba(66,165,245,0.12) !important; }
    .stInfo p { color: #ffffff !important; }
    .stSuccess { border-left: 5px solid #66bb6a !important; background: rgba(102,187,106,0.12) !important; }
    .stSuccess p { color: #ffffff !important; }
    .stWarning { border-left: 5px solid #ffa726 !important; background: rgba(255,167,38,0.12) !important; }
    .stWarning p { color: #ffffff !important; }

    .stTextInput input, .stSelectbox, .stNumberInput input {
        background: rgba(255,255,255,0.08) !important;
        border: 2px solid rgba(255,255,255,0.15) !important;
        border-radius: 8px !important;
        color: #ffffff !important;
        font-size: 1rem !important;
    }
    .stTextInput input:focus {
        border-color: #42a5f5 !important;
        box-shadow: 0 0 0 3px rgba(66,165,245,0.3) !important;
    }
    .stSelectbox div[data-baseweb="select"] > div {
        border: 2px solid rgba(255,255,255,0.15) !important;
        background: rgba(255,255,255,0.08) !important;
    }

    .st-bq { background: rgba(255,255,255,0.04) !important; border: 1px solid rgba(255,255,255,0.1) !important; border-radius: 12px !important; }
    .stSidebar { background: #0d1117 !important; border-right: 2px solid rgba(255,255,255,0.08) !important; }
    .stSidebar .st-bq { background: transparent !important; border: none !important; }
    .stSidebar .stMarkdown p { color: #ccc !important; }

    div[data-testid="stExpander"] {
        background: rgba(255,255,255,0.03) !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        border-radius: 12px !important;
    }
    div[data-testid="stExpander"] summary p {
        font-weight: 700 !important;
        color: #ffffff !important;
    }

    .stDataFrame { background: rgba(255,255,255,0.03) !important; border-radius: 8px !important; border: 1px solid rgba(255,255,255,0.08) !important; }
    .stDataFrame th { font-size: 0.75rem !important; text-transform: uppercase; letter-spacing: 1.5px; color: #aaa !important; font-weight: 700 !important; }
    .stDataFrame td { font-size: 0.85rem !important; color: #ffffff !important; font-family: 'JetBrains Mono', monospace !important; font-weight: 500 !important; }

    .stCode { background: rgba(255,255,255,0.05) !important; border: 1px solid rgba(255,255,255,0.1) !important; color: #ffffff !important; }
    .stCode code { color: #ffffff !important; }
    .stSpinner > div { border-color: #f44336 transparent transparent transparent !important; border-width: 4px !important; }

    .stCaption { color: #999 !important; font-size: 0.85rem !important; }
    hr { border-color: rgba(255,255,255,0.1) !important; border-width: 1px !important; }

    div[data-testid="stNotification"] { background: #1a1a2e !important; border: 1px solid #f44336 !important; }
    div[data-testid="stNotification"] p { color: #ffffff !important; font-weight: 600 !important; }

    @keyframes flashRed {
        0%, 100% { opacity: 1; box-shadow: 0 0 0 0 rgba(244,67,54,0.6); }
        50% { opacity: 0.5; box-shadow: 0 0 30px 15px rgba(244,67,54,0.2); }
    }
    .flash-node { animation: flashRed 0.8s ease-in-out infinite; }

    @keyframes slideDown {
        from { transform: translateY(-100%); opacity: 0; }
        to { transform: translateY(0); opacity: 1; }
    }
    .alert-banner { animation: slideDown 0.3s ease-out; }
</style>
""",
    unsafe_allow_html=True,
)

# ── Session state ─────────────────────────────────────────────────────
for key, default in [
    ("deployed", False),
    ("company_name", "Acme Kenya Ltd"),
    ("industry", "Financial Services"),
    ("output_dir", DEFAULT_OUTPUT),
    ("last_alert_count", 0),
    ("accessed_files", set()),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ── Streamlit intercept for /track requests hitting port 8501 ────────
try:
    _qp = st.query_params
    if "file" in _qp:
        fname = _qp["file"]
        ts = datetime.now().isoformat()
        with open(ALERTS_LOG, "a") as f:
            f.write(f"{ts}|TRACK|{fname}|127.0.0.1|streamlit-intercept\n")
        _db_insert(ts, "TRACK", fname, "127.0.0.1", "streamlit-intercept")
except Exception:
    pass

# ── Start tracking pixel HTTP server (once per session) ─────────────
_ensure_tracking_server()

# ── Browser Notification Permission ─────────────────────────────────
st.markdown(
    """
<script>
if ('Notification' in window && Notification.permission === 'default') {
    Notification.requestPermission();
}
</script>
""",
    unsafe_allow_html=True,
)

# ── Helpers ───────────────────────────────────────────────────────────


def parse_alerts():
    accessed = set()
    all_events = _db_query(500)
    # Merge legacy alerts.log entries for backward compat
    if os.path.exists(ALERTS_LOG):
        with open(ALERTS_LOG, "r") as f:
            for raw in f:
                raw = raw.strip()
                if not raw:
                    continue
                parts = raw.split("|", 4)
                try:
                    ts_str = parts[0]
                    ev_type = parts[1]
                    target = parts[2]
                    ip = parts[3] if len(parts) > 3 else ""
                    detail = parts[4] if len(parts) > 4 else ""
                except (IndexError, ValueError):
                    continue
                all_events.append((ts_str, ev_type, target, ip, detail))
    # Deduplicate by (timestamp, type, target)
    seen = set()
    unique = []
    for ev in all_events:
        key = (ev[0], ev[1], ev[2])
        if key not in seen:
            seen.add(key)
            unique.append(ev)
            if ev[1] in ("TRACK", "MODIFIED", "DELETED", "MOVED"):
                accessed.add(ev[2])
    unique.sort(key=lambda x: x[0])
    return accessed, unique


def build_static_graph(company_name, manifest_entries):
    G = nx.DiGraph()
    center = f"File Server\n{company_name}"
    G.add_node(center, type="server", label=company_name)

    dept_files = {}
    for entry in manifest_entries:
        dept = entry.get("department", "Unknown")
        fname = entry.get("file", "")
        dept_files.setdefault(dept, []).append(fname)

    for dept in sorted(dept_files):
        dept_node = f"[{dept}]"
        G.add_node(dept_node, type="department")
        G.add_edge(center, dept_node)
        for fname in dept_files[dept]:
            short = fname[:45] + "…" if len(fname) > 45 else fname
            G.add_node(short, type="file", full_name=fname)
            G.add_edge(dept_node, short)

    return G, center


def layout_positions(G, center):
    pos = {}
    center_node = None
    for n, attr in G.nodes(data=True):
        if attr.get("type") == "server":
            center_node = n
            break
    if not center_node:
        center_node = list(G.nodes())[0]
    pos[center_node] = (0, 0)

    dept_nodes = [n for n in G.nodes if n != center_node and G.nodes[n].get("type") == "department"]
    n_depts = len(dept_nodes)

    if n_depts > 0:
        dept_spacing = max(5, n_depts * 1.5)
        total_width = (n_depts - 1) * dept_spacing
        start_x = -total_width / 2
        for i, dn in enumerate(dept_nodes):
            x = start_x + i * dept_spacing
            pos[dn] = (x, -3)
            children = [c for c in G.successors(dn) if G.nodes[c].get("type") == "file"]
            n_files = len(children)
            if n_files > 0:
                file_spacing = 2.2
                file_total = (n_files - 1) * file_spacing
                file_start = x - file_total / 2
                for j, fn in enumerate(children):
                    pos[fn] = (file_start + j * file_spacing, -5.5)

    leftover = [n for n in G.nodes if n not in pos]
    for n in leftover:
        pos[n] = (0, -8)
    return pos


def draw_graph(G, pos, accessed_files, container):
    accessed = set()
    for af in accessed_files:
        base = os.path.basename(af)
        accessed.add(base)

    node_colors = []
    node_sizes = []
    for n in G.nodes:
        ntype = G.nodes[n].get("type", "")
        full_name = G.nodes[n].get("full_name", "")
        base_name = os.path.basename(full_name) if full_name else ""
        is_accessed = (base_name in accessed or n in accessed or full_name in accessed)

        if ntype == "server":
            node_colors.append("#1565c0")
            node_sizes.append(5000)
        elif ntype == "department":
            node_colors.append("#e65100")
            node_sizes.append(3000)
        else:
            node_colors.append("#c62828" if is_accessed else "#2e7d32")
            node_sizes.append(2200)

    fig, ax = plt.subplots(figsize=(20, 12))
    fig.patch.set_facecolor("#0d1117")
    ax.set_facecolor("#0d1117")

    nx.draw_networkx_edges(
        G, pos, ax=ax,
        edge_color="#444",
        arrows=True,
        arrowsize=25,
        arrowstyle="-|>",
        width=3,
        alpha=0.5,
    )

    nx.draw_networkx_nodes(
        G, pos, ax=ax,
        node_color=node_colors,
        node_size=node_sizes,
        edgecolors="#666",
        linewidths=3,
    )

    labels = {}
    for n in G.nodes:
        ntype = G.nodes[n].get("type", "")
        label = n[:50]
        if len(n) > 50:
            label += "…"
        labels[n] = label

    for ntype_filter, font_sz in [("server", 17), ("department", 14), ("file", 11)]:
        filtered = {n: l for n, l in labels.items() if G.nodes[n].get("type", "") == ntype_filter}
        if filtered:
            nx.draw_networkx_labels(
                G, pos, ax=ax,
                labels=filtered,
                font_size=font_sz,
                font_color="#e0e0e0",
                font_weight="bold",
                bbox=dict(facecolor="#1a1a2e", edgecolor="#333", alpha=0.95, pad=5, boxstyle="round,pad=0.4"),
            )

    ax.set_title(
        "Project Ember — HoneyToken Minefield",
        fontsize=24, fontweight="bold", color="#e0e0e0", pad=20,
    )
    ax.axis("off")
    fig.tight_layout()
    container.pyplot(fig)
    plt.close(fig)


# ── UI ────────────────────────────────────────────────────────────────
st.markdown(
    "<h1 style='display:flex; align-items:center; gap:12px; margin-bottom:0;'>"
    "<span style='background:linear-gradient(135deg,#c62828,#ff1744); "
    "width:40px; height:40px; border-radius:10px; display:flex; "
    "align-items:center; justify-content:center; font-size:1.4rem;'>"
    "<i class='bi bi-activity' style='color:#fff;'></i></span> "
    "<span style='background:linear-gradient(135deg,#e0e0e0,#fff); "
    "-webkit-background-clip:text; -webkit-text-fill-color:transparent;'>"
    "Project Ember</span></h1>",
    unsafe_allow_html=True,
)
st.markdown(
    "<p style='color:#666; margin-top:-8px; font-size:0.9rem; letter-spacing:0.5px;'>"
    "<i class='bi bi-shield-check' style='margin-right:6px;'></i>"
    "The AI HoneyToken Factory — Deploy intelligent decoys to trap ransomware &amp; malicious insiders</p>",
    unsafe_allow_html=True,
)

# ── Sidebar: Configuration ───────────────────────────────────────────
with st.sidebar:
    st.header("Configuration")

    company_name = st.text_input(
        "Company Name",
        value=st.session_state.company_name,
        placeholder="e.g., Acme Kenya Ltd",
    )
    st.session_state.company_name = company_name

    industry = st.text_input(
        "Industry",
        value=st.session_state.industry,
        placeholder="e.g., Financial Services",
    )
    st.session_state.industry = industry

    departments = list(DEPARTMENT_PROMPTS.keys())
    selected_dept = st.selectbox("Department", departments, index=0)

    output_dir = st.text_input(
        "Output Directory",
        value=st.session_state.output_dir,
    )
    st.session_state.output_dir = output_dir

    _cfg = _load_config()
    tracker_base_url = st.text_input(
        "Tracking Server Public URL",
        value=_cfg.get("tracker_base_url", "http://localhost:8765"),
        placeholder="http://localhost:8765 or https://track.loca.lt",
        help="Public URL of the tracking server for pixel beacons. Use localhost for local testing, or the localtunnel URL for judges to test from their own laptops.",
    )
    _save_config("tracker_base_url", tracker_base_url)
    st.caption(f"Pixel: `{tracker_base_url}/track?file=FILENAME`")

    # Parse the base URL for the generator
    try:
        parsed_url = urlparse(tracker_base_url)
        tracker_host = parsed_url.hostname or "localhost"
        tracker_port = parsed_url.port or 8765
    except Exception:
        tracker_host = "localhost"
        tracker_port = 8765

    col1, col2 = st.columns(2)
    with col1:
        deploy_btn = st.button("Deploy HoneyTokens", type="primary", width="stretch")
    with col2:
        if st.button("Clear Alerts", width="stretch"):
            open(ALERTS_LOG, "w").close()
            _db_clear()
            st.session_state.accessed_files = set()
            st.rerun()

    with st.expander("Notifications & Deployment", expanded=False):
        slack_url = st.text_input(
            "Slack Webhook URL",
            value=_cfg.get("slack_url", ""),
            placeholder="https://hooks.slack.com/services/...",
            help="Paste a Slack Incoming Webhook URL to get push alerts on your phone",
        )
        _save_config("slack_url", slack_url)
        smb_path = st.text_input(
            "Deploy Target Path",
            value=_cfg.get("smb_path", ""),
            placeholder="/mnt/fileserver/shared/ or //SERVER/share",
            help="SMB/network path to auto-deploy honeytokens (optional)",
        )
        _save_config("smb_path", smb_path)
    
    st.divider()
    st.markdown(
        "**How it works**\n\n"
        "1. Configure your company profile\n"
        "2. Click Deploy to generate 3 realistic decoy files\n"
        "3. Place the files on a file server or share\n"
        "4. The dashboard monitors for file access & modification\n"
        "5. When a trap is triggered, you get an instant alert"
    )

# ── Deploy ────────────────────────────────────────────────────────────
if deploy_btn:
    with st.spinner("🧠 Gemini is crafting your honeytokens..."):
        try:
            manifest = generate_honeytokens(
                company_name=company_name,
                department=selected_dept,
                output_dir=output_dir,
                tracker_host=tracker_host,
                tracker_port=tracker_port,
            )
            st.session_state.deployed = True
            st.success(
                f"Deployed {len(manifest)} honeytokens to `{output_dir}/`",
            )
            for entry in manifest:
                st.code(f"  {entry['file']}  —  tracking: {entry['tracking_id']}")

            # Auto-deploy to SMB/network path if configured
            if smb_path.strip():
                import shutil
                smb_dest = Path(smb_path.strip())
                try:
                    smb_dest.mkdir(parents=True, exist_ok=True)
                    for entry in manifest:
                        src = Path(output_dir) / entry["file"]
                        dst = smb_dest / entry["file"]
                        shutil.copy2(src, dst)
                    st.success(f"Also deployed to network path: `{smb_dest}/`")
                except Exception as smb_err:
                    st.warning(f"Network deploy failed: {smb_err}")

            time.sleep(0.5)
            st.rerun()
        except Exception as e:
            st.error(f"Deployment failed: {e}", icon="🚨")

# ── Main layout ───────────────────────────────────────────────────────
col_left, col_right = st.columns([3, 2], gap="large")

# ── Graph (STATIC — renders once, never auto-refreshes) ───────────────
with col_left:
    st.markdown("<h3><i class='bi bi-diagram-3-fill' style='color:#1565c0;'></i> HoneyToken Minefield</h3>", unsafe_allow_html=True)
    graph_placeholder = st.empty()

manifest_path = os.path.join(output_dir, "manifest.json")
accessed_files, all_events = parse_alerts()
st.session_state.accessed_files = accessed_files

graph_state = {"G": None, "center_node": None}
if os.path.exists(manifest_path):
    with open(manifest_path) as f:
        manifest_entries = json.load(f)
    G, center_node = build_static_graph(company_name, manifest_entries)
    graph_state = {"G": G, "center_node": center_node}
    if G and center_node:
        pos_map = layout_positions(G, center_node)
        with col_left:
            graph_placeholder.empty()
            draw_graph(G, pos_map, accessed_files, col_left)
    else:
        with col_left:
            graph_placeholder.info(
                "No honeytokens deployed yet. "
                "Configure and click **Deploy HoneyTokens** in the sidebar.",
            )

# ── Live panels (alerts + metrics + log — text only, no graph redraw) ─
with col_right:
    st.markdown("<h3><i class='bi bi-shield-exclamation' style='color:#c62828;'></i> Live Threat Monitor</h3>", unsafe_allow_html=True)
    alert_placeholder = st.empty()

metrics_placeholder = st.empty()
log_placeholder = st.empty()


def render_static_panels(events):
    recent = events[-50:][::-1] if events else []
    intrusion = any(e[1] in ("TRACK", "MODIFIED", "DELETED", "MOVED") for e in recent[:10])

    with col_right:
        alert_placeholder.empty()
        with alert_placeholder.container():
            if intrusion:
                st.error(
                    "**CRITICAL INTRUSION DETECTED!**\n\n"
                    "One or more honeytokens have been accessed or modified.",
                )
                st.markdown(
                    "<div style='background:#c62828; color:#fff; padding:12px; "
                    "border-radius:6px; text-align:center; font-size:1.4rem; "
                    "font-weight:bold;'>"
                    "INTRUSION IN PROGRESS</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.info("All honeytokens are quiet. No intrusions detected.")

            if recent:
                df = pd.DataFrame(recent[:15], columns=["Timestamp", "Type", "Target", "IP", "User-Agent"])
                df["Type"] = df["Type"].apply(
                    lambda t: {
                        "TRACK": "TRACK",
                        "MODIFIED": "MODIFY",
                        "DELETED": "DELETE",
                        "CREATED": "CREATE",
                        "MOVED": "MOVE",
                        "WATCHDOG_STARTED": "START",
                        "WATCHDOG_STOPPED": "STOP",
                    }.get(t, t)
                )
                st.dataframe(df, width="stretch", hide_index=True)
            else:
                st.caption("No events yet.")

    with metrics_placeholder.container():
        mcol1, mcol2, mcol3, mcol4 = st.columns(4)
        total_tokens = 0
        if os.path.exists(manifest_path):
            with open(manifest_path) as f:
                total_tokens = len(json.load(f))
        with mcol1:
            st.metric("Active Tokens", total_tokens)
        with mcol2:
            st.metric("Tracking Hits", _db_count_by_type("TRACK"))
        with mcol3:
            st.metric("Filesystem Events",
                _db_count_by_type("CREATED") + _db_count_by_type("MODIFIED")
                + _db_count_by_type("DELETED") + _db_count_by_type("MOVED"))
        with mcol4:
            st.metric("Total Events", _db_count())

    with log_placeholder.container():
        with st.expander("Full Event Log", expanded=False):
            if events:
                full_df = pd.DataFrame(events, columns=["Timestamp", "Type", "Target", "IP", "User-Agent"])
                full_df = full_df.iloc[::-1]
                st.dataframe(full_df, width="stretch", hide_index=True)
            else:
                st.caption("No events logged yet.")


render_static_panels(all_events)

# ── Tiny notification poller (only this auto-refreshes, no visible flicker) ──
if "prev_event_count" not in st.session_state:
    st.session_state.prev_event_count = len(all_events)


@st.fragment(run_every=1)
def event_poller():
    accessed_files, events = parse_alerts()
    n = len(events)
    prev = st.session_state.prev_event_count
    new_count = n - prev
    latest_events = events[-5:][::-1] if events else []

    # Decide if alert banner should show (last event within 10s)
    show_alert = False
    if events:
        try:
            latest_ts = datetime.fromisoformat(events[-1][0])
            show_alert = (datetime.now() - latest_ts).total_seconds() < 10
        except (ValueError, IndexError):
            pass
 
    # Sound on new events (fires once)
    if new_count > 0:
        st.session_state.prev_event_count = n

        components.html(
            """
            <script>
            try {
                var ctx = new (window.AudioContext || window.webkitAudioContext)();
                var now = ctx.currentTime;
                var o1 = ctx.createOscillator();
                var g1 = ctx.createGain();
                o1.type = 'sine'; o1.frequency.value = 180;
                g1.gain.setValueAtTime(0, now);
                g1.gain.linearRampToValueAtTime(0.5, now + 0.03);
                g1.gain.exponentialRampToValueAtTime(0.01, now + 0.25);
                o1.connect(g1); g1.connect(ctx.destination);
                o1.start(now); o1.stop(now + 0.25);
                var o2 = ctx.createOscillator();
                var g2 = ctx.createGain();
                o2.type = 'sawtooth';
                o2.frequency.setValueAtTime(500, now + 0.12);
                o2.frequency.linearRampToValueAtTime(900, now + 0.35);
                g2.gain.setValueAtTime(0, now + 0.12);
                g2.gain.linearRampToValueAtTime(0.2, now + 0.18);
                g2.gain.exponentialRampToValueAtTime(0.01, now + 0.5);
                o2.connect(g2); g2.connect(ctx.destination);
                o2.start(now + 0.12); o2.stop(now + 0.5);
                setTimeout(function(){ ctx.close(); }, 600);
            } catch(e) {}
            </script>
            """,
            height=0,
        )

    # Slack: fires for all recent events + re-sends when URL changes
    if show_alert and slack_url:
        last_slack = st.session_state.get("last_slack_ts", "")
        latest_ts = events[-1][0] if events else ""
        if latest_ts != last_slack:
            st.session_state.last_slack_ts = latest_ts
            latest = events[-1]
            slack_text = (
                f"🚨 *Project Ember — Intrusion Detected*\n"
                f"• *File:* `{latest[2]}`\n"
                f"• *Type:* `{latest[1]}`\n"
                f"• *Time:* `{latest[0]}`\n"
                f"• *IP:* `{latest[3]}` ({geoip(latest[3])})\n"
                f"• *Browser:* `{latest[4][:80]}`"
            )
            _send_slack(slack_url, slack_text)

    # Browser notification (works in background tabs)
    if show_alert:
        components.html(
            """
            <script>
            if ('Notification' in window && Notification.permission === 'granted') {
                var n = new Notification('Project Ember — Intrusion Detected', {
                    body: 'New security event detected — click to open dashboard',
                    icon: 'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/icons/activity.svg',
                    tag: 'ember-alert',
                    requireInteraction: true
                });
                n.onclick = function() { window.focus(); };
            }
            </script>
            """,
            height=0,
        )

        details = ""
        for ev in latest_events[:3]:
            ts_str, ev_type, target, ip, ua = ev[0], ev[1], ev[2], ev[3], ev[4]
            short_tgt = os.path.basename(target) if target else target
            ua_short = ua[:60] + "…" if len(ua) > 60 else ua
            details += (
                f"<div style='display:flex;align-items:center;gap:8px;"
                f"padding:3px 0;font-size:12px;'>"
                f"<span class='flash-node' style='display:inline-block;width:10px;"
                f"height:10px;border-radius:50%;background:#ff1744;flex-shrink:0;'></span>"
                f"<span style='color:rgba(255,255,255,0.5);font-weight:normal;'>{ts_str}</span>"
                f"<span style='font-weight:bold;color:#fff;'>{ev_type}</span>"
                f"<span style='color:rgba(255,255,255,0.9);'>{short_tgt}</span>"
                f"<span style='color:rgba(255,255,255,0.6);font-size:11px;'>{geoip(ip)}</span>"
                f"<span style='color:rgba(255,255,255,0.4);font-size:10px;'>{ua_short}</span>"
                f"</div>"
            )

        st.error(
            f"**CRITICAL INTRUSION DETECTED** — {len(latest_events)} recent event(s)\n\n"
            f"See banner above for file details, attacker IP, and browser profile.",
        )

        st.markdown(
            f"<div style='position:fixed;top:0;left:0;right:0;"
            f"z-index:999999;background:linear-gradient(135deg,#c62828,#b71c1c);"
            f"color:#fff;padding:14px 28px;"
            f"box-shadow:0 4px 30px rgba(198,40,40,0.6);"
            f"border-bottom:2px solid rgba(255,255,255,0.15);'>"
            f"<div style='display:flex;align-items:center;gap:10px;font-size:18px;font-weight:bold;'>"
            f"<i class='bi bi-exclamation-triangle-fill' style='font-size:1.3em;'></i> "
            f"CRITICAL INTRUSION DETECTED"
            f"</div>"
            f"<div style='margin-top:6px;font-size:13px;color:rgba(255,255,255,0.85);'>"
            f"{new_count} new security event(s):</div>"
            f"{details}"
            f"</div>",
            unsafe_allow_html=True,
        )

    # Bottom-right badge
    st.markdown(
        f"<div style='position:fixed;bottom:16px;right:16px;z-index:99999;"
        f"background:#1a1a2e;color:#e0e0e0;padding:6px 14px;"
        f"border-radius:20px;font-size:13px;border:1px solid #444;"
        f"box-shadow:0 2px 12px rgba(0,0,0,0.5);'>"
        f"<i class='bi bi-bar-chart-fill' style='margin-right:4px;'></i> {n} events"
        f"</div>",
        unsafe_allow_html=True,
    )


event_poller()

# ── Refresh button ────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
if st.button("Refresh Dashboard", type="secondary"):
    st.rerun()
