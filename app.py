import os, sqlite3, time, json, datetime as dt, random, warnings, io, urllib.parse
warnings.filterwarnings("ignore")
try:
    from dotenv import load_dotenv; load_dotenv()
except: pass
import streamlit as st
import pandas as pd
import numpy as np
import requests
from PIL import Image, ImageDraw, ImageFont

DB_PATH = "agri.db"
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
THREE_CROPS = ["Cassava", "Maize", "Yam"]

LANGUAGES = {"English": "en", "Kinyarwanda": "rw", "Swahili": "sw", "French": "fr"}
BUYERS = {
    "Cassava": [
        ("Ingabo Syndicate", "Kigali", "+250788123456", "Cassava flour, 5-20 tons/month", "Premium quality, white flour"),
        ("AgriPro Ltd", "Rubavu", "+250788234567", "Fresh roots, 10-30 tons", "Disease-free, firm texture"),
        ("East African Foods", "Kampala", "+256700123456", "Cassava chips, 50+ tons", "Sun-dried, export grade"),
        ("Rwanda Grain Corp", "Kigali", "+250788345678", "All cassava products", "Grade 1 or 2"),
        ("Muhanga Coop", "Muhanga", "+250788456789", "Fresh local delivery", "Organic preferred"),
    ],
    "Maize": [
        ("MINAGRI Grain Reserve", "Kigali", "+250788567890", "Maize grain, 100+ tons", "Moisture < 13.5%"),
        ("Africa Improved Foods", "Kigali", "+250788678901", "Fortified maize flour", "Aflatoxin-free certified"),
        ("FarmFresh Exports", "Nairobi", "+254700123456", "Export maize, 50+ tons", "Grade 1, non-GMO"),
        ("Rwanda Grain Corp", "Kigali", "+250788345678", "All grains", "Market standard"),
        ("Rulindo Farmers Ltd", "Rulindo", "+250788789012", "Direct from farmers", "Local, fresh"),
    ],
    "Yam": [
        ("Kigali Fresh Market", "Kigali", "+250788890123", "Fresh yams, 1-5 tons/week", "Firm, no bruises"),
        ("Hotel Distributors Ltd", "Kigali", "+250788901234", "Premium yams for restaurants", "Uniform size, Grade A"),
        ("Cross-Border Traders", "Gisenyi", "+250788012345", "Export to DRC, 10+ tons", "Any grade, bulk"),
        ("Gicumbi Coop", "Gicumbi", "+250788123789", "Local yam collection", "Organic"),
        ("Urban Greens Ltd", "Kigali", "+250788234890", "Organic yams, premium", "Certified organic"),
    ],
}

MARKET_PRICES = {
    "Cassava": (300, 500, "stable"), "Maize": (600, 900, "rising"),
    "Yam": (800, 1400, "stable"),
}

RWANDA_COORDS = {"Rulindo": (-1.72, 29.94), "Kigali": (-1.95, 30.10), "Musanze": (-1.50, 29.63),
    "Rubavu": (-1.68, 29.25), "Huye": (-2.60, 29.74), "Muhanga": (-2.08, 29.75),
    "Rwamagana": (-1.95, 30.43), "Gicumbi": (-1.62, 30.12), "Gisenyi": (-1.70, 29.26),
}

# ── Translation ──────────────────────────────────────────
T = {"English": {
    "app_title": "AgriScope AI", "app_subtitle": "Smart Scouting • Climate Advisor • Market Connect",
    "app_region": "Rwanda / East Africa", "farmer_name": "Farmer Name", "plot_location": "Plot Location",
    "crop_type": "Crop", "planting_date": "Planting Date", "plot_size": "Plot Size (hectares)",
    "budget": "Budget (RWF/season)", "save_plot": "Register Plot",
    "pillar1": "Pillar 1: Smart Scouting", "pillar2": "Pillar 2: Growing Calendar",
    "pillar3": "Pillar 3: Market Connect", "dashboard": "Dashboard",
    "scout_plan_btn": "Generate Weekly Scout Plan", "scout_photo": "Upload Scout Photo",
    "photo_checkin": "Photo Check-In", "human_verify": "Human Verification Recommended",
    "neighbor_alert": "Neighbor Early Warning", "no_alerts": "No active alerts in your area.",
    "growing_calendar": "Growing Calendar", "generate_calendar": "Generate Season Calendar",
    "market_connect": "Market Connect", "find_buyers": "Find Buyers",
    "action_pack": "Action Pack", "whatsapp_buyer": "WhatsApp Buyer",
    "sell_advice": "Sell Now vs Hold", "harvest_estimate": "Estimated Harvest",
    "weather": "Weather", "sources": "Sources: FAO, IITA, CGIAR, Open-Meteo",
    "gemini_on": "Gemini AI enabled", "gemini_off": "Gemini offline — demo mode",
    "welcome_title": "Welcome to AgriScope AI", "welcome_desc": "Register your plot to get a personalized scouting plan, climate-driven growing calendar, and market access — all in one tool.",
    "back": "Back to Dashboard",
}}

