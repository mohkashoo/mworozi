import os, sqlite3, time, json, datetime as dt
import warnings
warnings.filterwarnings("ignore")

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import streamlit as st
import pandas as pd
import numpy as np
import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DB_PATH = "agri.db"
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

LANGUAGES = {
    "English": "en",
    "Kinyarwanda": "rw",
    "Swahili": "sw",
    "French": "fr",
}

T = {
    "English": {
        "app_title": "MWOROZI",
        "app_subtitle": "AI Crop Health Assistant",
        "app_region": "Rwanda / East Africa",
        "farmer_info": "Farmer Info",
        "farmer_name": "Farmer's Name",
        "sector": "Sector / Village",
        "crop_type": "Crop Type",
        "response_lang": "Response Language",
        "resources": "Farming Resources",
        "resources_options": ["Both (Organic + Chemical)", "Organic Only", "Chemical Only"],
        "season": "Current Season",
        "season_options": ["Growing Season", "Planting Season", "Harvest Season", "Dry Season"],
        "save_info": "Save Info",
        "crop_image": "Crop Image",
        "img_source": "Image source",
        "img_options": ["Upload Photo", "Take Photo", "Demo Sample"],
        "upload_photo": "Upload crop photo",
        "camera_capture": "Point at the crop and take a photo",
        "camera_success": "Photo captured from camera",
        "sample_crop_issue": "Sample Crop Issue",
        "analyze_btn": "Analyze Crop Health",
        "gemini_on": "Gemini AI enabled",
        "gemini_off": "Gemini unavailable — using demo data",
        "please_name": "Please enter the farmer's name.",
        "please_img": "Please upload a crop photo or select a demo sample.",
        "analyzing": "Analyzing crop image with AI…",
        "severe_title": "Severe Disease Detected",
        "severe_msg": "Immediate action required",
        "moderate_title": "Moderate Issue Detected",
        "moderate_msg": "Treat within the week",
        "mild_title": "Mild Issue — Monitor",
        "mild_msg": "Monitor and apply preventive measures",
        "healthy_title": "Crop Appears Healthy",
        "healthy_msg": "No disease detected. Continue routine care.",
        "farmer_details": "Farmer Details",
        "crop_analysis": "Crop Health Analysis",
        "ai_confidence": "AI Confidence",
        "severity_label": "Severity",
        "season_label": "Season",
        "start_recovery": "Start Recovery Checklist for This Plant",
        "keep_healthy_btn": "Keep It Healthy Checklist",
        "voice_ready": "Audio ready — click play above",
        "voice_generate": "Generate Audio",
        "voice_generating": "Generating audio…",
        "voice_error": "Could not generate audio",
        "disclaimer": "This analysis is AI-generated and should be verified with a local agricultural extension officer.",
        "no_analysis": "No analysis available. Please try again with a clearer image.",
        "back_to_dash": "Back to Dashboard",
        "recovery_checklist": "Recovery Checklist",
        "keep_healthy_title": "Keep Healthy Checklist",
        "current_task": "Current Task",
        "upload_checkin": "Upload photo for",
        "notes": "Your notes (what do you see?)",
        "submit_ai": "Submit & Get AI Analysis",
        "upload_required": "Please upload a photo so AI can check progress.",
        "all_done": "All Tasks Complete",
        "all_done_recovery": "Your plant has recovered. Keep monitoring regularly.",
        "all_done_healthy": "Your plant is healthy. Continue good practices.",
        "overall_progress": "Overall Progress",
        "tasks": "tasks",
        "check_progress": "Check Progress — All Assessments",
        "checklist_history": "Checklist History — Active Plans",
        "recovery_label": "Recovery",
        "keep_healthy_label": "Keep Healthy",
        "completed": "completed",
        "check_progress_desc": "Select an assessment below to start or continue a recovery checklist for that plant.",
        "continue_btn": "Continue",
        "treat_btn": "Treat This Plant",
        "keep_healthy_row": "Keep Healthy",
        "no_assessments": "No assessments yet. Run an analysis to populate the history.",
        "welcome_title": "Welcome to Mworozi",
        "welcome_desc": "Upload a photo of your crop to detect diseases, get treatment recommendations, and receive prevention advice — all in your language.",
        "dashboard": "Dashboard",
        "check_progress_nav": "Check Progress",
        "assessment_history": "Assessment History",
        "no_assessments_yet": "No assessments yet. Upload a crop photo to get started.",
    },
    "Kinyarwanda": {
        "app_title": "MWOROZI",
        "app_subtitle": "Umufasha w'ubuhinzi ukoresha AI",
        "app_region": "Rwanda / Afurika y'Iburasirazuba",
        "farmer_info": "Amakuru y'umuhinzi",
        "farmer_name": "Izina ry'umuhinzi",
        "sector": "Umurenge / Akagari",
        "crop_type": "Ubwoko bw'igihingwa",
        "response_lang": "Ururimi rw'ibisubizo",
        "resources": "Uburyo bwo guhinga",
        "resources_options": ["Byombi (Organic + Chimique)", "Organic Gusa", "Chimique Gusa"],
        "season": "Igihe cy'ihinga",
        "season_options": ["Igihe cyo guhinga", "Igihe cyo gutera", "Igihe cyo gusarura", "Igihe cy'izuba"],
        "save_info": "Bika Amakuru",
        "crop_image": "Ifoto y'igihingwa",
        "img_source": "Aho ifoto ituruka",
        "img_options": ["Shyira Ifoto", "Fotora", "Igerageza"],
        "upload_photo": "Shyira ifoto y'igihingwa",
        "camera_capture": "Fotora igihingwa",
        "camera_success": "Ifoto yafashwe",
        "sample_crop_issue": "Igerageza ku ndwara",
        "analyze_btn": "Suzuma Ubuzima bw'igihingwa",
        "gemini_on": "Gemini AI irakora",
        "gemini_off": "Gemini ntabwo iboneka — dukoresha igerageza",
        "please_name": "Andika izina ry'umuhinzi.",
        "please_img": "Shyira ifoto y'igihingwa cyangwa hitamo igerageza.",
        "analyzing": "AI irimo gusuzuma ifoto…",
        "severe_title": "Indwara Ikomeye Yabonetse",
        "severe_msg": "Hakenewe igikorwa cyihuse",
        "moderate_title": "Ikibazo Giciriritse Cyabonetse",
        "moderate_msg": "Vura mu cyumweru kimwe",
        "mild_title": "Ikibazo Cyoroshye — Kora Ubigenzura",
        "mild_msg": "Kora ubigenzura kandi ukore uburyo bwo kwirinda",
        "healthy_title": "Igihingwa Kigaragara Nk'icyizima",
        "healthy_msg": "Nta ndwara yabonetse. Komeza kwita ku gihingwa.",
        "farmer_details": "Amakuru y'umuhinzi",
        "crop_analysis": "Isesengura ry'ubuzima bw'igihingwa",
        "ai_confidence": "Icyizere cya AI",
        "severity_label": "Ubukana",
        "season_label": "Igihe",
        "start_recovery": "Tangira Gahunda yo Kuvura iki gihingwa",
        "keep_healthy_btn": "Gahunda yo Kukomeza Ubuzima Bwiza",
        "voice_ready": "Amajwi araboneka — kanda gukina hejuru",
        "voice_generate": "Kora Amajwi",
        "voice_generating": "Gukora amajwi…",
        "voice_error": "Ntibishoboka gukora amajwi",
        "disclaimer": "Ibi byatanzwe na AI bigomba kugenzurwa n'umujyanama w'ubuhinzi.",
        "no_analysis": "Nta s analytical ibonetse. Ongera ugerageze n'ifoto nziza.",
        "back_to_dash": "Subira ku Ntangiriro",
        "recovery_checklist": "Urutonde rwo Kuvura",
        "keep_healthy_title": "Gahunda yo Gukomeza Ubuzima Bwiza",
        "current_task": "Igikorwa Kiriho",
        "upload_checkin": "Shyira ifoto ya",
        "notes": "Ibyo ubona (wandike hano):",
        "submit_ai": "Ohereza & AI isuzume",
        "upload_required": "Shyira ifoto kugira ngo AI igenzure aho bigeze.",
        "all_done": "Ibikorwa Byose Birangiye",
        "all_done_recovery": "Igihingwa cyawe cyakize. Komeza kugenzura buri gihe.",
        "all_done_healthy": "Igihingwa cyawe ni cyiza. Komeza gukora neza.",
        "overall_progress": "Iterambere Rusange",
        "tasks": "ibikorwa",
        "check_progress": "Reba Iterambere — Isesengura Ryose",
        "checklist_history": "Amateka y'Urutonde — Gahunda Zikiriho",
        "recovery_label": "Kuvura",
        "keep_healthy_label": "Gukomeza Ubuzima",
        "completed": "byarangiye",
        "check_progress_desc": "Hitamo is analytical hepfo kugira ngo utangire cyangwa ukomeze gahunda yo kuvura icyo gihingwa.",
        "continue_btn": "Komeza",
        "treat_btn": "Vura iki Gihingwa",
        "keep_healthy_row": "Komeza Ubuzima Bwiza",
        "no_assessments": "Nta s analytical zikiriho. Tangira isesengura kugira ngo ubike amateka.",
        "welcome_title": "Murakaza neza kuri Mworozi",
        "welcome_desc": "Shyira ifoto y'igihingwa cyawe kugira ngo AI imenye indwara, igutangire uburyo bwo kuvura, n'inama zo kwirinda — byose mu rurimi rwawe.",
        "dashboard": "Inshuro ya Mbere",
        "check_progress_nav": "Reba Iterambere",
        "assessment_history": "Amateka y'Isesengura",
        "no_assessments_yet": "Nta s analytical zikiriho. Shyira ifoto y'igihingwa kugira ngo utangire.",
    },
}
# Swahili and French inherit English as fallback
T["Swahili"] = {
    **T["English"],
    "app_title": "MWOROZI",
    "app_subtitle": "Msaidizi wa Kilimo wa AI",
    "app_region": "Afrika Mashariki",
    "farmer_info": "Taarifa za Mkulima",
    "farmer_name": "Jina la Mkulima",
    "save_info": "Hifadhi Taarifa",
    "analyze_btn": "Chambua Afya ya Mmea",
    "welcome_title": "Karibu Mworozi",
    "welcome_desc": "Pakia picha ya mmea wako ili AI itambue magonjwa na kukupa ushauri wa matibabu — yote kwa lugha yako.",
    "check_progress": "Angalia Maendeleo — Tathmini Zote",
    "checklist_history": "Historia ya Orodha — Mipango Hai",
    "recovery_label": "Matibabu",
    "keep_healthy_label": "Dumisha Afya",
    "completed": "imekamilika",
    "dashboard": "Dashibodi",
    "check_progress_nav": "Angalia Maendeleo",
    "assessment_history": "Historia ya Uchambuzi",
    "start_recovery": "Anza Mpango wa Matibabu",
    "recovery_checklist": "Orodha ya Matibabu",
    "keep_healthy_title": "Endelea Kuwa na Afya",
    "all_done_recovery": "Mmea wako umepona. Endelea kufuatilia.",
    "no_assessments": "Hakuna uchambuzi bado. Pakia picha ya mmea ili kuanza.",
}
T["French"] = {
    **T["English"],
    "app_title": "MWOROZI",
    "app_subtitle": "Assistant Agricole IA",
    "app_region": "Rwanda / Afrique de l'Est",
    "farmer_info": "Info Agriculteur",
    "farmer_name": "Nom de l'agriculteur",
    "sector": "Secteur / Village",
    "save_info": "Enregistrer",
    "analyze_btn": "Analyser la Santé de la Culture",
    "welcome_title": "Bienvenue sur Mworozi",
    "welcome_desc": "Téléchargez une photo de votre culture pour détecter les maladies et obtenir des recommandations de traitement — dans votre langue.",
    "check_progress": "Voir les Progrès — Toutes les Évaluations",
    "checklist_history": "Historique des Listes — Plans Actifs",
    "recovery_label": "Récupération",
    "keep_healthy_label": "Maintien Santé",
    "completed": "terminé",
    "dashboard": "Tableau de Bord",
    "check_progress_nav": "Voir les Progrès",
    "assessment_history": "Historique des Analyses",
    "start_recovery": "Commencer le Plan de Traitement",
    "recovery_checklist": "Liste de Traitement",
    "all_done_recovery": "Votre plante a récupéré. Continuez à surveiller.",
    "no_assessments": "Aucune analyse pour le moment. Téléchargez une photo pour commencer.",
}

