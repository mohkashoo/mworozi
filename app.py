import os, sqlite3, time, json, textwrap, datetime as dt
import warnings
warnings.filterwarnings("ignore")

# Load .env file if present (so env vars work without manual export)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np

from audio_processor import NeonatalAudioEngine

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DB_PATH = "humura.db"
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
HIGH_RISK_THRESHOLD = 50  # risk_score >= this triggers Tier‑2 triage

# Healthy neonatal reference ranges
HEALTHY_F0_LOW = 350
HEALTHY_F0_HIGH = 650
HEALTHY_TEMP_LOW = 36.5
HEALTHY_TEMP_HIGH = 37.5
HEALTHY_HR_LOW = 120
HEALTHY_HR_HIGH = 160
HEALTHY_RR_LOW = 30
HEALTHY_RR_HIGH = 60

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Project Humura — Neonatal Cry Triage",
    page_icon="❤️‍🩹",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Cached resources
# ---------------------------------------------------------------------------
@st.cache_resource(show_spinner="Initialising acoustic engine…")
def get_engine():
    return NeonatalAudioEngine()


# ---------------------------------------------------------------------------
# Custom CSS — clinical SOC dark theme
# ---------------------------------------------------------------------------
CSS = """
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
<style>
    .bi { vertical-align: -0.125em; }
    /* Base */
    .stApp { background-color: #090a0f; }
    .main > div { padding: 1rem 1.5rem; }

    /* Cards */
    .card {
        background: #0f1520;
        border: 1px solid #1e293b;
        border-radius: 12px; padding: 1.25rem; margin-bottom: 1rem;
    }
    .card-title {
        font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.08em;
        color: #64748b; margin-bottom: 0.75rem;
    }

    /* Alert banner */
    .alert-critical {
        background: linear-gradient(135deg, #450a0a 0%, #7f1d1d 100%);
        border: 1px solid #ef4444; border-radius: 12px;
        padding: 1.25rem 1.5rem; margin-bottom: 1rem;
    }
    .alert-critical h2 { color: #fca5a5; margin: 0 0 0.25rem; font-size: 1.25rem; }
    .alert-critical p  { color: #fecaca; margin: 0; font-size: 0.9rem; }

    .alert-stable {
        background: linear-gradient(135deg, #052e16 0%, #14532d 100%);
        border: 1px solid #10b981; border-radius: 12px;
        padding: 1.25rem 1.5rem; margin-bottom: 1rem;
    }
    .alert-stable h2 { color: #86efac; margin: 0 0 0.25rem; font-size: 1.25rem; }
    .alert-stable p  { color: #bbf7d0; margin: 0; font-size: 0.9rem; }

    /* Risk score badge */
    .risk-badge {
        display: inline-block; border-radius: 999px;
        padding: 0.2rem 0.8rem; font-size: 0.8rem; font-weight: 600;
    }

    /* Sections */
    .section-label {
        font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.08em;
        color: #64748b; margin: 1.25rem 0 0.5rem; border-bottom: 1px solid #1e293b;
        padding-bottom: 0.3rem;
    }

    /* Sidebar tweaks */
    [data-testid="stSidebar"] { background-color: #0a0d14; border-right: 1px solid #1e293b; }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
        color: #e2e8f0;
    }

    /* Override Streamlit defaults */
    .stTextInput>div>div>input, .stNumberInput>div>div>input, .stTextArea>div>textarea {
        background-color: #131a26 !important; border-color: #1e293b !important;
        color: #e2e8f0 !important;
    }
    .stSelectbox>div>div>select { background-color: #131a26 !important; border-color: #1e293b !important; color: #e2e8f0 !important; }
    .stRadio > div { color: #94a3b8 !important; }

    /* Buttons */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #059669, #10b981) !important;
        border: none !important; color: white !important; font-weight: 600 !important;
    }
    .stButton > button[kind="secondary"] {
        background: transparent !important; border: 1px solid #334155 !important;
        color: #94a3b8 !important;
    }
    .stButton > button:hover {
        transform: translateY(-1px); box-shadow: 0 4px 12px rgba(16,185,129,0.2);
    }

    /* Data frame */
    .stDataFrame { background: transparent !important; }
    .stDataFrame td, .stDataFrame th {
        background-color: #0f1520 !important; color: #cbd5e1 !important;
        border-color: #1e293b !important;
    }

    hr { border-color: #1e293b !important; }

    /* Scrollbar */
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: #090a0f; }
    ::-webkit-scrollbar-thumb { background: #334155; border-radius: 3px; }
</style>
"""

# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS assessments (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id      TEXT UNIQUE,
            patient_name    TEXT NOT NULL,
            age_days        INTEGER,
            temperature     REAL,
            heart_rate      INTEGER,
            respiratory_rate INTEGER,
            weight          REAL,
            maternal_history TEXT DEFAULT '',
            acoustic_classification  INTEGER,
            acoustic_probability     REAL,
            acoustic_risk_score      REAL,
            triage_risk     TEXT,
            triage_summary  TEXT,
            referral_letter TEXT,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def save_assessment(record: dict) -> None:
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        conn.execute("""
            INSERT OR REPLACE INTO assessments
                (patient_id, patient_name, age_days, temperature, heart_rate,
                 respiratory_rate, weight, maternal_history,
                 acoustic_classification, acoustic_probability,
                 acoustic_risk_score, triage_risk, triage_summary, referral_letter)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            record["patient_id"], record["patient_name"],
            record["age_days"], record["temperature"],
            record["heart_rate"], record["respiratory_rate"],
            record["weight"], record["maternal_history"],
            record["acoustic_classification"],
            record["acoustic_probability"],
            record["acoustic_risk_score"],
            record["triage_risk"], record["triage_summary"],
            record["referral_letter"],
        ))
        conn.commit()
        conn.close()
    except Exception as exc:
        st.warning(f"Database write failed (non‑fatal): {exc}")


def get_assessments() -> pd.DataFrame:
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        df = pd.read_sql_query(
            "SELECT patient_id, patient_name, age_days, temperature, "
            "acoustic_risk_score, triage_risk, created_at "
            "FROM assessments ORDER BY created_at DESC LIMIT 50", conn
        )
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()


# ---------------------------------------------------------------------------
# Gemini integration  (Tier 2)
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


def _build_triage_prompt(
    risk_level: str, risk_score: float, anomaly_score: float,
    age_days: int, temperature: float, heart_rate: int,
    respiratory_rate: int, weight: float, maternal_history: str,
) -> str:
    return f"""You are a neonatal triage specialist at a rural health post in Rwanda. An infant has been assessed by the Humura acoustic triage system. Generate a structured clinical brief in the EXACT three‑section format below.

ACOUSTIC ANALYSIS:
- Risk Classification: {risk_level} (Score: {risk_score:.0f}/100)
- Anomaly Index: {anomaly_score:.2f}

VITAL SIGNS:
- Age: {age_days} days
- Temperature: {temperature:.1f} °C
- Heart Rate: {heart_rate} bpm
- Respiratory Rate: {respiratory_rate} breaths/min
- Weight: {weight:.2f} kg

MATERNAL HISTORY:
{maternal_history or "None reported"}

---

## 1. Emergency Assessment Profile
(Suspected conditions, severity level, and key clinical reasoning.)

## 2. Recommended Immediate Stabilization Steps
(Actionable steps the referring nurse or midwife can take with available resources — airway, breathing, circulation, warmth, monitoring.)

## 3. Emergency Referral Letter Draft
(Addressed to the Medical Officer in Charge, nearest referral hospital — include patient summary, reason for referral, and clinical notes.)"""


def _call_gemini(prompt: str) -> str | None:
    try:
        resp = gemini_client.models.generate_content(
            model=GEMINI_MODEL, contents=prompt,
            config={"temperature": 0.3, "max_output_tokens": 4096},
        )
        return resp.text
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Clinical rule engine  (fallback when Gemini is unavailable)
# ---------------------------------------------------------------------------
def _clinical_rule_engine(
    risk_score: float, anomaly_score: float,
    age_days: int, temperature: float, heart_rate: int,
    respiratory_rate: int, weight: float, maternal_history: str,
) -> dict:

    alerts = []

    if risk_score >= 80:
        alerts.append("Critical acoustic distress pattern — high probability of neurological or respiratory compromise.")
    elif risk_score >= 50:
        alerts.append("Elevated acoustic anomaly index — abnormal cry characteristics detected.")

    if temperature > 38.0:
        alerts.append(f"Fever ({temperature:.1f}°C) — suspect infection / sepsis.")
    elif temperature < 36.0:
        alerts.append(f"Hypothermia ({temperature:.1f}°C) — suspect sepsis or metabolic disorder.")

    if respiratory_rate > 65:
        alerts.append(f"Severe tachypnoea (RR {respiratory_rate}) — urgent respiratory assessment needed.")
    elif respiratory_rate > 60:
        alerts.append(f"Tachypnoea (RR {respiratory_rate}) — possible respiratory distress.")

    if heart_rate < 100:
        alerts.append(f"Bradycardia (HR {heart_rate}) — possible neurological distress or hypoxia.")
    elif heart_rate > 180:
        alerts.append(f"Tachycardia (HR {heart_rate}) — possible distress, sepsis, or dehydration.")

    if weight < 2.5:
        alerts.append(f"Low birth weight ({weight:.2f} kg) — increased vulnerability.")

    if age_days <= 7:
        alerts.append("Neonate in first week of life — elevated risk of early‑onset sepsis.")

    n_critical = sum(1 for a in alerts if any(k in a for k in ("Critical", "Severe", "urgent")))

    if n_critical >= 2 or risk_score >= 85:
        risk = "CRITICAL"
        color = "#ef4444"
        recommendation = "IMMEDIATE REFERRAL — Stabilise and transport to nearest referral hospital without delay."
    elif len(alerts) >= 2 or risk_score >= 60:
        risk = "HIGH"
        color = "#f59e0b"
        recommendation = "URGENT — Transfer to district health centre. Initiate monitoring and first‑line interventions per IMCI guidelines."
    elif len(alerts) >= 1 or risk_score >= 40:
        risk = "MODERATE"
        color = "#3b82f6"
        recommendation = "Monitor closely. Re‑assess vital signs every 30 minutes. Refer if condition worsens."
    else:
        risk = "STABLE"
        color = "#10b981"
        recommendation = "Cry pattern within normal range. Continue routine newborn care. Re‑assess if new symptoms develop."

    assessment_lines = "\n".join(f"- {a}" for a in alerts) if alerts else "No acute clinical alerts generated."

    pid = st.session_state.get("patient_id", f"HUM-{dt.date.today().strftime('%Y%m%d')}-001")
    pname = st.session_state.get("patient_name", "Unknown")

    summary = f"""**Clinical Alerts**  
{assessment_lines}

**Recommendation**  
{recommendation}"""

    referral = f"""**EMERGENCY REFERRAL LETTER**

**To:** Medical Officer in Charge — Nearest Referral Hospital
**From:** {pname} — referring clinician, {st.session_state.get("clinic_name", "Rural Health Post")}
**Patient:** {pname} (ID: {pid}), {age_days}‑day‑old neonate

**Reason for referral:**  
{risk}‑risk triage classification following acoustic and clinical assessment.

**Clinical summary:**  
{alerts[0] if alerts else "See above alerts."}

**Vitals:** Temp {temperature:.1f}°C | HR {heart_rate} bpm | RR {respiratory_rate} | Wt {weight:.2f} kg

**Action requested:** Urgent paediatric evaluation and management.

_Generated by Project Humura — Neonatal Cry Diagnostic Triage Platform_"""

    return {
        "risk": risk,
        "color": color,
        "summary": summary,
        "referral_letter": referral,
        "findings": alerts,
    }


# ---------------------------------------------------------------------------
# Spectrogram figure
# ---------------------------------------------------------------------------
def build_spectrogram_figure(spec: dict) -> go.Figure:
    fig = go.Figure()

    fig.add_trace(go.Heatmap(
        z=spec["spectrogram"], x=spec["times"], y=spec["frequencies"],
        colorscale="Viridis", name="dB",
        colorbar=dict(title="dB", len=0.85, x=1.02),
        hovertemplate="Time: %{x:.2f}s<br>Freq: %{y:.0f} Hz<br>Mag: %{z:.1f} dB<extra></extra>",
    ))

    f0 = spec.get("f0_track")
    if f0 is not None:
        f0_clean = np.where(f0 > 0, f0, np.nan)
        ft = spec.get("f0_times", [])
        fig.add_trace(go.Scatter(
            x=ft, y=f0_clean, mode="lines",
            line=dict(color="white", width=2),
            name="F0 Contour",
            hovertemplate="Time: %{x:.2f}s<br>F0: %{y:.0f} Hz<extra>F0</extra>",
        ))

    fig.add_hrect(y0=HEALTHY_F0_LOW, y1=HEALTHY_F0_HIGH,
                  fillcolor="#10b981", opacity=0.06, line_width=0, name="Healthy F0")
    fig.add_hline(y=HEALTHY_F0_LOW, line_color="#10b981",
                  line_dash="dash", line_width=1.5)
    fig.add_hline(y=HEALTHY_F0_HIGH, line_color="#10b981",
                  line_dash="dash", line_width=1.5)

    fig.add_annotation(x=spec["times"][-1] if len(spec["times"]) else 1,
                       y=HEALTHY_F0_LOW + 15,
                       text="Healthy F0 Range", showarrow=False,
                       font=dict(size=10, color="#10b981"),
                       xanchor="right")

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e2e8f0"),
        xaxis_title="Time (s)",
        yaxis_title="Frequency (Hz)",
        yaxis_range=[0, 4000],
        height=380,
        margin=dict(l=40, r=50, t=20, b=40),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


# ---------------------------------------------------------------------------
# Feature summary as mini table rows
# ---------------------------------------------------------------------------
def feature_summary_html(features: dict) -> str:
    if not features:
        return "<p style='color:#64748b'>No features available.</p>"

    rows = []
    pairs = [
        ("f0_mean", "F0 Mean", "Hz", 350, 650),
        ("f0_std", "F0 Std Dev", "Hz", 20, 120),
        ("spectral_centroid_mean", "Spectral Centroid", "Hz", 1500, 3500),
        ("bandwidth_mean", "Bandwidth", "Hz", 1500, 3500),
        ("zcr_mean", "Zero‑Crossing Rate", "", 0.02, 0.10),
        ("rms_mean", "RMS Energy", "", 0.01, 0.15),
    ]
    for key, label, unit, lo, hi in pairs:
        val = features.get(key)
        if val is None:
            continue
        ok = lo <= val <= hi
        badge = "<i class='bi bi-check-circle-fill' style='color:#10b981'></i>" if ok else "<i class='bi bi-x-circle-fill' style='color:#ef4444'></i>"
        unit_str = f" {unit}" if unit else ""
        rows.append(
            f"<tr><td style='color:#94a3b8;padding:2px 8px'>{badge} {label}"
            f"</td><td style='text-align:right;font-weight:600'>{val:.1f}{unit_str}</td>"
            f"<td style='text-align:right;color:#64748b;font-size:0.8em'>(norm {lo}–{hi})</td></tr>"
        )
    return f"<table style='width:100%'>" + "".join(rows) + "</table>"


# ===================================================================
# MAIN APP
# ===================================================================

init_db()
engine = get_engine()

# ── Initialise session state ─────────────────────────────────────
for key in ("analysis_done", "last_result", "last_spec", "last_triage"):
    if key not in st.session_state:
        st.session_state[key] = None if key != "analysis_done" else False

# ── Inject CSS ───────────────────────────────────────────────────
st.markdown(CSS, unsafe_allow_html=True)

# ── Title bar ────────────────────────────────────────────────────
c1, c2 = st.columns([0.08, 0.92])
with c1:
    st.markdown("<h1 style='font-size:2rem;margin:0;color:#10b981'>"
                "<i class='bi bi-heart-pulse-fill'></i></h1>",
                unsafe_allow_html=True)
with c2:
    st.markdown(
        "<h1 style='margin:0;font-size:1.5rem'>PROJECT HUMURA</h1>"
        "<p style='margin:0;color:#64748b;font-size:0.85rem'>"
        "<i class='bi bi-ear'></i> Neonatal Cry Acoustic Diagnostic Triage  •  "
        "<span style='color:#10b981'><i class='bi bi-shield-fill-check'></i> "
        "Low‑Resource Setting</span></p>",
        unsafe_allow_html=True,
    )

st.markdown("---")

# ═══════════════════════════════════════════════════════════════
# SIDEBAR — patient form + audio source
# ═══════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### <i class='bi bi-person-badge'></i> Patient Information", unsafe_allow_html=True)

    with st.form("patient_form", clear_on_submit=False):
        col_a, col_b = st.columns(2)
        with col_a:
            pname = st.text_input("Baby's Name / ID", placeholder="e.g. HUM‑001",
                                  key="patient_name")
            age_days = st.number_input("Age (days)", min_value=0, max_value=365,
                                       value=3, key="patient_age_days")
            temperature = st.number_input("Temperature (°C)", min_value=32.0,
                                          max_value=42.0, value=37.0, step=0.1,
                                          key="patient_temp")
            heart_rate = st.number_input("Heart Rate (bpm)", min_value=60,
                                         max_value=220, value=140,
                                         key="patient_hr")
        with col_b:
            respiratory_rate = st.number_input("Respiratory Rate (/min)",
                                               min_value=20, max_value=100,
                                               value=45, key="patient_rr")
            weight = st.number_input("Weight (kg)", min_value=0.5, max_value=10.0,
                                     value=3.2, step=0.1, key="patient_weight")
            maternal_history = st.text_area(
                "Maternal History",
                placeholder="Infections, medications, delivery complications…",
                key="patient_history",
            )
        st.form_submit_button("Save Patient Data",
                              use_container_width=True, type="secondary")

    st.markdown("---")
    st.markdown("### <i class='bi bi-mic'></i> Audio Source", unsafe_allow_html=True)

    audio_source = st.segmented_control(
        "Select input method",
        options=["🎤 Live Mic", "📁 Upload Audio", "🧪 Simulated Profile"],
        default="🎤 Live Mic",
        key="audio_source",
        label_visibility="collapsed",
    )

    audio_bytes = None
    profile_label = ""

    if "Live Mic" in audio_source:
        audio_value = st.audio_input(
            "Record live infant cry telemetry",
            key="live_mic",
        )
        if audio_value:
            audio_bytes = audio_value.read()
            profile_label = "Live mic capture"
            st.success("Audio captured successfully!")
    elif "Simulated Profile" in audio_source:
        profile = st.selectbox(
            "Simulation Profile",
            [
                "Normal Discomfort Cry",
                "High‑Risk Asphyxia Marker",
                "High‑Risk Respiratory Distress",
            ],
            key="sim_profile",
        )
        cat_map = {
            "Normal Discomfort Cry": "normal",
            "High‑Risk Asphyxia Marker": "distress",
            "High‑Risk Respiratory Distress": "distress",
        }
        audio_bytes = engine.generate_simulated_cry(cat_map[profile])
        profile_label = profile
        st.info(f"Using pre‑loaded simulation: {profile}")
    else:
        uploaded = st.file_uploader(
            "Upload infant cry recording",
            type=["wav", "mp3", "ogg", "flac"],
            key="uploaded_audio",
        )
        if uploaded:
            audio_bytes = uploaded.read()
            profile_label = uploaded.name

    st.markdown("---")

    analyze_btn = st.button(
        "▶ Run Triage Analysis",
        type="primary",
        use_container_width=True,
    )

    if GEMINI_AVAILABLE:
        st.markdown("<span style='color:#10b981'><i class='bi bi-cpu'></i> Gemini AI triage engine enabled</span>", unsafe_allow_html=True)
    else:
        st.markdown("<span style='color:#f59e0b'><i class='bi bi-cpu'></i> Gemini unavailable — using local clinical rules</span>", unsafe_allow_html=True)

    if GEMINI_AVAILABLE:
        st.caption(f"Engine: {GEMINI_MODEL}")

# ═══════════════════════════════════════════════════════════════
# MAIN AREA — analysis and results
# ═══════════════════════════════════════════════════════════════

# ── Run analysis ──────────────────────────────────────────────
if analyze_btn:
    pname = st.session_state.get("patient_name", "").strip()
    if not pname:
        st.error("Please enter the baby's name / ID before running analysis.")
    elif audio_bytes is None:
        st.error("Please provide an audio recording or select a simulated profile.")
    else:
        pid = f"HUM-{dt.date.today().strftime('%Y%m%d')}-{int(time.time()) % 10000:04d}"
        st.session_state["patient_id"] = pid

        with st.spinner("Running acoustic analysis…"):
            result = engine.evaluate_cry(audio_bytes)
            spec = engine.compute_spectrogram(audio_bytes)

        triage = None
        if result["error"]:
            st.error(f"Acoustic analysis error: {result['error']}")
        else:
            # Determine risk level label
            rs = result["risk_score"]

            if rs >= 80:
                risk_label = "CRITICAL"
            elif rs >= 50:
                risk_label = "HIGH"
            elif rs >= 41:
                risk_label = "MODERATE"
            else:
                risk_label = "STABLE"

            # Tier‑2 triage
            if rs >= HIGH_RISK_THRESHOLD:
                prompt = _build_triage_prompt(
                    risk_label, rs, result.get("anomaly_score", 0),
                    st.session_state.patient_age_days,
                    st.session_state.patient_temp,
                    st.session_state.patient_hr,
                    st.session_state.patient_rr,
                    st.session_state.patient_weight,
                    st.session_state.get("patient_history", ""),
                )

                if GEMINI_AVAILABLE:
                    with st.spinner("Generating clinical triage brief (Gemini)…"):
                        gemini_text = _call_gemini(prompt)
                        if gemini_text:
                            triage = {
                                "risk": risk_label,
                                "color": "#ef4444" if rs >= 80 else "#f59e0b",
                                "summary": gemini_text,
                                "referral_letter": gemini_text,
                            }
                        else:
                            triage = _clinical_rule_engine(
                                rs, result.get("anomaly_score", 0),
                                st.session_state.patient_age_days,
                                st.session_state.patient_temp,
                                st.session_state.patient_hr,
                                st.session_state.patient_rr,
                                st.session_state.patient_weight,
                                st.session_state.get("patient_history", ""),
                            )
                            st.markdown("<span style='color:#f59e0b'><i class='bi bi-exclamation-circle'></i> Gemini call failed — fell back to local clinical rules.</span>", unsafe_allow_html=True)
                else:
                    triage = _clinical_rule_engine(
                        rs, result.get("anomaly_score", 0),
                        st.session_state.patient_age_days,
                        st.session_state.patient_temp,
                        st.session_state.patient_hr,
                        st.session_state.patient_rr,
                        st.session_state.patient_weight,
                        st.session_state.get("patient_history", ""),
                    )
            else:
                triage = {
                    "risk": risk_label,
                    "color": "#10b981",
                    "summary": "Acoustic pattern is within normal limits for a healthy neonate. No immediate clinical intervention indicated. Continue routine newborn care and monitor for any change in feeding, tone, or cry quality.",
                    "referral_letter": "Not required. Routine care.",
                }

            # Save to database
            try:
                save_assessment({
                    "patient_id": pid,
                    "patient_name": pname,
                    "age_days": st.session_state.patient_age_days,
                    "temperature": st.session_state.patient_temp,
                    "heart_rate": st.session_state.patient_hr,
                    "respiratory_rate": st.session_state.patient_rr,
                    "weight": st.session_state.patient_weight,
                    "maternal_history": st.session_state.get("patient_history", ""),
                    "acoustic_classification": result["classification"],
                    "acoustic_probability": result["probability"],
                    "acoustic_risk_score": result["risk_score"],
                    "triage_risk": triage["risk"],
                    "triage_summary": triage["summary"],
                    "referral_letter": triage.get("referral_letter", ""),
                })
            except Exception as exc:
                st.warning(f"Could not save record: {exc}")

        # Store in session
        st.session_state["last_result"] = result
        st.session_state["last_spec"] = spec
        st.session_state["last_triage"] = triage
        st.session_state["analysis_done"] = True
        st.rerun()

# ── Display results (from session state) ─────────────────────
if st.session_state.get("analysis_done"):
    result = st.session_state["last_result"]
    spec = st.session_state["last_spec"]
    triage = st.session_state["last_triage"]

    if result and not result["error"]:

        # ── Alert banner ──────────────────────────────────
        rs = result["risk_score"]
        if rs >= 80:
            st.markdown(f"""
            <div class="alert-critical">
                <h2><i class='bi bi-exclamation-triangle-fill'></i> CRITICAL — Immediate Referral Needed</h2>
                <p>Risk Score <strong>{rs:.0f}/100</strong>  •  
                Classification: <strong>{triage["risk"] if triage else "CRITICAL"}</strong>  •  
                Confidence: <strong>{result["probability"]*100:.1f}%</strong></p>
            </div>
            """, unsafe_allow_html=True)
        elif rs >= 50:
            st.markdown(f"""
            <div class="alert-critical">
                <h2><i class='bi bi-exclamation-triangle-fill'></i> HIGH‑RISK TRIAGE ALERT</h2>
                <p>Risk Score <strong>{rs:.0f}/100</strong>  •  
                Classification: <strong>{triage["risk"] if triage else "HIGH"}</strong>  •  
                Confidence: <strong>{result["probability"]*100:.1f}%</strong></p>
            </div>
            """, unsafe_allow_html=True)
        elif rs >= 41:
            st.markdown(f"""
            <div style="background:linear-gradient(135deg,#422006 0%,#713f12 100%);
                        border:1px solid #f59e0b;border-radius:12px;
                        padding:1.25rem 1.5rem;margin-bottom:1rem">
                <h2 style="color:#fde68a;margin:0 0 0.25rem;font-size:1.25rem">
                    <i class='bi bi-exclamation-circle-fill'></i> MODERATE — Monitor Closely</h2>
                <p style="color:#fef3c7;margin:0;font-size:0.9rem">
                Risk Score <strong>{rs:.0f}/100</strong>  •  Elevated acoustic pattern. Re-assess in 30 minutes and monitor for changes in feeding, tone, or breathing.</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="alert-stable">
                <h2><i class='bi bi-check-circle-fill'></i> STABLE — Low‑Risk Cry Pattern</h2>
                <p>Risk Score <strong>{rs:.0f}/100</strong>  •  
                Acoustic pattern within normal limits.</p>
            </div>
            """, unsafe_allow_html=True)

        # ── Spectrogram + Features ───────────────────────
        col_vis, col_feat = st.columns([0.68, 0.32])

        with col_vis:
            if spec and spec.get("spectrogram") is not None:
                fig = build_spectrogram_figure(spec)
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        with col_feat:
            feat = result.get("features", {})
            if feat:
                st.markdown("<div class='card' style='min-height:380px'>"
                            "<div class='card-title'><i class='bi bi-graph-up'></i> Extracted Acoustic Features</div>"
                            + feature_summary_html(feat) +
                            "</div>", unsafe_allow_html=True)

        # ── Triage result ────────────────────────────────
        if triage:
            risk = triage.get("risk", "")
            color = triage.get("color", "#64748b")
            summary = triage.get("summary", "")
            referral = triage.get("referral_letter", "")

            st.markdown("<div class='card'>"
                        "<div class='card-title'><i class='bi bi-clipboard2-pulse'></i> Triage Result Matrix</div>",
                        unsafe_allow_html=True)

            # Risk badge
            st.markdown(
                f"<span class='risk-badge' "
                f"style='background:{color}22;color:{color};border:1px solid {color}'>"
                f"{risk}</span>",
                unsafe_allow_html=True,
            )
            st.markdown(f"<span style='color:#94a3b8;font-size:0.85rem;margin-left:0.5rem'>"
                        f"Risk Score: {result['risk_score']:.0f}/100  |  "
                        f"Probability: {result['probability']*100:.1f}%</span>",
                        unsafe_allow_html=True)

            if rs >= 50:
                st.markdown("""
                <div style='margin-top:1rem'>
                    <div class='section-label'><i class='bi bi-clipboard2-pulse'></i> Clinical Triage Brief</div>
                </div>
                """, unsafe_allow_html=True)
                st.markdown(summary)

                if referral:
                    with st.expander("📄 Emergency Referral Letter Draft"):
                        st.markdown(referral)

                st.markdown("""
                <div style='margin-top:1rem;padding:0.75rem;background:#1e293b33;
                            border-radius:8px;border-left:3px solid #ef4444'>
                    <p style='margin:0;color:#fca5a5;font-size:0.85rem'>
                    <i class='bi bi-info-circle-fill'></i> This triage guidance is generated for clinical decision support.
                    Always consult a qualified health professional for definitive diagnosis
                    and treatment.</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='margin-top:0.75rem'>{summary}</div>",
                            unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True)

    elif result and result["error"]:
        st.error(f"Acoustic analysis failed: {result['error']}")

