import os
import time
import json
import threading
import urllib.request
from datetime import datetime
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd

from forest_ai import analyze_tree_image, analyze_forest_audio, generate_reforestation_plan
from db import insert


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

# ── Page config ───────────────────────────────────────────────────
st.set_page_config(
    page_title="Ember Forest AI — Forest Intelligence Platform",
    page_icon="🌳",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Styles ────────────────────────────────────────────────────────
st.markdown(
    """
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@500;600;700;800&display=swap');
    * { font-family: 'Inter', sans-serif; }
    .stApp { background: #0a0e17; }
    .main > div { background: #0a0e17; }
    h1 { color: #ffffff !important; font-weight: 800 !important; }
    h3 { color: #ffffff !important; font-size: 1rem !important; text-transform: uppercase; letter-spacing: 2px; }
    .stButton button {
        background: #1e293b !important; color: #e2e8f0 !important;
        border: 1px solid #334155 !important; border-radius: 6px !important;
        font-weight: 500 !important; font-size: 0.8rem !important;
    }
    button[kind="primary"] {
        background: #059669 !important; border-color: #047857 !important;
        font-weight: 600 !important; color: #ffffff !important;
    }
    button[kind="primary"]:hover { background: #10b981 !important; }
    div[data-testid="stMetricValue"] {
        font-size: 2rem !important; font-weight: 800 !important; color: #fff !important;
    }
    div[data-testid="metric-container"] {
        background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08);
        border-radius: 12px; padding: 16px;
    }
    .stAlert { border-left: 4px solid #059669 !important; background: rgba(5,150,105,0.08) !important; }
    .stTextInput input, .stTextArea textarea {
        background: rgba(255,255,255,0.05) !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        color: #fff !important; border-radius: 8px !important;
    }
    .analysis-card {
        background: rgba(16,24,40,0.95); border: 1px solid #334155;
        border-radius: 12px; padding: 20px; margin: 12px 0;
        color: #e2e8f0; font-size: 0.9rem; line-height: 1.7;
        white-space: pre-wrap;
    }
    .analysis-card h1, .analysis-card h2, .analysis-card h3, .analysis-card strong { color: #ffffff; }
    .threat-badge {
        display: inline-block; padding: 4px 12px; border-radius: 20px;
        font-weight: 700; font-size: 0.8rem;
    }
</style>
""",
    unsafe_allow_html=True,
)

# ── Session state ─────────────────────────────────────────────────
for key in [
    "tree_result", "audio_result", "reforest_result",
    "audio_alert", "tree_health_score", "slack_url",
]:
    if key not in st.session_state:
        st.session_state[key] = "" if "result" in key or "url" in key else None

# ── Sidebar ───────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        "<h3 style='display:flex;align-items:center;gap:8px;'>"
        "<i class='bi bi-gear' style='color:#42a5f5;'></i> Analysis Mode</h3>",
        unsafe_allow_html=True,
    )

    mode = st.radio(
        "Select input type",
        ["🌿 Tree Photo", "🎤 Forest Audio", "📝 Land Description"],
        label_visibility="collapsed",
    )

    st.divider()

    slack_url = st.text_input(
        "Slack Alert URL",
        value=st.session_state.get("slack_url", ""),
        placeholder="https://hooks.slack.com/services/...",
        help="Get alerts when threats (chainsaws) are detected",
    )
    st.session_state.slack_url = slack_url

    api_key_set = bool(os.environ.get("GEMINI_API_KEY"))
    if api_key_set:
        st.success("Gemini API connected", icon="✅")
    else:
        st.warning("No API key — using mock analysis")

    st.divider()
    st.markdown(
        "<p style='color:#666;font-size:0.8rem;'>"
        "<i class='bi bi-info-circle'></i> "
        "Ember Forest AI uses Gemini 2.0 Flash to analyze photos, audio, "
        "and text descriptions of forest environments. "
        "Built for the Frontiers Gen-AI Hackathon Rwanda.</p>",
        unsafe_allow_html=True,
    )

# ── Main UI ───────────────────────────────────────────────────────
st.markdown(
    "<h1 style='display:flex;align-items:center;gap:12px;'>"
    "<span style='background:linear-gradient(135deg,#059669,#10b981);"
    "width:40px;height:40px;border-radius:10px;display:flex;"
    "align-items:center;justify-content:center;'>🌳</span>"
    "<span>Ember Forest AI</span></h1>",
    unsafe_allow_html=True,
)
st.markdown(
    "<p style='color:#666;margin-top:-8px;font-size:0.9rem;'>"
    "Multi-modal forest intelligence — analyze photos, audio, and land descriptions with Gemini</p>",
    unsafe_allow_html=True,
)

# ── Analysis tab ──────────────────────────────────────────────────
col_left, col_right = st.columns([2, 1], gap="large")

