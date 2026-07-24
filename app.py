import os
import time
import json
import math
import threading
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

# ── Config ─────────────────────────────────────────────────────────────
ALERTS_LOG = os.environ.get("EMBER_ALERTS_LOG", "alerts.log")
TRACKING_PORT = int(os.environ.get("EMBER_TRACKING_PORT", "8765"))
DEFAULT_OUTPUT = os.environ.get("EMBER_OUTPUT_DIR", "./honeytokens")

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

# ── Styles ────────────────────────────────────────────────────────────
st.markdown(
    """
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
<style>
div[data-testid="stMetricValue"] { font-size: 2rem; }
.stAlert { border-left: 5px solid #d32f2f !important; }
.bi { font-size: 1.1em; }
h1 .bi { font-size: 1.2em; }
@keyframes flashRed {
    0%, 100% { opacity: 1; box-shadow: 0 0 0 0 rgba(198,40,40,0.4); }
    50% { opacity: 0.6; box-shadow: 0 0 25px 12px rgba(198,40,40,0.15); }
}
.flash-node {
    animation: flashRed 1s ease-in-out infinite;
}
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
except Exception:
    pass

# ── Start tracking pixel HTTP server (once per session) ─────────────
_ensure_tracking_server()

# ── Helpers ───────────────────────────────────────────────────────────


def parse_alerts():
    accessed = set()
    events = []
    if not os.path.exists(ALERTS_LOG):
        return accessed, events
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
            if ev_type in ("TRACK", "MODIFIED", "DELETED", "MOVED"):
                accessed.add(target)
            events.append((ts_str, ev_type, target, ip, detail))
    return accessed, events


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
    fig.patch.set_facecolor("#ffffff")
    ax.set_facecolor("#fafafa")

    nx.draw_networkx_edges(
        G, pos, ax=ax,
        edge_color="#aaa",
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
        edgecolors="#333",
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
                font_color="#000",
                font_weight="bold",
                bbox=dict(facecolor="white", edgecolor="#ccc", alpha=0.95, pad=5, boxstyle="round,pad=0.4"),
            )

    ax.set_title(
        "Project Ember — HoneyToken Minefield",
        fontsize=24, fontweight="bold", color="#1a1a2e", pad=20,
    )
    ax.axis("off")
    fig.tight_layout()
    container.pyplot(fig)
    plt.close(fig)


# ── UI ────────────────────────────────────────────────────────────────
st.markdown(
    "<h1 style='display:flex; align-items:center; gap:10px;'>"
    "<i class='bi bi-activity' style='font-size:2rem; color:#e65100;'></i> "
    "<span>Project Ember</span></h1>",
    unsafe_allow_html=True,
)
st.markdown(
    "<p style='color:#888; margin-top:-12px;'><em>The AI HoneyToken Factory — "
    "Deploy intelligent decoys to trap ransomware &amp; malicious insiders</em></p>",
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

    tracker_port = st.number_input(
        "Tracking Pixel Port",
        min_value=1024,
        max_value=65535,
        value=TRACKING_PORT,
        step=1,
        help="Port for the hidden tracking-pixel HTTP server. Must match the port in generated files.",
    )

    api_key_set = bool(os.environ.get("GEMINI_API_KEY"))
    if api_key_set:
        st.success("GEMINI_API_KEY detected", icon="🔑")
    else:
            st.warning(
                "GEMINI_API_KEY not set — using mock output. "
                "Set the environment variable for AI-generated content.",
            )

    # Tracking URL display
    st.caption(
        f"Tracking pixel base URL:\n"
        f"`http://localhost:{tracker_port}/track?file=FILENAME`"
    )

    col1, col2 = st.columns(2)
    with col1:
        deploy_btn = st.button("Deploy HoneyTokens", type="primary", width="stretch")
    with col2:
        if st.button("Clear Alerts", width="stretch"):
            open(ALERTS_LOG, "w").close()
            st.session_state.accessed_files = set()
            st.rerun()
    
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
                tracker_port=tracker_port,
            )
            st.session_state.deployed = True
            st.success(
                f"Deployed {len(manifest)} honeytokens to `{output_dir}/`",
            )
            for entry in manifest:
                st.code(f"  {entry['file']}  —  tracking: {entry['tracking_id']}")
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
            st.metric("Tracking Hits", sum(1 for e in events if e[1] == "TRACK"))
        with mcol3:
            fs_events = sum(1 for e in events if e[1] in ("CREATED", "MODIFIED", "DELETED", "MOVED"))
            st.metric("Filesystem Events", fs_events)
        with mcol4:
            st.metric("Total Events", len(events))

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

    # Alert banner persists for 10s after last event
    if show_alert:
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
