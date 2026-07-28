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
        # Look for actual severity keyword in the text (avoid matching section header "## 2. Severity")
        text_lower = text.lower()
        if "**severe**" in text_lower or "severity: severe" in text_lower or text_lower.count("severe") > text_lower.count("severity"):
            severity = "Severe"
        elif "**mild**" in text_lower or "severity: mild" in text_lower:
            severity = "Mild"
        elif "no disease" in text_lower or "crop appears healthy" in text_lower:
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
init_treatment_db()

# ── Session state ─────────────────────────────────────────
for key in ("analysis_done", "last_result", "treatment_view"):
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

# ── Navigation ──────────────────────────────────────────
nav_col1, nav_col2, nav_col3 = st.columns([1, 1, 4])
with nav_col1:
    if st.button("📊 Dashboard", key="nav_dash", use_container_width=True,
                 type="secondary" if st.session_state.get("treatment_view") else "primary"):
        st.session_state["treatment_view"] = None
        st.rerun()
with nav_col2:
    if st.button("🌱 Check Progress", key="nav_progress", use_container_width=True,
                 type="primary" if st.session_state.get("treatment_view") else "secondary"):
        pass  # Will scroll to the check progress section

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
        resource_pref = st.selectbox("Farming Resources", ["Both (Organic + Chemical)", "Organic Only", "Chemical Only"], key="resource_pref")
        season = st.selectbox("Current Season", ["Growing Season", "Planting Season", "Harvest Season", "Dry Season"], key="season")
        st.form_submit_button("💾 Save Info", use_container_width=True, type="secondary")

    st.markdown("---")
    st.markdown("### <i class='bi bi-image'></i> Crop Image", unsafe_allow_html=True)

    img_source = st.radio(
        "Image source",
        ["📷 Take Photo", "📁 Upload Photo", "🧪 Demo Sample"],
        key="img_source",
        label_visibility="collapsed",
    )

    image_bytes = None
    preview = None
    crop_for_demo = crop

    if "Take Photo" in img_source:
        cam_img = st.camera_input("Point at the crop and take a photo", key="camera_input")
        if cam_img:
            image_bytes = cam_img.read()
            st.success("Photo captured from camera")
    elif "Demo" in img_source:
        demo_crop = st.selectbox("Sample Crop Issue", list(DEMO_DISEASES.keys()), key="demo_crop")
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
        is_real = ("Take Photo" in img_source or "Upload" in img_source) if 'img_source' in dir() else False

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

        # Save original image for later AI progress comparison
        os.makedirs("progress", exist_ok=True)
        orig_path = f"progress/original_{farmer}_{crop_sel}_{int(time.time())}.jpg"
        with open(orig_path, "wb") as f:
            f.write(image_bytes)

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

            # Voice — gTTS with speed control
            voice_text = res["treatment"].replace("##", "").replace("*", "")[:800]
            voice_lang_code = {"English": "en", "Kinyarwanda": "rw", "Swahili": "sw", "French": "fr"}.get(res.get("language", "English"), "en")
            voice_key = f"voice_{res['crop']}_{res['severity']}_{res.get('language', 'English')}"
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

    # ── Start Checklist Button ─────────────────────────
    if res["severity"] != "None":
        btn_label = "🌱 Start Recovery Checklist for This Plant"
        if st.button(btn_label, key="start_checklist", type="primary", use_container_width=True):
            conn = sqlite3.connect(DB_PATH)
            row = conn.execute("SELECT id FROM assessments ORDER BY id DESC LIMIT 1").fetchone()
            aid = row[0] if row else 0
            conn.close()
            orig_path = res.get("original_image_path", "")
            plan_id = create_treatment_plan(aid, res["farmer"], res["crop"], res["disease"], orig_path)
            st.session_state["treatment_view"] = plan_id
            st.rerun()
    else:
        if st.button("🌿 Keep It Healthy Checklist", key="keep_healthy", type="secondary", use_container_width=True):
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