def t(key: str) -> str:
    lang = st.session_state.get("ui_language", "English")
    return T.get(lang, T["English"]).get(key, T["English"].get(key, key))

# Common crops in Rwanda / East Africa
CROPS = [
    "Maize", "Beans", "Cassava", "Sweet Potato", "Irish Potato",
    "Banana", "Coffee", "Tea", "Rice", "Soybean",
    "Tomato", "Cabbage", "Onion", "Sorghum", "Wheat",
    "Other (let AI detect)",
]

# ── Weather API (Open-Meteo — free, no key) ────────────
RWANDA_COORDS = {"Rulindo": (-1.72, 29.94), "Kigali": (-1.95, 30.10),
    "Musanze": (-1.50, 29.63), "Rubavu": (-1.68, 29.25), "Huye": (-2.60, 29.74),
    "Muhanga": (-2.08, 29.75), "Rwamagana": (-1.95, 30.43), "Gicumbi": (-1.62, 30.12),
}

@st.cache_data(ttl=600)
def get_weather(location: str) -> dict:
    """Fetch weather for a location using Open-Meteo free API."""
    coords = RWANDA_COORDS.get(location, (-1.95, 30.10))
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={coords[0]}&longitude={coords[1]}&current=temperature_2m,relative_humidity_2m,rain,weather_code&daily=precipitation_probability_max,temperature_2m_max&timezone=Africa%2FKigali&forecast_days=2"
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            d = r.json()
            curr = d.get("current", {})
            return {
                "temp": curr.get("temperature_2m", "?"),
                "humidity": curr.get("relative_humidity_2m", "?"),
                "rain": curr.get("rain", 0) or 0,
                "code": curr.get("weather_code", 0),
                "rain_prob": d.get("daily", {}).get("precipitation_probability_max", [0])[0] if d.get("daily") else 0,
                "tomorrow_temp": d.get("daily", {}).get("temperature_2m_max", [0])[1] if len(d.get("daily", {}).get("temperature_2m_max", [])) > 1 else 0,
            }
    except Exception:
        pass
    return {"temp": "?", "humidity": "?", "rain": 0, "code": 0, "rain_prob": 0, "tomorrow_temp": 0}

WEATHER_ICONS = {0: "☀️", 1: "🌤️", 2: "⛅", 3: "☁️", 45: "🌫️", 51: "🌦️", 61: "🌧️", 80: "🌦️", 95: "⛈️"}

# ── Market Prices (Rwanda / East Africa — estimated per kg in RWF) ──
MARKET_PRICES = {
    "Maize": (600, 900), "Beans": (1200, 1800), "Cassava": (300, 500),
    "Sweet Potato": (400, 700), "Irish Potato": (500, 800), "Banana": (400, 700),
    "Coffee": (3500, 5500), "Tea": (2500, 4000), "Rice": (1200, 1800),
    "Soybean": (1000, 1500), "Tomato": (800, 1400), "Cabbage": (300, 600),
    "Onion": (700, 1200), "Sorghum": (500, 800), "Wheat": (800, 1200),
}