# Inherit English for other languages
T["Kinyarwanda"] = {**T["English"], "app_title": "AgriScope AI", "app_subtitle": "Gushakisha • Inama y'Ibihe • Isoko",
    "farmer_name": "Izina ry'Umuhinzi", "plot_location": "Aho Umurima Uri",
    "crop_type": "Igihingwa", "planting_date": "Itariki yo Gutera",
    "plot_size": "Ingano y'Umurima (ha)", "budget": "Bije (RWF/igihembwe)",
    "save_plot": "Andikisha Umurima", "welcome_title": "Murakaza neza kuri AgriScope AI",
    "welcome_desc": "Andikisha umurima wawe kugira ngo ubone gahunda yo gushakisha, kalendari y'ihinga ishingiye ku kirere, n'isoko — byose hamwe."}
T["Swahili"] = {**T["English"], "app_title": "AgriScope AI", "farmer_name": "Jina la Mkulima",
    "crop_type": "Zao", "save_plot": "Sajili Shamba", "welcome_title": "Karibu AgriScope AI"}
T["French"] = {**T["English"], "app_title": "AgriScope AI", "farmer_name": "Nom de l'Agriculteur",
    "crop_type": "Culture", "save_plot": "Enregistrer la Parcelle", "welcome_title": "Bienvenue sur AgriScope AI"}

def t(key: str) -> str:
    lang = st.session_state.get("ui_language", "English")
    return T.get(lang, T["English"]).get(key, T["English"].get(key, key))