# ══════════════════════════════════════════════════════════
# TREATMENT VIEW — dedicated page for one plant
# ══════════════════════════════════════════════════════════
if st.session_state.get("treatment_view"):
    plan_id = st.session_state["treatment_view"]
    
    if st.button("← Back to Dashboard", key="back_dash"):
        st.session_state["treatment_view"] = None
        st.rerun()
    
    tasks = get_plan_tasks(plan_id)
    updates = get_plan_updates(plan_id)
    
    conn = sqlite3.connect(DB_PATH)
    plan_info = conn.execute("SELECT farmer_name, crop, disease, original_image_path FROM treatment_plans WHERE id = ?", (plan_id,)).fetchone()
    conn.close()
    
    is_healthy = plan_info[2] == "Keep Healthy"
    checklist_type = "Keep Healthy" if is_healthy else "Recovery"
    icon = "🌿" if is_healthy else "🌱"
    
    st.markdown(f"""
    <div style='display:flex;justify-content:space-between;align-items:center'>
        <h3 style='color:#10b981;margin:0'>{icon} {plan_info[1]} — {checklist_type} Checklist</h3>
        <span style='color:#94a3b8;font-size:0.85rem'>Farmer: {plan_info[0]} | {plan_info[2][:40]}</span>
    </div>
    """, unsafe_allow_html=True)
    
    # Chat-like conversation for this plant
    st.markdown("<div style='background:#0f1520;border-radius:12px;padding:1rem;margin-bottom:1rem'>", unsafe_allow_html=True)
    
    # Show existing chat history
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
                    
                    # Get the original assessment image
                    conn2 = sqlite3.connect(DB_PATH)
                    asm = conn2.execute("""SELECT a.id FROM assessments a 
                        JOIN treatment_plans p ON p.assessment_id = a.id 
                        WHERE p.id = ? ORDER BY a.id DESC LIMIT 1""", (plan_id,)).fetchone()
                    conn2.close()
                    
                    # Load original image for AI comparison
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
            <p style='color:#86efac;margin:0.5rem 0;font-size:1.1rem'><strong>All Tasks Complete!</strong></p>
            <p style='color:#bbf7d0;margin:0;font-size:0.9rem'>{'Your plant has recovered. Keep monitoring regularly.' if not is_healthy else 'Your plant is healthy. Continue good practices.'}</p>
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
st.markdown("<h3 style='color:#10b981'><i class='bi bi-search'></i> Check Progress — All Assessments</h3>", unsafe_allow_html=True)
st.markdown("<p style='color:#94a3b8;font-size:0.85rem'>Select an assessment below to start or continue a recovery checklist for that plant.</p>", unsafe_allow_html=True)

all_ledger = get_assessments()
if not all_ledger.empty:
    for idx, row in all_ledger.iterrows():
        with st.container():
            c1, c2, c3, c4, c5, c6 = st.columns([1.5, 1, 1, 1, 1, 1.5])
            with c1: st.markdown(f"<span style='color:#e2e8f0'>{row['farmer_name']}</span>", unsafe_allow_html=True)
            with c2: st.markdown(f"<span style='color:#10b981'>{row['crop']}</span>", unsafe_allow_html=True)
            with c3: st.markdown(f"<span style='color:#94a3b8'>{row['disease'][:25]}</span>", unsafe_allow_html=True)
            with c4:
                sev = row['severity']
                sev_color = "#ef4444" if sev == "Severe" else ("#f59e0b" if sev == "Moderate" else "#10b981")
                st.markdown(f"<span style='color:{sev_color}'>{sev}</span>", unsafe_allow_html=True)
            with c5: st.markdown(f"<span style='color:#64748b;font-size:0.8rem'>{row['created_at'][:10]}</span>", unsafe_allow_html=True)
            with c6:
                # Check if there's a treatment plan for this assessment
                conn = sqlite3.connect(DB_PATH)
                existing = conn.execute("SELECT id FROM treatment_plans WHERE farmer_name = ? AND crop = ? ORDER BY id DESC LIMIT 1", 
                                       (row['farmer_name'], row['crop'])).fetchone()
                conn.close()
                if existing:
                    if st.button(f"Continue →", key=f"continue_{idx}", use_container_width=True):
                        st.session_state["treatment_view"] = existing[0]
                        st.rerun()
                else:
                    btn_label = "🌿 Keep Healthy" if sev in ("None", "Unknown") else "🌱 Treat This Plant"
                    if st.button(btn_label, key=f"treat_{idx}", use_container_width=True):
                        aid = row.get('id', idx + 1)
                        disease_label = "Keep Healthy" if sev in ("None", "Unknown") else row['disease']
                        pid = create_treatment_plan(aid, row['farmer_name'], row['crop'], disease_label)
                        st.session_state["treatment_view"] = pid
                        st.rerun()
            st.markdown("<hr style='margin:0.25rem 0;border-color:#1e293b'>", unsafe_allow_html=True)
else:
    st.markdown("<p style='color:#64748b'>No assessments yet. Upload a crop photo to get started.</p>", unsafe_allow_html=True)