with col_left:
    if mode == "🌿 Tree Photo":
        st.markdown("<h3><i class='bi bi-camera' style='color:#10b981;'></i> Upload a Tree Photo</h3>", unsafe_allow_html=True)
        uploaded_file = st.file_uploader("Choose a tree photo", type=["jpg", "jpeg", "png", "webp"])
        if uploaded_file and st.button("Analyze Tree Health", type="primary", use_container_width=True):
            with st.spinner("Gemini is analyzing the tree..."):
                image_bytes = uploaded_file.getvalue()
                result, is_real = analyze_tree_image(image_bytes)
                st.session_state.tree_result = result

        if st.session_state.tree_result:
            st.markdown(f"<div class='analysis-card'>{st.session_state.tree_result}</div>", unsafe_allow_html=True)

    elif mode == "🎤 Forest Audio":
        st.markdown("<h3><i class='bi bi-mic' style='color:#10b981;'></i> Upload a Forest Recording</h3>", unsafe_allow_html=True)
        st.markdown(
            "<p style='color:#888;font-size:0.85rem;'>"
            "Record 10-30 seconds of forest sounds and upload. "
            "Gemini will identify bird species, assess biodiversity, "
            "and detect threats like chainsaws.</p>",
            unsafe_allow_html=True,
        )
        audio_file = st.file_uploader("Choose an audio file", type=["wav", "mp3", "m4a", "ogg", "flac"])
        if audio_file and st.button("Analyze Forest Sounds", type="primary", use_container_width=True):
            with st.spinner("Gemini is listening to the forest..."):
                audio_bytes = audio_file.getvalue()
                result, is_real = analyze_forest_audio(audio_bytes)
                st.session_state.audio_result = result
                if "chainsaw" in result.lower() or "alert needed: yes" in result.lower():
                    st.session_state.audio_alert = True
                    ts = datetime.now().isoformat()
                    if st.session_state.slack_url:
                        slack_text = (
                            f"🚨 *Ember Forest AI — Threat Detected*\n"
                            f"• *Alert:* Chainsaw or threat detected in audio\n"
                            f"• *Time:* {ts}\n"
                            f"• *Action:* Park rangers should investigate immediately"
                        )
                        _send_slack(st.session_state.slack_url, slack_text)

        if st.session_state.audio_result:
            if st.session_state.audio_alert:
                st.error("🚨 **THREAT DETECTED** — Chainsaw or human activity detected in forest audio!", icon="🔥")
            st.markdown(f"<div class='analysis-card'>{st.session_state.audio_result}</div>", unsafe_allow_html=True)

    elif mode == "📝 Land Description":
        st.markdown("<h3><i class='bi bi-pencil' style='color:#10b981;'></i> Describe Your Land</h3>", unsafe_allow_html=True)
        st.markdown(
            "<p style='color:#888;font-size:0.85rem;'>"
            "Describe the land you want to reforest — size, location, soil type, "
            "nearby water, current vegetation. Example: "
            "<em>'2 hectares in Musanze, volcanic soil, near a stream, "
            "sloped terrain, current grass and shrubs'</em></p>",
            unsafe_allow_html=True,
        )
        land_desc = st.text_area("Land description", placeholder="Describe your land in detail...", height=150)
        if land_desc and st.button("Generate Reforestation Plan", type="primary", use_container_width=True):
            with st.spinner("Gemini is creating your reforestation plan..."):
                result, is_real = generate_reforestation_plan(land_desc)
                st.session_state.reforest_result = result

        if st.session_state.reforest_result:
            st.markdown(f"<div class='analysis-card'>{st.session_state.reforest_result}</div>", unsafe_allow_html=True)

# ── Right panel: history + alerts ────────────────────────────────
with col_right:
    st.markdown("<h3><i class='bi bi-clock-history' style='color:#42a5f5;'></i> Recent Analyses</h3>", unsafe_allow_html=True)

    history = []
    if st.session_state.tree_result:
        history.append(("🌿 Tree Health", datetime.now().strftime("%H:%M")))
    if st.session_state.audio_result:
        history.append(("🎤 Forest Audio", datetime.now().strftime("%H:%M")))
    if st.session_state.reforest_result:
        history.append(("📝 Reforestation Plan", datetime.now().strftime("%H:%M")))

    if history:
        for item, ts in reversed(history):
            st.markdown(
                f"<div style='background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);"
                f"border-radius:8px;padding:10px;margin-bottom:8px;'>"
                f"<div style='color:#fff;font-weight:600;'>{item}</div>"
                f"<div style='color:#666;font-size:0.8rem;'>{ts}</div></div>",
                unsafe_allow_html=True,
            )
    else:
        st.info("No analyses yet. Upload a photo, audio, or describe land to begin.")

    if st.session_state.audio_alert:
        st.divider()
        st.markdown("<h3 style='color:#f44336;'><i class='bi bi-exclamation-triangle'></i> Active Threats</h3>", unsafe_allow_html=True)
        st.markdown(
            "<div style='background:rgba(244,67,54,0.1);border:1px solid #f44336;"
            "border-radius:8px;padding:12px;text-align:center;'>"
            "<span style='color:#f44336;font-weight:700;font-size:1.2rem;'>⚠️ CHAINSAW DETECTED</span>"
            "<p style='color:#ccc;font-size:0.85rem;margin-top:4px;'>"
            "Slack alert sent to park rangers</p></div>",
            unsafe_allow_html=True,
        )

    st.divider()
    st.markdown(
        "<div style='background:rgba(5,150,105,0.05);border:1px solid rgba(5,150,105,0.2);"
        "border-radius:8px;padding:12px;'>"
        "<p style='color:#10b981;font-weight:600;margin:0;font-size:0.9rem;'>"
        "<i class='bi bi-tree'></i> Powered by Gemini 2.0 Flash</p>"
        "<p style='color:#888;font-size:0.8rem;margin:4px 0 0 0;'>"
        "Multi-modal forest intelligence for Rwanda's conservation efforts</p></div>",
        unsafe_allow_html=True,
    )

# ── Footer ────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<p style='color:#444;text-align:center;font-size:0.8rem;'>"
    "Ember Forest AI — Built at Frontiers Gen-AI Hackathon Rwanda 2026 · "
    "GDG Kigali × The Changemakers Convening</p>",
    unsafe_allow_html=True,
)