# ── DB ──────────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""CREATE TABLE IF NOT EXISTS plots (id INTEGER PRIMARY KEY AUTOINCREMENT,
        farmer TEXT, location TEXT, crop TEXT, planting_date TEXT, plot_size REAL, budget REAL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS scouts (id INTEGER PRIMARY KEY AUTOINCREMENT,
        plot_id INTEGER, week INTEGER, date TEXT, findings TEXT, photo_path TEXT, confidence TEXT,
        human_verified INTEGER DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS alerts (id INTEGER PRIMARY KEY AUTOINCREMENT,
        plot_id INTEGER, alert_type TEXT, message TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS assessments (id INTEGER PRIMARY KEY AUTOINCREMENT,
        farmer_name TEXT, location TEXT, crop TEXT, disease TEXT, severity TEXT, treatment TEXT,
        language TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    conn.commit()
    conn.close()

def register_plot(farmer, location, crop, planting_date, plot_size, budget):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT INTO plots (farmer, location, crop, planting_date, plot_size, budget) VALUES (?,?,?,?,?,?)",
                 (farmer, location, crop, planting_date, plot_size, budget))
    pid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    conn.close()
    return pid

def get_plots():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT rowid AS row_id, * FROM plots ORDER BY created_at DESC", conn)
    conn.close()
    return df

def save_assessment(farmer, location, crop, disease, severity, treatment, language):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT INTO assessments (farmer_name, location, crop, disease, severity, treatment, language) VALUES (?,?,?,?,?,?,?)",
                 (farmer, location, crop, disease, severity, treatment, language))
    conn.commit()
    conn.close()

def get_assessments():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT rowid AS row_id, farmer_name, location, crop, disease, severity, language, created_at FROM assessments ORDER BY created_at DESC LIMIT 30", conn)
    conn.close()
    return df

# ── Weather ─────────────────────────────────────────────
@st.cache_data(ttl=600)
def get_weather(loc):
    coords = RWANDA_COORDS.get(loc, (-1.95, 30.10))
    try:
        r = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={coords[0]}&longitude={coords[1]}&current=temperature_2m,relative_humidity_2m,rain,weather_code&daily=precipitation_probability_max,temperature_2m_max,precipitation_sum&timezone=Africa%2FKigali&forecast_days=7", timeout=5)
        if r.status_code == 200:
            d = r.json()
            curr = d.get("current", {})
            daily = d.get("daily", {})
            return {"temp": curr.get("temperature_2m", "?"), "humidity": curr.get("relative_humidity_2m", "?"),
                    "rain": curr.get("rain", 0) or 0, "code": curr.get("weather_code", 0),
                    "rain_prob": daily.get("precipitation_probability_max", [0])[0] if daily.get("precipitation_probability_max") else 0,
                    "week_rain": sum(daily.get("precipitation_sum", [0])[:7])}
    except: pass
    return {"temp": "?", "humidity": "?", "rain": 0, "code": 0, "rain_prob": 0, "week_rain": 0}

# ── Gemini ──────────────────────────────────────────────
gemini_client = None
if GEMINI_API_KEY:
    try:
        from google import genai
        gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    except: pass

def ask_gemini(prompt, tokens=1000) -> str:
    if not gemini_client: return ""
    try:
        r = gemini_client.models.generate_content(model=GEMINI_MODEL, contents=prompt, config={"temperature": 0.3, "max_output_tokens": tokens})
        return r.text
    except: return ""

def ask_gemini_vision(image_bytes, prompt, tokens=800) -> str:
    if not gemini_client: return ""
    try:
        from google.genai import types as gtypes
        r = gemini_client.models.generate_content(model=GEMINI_MODEL, contents=[prompt, gtypes.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")], config={"temperature": 0.3, "max_output_tokens": tokens})
        return r.text
    except: return ""

# ── Pillar 1: Scout Plan Generator ──────────────────────
def generate_scout_plan(crop, location, planting_date, plot_size) -> str:
    w = get_weather(location)
    prompt = f"""You are an agricultural extension officer in Rwanda. Generate a weekly scouting plan for a {crop} farm.

Plot: {plot_size} hectares, planted {planting_date}, location {location}.
Current weather: {w.get('temp','?')}C, rain probability {w.get('rain_prob',0)}%, weekly rain forecast {w.get('week_rain',0)}mm

Output a structured weekly scouting card:

## When to Scout
(Specific best day this week based on weather. E.g., "Scout on Wednesday before predicted Thursday rain.")

## Where to Scout (Sampling Pattern)
(5 spots × 4 plants = 20 sample points. Check edges and low-lying areas first.)

## What to Look For (Top 3 Threats)
(Based on {crop} growth stage, current climate, and season. List specific symptoms.)

## Action If Found
(What to do immediately if these threats are detected.)

Cite sources: FAO, IITA, or CGIAR where relevant. Keep it farmer-friendly."""
    return ask_gemini(prompt, 600)

# ── Pillar 2: Growing Calendar ──────────────────────────
def generate_calendar(crop, location, planting_date, plot_size, budget) -> str:
    w = get_weather(location)
    prompt = f"""You are an agricultural advisor in Rwanda. Generate a personalized growing calendar for a {plot_size}ha {crop} farm in {location}, planted {planting_date}. 
Budget: {budget} RWF/season. Weather: {w.get('week_rain',0)}mm rain expected this week, temp {w.get('temp','?')}C.

Output a season-long calendar:

## 1. Land Prep Window
(When to prepare land based on historical rainfall onset in {location})

## 2. Optimal Planting Window
(Based on soil moisture forecast — if weather changed, advise delay or accelerate)

## 3. Weed Control Schedule
(Timing based on growth stage + rainfall patterns)

## 4. Fertilizer Application Timing
(Don't waste NPK before heavy rain. Advise specific timings within budget {budget} RWF)

## 5. Harvest Window
(Estimated maturity date based on planting date + weather risk)

## Budget-Friendly Tips
(How to stay within {budget} RWF — prioritize spending, suggest cheaper alternatives)

Cite data sources: Open-Meteo, FAO, IITA."""
    return ask_gemini(prompt, 800)

# ── Pillar 3: Market Connect ────────────────────────────
def generate_market_advice(crop, location, plot_size, planting_date, harvest_estimate) -> str:
    prices = MARKET_PRICES.get(crop, (500, 1000, "stable"))
    prompt = f"""You are a market advisor for {crop} farmers in {location}, Rwanda.
Plot: {plot_size}ha, planted {planting_date}. Estimated harvest: {harvest_estimate}.
Current farmgate price: {prices[0]}-{prices[1]} RWF/kg, trend: {prices[2]}.

Generate a market advisory:

## 1. Sell Now vs Hold
(Should the farmer sell at harvest or store? Why? Based on 30-day price trend {prices[2]}.)

## 2. Price Negotiation Tips
(What price to ask, how to negotiate with buyers.)

## 3. Quality Standards
(What quality specs buyers look for — moisture, size, disease-free, etc.)

## 4. Storage Advice
(How to store {crop} to maximize shelf life and bargaining power.)

Cite sources where relevant. Farmer-language, actionable."""
    return ask_gemini(prompt, 600)

def generate_whatsapp_buyer(crop, location, farmer, harvest_estimate, buyer_name, buyer_crop, lang="English") -> str:
    prices = MARKET_PRICES.get(crop, (500, 1000, "stable"))
    lang_instr = f"Write the message in {lang}." if lang != "English" else ""
    prompt = f"""You are a farmer from {location}, Rwanda. Write a WhatsApp message to a buyer named {buyer_name}.
Crop: {crop}, estimated harvest: {harvest_estimate}, farmgate price: {prices[0]}-{prices[1]} RWF/kg.
The message should be professional, culturally appropriate for Rwanda, and ready to send.
{lang_instr}
Keep it under 400 characters. Include: greeting, what you're selling, quantity, asking price range, and call to action."""
    return ask_gemini(prompt, 300) or f"Hello {buyer_name}, I have {crop} from {location}. Estimated {harvest_estimate}. Price: {prices[0]}-{prices[1]} RWF/kg. Are you interested?"

# ── Page Config ──────────────────────────────────────────
st.set_page_config(page_title="AgriScope AI", page_icon="🌱", layout="wide", initial_sidebar_state="expanded")

# ── CSS ─────────────────────────────────────────────────
st.markdown("""
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    * { font-family: 'Inter', sans-serif; }
    .bi { vertical-align: -0.125em; }
    .stApp { background: linear-gradient(180deg, #090a0f 0%, #0d1117 100%); }
    .main > div { padding: 1rem 1.5rem; }
    .card { background: linear-gradient(135deg, #0f1520 0%, #0d1117 100%); border: 1px solid #1e293b; border-radius: 16px; padding: 1.25rem; margin-bottom: 0.75rem; transition: all 0.3s ease; }
    .card:hover { border-color: #10b98133; box-shadow: 0 4px 20px rgba(16,185,129,0.08); transform: translateY(-2px); }
    .card-title { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.1em; color: #64748b; margin-bottom: 0.75rem; font-weight: 600; }
    [data-testid="stSidebar"] { background: linear-gradient(180deg, #0a0d14 0%, #080a10 100%); border-right: 1px solid #1e293b; }
    .stButton > button { border-radius: 12px !important; font-weight: 600 !important; transition: all 0.25s ease !important; }
    .stButton > button[kind="primary"] { background: linear-gradient(135deg, #059669, #10b981) !important; border: none !important; color: white !important; }
    .stButton > button[kind="primary"]:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(16,185,129,0.3); filter: brightness(1.1); }
    .stButton > button[kind="secondary"] { background: transparent !important; border: 1px solid #334155 !important; color: #94a3b8 !important; }
    .stButton > button[kind="secondary"]:hover { border-color: #10b981 !important; color: #10b981 !important; }
    .stTextInput>div>div>input, .stNumberInput>div>div>input { background: #131a26 !important; border: 1px solid #1e293b !important; color: #e2e8f0 !important; border-radius: 10px !important; }
    .stTextInput>div>div>input:focus { border-color: #10b981 !important; box-shadow: 0 0 0 2px rgba(16,185,129,0.2) !important; }
    .stSelectbox>div>div>select { background: #131a26 !important; border: 1px solid #1e293b !important; color: #e2e8f0 !important; border-radius: 10px !important; }
    hr { border-color: #1e293b !important; opacity: 0.5; }
    ::-webkit-scrollbar { width: 6px; } ::-webkit-scrollbar-track { background: #090a0f; } ::-webkit-scrollbar-thumb { background: #334155; border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: #10b981; }
    .stDataFrame td, .stDataFrame th { background-color: #0f1520 !important; color: #cbd5e1 !important; border-color: #1e293b !important; }
    @keyframes slideDown { from { opacity: 0; transform: translateY(-10px); } to { opacity: 1; transform: translateY(0); } }
</style>
""", unsafe_allow_html=True)

init_db()

# ── Session ──────────────────────────────────────────────
for k in ("ui_language", "active_plot_id", "active_pillar", "plot_registered"):
    if k not in st.session_state: st.session_state[k] = None
if not st.session_state.get("ui_language"): st.session_state["ui_language"] = "English"

# ── Sidebar ──────────────────────────────────────────────
with st.sidebar:
    # Language
    current_lang = st.session_state.get("ui_language", "English")
    idx = list(LANGUAGES.keys()).index(current_lang) if current_lang in LANGUAGES else 0
    selected = st.selectbox("🌐 Language", list(LANGUAGES.keys()), index=idx, key="lang_switch")
    if selected != current_lang: st.session_state["ui_language"] = selected; st.rerun()
    st.markdown("---")

    # Plot Registration
    st.markdown(f"### 🌱 {t('save_plot')}")    
    with st.form("plot_form"):
        farmer = st.text_input(t("farmer_name"), key="fname")
        loc = st.text_input(t("plot_location"), value="Kigali", key="floc")
        crop = st.selectbox(t("crop_type"), THREE_CROPS, key="fcrop")
        plant_date = st.date_input(t("planting_date"), key="fpdate")
        plot_size = st.number_input(t("plot_size"), 0.1, 100.0, 1.0, 0.1, key="fsize")
        budget = st.number_input(t("budget"), 0, 5000000, 100000, 10000, key="fbudget")
        if st.form_submit_button(t("save_plot"), use_container_width=True, type="primary"):
            if farmer:
                pid = register_plot(farmer, loc, crop, str(plant_date), plot_size, budget)
                st.session_state["active_plot_id"] = pid
                st.session_state["plot_registered"] = True
                st.success(f"Plot registered! {crop} in {loc}")
                st.rerun()
    
    st.markdown("---")
    # Plot selector
    plots_df = get_plots()
    if not plots_df.empty:
        plot_options = {f"{r['farmer']} — {r['crop']} ({r['location']})": r['row_id'] for _, r in plots_df.iterrows()}
        selected_plot = st.selectbox("Active Plot:", list(plot_options.keys()), key="plot_sel")
        if plot_options.get(selected_plot) != st.session_state.get("active_plot_id"):
            st.session_state["active_plot_id"] = plot_options[selected_plot]
            st.rerun()
    
    st.markdown("---")
    
    # Quick photo analysis (always available)
    st.markdown("### 📷 Quick Crop Scan")
    img_src = st.radio("", ["📁 Upload", "📸 Camera"], key="quick_img_src", label_visibility="collapsed", horizontal=True)
    cam_img = st.camera_input("Take photo", key="quick_cam") if "Camera" in img_src else None
    up_file = st.file_uploader("Upload crop photo", type=["jpg","jpeg","png"], key="quick_upload") if "Upload" in img_src else None
    
    if cam_img or up_file:
        img_bytes = cam_img.read() if cam_img else up_file.read()
        if img_bytes:
            with st.spinner("AI analyzing..."):
                import urllib.parse
                # Full detailed analysis prompt (from Mworozi)
                diagnosis = ask_gemini_vision(img_bytes, """You are an expert agricultural extension officer for East Africa. Analyze this crop image.

Provide your analysis in this EXACT format:

## Disease / Issue
(Name of the disease, pest, or nutrient deficiency affecting this crop.)

## Severity
(Mild / Moderate / Severe — and a brief explanation why.)

## Recommended Treatment
(Specific, actionable steps the farmer can take using locally available materials. Include organic options if possible.)

## Prevention
(How to prevent this in future growing seasons.)

If the crop appears healthy, say "No disease detected — crop appears healthy." and skip treatment/prevention.""", 800)

                if diagnosis:
                    # Extract disease + severity (must be before use)
                    sev = "Moderate"
                    if "Severe" in diagnosis or "severe" in diagnosis: sev = "Severe"
                    elif "Mild" in diagnosis or "mild" in diagnosis: sev = "Mild"
                    elif "healthy" in diagnosis.lower(): sev = "None"
                    disease_name = diagnosis.split("## Disease")[1].split("\n")[0].replace("/ Issue", "").strip() if "## Disease" in diagnosis else "See analysis"

                    # Save to DB
                    crop_guessed = "Unknown"
                    for c in THREE_CROPS:
                        if c.lower() in diagnosis.lower(): crop_guessed = c; break
                    save_assessment("Quick Scan", "Kigali", crop_guessed, disease_name, sev, diagnosis[:500], "English")

                    # Store for dashboard display
                    st.session_state["quick_scan_result"] = {"diagnosis": diagnosis, "severity": sev, "disease": disease_name, "img_bytes": img_bytes}
                    
                    st.markdown(f"<div class='card' style='padding:0.75rem'><p style='color:#e2e8f0;font-size:0.85rem'>{diagnosis[:300]}...</p></div>", unsafe_allow_html=True)
                    
                    # Share language dropdown
                    share_lang = st.selectbox("Report language:", list(LANGUAGES.keys()), key="share_lang_quick")
                    share_text = f"🌱 AgriScope AI Diagnosis\n\n🦠 {disease_name}\n⚠️ Severity: {sev}\n\n{diagnosis[:600]}"
                    
                    if share_lang != "English" and gemini_client:
                        with st.spinner(f"Translating to {share_lang}..."):
                            translated = ask_gemini(f"Translate this crop diagnosis into {share_lang}. Keep ALL emojis (🌱🦠⚠️📋) exactly as they are. Only translate the words:\n\n{share_text}", 800)
                            if translated: share_text = translated
                    
                    import urllib.parse
                    wa_url = f"https://wa.me/?text={urllib.parse.quote(share_text[:1500])}"
                    sms_url = f"sms:?body={urllib.parse.quote(share_text[:450])}"
                    col1, col2 = st.columns(2)
                    with col1: st.markdown(f'<a href="{wa_url}" target="_blank"><button style="width:100%;padding:0.4rem;border-radius:8px;border:1px solid #25D366;background:transparent;color:#25D366;cursor:pointer;font-size:0.8rem">💬 WhatsApp</button></a>', unsafe_allow_html=True)
                    with col2: st.markdown(f'<a href="{sms_url}"><button style="width:100%;padding:0.4rem;border-radius:8px;border:1px solid #3b82f6;background:transparent;color:#3b82f6;cursor:pointer;font-size:0.8rem">📱 SMS</button></a>', unsafe_allow_html=True)
                else:
                    st.warning("No result — check Gemini API key.")
    
    st.markdown("---")
    st.markdown(f"<span style='color:#10b981'><i class='bi bi-cpu'></i> {t('gemini_on' if gemini_client else 'gemini_off')}</span>", unsafe_allow_html=True)

# ── Title ────────────────────────────────────────────────
c1, c2 = st.columns([0.08, 0.92])
with c1: st.markdown("<h1 style='font-size:2rem;margin:0;color:#10b981'>🌱</h1>", unsafe_allow_html=True)
with c2:
    st.markdown(f"<h1 style='margin:0;font-size:1.5rem'>{t('app_title')}</h1><p style='margin:0;color:#64748b;font-size:0.85rem'><i class='bi bi-graph-up'></i> {t('app_subtitle')}  •  <span style='color:#10b981'><i class='bi bi-globe2'></i> {t('app_region')}</span></p>", unsafe_allow_html=True)
st.markdown("---")

# ── Main Content ─────────────────────────────────────────
if not st.session_state.get("active_plot_id"):
    st.markdown(f"""<div style='text-align:center;padding:4rem 2rem'><p style='font-size:3.5rem;margin:0;color:#10b981'><i class='bi bi-tree-fill'></i></p><h3 style='color:#64748b;margin:0.5rem 0'>{t('welcome_title')}</h3><p style='color:#475569;max-width:480px;margin:0 auto'>{t('welcome_desc')}</p></div>""", unsafe_allow_html=True)
else:
    # Get plot data
    pid = st.session_state["active_plot_id"]
    plot_row = plots_df[plots_df['row_id'] == pid].iloc[0]
    w = get_weather(plot_row['location'])

    # Plot info bar
    harvest_est = f"{plot_row['plot_size'] * random.uniform(8, 15):.1f} tons"
    st.markdown(f"""<div style='display:flex;gap:1rem;margin-bottom:1rem'>
        <div class='card' style='flex:1;text-align:center;padding:0.75rem'><p style='color:#10b981;font-size:1rem;margin:0'>{plot_row['crop']} — {plot_row['location']}</p></div>
        <div class='card' style='flex:1;text-align:center;padding:0.75rem'><p style='color:#f59e0b;font-size:1rem;margin:0'>{w['temp']}°C / {w['rain_prob']}% rain</p></div>
        <div class='card' style='flex:1;text-align:center;padding:0.75rem'><p style='color:#3b82f6;font-size:1rem;margin:0'>{plot_row['plot_size']}ha / {plot_row['budget']:,} RWF</p></div>
    </div>""", unsafe_allow_html=True)

    # Pillar Navigation
    # ── Dashboard Report (from Quick Scan) ──────────────────
    if "quick_scan_result" in st.session_state and st.session_state["quick_scan_result"]:
        res = st.session_state["quick_scan_result"]
        sev = res["severity"]
        colors = {"Severe": ("#450a0a", "#ef4444", "#fca5a5"), "Moderate": ("#422006", "#f59e0b", "#fde68a"), "Mild": ("#0c4a6e", "#3b82f6", "#93c5fd"), "None": ("#052e16", "#10b981", "#86efac")}
        bg, bd, cl = colors.get(sev, colors["Moderate"])
        st.markdown(f"""<div style='background:linear-gradient(135deg,{bg} 0%,{bg} 100%);border:1px solid {bd};border-radius:16px;padding:1.25rem 1.5rem;margin-bottom:1rem;animation:slideDown 0.4s ease'>
            <h2 style='color:{cl};margin:0 0 0.25rem'>{'⚠️ Severe' if sev == 'Severe' else ('⚠️ Moderate' if sev == 'Moderate' else ('ℹ️ Mild' if sev == 'Mild' else '✅ Healthy'))} — {res['disease'][:60]}</h2>
            <p style='color:{cl};margin:0;opacity:0.8;font-size:0.9rem'>Tap WhatsApp or SMS below to share this report with the farmer.</p>
        </div>""", unsafe_allow_html=True)

        col_diag, col_metrics = st.columns([0.65, 0.35])
        with col_diag:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown(res["diagnosis"])
            st.markdown("</div>", unsafe_allow_html=True)
        with col_metrics:
            st.markdown(f"""<div class='card' style='text-align:center;min-height:200px'>
                <div class='card-title'>Metrics</div>
                <p style='color:#10b981;font-size:2rem;margin:0'>85%</p><p style='color:#64748b;font-size:0.7rem;margin:0'>AI Confidence</p>
                <p style='color:{bd};font-size:1.2rem;margin:0.5rem 0'>{sev}</p><p style='color:#64748b;font-size:0.7rem;margin:0'>Severity</p>
            </div>""", unsafe_allow_html=True)

        # Share buttons
        import urllib.parse
        share_msg = f"🌱 AgriScope AI Diagnosis\n\n🦠 {res['disease']}\n⚠️ Severity: {sev}\n\n{res['diagnosis'][:800]}"
        wa_url = f"https://wa.me/?text={urllib.parse.quote(share_msg[:1500])}"
        sms_url = f"sms:?body={urllib.parse.quote(share_msg[:400])}"
        col_wa, col_sms, col_close = st.columns([1, 1, 1])
        with col_wa: st.markdown(f'<a href="{wa_url}" target="_blank"><button style="width:100%;padding:0.5rem;border-radius:8px;border:1px solid #25D366;background:transparent;color:#25D366;cursor:pointer;font-size:0.85rem">💬 WhatsApp Report</button></a>', unsafe_allow_html=True)
        with col_sms: st.markdown(f'<a href="{sms_url}"><button style="width:100%;padding:0.5rem;border-radius:8px;border:1px solid #3b82f6;background:transparent;color:#3b82f6;cursor:pointer;font-size:0.85rem">📱 SMS Report</button></a>', unsafe_allow_html=True)
        with col_close:
            if st.button("✕ Close Report", key="close_scan", use_container_width=True):
                del st.session_state["quick_scan_result"]
                st.rerun()
        st.markdown("---")

    pillar = st.radio("", [f"🔍 {t('pillar1')}", f"📅 {t('pillar2')}", f"💰 {t('pillar3')}"], horizontal=True, key="pillar_nav", label_visibility="collapsed")
    
    # ═══ PILLAR 1: SMART SCOUTING ═══
    if t('pillar1') in pillar:
        st.markdown(f"<h2 style='color:#10b981'>🔍 {t('pillar1')}</h2>", unsafe_allow_html=True)

        if st.button(f"🔍 {t('scout_plan_btn')}", type="primary", use_container_width=True):
            with st.spinner("Generating scout plan..."):
                plan = generate_scout_plan(plot_row['crop'], plot_row['location'], plot_row['planting_date'], plot_row['plot_size'])
                st.session_state["scout_plan"] = plan
                st.rerun()

        if "scout_plan" in st.session_state and st.session_state["scout_plan"]:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown(st.session_state["scout_plan"])
            st.markdown(f"<p style='color:#64748b;font-size:0.7rem;margin-top:0.5rem'>{t('sources')}</p></div>", unsafe_allow_html=True)

            # Share scout plan
            import urllib.parse
            wa_plan = f"https://wa.me/?text={urllib.parse.quote('AgriScope Scout Plan\n\n' + st.session_state['scout_plan'][:1500])}"
            st.markdown(f'<a href="{wa_plan}" target="_blank"><button style="width:100%;padding:0.5rem;border-radius:8px;border:1px solid #25D366;background:transparent;color:#25D366;cursor:pointer;font-size:0.85rem;margin-top:0.5rem">💬 Send Scout Plan via WhatsApp</button></a>', unsafe_allow_html=True)

        # Photo Check-In
        st.markdown(f"<h3 style='color:#10b981;margin-top:1rem'>📷 {t('photo_checkin')}</h3>", unsafe_allow_html=True)
        up_img = st.file_uploader(f"{t('scout_photo')}", type=["jpg","jpeg","png"], key="scout_upload")
        if up_img:
            img_bytes = up_img.read()
            with st.spinner("AI analyzing scout photo..."):
                diagnosis = ask_gemini_vision(img_bytes, f"""Analyze this {plot_row['crop']} plant from a scouting photo in {plot_row['location']}, Rwanda.
Report: 1) Any disease/pest found? 2) Severity (Low/Medium/High) 3) Recommended action 4) Confidence (High/Medium/Low).
If confidence is Low or Medium, say "HUMAN VERIFICATION RECOMMENDED — consult local extension officer."
Cite: FAO, IITA.""", 400)
                st.markdown("<div class='card'>", unsafe_allow_html=True)
                st.markdown(diagnosis)
                if "HUMAN VERIFICATION" in diagnosis.upper() or "LOW" in diagnosis.upper():
                    st.warning(f"⚠️ {t('human_verify')}")
                else:
                    st.markdown(f"<p style='color:#64748b;font-size:0.7rem;margin-top:0.5rem'>{t('sources')}</p>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

        # Neighbor Alerts (mock)
        st.markdown(f"<h3 style='color:#f59e0b;margin-top:1rem'>⚠️ {t('neighbor_alert')}</h3>", unsafe_allow_html=True)
        mock_alerts = [
            f"Cassava Mosaic Virus spotted 3km away in Gicumbi — check your plants for leaf curling and yellow mosaic patterns. (Source: Community Scout Network)",
            f"Fall Armyworm activity reported near {plot_row['location']} — inspect maize whorls for larvae and frass. (Source: FAO Rwanda Alert)",
        ] if plot_row['crop'] in ['Maize', 'Cassava'] else [
            f"Yam anthracnose reported in neighboring sector — check for dark leaf spots. (Source: IITA)",
        ]
        for alert in mock_alerts[:2]:
            st.markdown(f"""<div class='card' style='padding:0.75rem;border-left:3px solid #f59e0b;margin-bottom:0.5rem'>
                <span style='color:#fde68a;font-size:0.85rem'>⚠️ {alert}</span></div>""", unsafe_allow_html=True)

        st.markdown(f"<p style='color:#64748b;font-size:0.7rem'>{t('sources')}</p>", unsafe_allow_html=True)

    # ═══ PILLAR 2: CLIMATE CALENDAR ═══
    elif t('pillar2') in pillar:
        st.markdown(f"<h2 style='color:#f59e0b'>📅 {t('pillar2')}</h2>", unsafe_allow_html=True)

        if st.button(f"📅 {t('generate_calendar')}", type="primary", use_container_width=True):
            with st.spinner("Building your personalized growing calendar..."):
                calendar = generate_calendar(plot_row['crop'], plot_row['location'], plot_row['planting_date'], plot_row['plot_size'], plot_row['budget'])
                st.session_state["calendar"] = calendar
                st.rerun()

        if "calendar" in st.session_state and st.session_state["calendar"]:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown(st.session_state["calendar"])
            st.markdown(f"<p style='color:#64748b;font-size:0.7rem;margin-top:0.5rem'>{t('sources')}</p></div>", unsafe_allow_html=True)

            # Weather adaptation note
            if w.get('week_rain', 0) > 20:
                st.warning(f"⚠️ Heavy rain ({w['week_rain']}mm) expected this week. Consider delaying field operations.")
            if w.get('temp', 0) != '?' and float(str(w['temp']).replace('?','0')) > 32:
                st.warning(f"⚠️ High temperatures may stress {plot_row['crop']}. Ensure adequate irrigation.")

    # ═══ PILLAR 3: MARKET CONNECT ═══
    else:
        st.markdown(f"<h2 style='color:#3b82f6'>💰 {t('pillar3')}</h2>", unsafe_allow_html=True)

        # Harvest estimate
        st.markdown(f"""<div class='card' style='text-align:center'>
            <div class='card-title'>{t('harvest_estimate')}</div>
            <p style='color:#10b981;font-size:2rem;margin:0'>{harvest_est}</p>
            <p style='color:#64748b;font-size:0.8rem;margin:0'>{plot_row['crop']} from {plot_row['plot_size']}ha</p>
        </div>""", unsafe_allow_html=True)

        # Prices
        prices = MARKET_PRICES.get(plot_row['crop'], (500, 1000, "stable"))
        trend_icon = {"rising": "📈", "falling": "📉", "stable": "📊"}.get(prices[2], "📊")
        st.markdown(f"""<div class='card' style='text-align:center'>
            <div class='card-title'>{t('sell_advice')}</div>
            <p style='color:#e2e8f0;font-size:1.2rem;margin:0'>{prices[0]:,} – {prices[1]:,} RWF/kg {trend_icon} {prices[2]}</p>
        </div>""", unsafe_allow_html=True)

        # Buyers
        st.markdown(f"<h3 style='color:#10b981'>👥 {t('find_buyers')}</h3>", unsafe_allow_html=True)
        crop_buyers = BUYERS.get(plot_row['crop'], [])
        for buyer in crop_buyers:
            with st.expander(f"{buyer[0]} — {buyer[1]}"):
                st.markdown(f"**Needs:** {buyer[3]}")
                st.markdown(f"**Standards:** {buyer[4]}")
                st.markdown(f"**Contact:** {buyer[2]}")

                # WhatsApp buyer message
                if st.button(f"{t('whatsapp_buyer')} {buyer[0]}", key=f"wa_buyer_{buyer[0]}"):
                    msg = generate_whatsapp_buyer(plot_row['crop'], plot_row['location'], plot_row['farmer'], harvest_est, buyer[0], buyer[3], st.session_state.get('ui_language', 'English'))
                    wa_link = f"https://wa.me/{buyer[2].replace('+','')}?text={urllib.parse.quote(msg)}"
                    st.markdown(f'<a href="{wa_link}" target="_blank"><button style="width:100%;padding:0.5rem;border-radius:8px;border:1px solid #25D366;background:transparent;color:#25D366;cursor:pointer;font-size:0.85rem">💬 Send WhatsApp Message</button></a>', unsafe_allow_html=True)
                    st.markdown(f"<div class='card' style='margin-top:0.5rem;padding:0.75rem'><p style='color:#94a3b8;font-size:0.85rem'>{msg}</p></div>", unsafe_allow_html=True)

        # Market Advice
        if st.button(f"📊 {t('sell_advice')}", type="secondary", use_container_width=True):
            with st.spinner("Analyzing market..."):
                advice = generate_market_advice(plot_row['crop'], plot_row['location'], plot_row['plot_size'], plot_row['planting_date'], harvest_est)
                st.markdown("<div class='card'>", unsafe_allow_html=True)
                st.markdown(advice)
                st.markdown(f"<p style='color:#64748b;font-size:0.7rem;margin-top:0.5rem'>Sources: Market data, FAO</p></div>", unsafe_allow_html=True)

# ── Assessment History (always visible) ────────────────────
st.markdown("---")
st.markdown("<h3 style='color:#10b981'><i class='bi bi-database'></i> Assessment History</h3>", unsafe_allow_html=True)
assessments_df = get_assessments()
if not assessments_df.empty:
    assessments_df.columns = ["ID", "Farmer", "Location", "Crop", "Disease", "Severity", "Language", "Date"]
    st.dataframe(assessments_df[["Farmer", "Location", "Crop", "Disease", "Severity", "Date"]], use_container_width=True, hide_index=True)
else:
    st.markdown(f"<p style='color:#64748b'>No assessments yet. Upload a crop photo to start.</p>", unsafe_allow_html=True)
