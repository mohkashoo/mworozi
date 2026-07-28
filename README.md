# MWOROZI -- AI Crop Health Assistant

**Mworozi** ("farmer" in Kinyarwanda) is an AI-powered crop health platform that helps farmers detect diseases, receive structured treatment plans, and track crop recovery through visual progress monitoring. Designed for low-resource agricultural settings in East Africa.

Built for the **Frontiers GenAI Hackathon 2026** -- Track 01: Agriculture & BioSystems. In collaboration with **Google DeepMind**.

---

## Architecture

```
Farmer uploads/takes crop photo -> Gemini Vision analyzes for disease
    -> Returns: disease, severity, treatment, prevention
    -> Start Recovery Checklist or Keep Healthy Checklist
    -> Chat-style treatment view with staged tasks
    -> Each stage: upload follow-up photo -> AI compares before/after
    -> Verdict: improving / stable / worsening
    -> Dashboard tracks recovery across all plants
```

---

## Features

| Feature | Description |
|---------|-------------|
| **Disease Detection** | Upload a photo or take one with the camera. Gemini Vision identifies diseases, pests, or nutrient deficiencies |
| **Three Input Methods** | Camera capture, file upload, or pre-loaded demo samples |
| **Auto-Detect Crop** | Select "Other (let AI detect)" and Gemini identifies the crop type from the photo |
| **Demo Samples** | Pre-loaded disease cases (Maize Blight, Cassava Mosaic Virus, Tomato Late Blight) for offline demonstration |
| **Site-Wide Language Toggle** | Switch the entire UI between English, Kinyarwanda, Swahili, and French -- sidebar, buttons, alerts, headings all translate instantly |
| **Voice Playback** | gTTS reads treatment aloud in the farmer's language with speed control (0.75x, 1x, 1.25x, 1.5x). Kinyarwanda falls back to Swahili voice |
| **Smart Treatment Plans** | Two types: Recovery Checklist (diseased plants) and Keep It Healthy Checklist (disease prevention) |
| **Chat-Style Progress** | Each plant gets a dedicated chat view. Upload photos, add notes, AI replies with analysis |
| **AI Progress Tracking** | Gemini Vision compares original assessment photo against follow-up photos, classifying: improving, stable, or worsening |
| **Check Progress Section** | Lists all assessments as clickable rows. Click any to open its treatment plan or start one |
| **Evaluation Metrics** | AI confidence score, severity level, and seasonal context displayed with every diagnosis |
| **Personalization** | Farmers select resource preference (organic/chemical/both), current season, and location |
| **Assessment Ledger** | Full SQLite database of all diagnoses with farmer, crop, disease, severity, and date |
| **Fallback Mode** | If Gemini quota is exceeded or network is unavailable, the app continues with pre-loaded demo data |
| **Smooth Modern UI** | Inter font, card hover animations, gradient backgrounds, slide-in alerts, glow effects, progress bars |
| **Mobile-Compatible** | Streamlit renders on phones and tablets. Camera capture works on mobile browsers |

---

## Technology Stack

| Component | Technology | Role |
|-----------|-----------|------|
| Frontend | Streamlit 1.60 | Web application framework |
| UI/UX | Custom CSS + Inter font + Bootstrap Icons | Animations, gradients, hover effects, translations |
| AI Vision | Gemini 3.6-flash | Disease detection + auto crop identification from photos |
| AI Comparison | Gemini 3.6-flash | Before/after image analysis for progress tracking |
| Voice | gTTS | Text-to-speech with speed control (0.75x - 1.5x) |
| Database | SQLite + Pandas | Assessments, treatment plans, progress records |
| Image Generation | Pillow | Synthetic diseased leaf images for demo |
| Translation | Built-in dict system | Full site UI in EN, RW, SW, FR |
| Configuration | python-dotenv | Environment variable loading |
| Version Control | Git + GitHub | Team collaboration |

---

## Project Structure

```
.
|-- app.py                 # Application entry point
|-- requirements.txt       # Python dependencies
|-- .env                   # API credentials (not committed)
|-- .env.example           # Environment variable template
|-- .gitignore
|-- .streamlit/
|   |-- config.toml        # Streamlit theme configuration
|-- ONE-PAGER.txt          # Pitch presentation text
|-- ETHICS.md              # Ethics & accessibility brief
|-- progress/              # Assessment images + treatment check-in photos
|-- README.md
```

---

## Quick Start

```bash
pip install -r requirements.txt
export GEMINI_API_KEY="your-key-here"
export GEMINI_MODEL="gemini-3.6-flash"
streamlit run app.py
```

The application functions without an API key using built-in demo data. API access enables live image analysis and AI progress tracking.

---

## Demo Samples

| Crop | Disease | Severity |
|------|---------|----------|
| Maize | Northern Corn Leaf Blight | Moderate |
| Cassava | Cassava Mosaic Virus | Severe |
| Tomato | Late Blight | Severe |

Each generates a synthetic leaf image with disease symptoms for demonstration.

---

## Treatment Plan Stages

| Stage | Task |
|-------|------|
| Day 1 | Remove affected material, apply initial treatment |
| Day 3 | Re-apply treatment, monitor for new symptoms |
| Day 7 | Apply secondary (organic) option, continue monitoring |
| Day 14 | Final assessment: recovery confirmed or requires re-treatment |

Each stage accepts a follow-up photograph. AI compares it to the original assessment image and reports: improving, stable, or worsening.

---

## Keep It Healthy Checklist

| Stage | Task |
|-------|------|
| Week 1 | Water regularly. Check for pests under leaves. Remove weeds |
| Week 2 | Apply organic compost or fertilizer. Monitor for yellowing |
| Week 3 | Check soil moisture. Look for signs of disease or nutrient deficiency |
| Week 4 | Monthly assessment. Rotate crop next season for soil health |

---

## Language Support

| Language | UI | Analysis Response | Voice |
|----------|----|------------------|------|
| English | Yes | Yes | Yes |
| Kinyarwanda | Yes | Yes | Falls back to Swahili (gTTS limitation) |
| Swahili | Yes | Yes | Yes |
| French | Yes | Yes | Yes |

---

## Evaluation Metrics

| Metric | Details |
|--------|---------|
| AI Confidence | Percentage confidence in diagnosis (displayed after every analysis) |
| Severity | Mild / Moderate / Severe -- determines treatment urgency |
| Recovery Rate | Percentage of check-ins marked "improving" vs total |
| Seasonal Context | Planting / Growing / Harvest / Dry -- constrains treatment advice |
| Resource Preference | Organic only / Chemical only / Both -- personalized recommendations |

---

## Bonus Features (Judging Criteria)

| Criterion | Implementation |
|-----------|---------------|
| Human Approval Step | Every treatment plan requires user confirmation before creation |
| Evaluation Metrics | AI confidence, severity, recovery rate displayed on dashboard |
| Personalization with Constraints | Resource preference, season, location, and crop type constrain all recommendations |

---

## Limitations

- Treatment recommendations are AI-generated and should be verified with a local agricultural extension officer
- Diagnostic accuracy depends on image quality (clear, well-lit, focused on affected area)
- Voice playback requires internet on first generation; cached locally for replay
- Kinyarwanda voice falls back to Swahili (gTTS language limitation)
- Gemini API free tier: approximately 60 requests per minute

---

*Frontiers GenAI Hackathon 2026 -- ALX Kigali, Rwanda -- In collaboration with Google DeepMind*