else:
    # ── Empty state ─────────────────────────────────────
    st.markdown("""
    <div style='text-align:center;padding:4rem 2rem'>
        <p style='font-size:3.5rem;margin:0;color:#10b981'><i class='bi bi-heart-pulse-fill'></i></p>
        <h3 style='color:#64748b;margin:0.5rem 0'>Ready for Triage Assessment</h3>
        <p style='color:#475569;max-width:480px;margin:0 auto'>
        Complete the patient information form and select an audio source in the sidebar,
        then click <strong>Run Triage Analysis</strong> to begin.
        </p>
    </div>
    """, unsafe_allow_html=True)


# ── Patient assessment ledger (always visible) ────────────
st.markdown("<div class='card'><div class='card-title'>"
            "Patient Assessment Ledger</div>", unsafe_allow_html=True)
ledger = get_assessments()
if not ledger.empty:
    ledger_display = ledger.copy()
    ledger_display.columns = [
        "ID", "Name", "Age (d)", "Temp (°C)",
        "Risk Score", "Triage", "Recorded",
    ]
    st.dataframe(ledger_display, use_container_width=True, hide_index=True)
else:
    st.markdown("<span style='color:#64748b'><i class='bi bi-database'></i> No assessments recorded yet. Run a triage to populate the ledger.</span>", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)
