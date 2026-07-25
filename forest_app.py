import os
import time
import json
import threading
import urllib.request
from datetime import datetime

import streamlit as st

from forest_ai import analyze_tree_image, generate_reforestation_plan


def _send_slack(webhook_url, text):
    if not webhook_url:
        return
    def _fire():
        try:
            payload = json.dumps({"text": text}).encode()
            req = urllib.request.Request(webhook_url, data=payload, headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=5)
        except Exception:
            pass
    threading.Thread(target=_fire, daemon=True).start()

st.set_page_config(page_title="Ember Reforest AI", page_icon="🌱", layout="wide")

st.markdown("""
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
<style>
    * { font-family: 'Inter', sans-serif; }
    .stApp { background: #0a0e17; }
    .main > div { background: #0a0e17; }
    h1 { color: #fff !important; font-weight: 800 !important; }
    .stButton button {
        background: #1e293b !important; color: #e2e8f0 !important;
        border: 1px solid #334155 !important; border-radius: 6px !important;
    }
    button[kind="primary"] { background: #059669 !important; border-color: #047857 !important; color: #fff !important; font-weight: 600 !important; }
    button[kind="primary"]:hover { background: #10b981 !important; }
    div[data-testid="stMetricValue"] { font-size: 2rem !important; font-weight: 800 !important; color: #fff !important; }
    div[data-testid="metric-container"] { background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 16px; }
    .stTextInput input, .stTextArea textarea { background: rgba(255,255,255,0.05) !important; border: 1px solid rgba(255,255,255,0.1) !important; color: #fff !important; border-radius: 8px !important; }
    .analysis-card { background: rgba(16,24,40,0.95); border: 1px solid #334155; border-radius: 12px; padding: 20px; margin: 12px 0; color: #e2e8f0; font-size: 0.9rem; line-height: 1.7; white-space: pre-wrap; }
    .analysis-card strong { color: #10b981; }
</style>
""", unsafe_allow_html=True)

for key in ["plan_result", "health_result", "slack_url"]:
    if key not in st.session_state:
        st.session_state[key] = ""

# ── Header ──────────────────────────────────────────────────────────
st.markdown(
    "<h1 style='display:flex;align-items:center;gap:12px;'>"
    "<span style='background:linear-gradient(135deg,#059669,#10b981);"
    "width:40px;height:40px;border-radius:10px;display:flex;"
    "align-items:center;justify-content:center;'>🌱</span>"
    "<span>Ember Reforest AI</span></h1>",
    unsafe_allow_html=True,
)
st.markdown(
    "<p style='color:#666;margin-top:-8px;font-size:0.9rem;'>"
    "AI-powered reforestation planning for Rwanda's 40 million tree goal — "
    "describe your land, get a complete planting plan from Gemini</p>",
    unsafe_allow_html=True,
)

# ── Tabs ─────────────────────────────────────────────────────────────
tab1, tab2 = st.tabs(["🌱 Reforestation Planner", "🌿 Tree Health Check"])

with tab1:
    col_form, col_result = st.columns([1, 1], gap="large")

    with col_form:
        st.markdown("<h3>Describe Your Land</h3>", unsafe_allow_html=True)
        st.markdown(
            "<p style='color:#888;font-size:0.85rem;'>"
            "Tell us about the land you want to reforest. Include size, location, "
            "soil type, water sources, and current vegetation.</p>",
            unsafe_allow_html=True,
        )

        land_desc = st.text_area(
            "Land description",
            placeholder=(
                "Example: 2 hectares in Musanze district, volcanic soil, "
                "near a stream, sloped terrain, currently grass and shrubs. "
                "Altitude ~1800m. Rainfall is seasonal (March-May, October-December)."
            ),
            height=180,
        )

        with st.expander("💡 Tips for a good description"):
            st.markdown(
                "- **Size**: Hectares or acres\n"
                "- **Location**: District, sector, nearest town\n"
                "- **Soil type**: Volcanic, clay, sandy, loam\n"
                "- **Water**: River, stream, lake, seasonal rain\n"
                "- **Slope**: Flat, gentle, steep\n"
                "- **Current use**: Grassland, farmland, degraded forest\n"
                "- **Altitude**: Lowland (<1500m), midland (1500-2000m), highland (>2000m)"
            )

        col1, col2 = st.columns([1, 1])
        with col1:
            goal_hectares = st.number_input("Hectares to plant", min_value=0.1, max_value=100.0, value=1.0, step=0.5)
        with col2:
            primary_goal = st.selectbox(
                "Primary goal",
                ["Timber & shade", "Fruit & food", "Soil conservation", "Carbon credits", "Mixed"]
            )

        slack_url = st.text_input(
            "Slack alerts (optional)", value=st.session_state.slack_url,
            placeholder="https://hooks.slack.com/services/...",
        )
        st.session_state.slack_url = slack_url

        generate_btn = st.button("🌱 Generate Reforestation Plan", type="primary", use_container_width=True)

    with col_result:
        if generate_btn and land_desc.strip():
            with st.spinner("Gemini is designing your reforestation plan..."):
                enhanced_desc = (
                    f"{land_desc.strip()}\n\n"
                    f"Area: {goal_hectares} hectares. "
                    f"Primary goal: {primary_goal}."
                )
                result, is_real = generate_reforestation_plan(enhanced_desc)
                st.session_state.plan_result = result

        if st.session_state.plan_result:
            result = st.session_state.plan_result
            st.markdown(f"<div class='analysis-card'>{result}</div>", unsafe_allow_html=True)

            st.download_button(
                "📥 Download as Report",
                result,
                file_name=f"reforestation_plan_{datetime.now().strftime('%Y%m%d')}.md",
                mime="text/markdown",
            )

with tab2:
    col_photo, col_diag = st.columns([1, 1], gap="large")

    with col_photo:
        st.markdown("<h3>Upload a Tree Photo</h3>", unsafe_allow_html=True)
        st.markdown(
            "<p style='color:#888;font-size:0.85rem;'>"
            "Take a photo of a tree with visible symptoms — yellowing leaves, "
            "bark damage, pests, or stunted growth.</p>",
            unsafe_allow_html=True,
        )
        uploaded_file = st.file_uploader("Choose a photo", type=["jpg", "jpeg", "png", "webp"])
        if uploaded_file and st.button("🔍 Diagnose Tree", type="primary", use_container_width=True):
            with st.spinner("Gemini is analyzing the tree..."):
                result, is_real = analyze_tree_image(uploaded_file.getvalue())
                st.session_state.health_result = result

    with col_diag:
        if st.session_state.health_result:
            result = st.session_state.health_result
            st.markdown(f"<div class='analysis-card'>{result}</div>", unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<p style='color:#444;text-align:center;font-size:0.8rem;'>"
    "Ember Reforest AI — Frontiers Gen-AI Hackathon Rwanda 2026 · "
    "GDG Kigali × The Changemakers Convening · "
    "Powered by Gemini 2.0 Flash</p>",
    unsafe_allow_html=True,
)