def get_market_price(crop: str) -> str:
    price_range = None
    for key, val in MARKET_PRICES.items():
        if key.lower() in crop.lower():
            price_range = val
            break
    if price_range:
        return f"{price_range[0]:,} – {price_range[1]:,} RWF/kg"
    return "Contact local market"

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Mworozi — AI Crop Health Assistant",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS — smooth modern agri theme
# ---------------------------------------------------------------------------
CSS = """
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    * { font-family: 'Inter', sans-serif; }
    .bi { vertical-align: -0.125em; }

    .stApp { background: linear-gradient(180deg, #090a0f 0%, #0d1117 100%); }
    .main > div { padding: 1rem 1.5rem; }

    /* === Cards === */
    .card {
        background: linear-gradient(135deg, #0f1520 0%, #0d1117 100%);
        border: 1px solid #1e293b; border-radius: 16px;
        padding: 1.25rem; margin-bottom: 0.75rem;
        transition: all 0.3s ease;
    }
    .card:hover {
        border-color: #10b98133; box-shadow: 0 4px 20px rgba(16, 185, 129, 0.08);
        transform: translateY(-2px);
    }
    .card-title {
        font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.1em;
        color: #64748b; margin-bottom: 0.75rem; font-weight: 600;
    }

    /* === Alerts === */
    .alert-disease {
        background: linear-gradient(135deg, #450a0a 0%, #7f1d1d 100%);
        border: 1px solid #ef4444; border-radius: 16px;
        padding: 1.25rem 1.5rem; margin-bottom: 1rem;
        animation: slideDown 0.4s ease;
    }
    .alert-disease h2 { color: #fca5a5; margin: 0 0 0.25rem; font-size: 1.25rem; font-weight: 700; }
    .alert-disease p  { color: #fecaca; margin: 0; font-size: 0.9rem; }

    .alert-healthy {
        background: linear-gradient(135deg, #052e16 0%, #14532d 100%);
        border: 1px solid #10b981; border-radius: 16px;
        padding: 1.25rem 1.5rem; margin-bottom: 1rem;
        animation: slideDown 0.4s ease;
    }
    .alert-healthy h2 { color: #86efac; margin: 0 0 0.25rem; font-size: 1.25rem; font-weight: 700; }
    .alert-healthy p  { color: #bbf7d0; margin: 0; font-size: 0.9rem; }

    @keyframes slideDown {
        from { opacity: 0; transform: translateY(-10px); }
        to   { opacity: 1; transform: translateY(0); }
    }
    @keyframes fadeIn {
        from { opacity: 0; }
        to   { opacity: 1; }
    }
    @keyframes pulse {
        0%, 100% { transform: scale(1); }
        50%      { transform: scale(1.05); }
    }
    @keyframes gentleBounce {
        0%, 100% { transform: translateY(0); }
        50%      { transform: translateY(-6px); }
    }

    .section-label {
        font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.1em;
        color: #64748b; margin: 1.25rem 0 0.5rem; border-bottom: 1px solid #1e293b;
        padding-bottom: 0.3rem; font-weight: 600;
    }

    /* === Sidebar === */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0a0d14 0%, #080a10 100%);
        border-right: 1px solid #1e293b;
    }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
        color: #e2e8f0; font-weight: 600;
    }

    /* === Inputs === */
    .stTextInput>div>div>input, .stNumberInput>div>div>input, .stTextArea>div>textarea {
        background: #131a26 !important; border: 1px solid #1e293b !important;
        color: #e2e8f0 !important; border-radius: 10px !important;
        transition: border-color 0.3s;
    }
    .stTextInput>div>div>input:focus, .stTextArea>div>textarea:focus {
        border-color: #10b981 !important; box-shadow: 0 0 0 2px rgba(16,185,129,0.2) !important;
    }
    .stSelectbox>div>div>select {
        background: #131a26 !important; border: 1px solid #1e293b !important;
        color: #e2e8f0 !important; border-radius: 10px !important;
    }

    /* === Buttons === */
    .stButton > button {
        border-radius: 12px !important; font-weight: 600 !important;
        transition: all 0.25s ease !important; letter-spacing: 0.01em;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #059669, #10b981) !important;
        border: none !important; color: white !important;
    }
    .stButton > button[kind="primary"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(16, 185, 129, 0.3);
        filter: brightness(1.1);
    }
    .stButton > button[kind="secondary"] {
        background: transparent !important; border: 1px solid #334155 !important;
        color: #94a3b8 !important;
    }
    .stButton > button[kind="secondary"]:hover {
        border-color: #10b981 !important; color: #10b981 !important;
        transform: translateY(-2px); box-shadow: 0 4px 12px rgba(16,185,129,0.15);
    }

    /* === Radio & Segmented Control === */
    [data-testid="stRadio"] label { color: #94a3b8; }
    
    /* === Data === */
    .stDataFrame { background: transparent !important; }
    .stDataFrame td, .stDataFrame th {
        background-color: #0f1520 !important; color: #cbd5e1 !important;
        border-color: #1e293b !important; padding: 0.5rem 0.75rem !important;
    }
    .stDataFrame th { color: #10b981 !important; font-weight: 600 !important; font-size: 0.75rem; }
    
    /* === Expander === */
    .streamlit-expanderHeader {
        background: #0f1520 !important; border: 1px solid #1e293b !important;
        border-radius: 12px !important; color: #e2e8f0 !important;
        transition: all 0.3s;
    }
    .streamlit-expanderHeader:hover {
        border-color: #10b98144 !important;
    }

    /* === Misc === */
    hr { border-color: #1e293b !important; opacity: 0.5; }
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: #090a0f; }
    ::-webkit-scrollbar-thumb { background: #334155; border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: #10b981; }
    
    /* === Welcome Emoji Animation === */
    .welcome-icon { animation: gentleBounce 3s ease infinite; display: inline-block; }

    /* === Chat bubble animation === */
    [style*="border-radius:12px 12px 4px 12px"] {
        animation: fadeIn 0.3s ease;
    }
</style>
"""

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS assessments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            farmer_name TEXT,
            location TEXT,
            crop TEXT,
            disease TEXT,
            severity TEXT,
            treatment TEXT,
            language TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def save_assessment(record: dict):
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        conn.execute("""
            INSERT INTO assessments (farmer_name, location, crop, disease, severity, treatment, language)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (record["farmer_name"], record["location"], record["crop"],
              record["disease"], record["severity"], record["treatment"], record["language"]))
        conn.commit()
        conn.close()
    except Exception:
        pass


def delete_assessment(row_id: int):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM assessments WHERE rowid = ?", (row_id,))
    conn.commit()
    conn.close()


def update_assessment(row_id: int, field: str, value):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(f"UPDATE assessments SET {field} = ? WHERE rowid = ?", (value, row_id))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Treatment Plan Database
# ---------------------------------------------------------------------------
TREATMENT_PLANS = {
    "Northern Corn Leaf Blight": [
        ("Day 1", "Remove all infected leaves and destroy them. Apply copper fungicide."),
        ("Day 3", "Re-apply fungicide. Check for new spots. Ensure proper spacing."),
        ("Day 7", "Apply neem spray (organic). Remove any new infected leaves."),
        ("Day 14", "Final check. If no new spots → success. If still spreading → re-treat."),
    ],
    "Cassava Mosaic Virus": [
        ("Day 1", "Remove and burn all infected plants immediately. Treat soil with lime."),
        ("Day 3", "Apply neem oil spray to control whiteflies on remaining plants."),
        ("Day 7", "Check for new symptoms on remaining plants. Re-apply neem oil."),
        ("Day 14", "If no new symptoms → success. Plant resistant variety next season."),
    ],
    "Late Blight": [
        ("Day 1", "Remove all affected leaves and fruits. Apply copper oxychloride."),
        ("Day 3", "Re-apply fungicide. Check stems for dark lesions."),
        ("Day 7", "Apply baking soda spray (organic option). Remove any new spots."),
        ("Day 14", "Fruits should be safe to harvest. Prevent next season with resistant varieties."),
    ],
    "Keep Healthy": [
        ("Week 1", "Water regularly. Check for pests under leaves. Remove weeds."),
        ("Week 2", "Apply organic compost or fertilizer. Monitor for yellowing."),
        ("Week 3", "Check soil moisture. Look for signs of disease or nutrient deficiency."),
        ("Week 4", "Monthly assessment. Rotate crop next season for soil health."),
    ],
}


def init_treatment_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS treatment_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            assessment_id INTEGER,
            farmer_name TEXT,
            crop TEXT,
            disease TEXT,
            original_image_path TEXT DEFAULT '',
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Add column if missing (for existing DB)
    try:
        conn.execute("ALTER TABLE treatment_plans ADD COLUMN original_image_path TEXT DEFAULT ''")
    except:
        pass
    conn.execute("""
        CREATE TABLE IF NOT EXISTS progress_updates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id INTEGER,
            stage TEXT,
            day_number INTEGER,
            image_path TEXT,
            farmer_notes TEXT,
            ai_verdict TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS plan_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id INTEGER,
            stage TEXT,
            task TEXT,
            completed INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()
    # Ensure progress directory exists
    os.makedirs("progress", exist_ok=True)


def create_treatment_plan(assessment_id: int, farmer: str, crop: str, disease: str, orig_image_path: str = "") -> int:
    init_treatment_db()  # Ensure tables exist
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT INTO treatment_plans (assessment_id, farmer_name, crop, disease, original_image_path) VALUES (?, ?, ?, ?, ?)",
                 (assessment_id, farmer, crop, disease, orig_image_path))
    plan_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    # Create default tasks
    tasks = TREATMENT_PLANS.get(disease, [("Day 1", "Monitor the crop daily and follow treatment guidelines.")])
    for stage, task in tasks:
        conn.execute("INSERT INTO plan_tasks (plan_id, stage, task) VALUES (?, ?, ?)",
                     (plan_id, stage, task))
    conn.commit()
    conn.close()
    return plan_id


def get_active_plans() -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("""
        SELECT p.id, p.farmer_name, p.crop, p.disease, p.status, p.created_at,
               COUNT(u.id) as updates, SUM(u.ai_verdict = 'improving') as improving
        FROM treatment_plans p
        LEFT JOIN progress_updates u ON u.plan_id = p.id
        GROUP BY p.id ORDER BY p.created_at DESC
    """).fetchall()
    conn.close()
    return [{"id": r[0], "farmer": r[1], "crop": r[2], "disease": r[3], "status": r[4],
             "date": r[5], "updates": r[6], "improving": r[7]} for r in rows]


def get_plan_tasks(plan_id: int) -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT id, stage, task, completed FROM plan_tasks WHERE plan_id = ? ORDER BY id", (plan_id,)).fetchall()
    conn.close()
    return [{"id": r[0], "stage": r[1], "task": r[2], "completed": r[3]} for r in rows]


def get_plan_updates(plan_id: int) -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("""
        SELECT id, stage, day_number, image_path, farmer_notes, ai_verdict, created_at
        FROM progress_updates WHERE plan_id = ? ORDER BY day_number
    """, (plan_id,)).fetchall()
    conn.close()
    return [{"id": r[0], "stage": r[1], "day": r[2], "image": r[3], "notes": r[4], "verdict": r[5], "date": r[6]} for r in rows]


def add_progress_update(plan_id: int, stage: str, day: int, image_path: str, notes: str):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        INSERT INTO progress_updates (plan_id, stage, day_number, image_path, farmer_notes, ai_verdict)
        VALUES (?, ?, ?, ?, ?, 'pending')
    """, (plan_id, stage, day, image_path, notes))
    conn.commit()
    conn.close()


def check_progress_with_ai(original_image: bytes, new_image: bytes, crop: str, disease: str) -> str:
    if GEMINI_AVAILABLE and gemini_client:
        try:
            from google.genai import types as genai_types
            prompt = f"""Compare these two images of the same {crop} plant.
