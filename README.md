# 🌱 MWOROZI — AI Crop Health Assistant

**Mworozi** means "farmer" in Kinyarwanda. An AI-powered crop health platform that helps farmers detect diseases, get treatment plans, and track crop recovery — all in their own language.

Built for the **Frontiers GenAI Hackathon** (ALX Kigali, July 28, 2026) — Track 01: Agriculture & BioSystems.

---

## How It Works

```
🧑‍🌾 FARMER → 📷 UPLOAD CROP PHOTO
       ↓
🤖 GEMINI VISION analyzes the image
       ↓
🔍 DISEASE DETECTED → severity + treatment + prevention
       ↓
🌱 SMART TREATMENT PLAN → daily tasks with photo check-ins
       ↓
📊 RECOVERY TRACKING → AI compares before/after photos
```

---

## Features

| Feature | Details |
|---------|---------|
| **📷 Crop Disease Detection** | Upload a photo → Gemini Vision identifies diseases, pests, or nutrient deficiencies |
| **🧪 Demo Samples** | Pre-loaded disease samples (Maize Blight, Cassava Mosaic Virus, Tomato Late Blight) — works without internet |
| **🌍 Multi-Language** | English, Kinyarwanda, Swahili, French — farmers get results in their language |
| **🔊 Voice Playback** | Click "Listen" → browser reads the treatment aloud using built-in Speech Synthesis (no internet needed) |
| **🌱 Smart Treatment Plan** | Auto-generates a 4-step recovery timeline (Day 1 → Day 14) with specific tasks per disease |
| **📷 Progress Check-Ins** | Farmer uploads a new photo at each stage → AI compares before/after |
| **🤖 AI Progress Tracking** | Gemini evaluates if the crop is improving / stable / worsening |
| **📊 Treatment Dashboard** | See all active plans with % recovery score at a glance |
| **📋 Assessment History** | Full SQLite ledger of all diagnoses, always visible |
| **⚙️ Gemini Fallback** | If API is slow or quota exceeded → falls back to pre-loaded demo data (no crash) |
| **🖤 Dark SOC Theme** | Professional dashboard with Bootstrap Icons |
| **📱 Mobile-Friendly** | Streamlit works on phones and tablets |

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | Streamlit 1.60 | Web application framework |
| **AI Vision** | Google Gemini `gemini-flash-latest` | Crop disease detection from photos |
| **AI Progress** | Google Gemini | Before/after image comparison |
| **Voice** | Web Speech API (browser built-in) | Text-to-speech in farmer's language — instant, offline |
| **Database** | SQLite | Assessments, treatment plans, progress tracking |
| **Image Processing** | Pillow | Demo image generation with disease spots |
| **Data** | Pandas | Query and display assessment history |
| **Icons** | Bootstrap Icons 1.11.3 | Dashboard icons |
| **Config** | python-dotenv | Environment variable loading |
| **Auth** | .env file | Gemini API key management |
| **Version Control** | Git + GitHub | Team collaboration |
| **Theme** | Custom CSS (#090a0f / #10b981 / #ef4444) | Dark clinical SOC dashboard |

---

## Project Structure

```
├── app.py                 # Main Streamlit application
├── requirements.txt       # Python dependencies
├── .env                   # Gemini API key (not committed)
├── .env.example           # Environment variable template
├── .gitignore
├── .streamlit/config.toml # Streamlit dark theme config
└── progress/              # Treatment plan check-in photos
```

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set Gemini API key
export GEMINI_API_KEY="your-key-here"
export GEMINI_MODEL="gemini-flash-latest"

# 3. Launch
streamlit run app.py
```

**No API key?** The app works with demo disease samples. Gemini adds real AI analysis.

---

## Demo Samples

Select "Demo Sample" in the sidebar → choose from:

| Sample | Disease | Severity |
|--------|---------|----------|
| 🌽 Maize | Northern Corn Leaf Blight | Moderate |
| 🥔 Cassava | Cassava Mosaic Virus | Severe |
| 🍅 Tomato | Late Blight | Severe |

Each generates a realistic leaf image with disease spots for live demo.

---

## Smart Treatment Plan

When a disease is detected, the app offers a **treatment plan** tailored to that specific disease:

| Stage | Task |
|-------|------|
| **Day 1** | Remove infected parts, apply first treatment |
| **Day 3** | Re-apply treatment, check for new symptoms |
| **Day 7** | Apply organic option, monitor closely |
| **Day 14** | Final assessment — success or re-treat |

At each stage, the farmer uploads a new photo. AI compares it to the original and reports:
- **✅ improving** — treatment working, continue
- **⏸ stable** — no change yet, keep going
- **🔴 worsening** — needs stronger intervention

---

## Voice Support

Click **"Listen"** to hear the treatment plan spoken aloud in the farmer's language. Uses the browser's built-in Speech Synthesis API:
- **English** → English voice
- **Kinyarwanda** → Kinyarwanda voice (if OS supports it)
- **Swahili** → Swahili voice
- **French** → French voice

**No internet needed** for voice — works fully offline.

---

## Limitations

- Gemini API free tier: ~60 req/min → falls back to demo data
- Vision accuracy depends on photo quality (clear, well-lit, focused on affected area)
- Treatment recommendations are AI-generated — verify with local extension officer
- Speech Synthesis quality depends on browser + OS voice support

---

## License

Built for the Frontiers GenAI Hackathon 2026 — ALX Kigali, Rwanda.
