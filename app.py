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

# Common crops in Rwanda / East Africa
CROPS = [
    "Maize", "Beans", "Cassava", "Sweet Potato", "Irish Potato",
    "Banana", "Coffee", "Tea", "Rice", "Soybean",
    "Tomato", "Cabbage", "Onion", "Sorghum", "Wheat",
]

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
# Custom CSS — dark agri theme
# ---------------------------------------------------------------------------
CSS = """
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
<style>
    .bi { vertical-align: -0.125em; }
    .stApp { background-color: #090a0f; }
    .main > div { padding: 1rem 1.5rem; }

    .card {
        background: #0f1520;
        border: 1px solid #1e293b;
        border-radius: 12px; padding: 1.25rem; margin-bottom: 1rem;
    }
    .card-title {
        font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.08em;
        color: #64748b; margin-bottom: 0.75rem;
    }

    .alert-disease {
        background: linear-gradient(135deg, #450a0a 0%, #7f1d1d 100%);
        border: 1px solid #ef4444; border-radius: 12px;
        padding: 1.25rem 1.5rem; margin-bottom: 1rem;
    }
    .alert-disease h2 { color: #fca5a5; margin: 0 0 0.25rem; font-size: 1.25rem; }
    .alert-disease p  { color: #fecaca; margin: 0; font-size: 0.9rem; }

    .alert-healthy {
        background: linear-gradient(135deg, #052e16 0%, #14532d 100%);
        border: 1px solid #10b981; border-radius: 12px;
        padding: 1.25rem 1.5rem; margin-bottom: 1rem;
    }
    .alert-healthy h2 { color: #86efac; margin: 0 0 0.25rem; font-size: 1.25rem; }
    .alert-healthy p  { color: #bbf7d0; margin: 0; font-size: 0.9rem; }

    .section-label {
        font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.08em;
        color: #64748b; margin: 1.25rem 0 0.5rem; border-bottom: 1px solid #1e293b;
        padding-bottom: 0.3rem;
    }

    [data-testid="stSidebar"] { background-color: #0a0d14; border-right: 1px solid #1e293b; }

    .stTextInput>div>div>input, .stNumberInput>div>div>input, .stTextArea>div>textarea {
        background-color: #131a26 !important; border-color: #1e293b !important;
        color: #e2e8f0 !important;
    }
    .stSelectbox>div>div>select { background-color: #131a26 !important; border-color: #1e293b !important; color: #e2e8f0 !important; }

    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #059669, #10b981) !important;
        border: none !important; color: white !important; font-weight: 600 !important;
    }
    .stButton > button:hover {
        transform: translateY(-1px);
    }

    .stDataFrame { background: transparent !important; }
    .stDataFrame td, .stDataFrame th {
        background-color: #0f1520 !important; color: #cbd5e1 !important;
        border-color: #1e293b !important;
    }

    hr { border-color: #1e293b !important; }
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: #090a0f; }
    ::-webkit-scrollbar-thumb { background: #334155; border-radius: 3px; }
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


def get_assessments() -> pd.DataFrame:
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        df = pd.read_sql_query(
            "SELECT farmer_name, location, crop, disease, severity, created_at "
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
        if "Severe" in text or "severe" in text:
            severity = "Severe"
        elif "Mild" in text or "mild" in text:
            severity = "Mild"
        elif "No disease" in text or "healthy" in text.lower():
            severity = "None"

        # Extract disease name (first line after ## 1.)
        disease = "Unknown"
        for line in text.split("\n"):
            if line.strip().startswith("## 1.") or line.strip().startswith("**Disease") or line.strip().startswith("**Issue"):
                disease = line.split(":", 1)[-1].strip() if ":" in line else line.replace("## 1.", "").replace("**", "").strip()
                break

        return {
            "disease": disease if disease != "Unknown" else text.split("## 1.")[-1].split("\n")[0].strip() if "## 1." in text else "See analysis",
            "severity": severity,
            "treatment": text,
            "error": None,
        }
    except Exception as exc:
        return {"disease": "Analysis failed", "severity": "Unknown", "treatment": "", "error": str(exc)}


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

# ── Session state ─────────────────────────────────────────
for key in ("analysis_done", "last_result"):
    if key not in st.session_state:
        st.session_state[key] = None if key != "analysis_done" else False

# ── CSS ────────────────────────────────────────────────────
st.markdown(CSS, unsafe_allow_html=True)

# ── Title ──────────────────────────────────────────────────
c1, c2 = st.columns([0.08, 0.92])
with c1:
    st.markdown("<h1 style='font-size:2rem;margin:0;color:#10b981'>"
                "<i class='bi bi-tree-fill'></i></h1>", unsafe_allow_html=True)
with c2:
    st.markdown(
        "<h1 style='margin:0;font-size:1.5rem'>MWOROZI</h1>"
        "<p style='margin:0;color:#64748b;font-size:0.85rem'>"
        "<i class='bi bi-cloud-sun'></i> AI Crop Health Assistant  •  "
        "<span style='color:#10b981'><i class='bi bi-globe2'></i> "
        "Rwanda / East Africa</span></p>",
        unsafe_allow_html=True,
    )

st.markdown("---")

# ══════════════════════════════════════════════════════════
# SIDEBAR — Farmer info + crop selection
# ══════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### <i class='bi bi-person-badge'></i> Farmer Info", unsafe_allow_html=True)

    with st.form("farmer_form", clear_on_submit=False):
        farmer_name = st.text_input("Farmer's Name", placeholder="e.g. Jean", key="farmer_name")
        location = st.text_input("Sector / Village", placeholder="e.g. Rulindo", key="location")
        crop = st.selectbox("Crop Type", CROPS, key="crop")
        language = st.selectbox("Response Language", list(LANGUAGES.keys()), key="language")
        st.form_submit_button("💾 Save Info", use_container_width=True, type="secondary")

    st.markdown("---")
    st.markdown("### <i class='bi bi-image'></i> Crop Image", unsafe_allow_html=True)

    img_source = st.radio(
        "Image source",
        ["📷 Upload Photo", "🧪 Demo Sample"],
        key="img_source",
        label_visibility="collapsed",
    )

    image_bytes = None
    preview = None
    crop_for_demo = crop

    if "🧪" in img_source:
        # Simulated images — use colored placeholder + overlay text
        demo_crop = st.selectbox("Sample Crop Issue", list(DEMO_DISEASES.keys()), key="demo_crop")
        crop_for_demo = demo_crop

        # Create a visual placeholder image
        from PIL import Image, ImageDraw, ImageFont, ImageFilter
        import io as pil_io

        img = Image.new("RGB", (600, 400), (34, 139, 34))
        draw = ImageDraw.Draw(img)
        # Draw leaf-like shape
        draw.ellipse([100, 100, 500, 300], fill=(50, 180, 50))
        # Draw disease spots
        for _ in range(15):
            x = np.random.randint(150, 450)
            y = np.random.randint(130, 270)
            draw.ellipse([x-8, y-8, x+8, y+8], fill=(139, 90, 43))
            draw.ellipse([x-4, y-4, x+4, y+4], fill=(101, 67, 33))

        # Add text
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

    else:
        uploaded = st.file_uploader(
            "Upload crop photo", type=["jpg", "jpeg", "png", "webp"],
            key="uploaded_img",
        )
        if uploaded:
            image_bytes = uploaded.read()

    st.markdown("---")

    analyze_btn = st.button(
        "🔍 Analyze Crop Health",
        type="primary",
        use_container_width=True,
    )

    if GEMINI_AVAILABLE:
        st.markdown("<span style='color:#10b981'><i class='bi bi-cpu'></i> Gemini AI enabled</span>", unsafe_allow_html=True)
    else:
        st.markdown("<span style='color:#f59e0b'><i class='bi bi-cpu'></i> Gemini unavailable — using demo data</span>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# MAIN AREA
# ══════════════════════════════════════════════════════════

if analyze_btn:
    farmer = st.session_state.get("farmer_name", "").strip()
    loc = st.session_state.get("location", "").strip()
    crop_sel = st.session_state.get("crop", "Maize")
    lang = st.session_state.get("language", "English")

    if not farmer:
        st.error("Please enter the farmer's name.")
    elif image_bytes is None:
        st.error("Please upload a crop photo or select a demo sample.")
    else:
        with st.spinner("Analyzing crop image with AI…"):
            result = get_analysis(image_bytes, crop_for_demo if 'crop_for_demo' in dir() else crop_sel, lang)

        if result.get("error"):
            st.warning(f"Gemini analysis had an issue: {result['error']}. Showing best available data.")

        # Check if it's a demo image or real
        is_real = "📷" in img_source if 'img_source' in dir() else False

        sev = result.get("severity", "Unknown")
        disease = result.get("disease", "See analysis")
        treatment = result.get("treatment", "")

        # Save to DB
        try:
            save_assessment({
                "farmer_name": farmer,
                "location": loc,
                "crop": crop_sel,
                "disease": disease[:100],
                "severity": sev,
                "treatment": treatment[:500],
                "language": lang,
            })
        except Exception:
            pass

        # Store in session for display
        st.session_state["last_result"] = {
            "disease": disease,
            "severity": sev,
            "treatment": treatment,
            "crop": crop_sel,
            "farmer": farmer,
            "location": loc,
            "language": lang,
            "is_real": is_real,
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
            <h2><i class='bi bi-exclamation-triangle-fill'></i> Severe Disease Detected</h2>
            <p>Crop: <strong>{res['crop']}</strong>  •  
            Issue: <strong>{res['disease'][:80]}</strong>  •  
            Severity: <strong>SEVERE</strong> — Immediate action required</p>
        </div>
        """, unsafe_allow_html=True)
    elif res["severity"] == "Moderate":
        st.markdown(f"""
        <div class="alert-disease" style="background:linear-gradient(135deg,#422006 0%,#713f12 100%);border-color:#f59e0b">
            <h2 style="color:#fde68a"><i class='bi bi-exclamation-circle-fill'></i> Moderate Issue Detected</h2>
            <p style="color:#fef3c7">Crop: <strong>{res['crop']}</strong>  •  
            Issue: <strong>{res['disease'][:80]}</strong>  •  
            Severity: <strong>MODERATE</strong> — Treat within the week</p>
        </div>
        """, unsafe_allow_html=True)
    elif res["severity"] == "Mild":
        st.markdown(f"""
        <div class="alert-healthy" style="background:linear-gradient(135deg,#0c4a6e 0%,#075985 100%);border-color:#3b82f6">
            <h2 style="color:#93c5fd"><i class='bi bi-info-circle-fill'></i> Mild Issue — Monitor</h2>
            <p style="color:#dbeafe">Crop: <strong>{res['crop']}</strong>  •  
            Issue: <strong>{res['disease'][:80]}</strong>  •  
            Severity: <strong>MILD</strong> — Monitor and apply preventive measures</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="alert-healthy">
            <h2><i class='bi bi-check-circle-fill'></i> Crop Appears Healthy</h2>
            <p>Crop: <strong>{res['crop']}</strong>  •  
            No disease detected. Continue routine care.</p>
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
        """, unsafe_allow_html=True)

    with col_result:
        st.markdown("<div class='card'>"
                    "<div class='card-title'><i class='bi bi-clipboard2-pulse'></i> Crop Health Analysis</div>",
                    unsafe_allow_html=True)

        if res["treatment"]:
            st.markdown(res["treatment"])
        else:
            st.markdown("*No analysis available. Please try again with a clearer image.*")

        st.markdown("</div>", unsafe_allow_html=True)

    # ── Disclaimer ────────────────────────────────────
    st.markdown("""
    <div style='margin-top:1rem;padding:0.75rem;background:#1e293b33;
                border-radius:8px;border-left:3px solid #10b981'>
        <p style='margin:0;color:#94a3b8;font-size:0.85rem'>
        <i class='bi bi-info-circle-fill'></i> This analysis is AI-generated and should be verified 
        with a local agricultural extension officer. Treatment recommendations are based on common 
        East African farming practices.</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Assessment ledger ─────────────────────────────
    st.markdown("<div class='card'><div class='card-title'>"
                "<i class='bi bi-database'></i> Assessment History</div>", unsafe_allow_html=True)
    ledger = get_assessments()
    if not ledger.empty:
        ledger.columns = ["Farmer", "Location", "Crop", "Issue", "Severity", "Date"]
        st.dataframe(ledger, use_container_width=True, hide_index=True)
    else:
        st.markdown("<span style='color:#64748b'><i class='bi bi-database'></i> No assessments yet.</span>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

else:
    # ── Empty state ───────────────────────────────────
    st.markdown("""
    <div style='text-align:center;padding:4rem 2rem'>
        <p style='font-size:3.5rem;margin:0;color:#10b981'><i class='bi bi-tree-fill'></i></p>
        <h3 style='color:#64748b;margin:0.5rem 0'>Welcome to Mworozi</h3>
        <p style='color:#475569;max-width:480px;margin:0 auto'>
        Upload a photo of your crop to detect diseases, get treatment recommendations, 
        and receive prevention advice — all in your language.
        </p>
    </div>
    """, unsafe_allow_html=True)