- Image 1: BEFORE treatment (showing {disease})
- Image 2: NOW (current state)

Is the plant improving, stable, or worsening? Reply with ONE word: improving / stable / worsening.
Then a brief explanation in one sentence."""
            response = gemini_client.models.generate_content(
                model=GEMINI_MODEL,
                contents=[prompt,
                          genai_types.Part.from_bytes(data=original_image, mime_type="image/jpeg"),
                          genai_types.Part.from_bytes(data=new_image, mime_type="image/jpeg")],
                config={"temperature": 0.2, "max_output_tokens": 100},
            )
            text = response.text.lower()
            if "improving" in text: return "improving"
            if "worsening" in text: return "worsening"
            return "stable"
        except Exception:
            pass
    # Demo fallback — simulate improvement
    import random
    return random.choices(["improving", "stable", "worsening"], weights=[60, 30, 10])[0]


def get_assessments() -> pd.DataFrame:
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        df = pd.read_sql_query(
            "SELECT rowid AS row_id, farmer_name, location, crop, disease, severity, created_at "
            "FROM assessments ORDER BY created_at DESC LIMIT 50", conn
        )
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()


# ---------------------------------------------------------------------------
# Gemini integration
# ---------------------------------------------------------------------------
GEMINI_AVAILABLE = False
gemini_client = None
if GEMINI_API_KEY:
    try:
        from google import genai
        gemini_client = genai.Client(api_key=GEMINI_API_KEY)
        GEMINI_AVAILABLE = True
    except Exception:
        GEMINI_AVAILABLE = False


def analyze_crop(image_bytes: bytes, crop: str, language: str) -> dict:
    """Send image + crop info to Gemini and get disease analysis."""
    lang_code = LANGUAGES.get(language, "en")
    lang_instruction = f"Respond in {language}." if language != "English" else ""

    is_auto_detect = "Other" in crop

    if is_auto_detect:
        prompt = f"""You are an expert agricultural extension officer for East Africa. First, identify what crop or plant is shown in this image. Then analyze it for diseases, pests, or nutrient deficiencies.

{lang_instruction}

Provide your analysis in this EXACT format:

## Crop
(Name of the crop/plant you identified in the image.)

## 1. Disease / Issue
(Name of the disease, pest, or nutrient deficiency affecting this crop.)

## 2. Severity
(Mild / Moderate / Severe — and a brief explanation why.)

## 3. Recommended Treatment
(Specific, actionable steps the farmer can take using locally available materials. Include organic options if possible.)

## 4. Prevention
(How to prevent this in future growing seasons.)

## 5. Expected Yield Impact
(How much this will affect the harvest if untreated vs treated.)

If the crop appears healthy, say "No disease detected — crop appears healthy." and skip sections 3-5."""
    else:
        prompt = f"""You are an expert agricultural extension officer for East Africa. Analyze this {crop} plant/crop image.

{lang_instruction}

Provide your analysis in this EXACT format:

## 1. Disease / Issue
(Name of the disease, pest, or nutrient deficiency affecting this crop.)

## 2. Severity
(Mild / Moderate / Severe — and a brief explanation why.)

## 3. Recommended Treatment
(Specific, actionable steps the farmer can take using locally available materials. Include organic options if possible.)

## 4. Prevention
(How to prevent this in future growing seasons.)

## 5. Expected Yield Impact
(How much this will affect the harvest if untreated vs treated.)

If the crop appears healthy, say "No disease detected — crop appears healthy." and skip sections 3-5."""

    try:
        from google.genai import types as genai_types
        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[
                prompt,
                genai_types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
            ],
            config={"temperature": 0.3, "max_output_tokens": 2048},
        )
        text = response.text

        # Determine severity from response
        severity = "Moderate"
        text_lower = text.lower()
        if "**severe**" in text_lower or "severity: severe" in text_lower or text_lower.count("severe") > text_lower.count("severity"):
            severity = "Severe"
        elif "**mild**" in text_lower or "severity: mild" in text_lower:
            severity = "Mild"
        elif "no disease" in text_lower or "crop appears healthy" in text_lower:
            severity = "None"

        # Extract disease name
        disease = "Unknown"
        for line in text.split("\n"):
            if line.strip().startswith("## 1.") or line.strip().startswith("**Disease") or line.strip().startswith("**Issue"):
                disease = line.split(":", 1)[-1].strip() if ":" in line else line.replace("## 1.", "").replace("**", "").strip()
                break
        if disease == "Unknown" and "## 1." in text:
            disease = text.split("## 1.")[-1].split("\n")[0].strip()

        # Extract auto-detected crop name
        detected_crop = crop
        if is_auto_detect:
            for line in text.split("\n"):
                clean = line.strip()
                if clean.startswith("## Crop"):
                    detected_crop = clean.replace("## Crop", "").strip()
                    break
                elif clean.startswith("**Crop") or clean.startswith("* Crop"):
                    detected_crop = clean.replace("**Crop", "").replace("**", "").replace("* Crop", "").strip()
                    break
            if detected_crop == crop:  # Fallback: try first line
                first_line = text.split("\n")[0].strip()
                if first_line and len(first_line) < 50:
                    detected_crop = first_line

        return {
            "disease": disease if disease != "Unknown" else "See analysis",
            "severity": severity,
            "treatment": text,
            "detected_crop": detected_crop,
            "error": None,
        }
    except Exception as exc:
        return {"disease": "Analysis failed", "severity": "Unknown", "treatment": "", "detected_crop": crop, "error": str(exc)}


# ---------------------------------------------------------------------------
# Demo / Simulated analysis (fallback when Gemini unavailable)
# ---------------------------------------------------------------------------
DEMO_DISEASES = {
    "Maize": {
        "disease": "Northern Corn Leaf Blight",
        "severity": "Moderate",
        "treatment": """## 1. Disease / Issue
Northern Corn Leaf Blight (Exserohilum turcicum) — fungal disease affecting maize leaves.

## 2. Severity
Moderate — approximately 30% of leaf area affected. Early detection allows effective treatment.

## 3. Recommended Treatment
- Remove and destroy infected leaves immediately
- Apply copper-based fungicide (available at most agrovet shops)
- For organic treatment: mix 1kg neem leaves in 5L water, boil 30min, cool, strain, and spray weekly
- Ensure proper plant spacing (75cm between rows) for air circulation

## 4. Prevention
- Plant resistant varieties (check with local agrovet for hybrids)  
- Practice crop rotation — don't plant maize in same field for 2+ seasons
- Remove crop residue after harvest to reduce fungal spores

## 5. Expected Yield Impact
Untreated: 40-60% yield loss
Treated: 10-15% yield loss""",
    },
    "Cassava": {
        "disease": "Cassava Mosaic Virus",
        "severity": "Severe",
        "treatment": """## 1. Disease / Issue
Cassava Mosaic Virus (CMV) — viral disease transmitted by whiteflies.

## 2. Severity
Severe — significant leaf curling and stunting observed. Immediate action needed to prevent spread.

## 3. Recommended Treatment
- NO CURE for viral diseases — remove and burn infected plants immediately
- Use disease-free cuttings for next planting (soak cuttings in hot water at 50°C for 20min before planting)
- Control whiteflies with neem oil spray (10ml neem oil + 5ml soap per 1L water)

## 4. Prevention
- Plant certified virus-free varieties (NASE 14, NASE 19 recommended for Rwanda)
- Intercrop with maize or beans to reduce whitefly populations
- Remove wild cassava relatives near fields

## 5. Expected Yield Impact
Untreated: 70-100% crop loss
Treated (removal): Save remaining plants, 20-30% total loss""",
    },
    "Tomato": {
        "disease": "Late Blight",
        "severity": "Severe",
        "treatment": """## 1. Disease / Issue
Late Blight (Phytophthora infestans) — aggressive fungal-like pathogen affecting tomatoes.

## 2. Severity
Severe — dark lesions on leaves and stems with white fungal growth. Fruits developing brown rot.

## 3. Recommended Treatment
- Remove all affected plant parts and destroy them (do not compost)
- Apply copper oxychloride fungicide immediately
- For organic: spray with baking soda solution (1 tsp baking soda + 1 tsp vegetable oil + few drops soap per 1L water)
- Apply every 5-7 days during wet season

## 4. Prevention
- Plant resistant varieties (e.g. 'Mtita' hybrid)
- Use stake/trellis to improve air circulation
- Water at soil level, not on leaves
- Apply preventive copper spray after heavy rain

## 5. Expected Yield Impact
Untreated: 80-100% crop loss within 2 weeks
Treated: 20-30% loss""",
    },
}

DEFAULT_ADVICE = """## 1. Disease / Issue
No specific disease detected or crop not identified. General assessment follows.

## 2. Severity
Unknown — unable to determine from the provided information.

## 3. Recommended Treatment
- Monitor the crop daily for any changes
- Ensure adequate water (not too much or too little)
- Check for pests under leaves and at stem base
- Consult local agrovet extension officer if symptoms persist

## 4. Prevention
- Maintain regular weeding schedule
- Use organic compost for soil health
- Rotate crops each season
- Save seeds from healthiest plants

## 5. Expected Yield Impact
Depends on the specific issue — consult local extension officer for accurate assessment."""


def get_analysis(image_bytes: bytes, crop: str, language: str) -> dict:
    if GEMINI_AVAILABLE and gemini_client:
        result = analyze_crop(image_bytes, crop, language)
        if not result["error"]:
            return result

    # Fallback to demo data
    demo = DEMO_DISEASES.get(crop, None)
    if demo:
        return demo

    # Generic fallback
    return {
        "disease": "General assessment needed",
        "severity": "Unknown",
        "treatment": DEFAULT_ADVICE,
    }


# ===================================================================
# MAIN APP
# ===================================================================

init_db()
init_treatment_db()

# ── Session state ─────────────────────────────────────────
for key in ("analysis_done", "last_result", "treatment_view", "ui_language"):
    if key not in st.session_state:
        st.session_state[key] = None if key != "analysis_done" else False
if not st.session_state.get("ui_language"):
    st.session_state["ui_language"] = "English"

# ── CSS ────────────────────────────────────────────────────
st.markdown(CSS, unsafe_allow_html=True)

# ── Title ──────────────────────────────────────────────────
c1, c2 = st.columns([0.08, 0.92])
with c1:
    st.markdown("<h1 style='font-size:2rem;margin:0;color:#10b981'>"
                "<i class='bi bi-tree-fill'></i></h1>", unsafe_allow_html=True)
with c2:
    st.markdown(
        f"<h1 style='margin:0;font-size:1.5rem'>MWOROZI</h1>"
        f"<p style='margin:0;color:#64748b;font-size:0.85rem'>"
        f"<i class='bi bi-cloud-sun'></i> {t('app_subtitle')}  •  "
        f"<span style='color:#10b981'><i class='bi bi-globe2'></i> "
        f"{t('app_region')}</span></p>",
        unsafe_allow_html=True,
    )

# ── Navigation ──────────────────────────────────────────
nav_col1, nav_col2, nav_col3 = st.columns([1, 1, 4])
with nav_col1:
    if st.button(f"📊 {t('dashboard')}", key="nav_dash", use_container_width=True,
                 type="secondary" if st.session_state.get("treatment_view") else "primary"):
        st.session_state["treatment_view"] = None
        st.rerun()
with nav_col2:
    if st.button(f"🌱 {t('check_progress_nav')}", key="nav_progress", use_container_width=True,
                 type="primary" if st.session_state.get("treatment_view") else "secondary"):
        pass  # Will scroll to the check progress section

st.markdown("---")

# ══════════════════════════════════════════════════════════
# SIDEBAR — Farmer info + crop selection
# ══════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### 🌐 Language / Ururimi / Lugha / Langue", unsafe_allow_html=True)
    current_lang = st.session_state.get("ui_language", "English")
    idx = list(LANGUAGES.keys()).index(current_lang) if current_lang in LANGUAGES else 0
    selected = st.selectbox("Site Language", list(LANGUAGES.keys()), index=idx, key="lang_switch")
    if selected != current_lang:
        st.session_state["ui_language"] = selected
        st.rerun()
    st.markdown("---")
    st.markdown(f"### <i class='bi bi-person-badge'></i> {t('farmer_info')}", unsafe_allow_html=True)

    with st.form("farmer_form", clear_on_submit=False):
        farmer_name = st.text_input(t("farmer_name"), placeholder="e.g. Jean", key="farmer_name")
        location = st.text_input(t("sector"), placeholder="e.g. Rulindo", key="location")
        crop = st.selectbox(t("crop_type"), CROPS, key="crop")
        language = st.selectbox(t("response_lang"), list(LANGUAGES.keys()), key="language")
        resource_pref = st.selectbox(t("resources"), t("resources_options"), key="resource_pref")
        season = st.selectbox(t("season"), t("season_options"), key="season")
        st.form_submit_button(t("save_info"), use_container_width=True, type="secondary")

    st.markdown("---")
    
    # Weather widget
    loc = st.session_state.get("location", "").strip()
    if loc:
        w = get_weather(loc)
        w_icon = WEATHER_ICONS.get(w.get("code", 0), "🌤️")
        st.markdown(f"### <i class='bi bi-cloud-sun'></i> Weather — {loc}", unsafe_allow_html=True)
        st.markdown(f"""
        <div class='card' style='padding:0.75rem'>
            <div style='display:flex;justify-content:space-between;align-items:center'>
                <span style='font-size:1.5rem'>{w_icon} {w['temp']}°C</span>
                <span style='color:#94a3b8;font-size:0.8rem'>Humidity: {w['humidity']}%</span>
            </div>
            <div style='display:flex;justify-content:space-between;margin-top:0.4rem'>
                <span style='color:#94a3b8;font-size:0.75rem'>Rain prob: {w['rain_prob']}%</span>
                <span style='color:#64748b;font-size:0.75rem'>Tomorrow: {w['tomorrow_temp']}°C</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    st.markdown("---")
    
    st.markdown(f"### <i class='bi bi-image'></i> {t('crop_image')}", unsafe_allow_html=True)

    img_source = st.radio(
        t("img_source"),
        t("img_options"),
        key="img_source",
        label_visibility="collapsed",
    )

    image_bytes = None
    preview = None
    crop_for_demo = crop

    if img_source == t("img_options")[1]:
        cam_img = st.camera_input(t("camera_capture"), key="camera_input")
        if cam_img:
            image_bytes = cam_img.read()
            st.success(t("camera_success"))
    elif img_source == t("img_options")[2]:
        demo_crop = st.selectbox(t("sample_crop_issue"), list(DEMO_DISEASES.keys()), key="demo_crop")
        crop_for_demo = demo_crop

        from PIL import Image, ImageDraw, ImageFont
        import io as pil_io

        img = Image.new("RGB", (600, 400), (34, 139, 34))
        draw = ImageDraw.Draw(img)
        draw.ellipse([100, 100, 500, 300], fill=(50, 180, 50))
        for _ in range(15):
            x = np.random.randint(150, 450)
            y = np.random.randint(130, 270)
            draw.ellipse([x-8, y-8, x+8, y+8], fill=(139, 90, 43))
            draw.ellipse([x-4, y-4, x+4, y+4], fill=(101, 67, 33))

        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
        except:
            font = ImageFont.load_default()
        draw.text((180, 50), f"{demo_crop}", fill=(255, 255, 255), font=font)
        draw.text((130, 350), f"Sample {demo_crop} leaf", fill=(200, 230, 200), font=font if 'font' in dir() else ImageFont.load_default())

        buf = pil_io.BytesIO()
        img.save(buf, format="JPEG")
        image_bytes = buf.getvalue()
        preview = img

        st.info(f"Using sample: {demo_crop} leaf with disease spots")

    elif "Upload" in img_source:
        uploaded = st.file_uploader(
            "Upload crop photo", type=["jpg", "jpeg", "png", "webp"],
            key="uploaded_img",
        )
        if uploaded:
            image_bytes = uploaded.read()

    st.markdown("---")

    analyze_btn = st.button(t("analyze_btn"), type="primary", use_container_width=True)

    if GEMINI_AVAILABLE:
        st.markdown(f"<span style='color:#10b981'><i class='bi bi-cpu'></i> {t('gemini_on')}</span>", unsafe_allow_html=True)
    else:
        st.markdown(f"<span style='color:#f59e0b'><i class='bi bi-cpu'></i> {t('gemini_off')}</span>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# MAIN AREA
# ══════════════════════════════════════════════════════════

if analyze_btn:
    farmer = st.session_state.get("farmer_name", "").strip()
    loc = st.session_state.get("location", "").strip()
    crop_sel = st.session_state.get("crop", "Maize")
    lang = st.session_state.get("language", "English")

    if not farmer:
        st.error(t("please_name"))
    elif image_bytes is None:
        st.error(t("please_img"))
    else:
        with st.spinner(t("analyzing")):
            result = get_analysis(image_bytes, crop_for_demo if 'crop_for_demo' in dir() else crop_sel, lang)

        if result.get("error"):
            st.warning(f"Gemini analysis had an issue: {result['error']}. Showing best available data.")

        # Check if it's a demo image or real
        is_real = img_source != t("img_options")[2]  # Not demo = real photo

        sev = result.get("severity", "Unknown")
        disease = result.get("disease", "See analysis")
        treatment = result.get("treatment", "")
        actual_crop = result.get("detected_crop", crop_sel)

        # Save to DB
        try:
            save_assessment({
                "farmer_name": farmer,
                "location": loc,
                "crop": actual_crop,
                "disease": disease[:100],
                "severity": sev,
                "treatment": treatment[:500],
                "language": lang,
            })
        except Exception:
            pass

        # Save original image for later AI progress comparison
        os.makedirs("progress", exist_ok=True)
        orig_path = f"progress/original_{farmer}_{actual_crop}_{int(time.time())}.jpg"
        with open(orig_path, "wb") as f:
            f.write(image_bytes)

        # Store in session for display
        st.session_state["last_result"] = {
            "disease": disease,
            "severity": sev,
            "treatment": treatment,
            "crop": actual_crop,
            "farmer": farmer,
            "location": loc,
            "language": lang,
            "is_real": is_real,
            "original_image": image_bytes,
            "original_image_path": orig_path,
        }
        st.session_state["analysis_done"] = True
        st.rerun()

# ── Display results ───────────────────────────────────────
if st.session_state.get("analysis_done"):
    res = st.session_state["last_result"]

    # ── Alert banner ─────────────────────────────────
    if res["severity"] == "Severe":
        st.markdown(f"""
        <div class="alert-disease">
            <h2><i class='bi bi-exclamation-triangle-fill'></i> {t('severe_title')}</h2>
            <p>Crop: <strong>{res['crop']}</strong>  •  
            Issue: <strong>{res['disease'][:80]}</strong>  •  
            Severity: <strong>{t('severe_msg')}</strong></p>
        </div>
        """, unsafe_allow_html=True)
    elif res["severity"] == "Moderate":
        st.markdown(f"""
        <div class="alert-disease" style="background:linear-gradient(135deg,#422006 0%,#713f12 100%);border-color:#f59e0b">
            <h2 style="color:#fde68a"><i class='bi bi-exclamation-circle-fill'></i> {t('moderate_title')}</h2>
            <p style="color:#fef3c7">Crop: <strong>{res['crop']}</strong>  •  
            Issue: <strong>{res['disease'][:80]}</strong>  •  
            Severity: <strong>{t('moderate_msg')}</strong></p>
        </div>
        """, unsafe_allow_html=True)
    elif res["severity"] == "Mild":
        st.markdown(f"""
        <div class="alert-healthy" style="background:linear-gradient(135deg,#0c4a6e 0%,#075985 100%);border-color:#3b82f6">
            <h2 style="color:#93c5fd"><i class='bi bi-info-circle-fill'></i> {t('mild_title')}</h2>
            <p style="color:#dbeafe">Crop: <strong>{res['crop']}</strong>  •  
            Issue: <strong>{res['disease'][:80]}</strong>  •  
            Severity: <strong>{t('mild_msg')}</strong></p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="alert-healthy">
            <h2><i class='bi bi-check-circle-fill'></i> {t('healthy_title')}</h2>
            <p>Crop: <strong>{res['crop']}</strong>  •  
            {t('healthy_msg')}</p>
        </div>
        """, unsafe_allow_html=True)

    # ── Image preview + analysis ──────────────────────
    col_img, col_result = st.columns([0.35, 0.65])

    with col_img:
        if image_bytes:
            st.image(image_bytes, caption=f"{res['crop']} — {'Uploaded photo' if res.get('is_real') else 'Demo sample'}", use_container_width=True)
        st.markdown(f"""
        <div class='card'>
            <div class='card-title'><i class='bi bi-person'></i> Farmer Details</div>
            <p style='margin:0;color:#e2e8f0'><strong>{res['farmer']}</strong></p>
            <p style='margin:0;color:#94a3b8;font-size:0.85rem'>{res['location']}</p>
            <p style='margin:0;color:#94a3b8;font-size:0.85rem'>{res['crop']}  •  {res['language']}</p>
        </div>
        <div class='card'>
            <div class='card-title'><i class='bi bi-cash-stack'></i> Market Price</div>
            <p style='color:#e2e8f0;font-size:1.1rem;margin:0'><strong>{get_market_price(res['crop'])}</strong></p>
            <p style='color:#64748b;font-size:0.7rem;margin:0'>Estimated {res['crop']} price — Kigali market</p>
        </div>
        """, unsafe_allow_html=True)

    with col_result:
        st.markdown("<div class='card'>"
                    "<div class='card-title'><i class='bi bi-clipboard2-pulse'></i> Crop Health Analysis</div>",
                    unsafe_allow_html=True)

        if res["treatment"]:
            st.markdown(res["treatment"])

            # Voice — gTTS with speed control
            voice_text = res["treatment"].replace("##", "").replace("*", "")[:800]
            # Voice — Kinyarwanda falls back to Swahili (gTTS doesn't support 'rw')
            voice_lang_code = {"English": "en", "Kinyarwanda": "sw", "Swahili": "sw", "French": "fr"}.get(res.get("language", "English"), "en")
            voice_key = f"voice_{res['crop']}_{res['severity']}_{voice_lang_code}"
            voice_path = f"progress/{voice_key}.mp3"

            if os.path.exists(voice_path):
                import base64
                with open(voice_path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode()
                speed_html = f"""
                <div style="margin-top:0.75rem">
                    <audio id="humuraAudio" controls style="width:100%;height:40px">
                        <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
                    </audio>
                    <div style="display:flex;gap:0.5rem;margin-top:0.4rem;align-items:center">
                        <span style="color:#64748b;font-size:0.8rem">Speed:</span>
                        <button onclick="document.getElementById('humuraAudio').playbackRate=0.75" style="padding:0.15rem 0.6rem;border-radius:4px;border:1px solid #334155;background:transparent;color:#94a3b8;cursor:pointer;font-size:0.8rem">0.75x</button>
                        <button onclick="document.getElementById('humuraAudio').playbackRate=1.0;this.style.borderColor='#10b981';this.style.color='#10b981'" style="padding:0.15rem 0.6rem;border-radius:4px;border:1px solid #10b981;background:transparent;color:#10b981;cursor:pointer;font-size:0.8rem">1x</button>
                        <button onclick="document.getElementById('humuraAudio').playbackRate=1.25" style="padding:0.15rem 0.6rem;border-radius:4px;border:1px solid #334155;background:transparent;color:#94a3b8;cursor:pointer;font-size:0.8rem">1.25x</button>
                        <button onclick="document.getElementById('humuraAudio').playbackRate=1.5" style="padding:0.15rem 0.6rem;border-radius:4px;border:1px solid #334155;background:transparent;color:#94a3b8;cursor:pointer;font-size:0.8rem">1.5x</button>
                    </div>
                </div>
                """
                st.components.v1.html(speed_html, height=100)
            else:
                if st.button("Generate Audio", key="voice_btn", use_container_width=True):
                    with st.spinner("Generating audio…"):
                        try:
                            from gtts import gTTS
                            tts = gTTS(text=voice_text, lang=voice_lang_code, slow=False)
                            tts.save(voice_path)
                            st.rerun()
                        except ImportError:
                            st.warning("Voice unavailable — installing gTTS dependency on next deploy.")
                        except Exception as e:
                            st.warning(f"Could not generate audio: {e}")
        else:
            st.markdown("*No analysis available. Please try again with a clearer image.*")

        st.markdown("</div>", unsafe_allow_html=True)

    # ── Evaluation Metrics ─────────────────────────────
    confidence = 85 if GEMINI_AVAILABLE else 72
    st.markdown(f"""
    <div style='display:flex;gap:1rem;margin-bottom:0.5rem'>
        <div class='card' style='flex:1;text-align:center;padding:0.75rem'>
            <p style='color:#10b981;font-size:1.1rem;margin:0'>{confidence}%</p>
            <p style='color:#64748b;font-size:0.7rem;margin:0'>AI Confidence</p>
        </div>
        <div class='card' style='flex:1;text-align:center;padding:0.75rem'>
            <p style='color:#f59e0b;font-size:1.1rem;margin:0'>{res['severity']}</p>
            <p style='color:#64748b;font-size:0.7rem;margin:0'>Severity</p>
        </div>
        <div class='card' style='flex:1;text-align:center;padding:0.75rem'>
            <p style='color:#3b82f6;font-size:1.1rem;margin:0'>{st.session_state.get("season", "Growing")}</p>
            <p style='color:#64748b;font-size:0.7rem;margin:0'>Season</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Share & Export ──────────────────────────────────
    # Build clean treatment text (strip markdown headers)
    raw_treatment = res.get('treatment', '')
    clean_lines = []
    for line in raw_treatment.split('\n'):
        line = line.strip()
        if line.startswith('## ') or line.startswith('**'):
            line = line.replace('##','').replace('**','').strip()
            clean_lines.append(f'• {line}')
        elif line.startswith('-'):
            clean_lines.append(f'  {line}')
        elif line and not line.startswith('(') and not line.startswith('If'):
            clean_lines.append(line)
    clean_treatment = '\n'.join(clean_lines)[:600]

    # Build full treatment steps
    steps_text = ""
    disease_for_plan = res['disease']
    for plan_key in TREATMENT_PLANS:
        if plan_key.lower() in res['disease'].lower() or (res['disease'].lower() in plan_key.lower()):
            disease_for_plan = plan_key
            break
    if disease_for_plan in TREATMENT_PLANS:
        steps_text = "\n\n📋 Recovery Steps:\n"
        for stage, task in TREATMENT_PLANS[disease_for_plan]:
            steps_text += f"\n  ✅ {stage}: {task}"

    share_text = f"🌱 Mworozi AI Diagnosis\n\n🌾 Crop: {res['crop']}\n🦠 Disease: {res['disease']}\n⚠️ Severity: {res['severity']}\n\n💊 Treatment:\n{clean_treatment}{steps_text}"

    # ── Share Language Selector ──────────────────────────
    share_lang = st.selectbox("Send report in:", list(LANGUAGES.keys()), index=list(LANGUAGES.keys()).index(res.get('language', 'English')) if res.get('language', 'English') in LANGUAGES else 0, key="share_lang")
    
    final_text = share_text
    if share_lang != "English" and GEMINI_AVAILABLE and gemini_client:
        try:
            with st.spinner(f"Translating to {share_lang}..."):
                resp = gemini_client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=f"Translate the following crop diagnosis into {share_lang}. Keep the emojis and structure exactly the same. Only translate the text:\n\n{share_text}",
                    config={"temperature": 0.2, "max_output_tokens": 1000}
                )
                final_text = resp.text
        except Exception:
            pass  # Fall back to English

    # URL-encode for the WhatsApp/SMS links
    import urllib.parse
    wa_url = f"https://wa.me/?text={urllib.parse.quote(final_text[:1200])}"
    sms_url = f"sms:?body={urllib.parse.quote(final_text[:400])}"
    col_share, col_sms, col_csv = st.columns([1, 1, 1])
    with col_share:
        st.markdown(f'<a href="{wa_url}" target="_blank"><button style="width:100%;padding:0.5rem;border-radius:8px;border:1px solid #25D366;background:transparent;color:#25D366;cursor:pointer;font-size:0.85rem">💬 WhatsApp</button></a>', unsafe_allow_html=True)
    with col_sms:
        st.markdown(f'<a href="{sms_url}"><button style="width:100%;padding:0.5rem;border-radius:8px;border:1px solid #3b82f6;background:transparent;color:#3b82f6;cursor:pointer;font-size:0.85rem">📱 SMS</button></a>', unsafe_allow_html=True)
    with col_csv:
        import io as csv_io
        buf = csv_io.StringIO()
        buf.write("Field,Value\n")
        for k,v in [("Crop",res['crop']),("Disease",res['disease']),("Severity",res['severity']),("Farmer",res['farmer']),("Location",res['location'])]:
            buf.write(f"{k},{v}\n")
        st.download_button("📥 Report", buf.getvalue().encode(), f"mworozi_{res['farmer']}_{res['crop']}.csv", "text/csv", key="report_csv", use_container_width=True)

    # ── Start Checklist Button ─────────────────────────
    if res["severity"] != "None":
        if st.button(f"🌱 {t('start_recovery')}", key="start_checklist", type="primary", use_container_width=True):
            conn = sqlite3.connect(DB_PATH)
            row = conn.execute("SELECT id FROM assessments ORDER BY id DESC LIMIT 1").fetchone()
            aid = row[0] if row else 0
            conn.close()
            orig_path = res.get("original_image_path", "")
            plan_id = create_treatment_plan(aid, res["farmer"], res["crop"], res["disease"], orig_path)
            st.session_state["treatment_view"] = plan_id
            st.rerun()
    else:
        if st.button(f"🌿 {t('keep_healthy_btn')}", key="keep_healthy", type="secondary", use_container_width=True):
            conn = sqlite3.connect(DB_PATH)
            row = conn.execute("SELECT id FROM assessments ORDER BY id DESC LIMIT 1").fetchone()
            aid = row[0] if row else 0
            conn.close()
            orig_path = res.get("original_image_path", "")
            plan_id = create_treatment_plan(aid, res["farmer"], res["crop"], "Keep Healthy", orig_path)
            st.session_state["treatment_view"] = plan_id
            st.rerun()

else:
    # ── Empty state ───────────────────────────────────
    st.markdown(f"""
    <div style='text-align:center;padding:4rem 2rem'>
        <p style='font-size:3.5rem;margin:0;color:#10b981'><i class='bi bi-tree-fill'></i></p>
        <h3 style='color:#64748b;margin:0.5rem 0'>{t('welcome_title')}</h3>
        <p style='color:#475569;max-width:480px;margin:0 auto'>{t('welcome_desc')}</p>
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════
# TREATMENT VIEW — dedicated page for one plant
# ══════════════════════════════════════════════════════════
if st.session_state.get("treatment_view"):
    plan_id = st.session_state["treatment_view"]
    
    if st.button(f"← {t('back_to_dash')}", key="back_dash"):
        st.session_state["treatment_view"] = None
        st.rerun()
    
    tasks = get_plan_tasks(plan_id)
    updates = get_plan_updates(plan_id)
    
    conn = sqlite3.connect(DB_PATH)
    plan_info = conn.execute("SELECT farmer_name, crop, disease, original_image_path FROM treatment_plans WHERE id = ?", (plan_id,)).fetchone()
    conn.close()
    
    if not plan_info:
        st.error("Treatment plan not found. It may have been deleted.")
        if st.button("← Back to Dashboard", key="back_err"):
            st.session_state["treatment_view"] = None
            st.rerun()
    else:
        is_healthy = plan_info[2] == "Keep Healthy"
        checklist_type = t("keep_healthy_title") if is_healthy else t("recovery_checklist")
        icon = "🌿" if is_healthy else "🌱"
        
        st.markdown(f"""
        <div style='display:flex;justify-content:space-between;align-items:center'>
            <h3 style='color:#10b981;margin:0'>{icon} {plan_info[1]} — {checklist_type}</h3>
            <span style='color:#94a3b8;font-size:0.85rem'>Farmer: {plan_info[0]} | {plan_info[2][:40]}</span>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<div style='background:#0f1520;border-radius:12px;padding:1rem;margin-bottom:1rem'>", unsafe_allow_html=True)
        
        if updates:
            for upd in updates:
                st.markdown(f"""
                <div style='margin-bottom:1rem'>
                    <div style='background:#1e293b;border-radius:12px 12px 12px 4px;padding:0.75rem;display:inline-block;max-width:85%'>
                        <p style='margin:0;color:#e2e8f0;font-size:0.85rem'><strong>📷 {upd['stage']} Check-In</strong></p>
                        <p style='margin:0;color:#94a3b8;font-size:0.8rem'>{upd.get('notes','No notes')}</p>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                if upd.get('image') and os.path.exists(upd['image']):
                    st.image(upd['image'], width=250)
                
                v = upd.get('verdict', 'pending')
                if v == 'improving':
                    st.markdown(f"<div style='background:#052e16;border-radius:12px 12px 4px 12px;padding:0.75rem;display:inline-block;max-width:85%;float:right;clear:both'><p style='margin:0;color:#86efac'><strong>🤖 AI:</strong> ✅ Improving! Treatment is working.</p></div>", unsafe_allow_html=True)
                elif v == 'stable':
                    st.markdown(f"<div style='background:#422006;border-radius:12px 12px 4px 12px;padding:0.75rem;display:inline-block;max-width:85%;float:right;clear:both'><p style='margin:0;color:#fde68a'><strong>🤖 AI:</strong> ⏸ Stable — no significant change. Continue treatment.</p></div>", unsafe_allow_html=True)
                elif v == 'worsening':
                    st.markdown(f"<div style='background:#450a0a;border-radius:12px 12px 4px 12px;padding:0.75rem;display:inline-block;max-width:85%;float:right;clear:both'><p style='margin:0;color:#fca5a5'><strong>🤖 AI:</strong> 🔴 Worsening! Consider stronger treatment or consult an expert.</p></div>", unsafe_allow_html=True)
        
        st.markdown("<div style='clear:both'></div>", unsafe_allow_html=True)
        
        # Current task — show as chat input
        next_task = next((t for t in tasks if not t['completed']), None)
        if next_task:
            st.markdown(f"""
            <div style='margin-top:1rem;background:#1e293b;border-radius:12px;padding:1rem'>
                <p style='color:#10b981;margin:0;font-size:0.9rem'><strong>📋 Current Task: {next_task['stage']}</strong></p>
                <p style='color:#94a3b8;margin:0.25rem 0;font-size:0.85rem'>{next_task['task']}</p>
            </div>
            """, unsafe_allow_html=True)
            
            up_img = st.file_uploader(f"📷 Upload photo for {next_task['stage']}", type=["jpg", "jpeg", "png"], key=f"chat_img")
            notes = st.text_area("✏️ Your notes (what do you see?):", placeholder="e.g. The leaves look greener today, no new spots...", key=f"chat_notes", height=80)
            
            if st.button("📤 Submit & Get AI Analysis", key="chat_submit", type="primary", use_container_width=True):
                if up_img:
                    with st.spinner("🤖 AI is analyzing your photo and comparing with the previous state..."):
                        img_bytes = up_img.read()
                        img_path = f"progress/plan_{plan_id}_{next_task['stage'].replace(' ','_')}.jpg"
                        with open(img_path, "wb") as f:
                            f.write(img_bytes)
                        
                        conn2 = sqlite3.connect(DB_PATH)
                        asm = conn2.execute("""SELECT a.id FROM assessments a 
                            JOIN treatment_plans p ON p.assessment_id = a.id 
                            WHERE p.id = ? ORDER BY a.id DESC LIMIT 1""", (plan_id,)).fetchone()
                        conn2.close()
                        
                        orig_img_bytes = b"demo"
                        orig_path = plan_info[3] if len(plan_info) > 3 else ""
                        if orig_path and os.path.exists(orig_path):
                            with open(orig_path, "rb") as of:
                                orig_img_bytes = of.read()
                        verdict = check_progress_with_ai(orig_img_bytes, img_bytes, plan_info[1], plan_info[2])
                        
                        add_progress_update(plan_id, next_task['stage'], len(updates)+1, img_path, notes or "")
                        conn3 = sqlite3.connect(DB_PATH)
                        conn3.execute("UPDATE plan_tasks SET completed = 1 WHERE id = ?", (next_task['id'],))
                        conn3.execute("UPDATE progress_updates SET ai_verdict = ? WHERE plan_id = ? AND stage = ?",
                                     (verdict, plan_id, next_task['stage']))
                        conn3.commit()
                        conn3.close()
                        st.rerun()
                else:
                    st.error("Please upload a photo so AI can check progress.")
        else:
            st.markdown(f"""
            <div style='text-align:center;padding:1rem;background:#052e16;border-radius:12px'>
                <p style='font-size:2rem;margin:0'>🎉</p>
                <p style='color:#86efac;margin:0.5rem 0;font-size:1.1rem'><strong>{t('all_done')}!</strong></p>
                <p style='color:#bbf7d0;margin:0;font-size:0.9rem'>{t('all_done_recovery') if not is_healthy else t('all_done_healthy')}</p>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Progress bar
        done_count = sum(1 for t in tasks if t['completed'])
        pct = int((done_count / len(tasks)) * 100) if tasks else 0
        st.markdown(f"""
        <div style='margin-bottom:0.5rem'>
            <div style='display:flex;justify-content:space-between'>
                <span style='color:#94a3b8;font-size:0.8rem'>Overall Progress</span>
                <span style='color:#10b981;font-size:0.8rem'>{done_count}/{len(tasks)} tasks</span>
            </div>
            <div style='background:#1e293b;border-radius:99px;height:8px;margin-top:0.25rem'>
                <div style='background:#10b981;border-radius:99px;height:8px;width:{pct}%'></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# CHECK PROGRESS — list all assessments
# ══════════════════════════════════════════════════════════
st.markdown("---")
st.markdown(f"<h3 style='color:#10b981'><i class='bi bi-search'></i> {t('check_progress')}</h3>", unsafe_allow_html=True)
st.markdown(f"<p style='color:#94a3b8;font-size:0.85rem'>{t('check_progress_desc')}</p>", unsafe_allow_html=True)

all_ledger = get_assessments()
if not all_ledger.empty:
    csv = all_ledger.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download CSV (Excel-ready)", csv, "mworozi_assessments.csv", "text/csv", key="csv_download", use_container_width=True)
    for idx, row in all_ledger.iterrows():
        with st.container():
            c1, c2, c3, c4, c5, c6, c7, c8 = st.columns([1.2, 0.8, 0.9, 0.8, 1, 1, 0.5, 0.5])
            with c1: st.markdown(f"<span style='color:#e2e8f0'>{row['farmer_name']}</span>", unsafe_allow_html=True)
            with c2: st.markdown(f"<span style='color:#10b981'>{row['crop']}</span>", unsafe_allow_html=True)
            with c3: st.markdown(f"<span style='color:#94a3b8'>{row['disease'][:25]}</span>", unsafe_allow_html=True)
            with c4:
                sev = row['severity']
                sev_color = "#ef4444" if sev == "Severe" else ("#f59e0b" if sev == "Moderate" else "#10b981")
                st.markdown(f"<span style='color:{sev_color}'>{sev}</span>", unsafe_allow_html=True)
            with c5: st.markdown(f"<span style='color:#64748b;font-size:0.8rem'>{row['created_at'][:10]}</span>", unsafe_allow_html=True)
            with c6:
                conn_chk = sqlite3.connect(DB_PATH)
                existing = conn_chk.execute("SELECT id FROM treatment_plans WHERE farmer_name = ? AND crop = ? ORDER BY id DESC LIMIT 1", 
                                       (row['farmer_name'], row['crop'])).fetchone()
                conn_chk.close()
                if existing:
                    if st.button(f"{t('continue_btn')} →", key=f"continue_{idx}", use_container_width=True):
                        st.session_state["treatment_view"] = existing[0]
                        st.rerun()
                else:
                    btn_label = f"🌿 {t('keep_healthy_row')}" if sev in ("None", "Unknown") else f"🌱 {t('treat_btn')}"
                    if st.button(btn_label, key=f"treat_{idx}", use_container_width=True):
                        disease_label = "Keep Healthy" if sev in ("None", "Unknown") else row['disease']
                        pid = create_treatment_plan(row['row_id'], row['farmer_name'], row['crop'], disease_label)
                        st.session_state["treatment_view"] = pid
                        st.rerun()
            with c7:
                if st.button("✏️", key=f"edit_{idx}", help="Edit this assessment", use_container_width=True):
                    st.session_state[f"editing_{idx}"] = not st.session_state.get(f"editing_{idx}", False)
            with c8:
                if st.button("🗑️", key=f"delete_{idx}", help="Remove this assessment", use_container_width=True):
                    delete_assessment(int(row['row_id']))
                    st.rerun()
            
            # Edit form (collapsible)
            if st.session_state.get(f"editing_{idx}", False):
                with st.expander(f"Editing: {row['farmer_name']} — {row['crop']}", expanded=True):
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        new_name = st.text_input("Name", value=row['farmer_name'], key=f"ename_{idx}")
                        new_crop = st.text_input("Crop", value=row['crop'], key=f"ecrop_{idx}")
                    with col_b:
                        new_disease = st.text_input("Disease", value=row['disease'], key=f"edis_{idx}")
                        new_sev = st.selectbox("Severity", ["Mild", "Moderate", "Severe", "None"], 
                                              index=["Mild","Moderate","Severe","None"].index(row['severity']) if row['severity'] in ["Mild","Moderate","Severe","None"] else 1,
                                              key=f"esev_{idx}")
                    with col_c:
                        new_loc = st.text_input("Location", value=row['location'], key=f"eloc_{idx}")
                    
                    if st.button("Save Changes", key=f"save_{idx}", type="primary"):
                        update_assessment(int(row['row_id']), 'farmer_name', new_name)
                        update_assessment(int(row['row_id']), 'crop', new_crop)
                        update_assessment(int(row['row_id']), 'disease', new_disease)
                        update_assessment(int(row['row_id']), 'severity', new_sev)
                        update_assessment(int(row['row_id']), 'location', new_loc)
                        st.session_state[f"editing_{idx}"] = False
                        st.rerun()
            
            st.markdown("<hr style='margin:0.25rem 0;border-color:#1e293b'>", unsafe_allow_html=True)
else:
    st.markdown(f"<p style='color:#64748b'>{t('no_assessments')}</p>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════
# CHECKLIST HISTORY — All active plans
# ══════════════════════════════════════════════════════════
st.markdown("---")
st.markdown(f"<h3 style='color:#10b981'><i class='bi bi-list-check'></i> {t('checklist_history')}</h3>", unsafe_allow_html=True)

all_plans = get_active_plans()
if all_plans:
    for plan in all_plans:
        tasks = get_plan_tasks(plan['id'])
        done = sum(1 for t in tasks if t['completed'])
        total = len(tasks)
        pct = int((done / total) * 100) if total > 0 else 0
        is_healthy = "Keep Healthy" in str(plan.get('disease', ''))
        plan_type = t('keep_healthy_label') if is_healthy else t('recovery_label')
        icon = "🌿" if is_healthy else "🌱"
        color = "#10b981" if pct >= 75 else ("#f59e0b" if pct >= 25 else "#ef4444")

        with st.container():
            c1, c2, c3, c4, c5, c6 = st.columns([1.5, 1, 0.8, 1, 1, 1.5])
            with c1: st.markdown(f"<span style='color:#e2e8f0'>{plan['farmer']}</span>", unsafe_allow_html=True)
            with c2: st.markdown(f"<span style='color:#10b981'>{plan['crop']}</span>", unsafe_allow_html=True)
            with c3: st.markdown(f"<span style='color:#94a3b8;font-size:0.8rem'>{icon} {plan_type}</span>", unsafe_allow_html=True)
            with c4: st.markdown(f"<span style='color:{color};font-weight:600'>{pct}%</span>", unsafe_allow_html=True)
            with c5:
                st.markdown(f"""
                <div style='background:#1e293b;border-radius:99px;height:6px;margin-top:8px'>
                    <div style='background:{color};border-radius:99px;height:6px;width:{pct}%'></div>
                </div>
                """, unsafe_allow_html=True)
            with c6:
                if st.button(f"Open Plan", key=f"hist_plan_{plan['id']}", use_container_width=True):
                    st.session_state["treatment_view"] = plan['id']
                    st.rerun()
            st.markdown("<hr style='margin:0.25rem 0;border-color:#1e293b'>", unsafe_allow_html=True)
else:
    st.markdown(f"<p style='color:#64748b'>{t('no_assessments')}</p>", unsafe_allow_html=True)
